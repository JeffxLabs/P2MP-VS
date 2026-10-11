#!/usr/bin/env python3
"""Switch BlueStacks instances around a VS capture."""
import os
import shlex
import signal
import subprocess
import tempfile
import time
from contextlib import contextmanager


BLUESTACKS_APP = "/Applications/BlueStacks.app"
BLUESTACKS_BIN = f"{BLUESTACKS_APP}/Contents/MacOS/BlueStacks"
GAME_PACKAGE = "com.zroute.global"


def running_instances():
    """Return BlueStacks instance names and the pid of each running process."""
    out = subprocess.run(["ps", "-axo", "pid=,args="], check=True,
                         capture_output=True, text=True).stdout
    instances = {}
    for line in out.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2:
            continue
        try:
            pid = int(fields[0])
            argv = shlex.split(fields[1])
        except ValueError:
            continue
        if not argv or argv[0] != BLUESTACKS_BIN:
            continue
        for i, arg in enumerate(argv[1:], 1):
            if arg == "--instance" and i + 1 < len(argv):
                instances[argv[i + 1]] = pid
                break
            if arg.startswith("--instance="):
                instances[arg.split("=", 1)[1]] = pid
                break
    return instances


def _instance_pid(name, pid):
    return running_instances().get(name) == pid


def _wait_for_instance_exit(name, pid, timeout):
    deadline = time.monotonic() + timeout
    while _instance_pid(name, pid):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(1, remaining))
    return True


def quit_instance(name, log=print, timeout=40):
    """Ask an instance to quit, then force it if it does not stop in time."""
    pid = running_instances().get(name)
    if pid is None:
        log(f"BlueStacks instance {name} is not running.")
        return

    log(f"Quitting BlueStacks instance {name} (pid {pid}) ...")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    if _wait_for_instance_exit(name, pid, timeout):
        return

    log(f"BlueStacks instance {name} did not quit; sending SIGKILL.")
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    if not _wait_for_instance_exit(name, pid, max(5, timeout)):
        raise RuntimeError(f"BlueStacks instance {name} (pid {pid}) did not exit after SIGKILL")


def launch_instance(name, log=print):
    log(f"Launching BlueStacks instance {name} ...")
    subprocess.run(["open", "-n", "-a", BLUESTACKS_APP, "--args", "--instance", name], check=True)


def wait_for_adb(adb, serial, log=print, timeout=180):
    """Connect to an emulator and wait for Android to finish booting."""
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(f"Timed out waiting for Android on {serial} to boot")
        try:
            subprocess.run([adb, "connect", serial], capture_output=True, text=True,
                           timeout=min(10, remaining), check=False)
            result = subprocess.run([adb, "-s", serial, "shell", "getprop", "sys.boot_completed"],
                                    capture_output=True, text=True, timeout=min(10, remaining), check=False)
            if result.returncode == 0 and result.stdout.strip() == "1":
                log(f"Android is ready on {serial}.")
                return
        except subprocess.TimeoutExpired:
            pass
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(2, remaining))


def start_game(adb, serial):
    subprocess.run([adb, "-s", serial, "shell", "monkey", "-p", GAME_PACKAGE,
                    "-c", "android.intent.category.LAUNCHER", "1"], check=True, capture_output=True)


def wait_for_city(dev, log=print, timeout=300):
    """Wait for the game's city HUD, dismissing the exit dialog and other pop-ups."""
    # Imported lazily because capture_all uses this module for its instance context.
    from capture_all import centre, find

    started = time.monotonic()
    deadline = started + timeout
    last_back = None
    while time.monotonic() < deadline:
        items = dev.read(dev.shot("boot"))
        cancel = find(items, r"^Cancel$")
        if cancel and find(items, r"(exit|quit)"):
            dev.tap(*centre(cancel))
            log("Dismissed the game exit dialog.")
        elif find(items, r"^Alliance$") and (find(items, r"Mail$") or find(items, r"^Bag$")):
            log("Game is in the city view.")
            return

        now = time.monotonic()
        if now - started >= 60 and (last_back is None or now - last_back >= 10):
            dev.back()
            last_back = now
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(5, remaining))
    raise RuntimeError("Timed out waiting for the game city view")


def _restore_instance(instance, restore_instance, restore_serial, adb, log, was_running):
    errors = []

    def attempt(label, action):
        try:
            action()
        except Exception as exc:
            errors.append(exc)
            log(f"WARNING: {label} failed ({exc})")

    def launch_and_wait():
        launch_instance(restore_instance, log)
        wait_for_adb(adb, restore_serial, log)
        start_game(adb, restore_serial)
        from capture_all import Device
        with tempfile.TemporaryDirectory(prefix="bluestacks-switch-") as shots_dir:
            dev = Device(adb, restore_serial, shots_dir)
            try:
                wait_for_city(dev, log)
            finally:
                dev.close()

    attempt(f"quitting BlueStacks instance {instance}", lambda: quit_instance(instance, log))
    if not was_running:
        return errors

    # The old forwards can point at the instance that was just stopped.
    try:
        subprocess.run([adb, "-s", restore_serial, "forward", "--remove-all"],
                       capture_output=True, text=True, check=False)
    except Exception:
        pass
    attempt(f"restoring BlueStacks instance {restore_instance}", launch_and_wait)
    return errors


@contextmanager
def switched_instance(cfg, adb, log=print):
    """Use the configured instance, restoring the previously running one on exit.

    The caller supplies ``serial`` alongside the profile's switch settings so a
    command-line device override is respected.
    """
    instance = cfg["instance"]
    restore_instance = cfg["restore_instance"]
    restore_serial = cfg["restore_serial"]
    serial = cfg["serial"]

    running = running_instances()
    restore_was_running = restore_instance in running
    target_was_running = instance in running
    leave_target_running = target_was_running and not restore_was_running

    original_error = None
    try:
        if restore_was_running:
            quit_instance(restore_instance, log)
        if not target_was_running:
            launch_instance(instance, log)
        wait_for_adb(adb, serial, log)
        if not leave_target_running:
            start_game(adb, serial)
        yield
    except BaseException as exc:
        original_error = exc
        raise
    finally:
        if not leave_target_running:
            errors = _restore_instance(instance, restore_instance, restore_serial, adb, log,
                                       restore_was_running)
            if errors and original_error is None:
                raise errors[0]

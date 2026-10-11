import os
import sys
import types
import unittest
from unittest import mock


PIPELINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

import bluestacks_switch


class RunningInstancesTests(unittest.TestCase):
    def test_parses_blue_stacks_instance_processes(self):
        output = """\
  101 /Applications/BlueStacks.app/Contents/MacOS/BlueStacks --instance Tiramisu64_1
  202 /Applications/BlueStacks.app/Contents/MacOS/BlueStacks --instance=Tiramisu64
  303 /Applications/BlueStacks.app/Contents/MacOS/BlueStacksHelper --instance ignored
  404 /usr/bin/python3 --instance ignored
"""
        with mock.patch.object(bluestacks_switch.subprocess, "run",
                               return_value=types.SimpleNamespace(stdout=output)) as run:
            self.assertEqual(bluestacks_switch.running_instances(), {
                "Tiramisu64_1": 101,
                "Tiramisu64": 202,
            })
        run.assert_called_once_with(["ps", "-axo", "pid=,args="], check=True,
                                    capture_output=True, text=True)


class SwitchedInstanceTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "instance": "Tiramisu64",
            "restore_instance": "Tiramisu64_1",
            "restore_serial": "127.0.0.1:5565",
            "serial": "127.0.0.1:5555",
        }
        self.events = []
        self.log = lambda message: self.events.append(("log", message))

    def _device_module(self):
        events = self.events

        class Device:
            def __init__(self, adb, serial, shots_dir):
                self.serial = serial
                events.append(("device-open", serial))

            def close(self):
                events.append(("device-close", self.serial))

        module = types.ModuleType("capture_all")
        module.Device = Device
        return module

    def test_restores_running_instance_after_body_exception(self):
        self.events.clear()
        forward = ["/mock/adb", "-s", "127.0.0.1:5565", "forward", "--remove-all"]
        with mock.patch.dict(sys.modules, {"capture_all": self._device_module()}), \
                mock.patch.object(bluestacks_switch, "running_instances",
                                  return_value={"Tiramisu64_1": 123}), \
                mock.patch.object(bluestacks_switch, "quit_instance",
                                  side_effect=lambda name, log: self.events.append(("quit", name))), \
                mock.patch.object(bluestacks_switch, "launch_instance",
                                  side_effect=lambda name, log: self.events.append(("launch", name))), \
                mock.patch.object(bluestacks_switch, "wait_for_adb",
                                  side_effect=lambda adb, serial, log: self.events.append(("adb-ready", serial))), \
                mock.patch.object(bluestacks_switch, "start_game",
                                  side_effect=lambda adb, serial: self.events.append(("game-start", serial))), \
                mock.patch.object(bluestacks_switch, "wait_for_city",
                                  side_effect=lambda dev, log: self.events.append(("city", dev.serial))), \
                mock.patch.object(bluestacks_switch.subprocess, "run",
                                  side_effect=lambda args, **kwargs: self.events.append(("forward", args))):
            with self.assertRaisesRegex(ValueError, "capture failed"):
                with bluestacks_switch.switched_instance(self.cfg, "/mock/adb", self.log):
                    self.events.append(("body", None))
                    raise ValueError("capture failed")

        self.assertEqual([event[0] for event in self.events if event[0] != "log"], [
            "quit", "launch", "adb-ready", "game-start", "body", "quit", "forward",
            "launch", "adb-ready", "game-start", "device-open", "city", "device-close",
        ])
        self.assertEqual([event for event in self.events if event[0] in ("quit", "launch")], [
            ("quit", "Tiramisu64_1"),
            ("launch", "Tiramisu64"),
            ("quit", "Tiramisu64"),
            ("launch", "Tiramisu64_1"),
        ])
        self.assertIn(("forward", forward), self.events)
        self.assertIn(("city", "127.0.0.1:5565"), self.events)

    def test_already_on_target_only_ensures_adb_and_leaves_it_running(self):
        self.events.clear()
        with mock.patch.object(bluestacks_switch, "running_instances",
                               return_value={"Tiramisu64": 456}), \
                mock.patch.object(bluestacks_switch, "wait_for_adb",
                                  side_effect=lambda adb, serial, log: self.events.append(("adb-ready", serial))), \
                mock.patch.object(bluestacks_switch, "quit_instance") as quit_instance, \
                mock.patch.object(bluestacks_switch, "launch_instance") as launch_instance, \
                mock.patch.object(bluestacks_switch, "start_game") as start_game:
            with bluestacks_switch.switched_instance(self.cfg, "/mock/adb", self.log):
                self.events.append(("body", None))

        self.assertEqual(self.events, [
            ("adb-ready", "127.0.0.1:5555"),
            ("body", None),
        ])
        quit_instance.assert_not_called()
        launch_instance.assert_not_called()
        start_game.assert_not_called()


if __name__ == "__main__":
    unittest.main()

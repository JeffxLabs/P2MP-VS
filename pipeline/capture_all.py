#!/usr/bin/env python3
"""
Alliance Competition (VS) ranking capture for Z Route: Redemption.

Hands-off flow:
  1. Navigate by OCR: back out of whatever is open -> VS icon (right-hand side of the city/map HUD)
     -> RANKINGS (bottom of the Alliance Competition page).
  2. For each tab in order MON, TUE, WED, THUR, FRI, SAT, This Week: tap it and confirm it is the
     highlighted tab (pixel check), rewind to rank 1 (verified), then scroll down the whole list with
     continuous capture (screenshots taken back to back while the list scrolls). Every frame must
     overlap the previous one by rank number; on a gap the list is scrolled back and re-read. The pinned own-rank row under the list is never read as a list row.
  3. Every rank is read on several frames and voted on (points exactly, names on their letter/digit
     core). Ranks that are missing, read only once, disagree, break the descending points order or
     repeat a player are revisited and re-read (repair pass).
  4. Tabs that are still changing (today's day tab and This Week) are checked for movement during the
     scan (one player at two ranks, one rank read as two players or two point values); if the list moved
     it is scanned again and the scans are merged by player (highest points = latest), then re-ranked,
     so a player who moves during the scan is neither lost nor counted twice.
  5. Writes data/weeks/<week>/{mon..sat,week}.json, capture_qa.json and capture.json, then rebuilds
     the analytics and the site bundle. Exits non-zero if anything is unresolved.

Usage:
  python3 pipeline/capture_all.py                         # P1MP profile, week ending this Saturday
  python3 pipeline/capture_all.py --profile p2mp          # other account (pauses Apparatchik)
  python3 pipeline/capture_all.py --tabs sat,week --no-navigate
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import queue
import sys
import threading
import time
import unicodedata
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

from aliases import apply as alias_name
from screenshots import archive as archive_screenshots
from vs_frame_parser import parse_frame, is_rank_list, to_px, VIEW_TOP, VIEW_TOP_WEEK

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PIPELINE_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
WEEKS_DIR = os.path.join(DATA_DIR, "weeks")
OCR_SRC = os.path.join(PIPELINE_DIR, "vision_ocr.swift")
OCR_BIN = os.path.join(PIPELINE_DIR, "vision_ocr")
PROBE_SRC = os.path.join(PIPELINE_DIR, "pixel_probe.swift")
PROBE_BIN = os.path.join(PIPELINE_DIR, "pixel_probe")
CACHE_DIR = os.path.expanduser("~/Library/Caches/s117-vs-captures")

# Game server time ("State Time"): days roll over at 00:00 UTC-2
SERVER_TZ = timezone(timedelta(hours=-2), "server (UTC-2)")

DAY_TABS = ["mon", "tue", "wed", "thu", "fri", "sat"]
TAB_LABEL = {"mon": "MON", "tue": "TUE", "wed": "WED", "thu": "THUR", "fri": "FRI", "sat": "SAT", "week": "This Week"}
DAY_TAB_X = {"mon": 90, "tue": 270, "wed": 450, "thu": 630, "fri": 810, "sat": 990}
DAY_TAB_Y = 228
TODAY_TAB = (270, 130)
WEEK_TAB = (810, 130)

SWIPE_MS = 800
SCROLL_FROM, SCROLL_TO, SCROLL_MS = 1450, 350, 1200   # continuous scan: ~5 rows/s, ~2.7 reads per rank
BOTTOM_STILL_SEC = 3.0
SETTLE_SEC = 0.9
ROW_DRAG_PX = 130     # approx. drag px per row for seeking (closed loop, so only a starting estimate)


def log(msg=""):
    print(msg, flush=True)


# ---------------------------------------------------------------- device / OCR helpers

class Device:
    def __init__(self, adb, serial, shots_dir):
        self.adb, self.serial, self.shots_dir = adb, serial, shots_dir
        self.n = 0
        os.makedirs(shots_dir, exist_ok=True)
        self.ocr = subprocess.Popen([OCR_BIN, "--stdin"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True, bufsize=1)

    def sh(self, *args):
        subprocess.run([self.adb, "-s", self.serial, "shell", *args], check=True)

    def tap(self, x, y, wait=1.2):
        self.sh("input", "tap", str(int(x)), str(int(y)))
        time.sleep(wait)

    def back(self, wait=1.5):
        self.sh("input", "keyevent", "4")
        time.sleep(wait)

    def drag(self, y0, y1, ms=SWIPE_MS, x=540):
        self.sh("input", "swipe", str(x), str(int(y0)), str(x), str(int(y1)), str(int(ms)))

    def shot(self, label):
        self.n += 1
        path = os.path.join(self.shots_dir, f"{self.n:05d}_{label}.png")
        with open(path, "wb") as f:
            subprocess.run([self.adb, "-s", self.serial, "exec-out", "screencap", "-p"], stdout=f, check=True)
        return path

    def read(self, path):
        self.ocr.stdin.write(path + "\n")
        self.ocr.stdin.flush()
        line = self.ocr.stdout.readline()
        if not line:
            raise RuntimeError("OCR worker stopped")
        return json.loads(line)

    def probe(self, path, rects):
        out = subprocess.check_output([PROBE_BIN, path] + [",".join(map(str, r)) for r in rects], text=True)
        return [tuple(int(v) for v in l.split()) for l in out.strip().splitlines()]

    def close(self):
        try:
            self.ocr.stdin.close()
            self.ocr.terminate()
        except Exception:
            pass


def compile_tools():
    for src, binp in ((OCR_SRC, OCR_BIN), (PROBE_SRC, PROBE_BIN)):
        if not os.path.exists(binp) or os.path.getmtime(src) > os.path.getmtime(binp):
            log(f"Compiling {os.path.basename(src)} ...")
            subprocess.run(["swiftc", "-O", src, "-o", binp], check=True)


# ---------------------------------------------------------------- navigation

def centre(it):
    b = to_px(it)
    return b["cx"], b["cy"]


def find(items, pattern, region=None):
    """region = (x0, x1, y0, y1) in pixels, top-left origin."""
    rx = re.compile(pattern, re.I)
    for it in items:
        if not rx.search(it["text"].strip()):
            continue
        cx, cy = centre(it)
        if region and not (region[0] <= cx <= region[1] and region[2] <= cy <= region[3]):
            continue
        return it
    return None


def is_competition_page(items):
    return bool(find(items, r"ALLIANCE\s*COMPETITION") and find(items, r"^RANKINGS$"))


def vs_icon_candidates(items):
    """The VS icon's label OCRs as VS / Vs / US / Us; its countdown timer sits right under it."""
    out = []
    lab = find(items, r"^(V|U)\s?[S5]$", region=(860, 1080, 300, 1500))
    if lab:
        out.append(centre(lab))
    for it in items:
        if re.fullmatch(r"\d{2}:\d{2}:\d{2}", it["text"].strip()):
            cx, cy = centre(it)
            if cx > 900 and 300 < cy < 1500:
                out.append((cx, cy - 60))
    return out


def return_to_city(dev, max_back=8):
    """Back out to the city view (the Apparatchik guard expects it after a capture)."""
    for _ in range(max_back):
        items = dev.read(dev.shot("to_city"))
        cancel = find(items, r"^Cancel$")
        if cancel and find(items, r"(exit|quit)"):
            dev.tap(*centre(cancel))
            return True
        if find(items, r"^Alliance$") and (find(items, r"Mail$") or find(items, r"^Bag$")):
            log("  back in the city view")
            return True
        dev.back()
    log("  WARNING: could not confirm the city view")
    return False


def go_to_rankings(dev, max_back=10):
    log("Navigating: VS icon > RANKINGS ...")
    tried = set()
    for step in range(max_back + 6):
        p = dev.shot("nav")
        items = dev.read(p)
        if is_rank_list(items):
            log("  on the VS RANK list")
            return
        if is_competition_page(items):
            it = find(items, r"^RANKINGS$")
            x, y = centre(it)
            log(f"  tap RANKINGS at ({x:.0f},{y:.0f})")
            dev.tap(x, y, wait=2.5)
            continue
        cancel = find(items, r"^Cancel$")
        if cancel and find(items, r"(exit|quit)"):
            dev.tap(*centre(cancel))
            continue
        cands = [c for c in vs_icon_candidates(items) if (round(c[0], -1), round(c[1], -1)) not in tried]
        if cands:
            x, y = cands[0]
            tried.add((round(x, -1), round(y, -1)))
            log(f"  tap VS icon at ({x:.0f},{y:.0f})")
            dev.tap(x, y, wait=2.5)
            p2 = dev.shot("nav_after_vs")
            items2 = dev.read(p2)
            if not (is_competition_page(items2) or is_rank_list(items2)):
                log("  that was not the VS icon; backing out")
                dev.back()
            continue
        dev.back()
    raise RuntimeError("Could not reach the VS RANK list")


# ---------------------------------------------------------------- tabs

def selected_tabs(dev, path):
    """Which top tab (today/week) and which day tab is highlighted, from the tab background colour."""
    rects = [(30, 100, 120, 15), (600, 100, 120, 15)] + [(DAY_TAB_X[d] - 70, 190, 140, 15) for d in DAY_TABS]
    vals = dev.probe(path, rects)
    bright = [v[0] for v in vals]
    top = "today" if bright[0] > bright[1] + 40 else ("week" if bright[1] > bright[0] + 40 else None)
    days = bright[2:]
    best = max(range(6), key=lambda i: days[i])
    others = sorted(days)[-2]
    day = DAY_TABS[best] if days[best] > others + 30 else None
    return top, day


def open_tab(dev, tab, tries=4):
    for attempt in range(tries):
        if tab == "week":
            dev.tap(*WEEK_TAB, wait=1.5)
        else:
            dev.tap(*TODAY_TAB, wait=1.0)
            dev.tap(DAY_TAB_X[tab], DAY_TAB_Y, wait=1.5)
        p = dev.shot(f"{tab}_tab")
        top, day = selected_tabs(dev, p)
        items = dev.read(p)
        if is_rank_list(items) and ((tab == "week" and top == "week") or (tab != "week" and top == "today" and day == tab)):
            log(f"  {TAB_LABEL[tab]} tab selected")
            return
        log(f"  tab check failed (top={top}, day={day}); retrying")
        if not is_rank_list(items):
            go_to_rankings(dev)
    raise RuntimeError(f"Could not select the {TAB_LABEL[tab]} tab")


# ---------------------------------------------------------------- frames

def read_frame(dev, label, view_top, at_top=False):
    p = dev.shot(label)
    items = dev.read(p)
    if not is_rank_list(items):
        # A pop-up or notification covering the header: wait and re-read once
        time.sleep(1.5)
        p = dev.shot(label + "_retry")
        items = dev.read(p)
        if not is_rank_list(items):
            raise RuntimeError(f"Lost the RANK list ({p})")
    res = parse_frame(items, at_top_hint=at_top, view_top=view_top)
    return res, p


def _at_top(res, view_top):
    return not res.rows or (res.offset == 1 and res.rows[0]["rank"] == 1
                            and abs(res.rows[0]["y"] - (view_top + 93)) < 15)


def rewind_to_top(dev, view_top, tab, reopen=True):
    """Scroll back to rank 1 with closed-loop drags (~13 rows each). Very fast flings are ignored by
    some BlueStacks instances, so drags last 300 ms. Fallback: leave and re-enter the RANK page,
    which opens the tab at rank 1."""
    res, p = read_frame(dev, f"{tab}_top", view_top, at_top=True)
    last = None
    stuck = 0
    for _ in range(30):
        if _at_top(res, view_top):
            return res
        off = res.offset or 999
        for _ in range(max(1, min(6, off // 12 + 1))):
            dev.drag(450, 1750, ms=300)
            time.sleep(0.1)
        time.sleep(0.9)
        res, p = read_frame(dev, f"{tab}_top", view_top, at_top=True)
        stuck = stuck + 1 if res.offset == last else 0
        last = res.offset
        if stuck >= 2:
            break
    if _at_top(res, view_top):
        return res
    if reopen:
        log(f"  list did not scroll back to rank 1 (at {res.offset}); re-entering the RANK page")
        dev.back(wait=2.0)
        go_to_rankings(dev)
        open_tab(dev, tab)
        return rewind_to_top(dev, view_top, tab, reopen=False)
    raise RuntimeError("Could not verify the top of the list (rank 1)")


def name_key(name):
    return "".join(ch for ch in unicodedata.normalize("NFKC", name or "") if ch.isalnum()).casefold()


# Characters this game font renders (near) identically, so OCR legitimately flips between them
_LOOKALIKE = str.maketrans({"l": "i", "1": "i", "|": "i", "і": "i", "ı": "i", "0": "o", "о": "o",
                            "а": "a", "е": "e", "р": "p", "с": "c", "у": "y", "х": "x", "к": "k",
                            "м": "m", "т": "t", "н": "h", "в": "b", "ѕ": "s"})


def loose_key(name):
    """name_key with look-alike characters folded together (l/I/1, O/0, Cyrillic/Latin twins)."""
    return name_key(name).translate(_LOOKALIKE)


class Store:
    def __init__(self):
        self.by_rank = {}
        self.frames = []

    def add(self, res, path, pass_no):
        rec = {"frame": os.path.basename(path), "pass": pass_no, "offset": res.offset,
               "digit_conflicts": res.digit_conflicts, "t": time.time(), "rows": []}
        if res.digit_conflicts:
            # Fitted rank disagrees with a digit on screen: trust nothing from this frame
            rec["rejected"] = True
            self.frames.append(rec)
            return
        for r in res.rows:
            o = dict(r)
            o["frame"] = rec["frame"]
            o["t"] = rec["t"]
            rec["rows"].append(o)
            self.by_rank.setdefault(r["rank"], []).append(o)
        self.frames.append(rec)

    def merge(self):
        return [merge_rank(rk, obs) for rk, obs in sorted(self.by_rank.items())]

    def frame_ranks(self):
        """{frame file: complete ranks read on it} for the screenshot archive."""
        return {f["frame"]: [r["rank"] for r in f["rows"] if r["complete"]]
                for f in self.frames if not f.get("rejected")}


def vote_name(names):
    if not names:
        return "", 0.0
    keys = Counter(name_key(n) for n in names)
    best_key, n = keys.most_common(1)[0]
    agree = [x for x in names if name_key(x) == best_key]
    if len(agree) / len(names) <= 0.5:
        def close(a, b):
            return difflib.SequenceMatcher(None, name_key(a), name_key(b)).ratio() >= 0.8
        best = max(names, key=lambda a: sum(close(a, b) for b in names))
        agree = [x for x in names if close(best, x)]
    return Counter(agree).most_common(1)[0][0], len(agree) / len(names)


def merge_rank(rank, obs):
    for o in obs:
        o["player"] = alias_name(o["player"], o.get("alliance", ""))
    clean = [o for o in obs if o["complete"]]
    pool = clean or obs
    pts = Counter(o["points"] for o in pool if o["points"] is not None)
    points, p_n = (pts.most_common(1)[0] if pts else (None, 0))
    names = [o["player"] for o in pool if o["player"]]
    name, _ = vote_name(names)
    # Tie between letter/digit cores: the most confident reading wins, then the one nearest mid-list
    cores = Counter(loose_key(n) for n in names)
    if cores and list(cores.values()).count(max(cores.values())) > 1:
        best = max((o for o in pool if o["player"]), key=lambda o: (cores[loose_key(o["player"])], o.get("name_conf", 0), -abs(o["y"] - 928)))
        name = best["player"]
    name_agree = (sum(1 for n in names if loose_key(n) == loose_key(name)) / len(names)) if names else 0.0
    ally = Counter(o["alliance"] for o in pool if o["alliance"])
    return {"rank": rank, "player": name, "alliance_raw": ally.most_common(1)[0][0] if ally else "",
            "points": points, "t": max(o["t"] for o in pool),
            "diag": {"n_obs": len(obs), "n_clean": len(clean),
                     "points_agree": round(p_n / max(sum(pts.values()), 1), 3),
                     "name_agree": round(name_agree, 3),
                     "points_reads": dict(Counter(str(o["points"]) for o in pool)),
                     "name_reads": dict(Counter(o["player"] for o in pool if o["player"]))}}


def problems(merged, live=False):
    out = {}
    by = {m["rank"]: m for m in merged}
    top = max(by) if by else 0
    for r in range(1, top + 1):
        m = by.get(r)
        if m is None:
            out[r] = "missing"
            continue
        d = m["diag"]
        if d["n_clean"] == 0:
            out[r] = "no complete read"
        elif d["n_clean"] < 2:
            out[r] = "read once"
        elif not live and (d["points_agree"] < 0.75 or (d["points_agree"] < 1.0 and d["n_clean"] < 3)):
            # 3+ clean reads with a 75%+ majority: a stray truncated read (e.g. '1,280') is outvoted
            out[r] = "points disagree"
        elif not live and (d["name_agree"] < 0.6 or (d["name_agree"] < 1.0 and d["n_clean"] < 3)):
            # A clear majority over 3+ clean reads is accepted: the minority reads are OCR noise on
            # decorative characters, and re-reading the same pixels cannot settle them
            out[r] = "name disagree"
    if not live:
        seq = [by[r] for r in sorted(by)]
        for a, b in zip(seq, seq[1:]):
            if a["points"] is not None and b["points"] is not None and b["points"] > a["points"]:
                out.setdefault(a["rank"], "order")
                out.setdefault(b["rank"], "order")
        seen = {}
        for m in seq:
            k = loose_key(m["player"])
            if k and k in seen:
                out.setdefault(m["rank"], f"same player as rank {seen[k]}")
                out.setdefault(seen[k], f"same player as rank {m['rank']}")
            seen.setdefault(k, m["rank"])
    return out


def _continuous_segment(dev, tab, store, pass_no, view_top, seen_max, seg, max_sec=240):
    """Swipe continuously while a second thread takes screenshots back to back; every frame is
    read by OCR as it arrives. screencap grabs one composited frame, so frames are sharp while the
    list moves. Returns (seen_max, reason) with reason 'bottom' or ('gap', after_rank)."""
    frames = queue.Queue()
    stop = threading.Event()

    def mover():
        while not stop.is_set():
            dev.drag(SCROLL_FROM, SCROLL_TO, ms=SCROLL_MS)

    def capper():
        i = 0
        while not stop.is_set():
            frames.put(dev.shot(f"{tab}_p{pass_no}_s{seg:02d}_{i:03d}"))
            i += 1
        frames.put(None)

    threads = [threading.Thread(target=mover, daemon=True), threading.Thread(target=capper, daemon=True)]
    for t in threads:
        t.start()
    t0 = time.time()
    last_move_t = time.time()
    last_top = None
    reason = None
    n = 0
    try:
        while True:
            path = frames.get()
            if path is None:
                break
            n += 1
            items = dev.read(path)
            if not is_rank_list(items):
                raise RuntimeError(f"Lost the RANK list ({path})")
            res = parse_frame(items, view_top=view_top)
            store.add(res, path, pass_no)
            in_view = [r["rank"] for r in res.rows if not r["cut"]]
            if not in_view or res.digit_conflicts:
                continue
            if min(in_view) > seen_max + 1:
                reason = ("gap", seen_max)
                break
            comp = res.complete_ranks()
            top = max(comp) if comp else max(in_view)
            if top > seen_max:
                seen_max = top
                last_move_t = time.time()   # progress = a new highest rank (the list bounces at its end)
            sys.stdout.write(f"\r  [{TAB_LABEL[tab]} pass {pass_no}] ranks {min(in_view)}-{max(in_view)}  "
                             f"highest {seen_max}  {n} frames  {seen_max / max(time.time() - t0, 0.1):.1f} ranks/s ")
            sys.stdout.flush()
            if time.time() - last_move_t > BOTTOM_STILL_SEC:
                reason = "bottom"
                break
            if time.time() - t0 > max_sec:
                raise RuntimeError("Scan segment took too long")
    finally:
        stop.set()
        for t in threads:
            t.join(timeout=10)
        # read whatever was captured after the stop decision (it can only add observations)
        while True:
            try:
                path = frames.get_nowait()
            except queue.Empty:
                break
            if path is None:
                continue
            items = dev.read(path)
            if is_rank_list(items):
                res = parse_frame(items, view_top=view_top)
                store.add(res, path, pass_no)
                comp = res.complete_ranks()
                in_view = [r["rank"] for r in res.rows if not r["cut"]]
                if comp and not res.digit_conflicts and in_view and min(in_view) <= seen_max + 1:
                    seen_max = max(seen_max, max(comp))
    return seen_max, reason


def scan(dev, tab, store, pass_no, view_top):
    """Rank 1 to the bottom of the list with continuous capture. A gap (the list lazy-loads more
    rows near its end and can jump) is closed by seeking back to it with stop-and-read moves; the
    bottom is accepted only when the list stays still through a second, separate check."""
    res = rewind_to_top(dev, view_top, tab)
    store.add(res, os.path.join(dev.shots_dir, "top"), pass_no)
    if not res.rows:
        log("  list is empty")
        return 0
    # Medal rows 1-3 leave the screen first: give them two more still reads
    for k in range(2):
        time.sleep(0.2)
        r2, p2 = read_frame(dev, f"{tab}_p{pass_no}_top{k}", view_top, at_top=True)
        store.add(r2, p2, pass_no)
    seen_max = max(res.complete_ranks() or [0])
    t0 = time.time()
    for seg in range(30):
        seen_max, reason = _continuous_segment(dev, tab, store, pass_no, view_top, seen_max, seg)
        if reason == "bottom":
            # Confirm: the list may have been lazy-loading. Wait, push again, re-read.
            time.sleep(1.5)
            for _ in range(2):
                dev.drag(SCROLL_FROM, SCROLL_TO, ms=600)
            time.sleep(1.2)
            r3, p3 = read_frame(dev, f"{tab}_p{pass_no}_bottom", view_top)
            store.add(r3, p3, pass_no)
            comp = r3.complete_ranks()
            if comp and max(comp) <= seen_max:
                log(f"\n  bottom of the list at rank {seen_max} ({time.time() - t0:.0f}s)")
                return seen_max
            if comp and min(comp) <= seen_max + 1:
                seen_max = max(comp)
                continue
            reason = ("gap", seen_max)
        if isinstance(reason, tuple):
            log(f"\n  gap after rank {reason[1]}; seeking back")
            if not seek(dev, tab, view_top, reason[1] + 1):
                raise RuntimeError(f"Could not return to rank {reason[1] + 1}")
            for k in range(2):
                r4, p4 = read_frame(dev, f"{tab}_p{pass_no}_gap{seg}_{k}", view_top)
                store.add(r4, p4, pass_no)
                comp = r4.complete_ranks()
                if comp and min(comp) <= seen_max + 1:
                    seen_max = max(seen_max, max(comp))
    raise RuntimeError("Too many scan segments")


def visible(dev, tab, view_top, label):
    res, p = read_frame(dev, label, view_top)
    return res, p


def seek(dev, tab, view_top, target, max_moves=40):
    for move in range(max_moves):
        res, p = visible(dev, tab, view_top, f"{tab}_seek{target}_{move:02d}")
        comp = res.complete_ranks()
        if not comp:
            time.sleep(0.8)
            continue
        lo, hi = min(comp), max(comp)
        if lo < target < hi or (target <= 2 and lo == 1) or (lo <= target <= hi and (target == lo == 1)):
            return True
        if lo <= target <= hi:
            # visible but at the edge: nudge it towards the middle
            delta = 1 if target == hi else -1
        else:
            delta = target - (lo + hi) / 2
        if abs(delta) > 30:
            for _ in range(2 if abs(delta) > 80 else 1):
                if delta > 0:
                    dev.drag(1450, 450, ms=300)
                else:
                    dev.drag(450, 1450, ms=300)
                time.sleep(0.2)
            time.sleep(1.4)
        else:
            px = int(min(1000, max(160, abs(delta) * ROW_DRAG_PX)))
            if delta > 0:
                dev.drag(1400, 1400 - px, ms=900)
            else:
                dev.drag(500, 500 + px, ms=900)
            time.sleep(SETTLE_SEC)
    return False


def repair(dev, tab, store, view_top, live, rounds=3):
    fixed = set()
    name_tried = set()
    for rnd in range(1, rounds + 1):
        probs = problems(store.merge(), live=live)
        # Re-reading a name OCR reads differently every time (decorative glyphs) cannot settle it:
        # try such a rank once, then leave it to data/aliases.json
        probs = {r: w for r, w in probs.items() if not (w == "name disagree" and r in name_tried)}
        name_tried.update(r for r, w in probs.items() if w == "name disagree")
        if not probs:
            break
        log(f"  repair round {rnd}: {len(probs)} rank(s): " +
            ", ".join(f"{r} ({why})" for r, why in list(sorted(probs.items()))[:12]))
        covered = set()
        for rank in sorted(probs):
            if rank in covered:
                continue
            fixed.add(rank)
            if not seek(dev, tab, view_top, rank):
                log(f"    could not bring rank {rank} on screen")
                continue
            for shot in range(3):
                res, p = read_frame(dev, f"{tab}_repair{rnd}_{rank}_{shot}", view_top)
                store.add(res, p, 99)
                covered.update(r["rank"] for r in res.rows if r["complete"])
                time.sleep(0.35)
    return problems(store.merge(), live=live)


# ---------------------------------------------------------------- alliance tags

def split_alliance(raw, profile, known_tags):
    s = (raw or "").strip()
    if not s:
        return "", ""
    body = s.lstrip("[(").strip()
    for v in profile["tag_variants"]:
        if body.upper().startswith(v.upper()):
            return profile["home_tag"], profile["home_name"]
    m = re.match(r"^\[?([^\[\]\s]{2,6})[\]\)|]\s*(.*)$", s)
    if m:
        return m.group(1), m.group(2).strip()
    for tag, name in known_tags.items():
        if body.upper().startswith(tag.upper()):
            return tag, name
    return "", s


def finalize(merged, profile):
    tags = Counter()
    names = {}
    for m in merged:
        mm = re.match(r"^\[?([^\[\]\s]{2,6})\]\s*(.+)$", m["alliance_raw"] or "")
        if mm:
            tags[mm.group(1)] += 1
            names.setdefault(mm.group(1), Counter())[mm.group(2).strip()] += 1
    known = {t: names[t].most_common(1)[0][0] for t in tags}
    out = []
    for m in merged:
        tag, name = split_alliance(m["alliance_raw"], profile, known)
        if tag in known and tag != profile["home_tag"]:
            name = known[tag]
        out.append({"rank": m["rank"], "player": m["player"],
                    "alliance": f"[{tag}] {name}" if tag else name,
                    "alliance_tag": tag, "alliance_name": name, "points": m["points"]})
    return out


def live_movement(merged):
    """Signs that a live list changed while it was being scanned: the same player at two ranks,
    one rank read as different players, or one rank read with different points."""
    signs = []
    seen = {}
    for m in merged:
        k = loose_key(m["player"])
        if k and k in seen:
            signs.append(f"{m['player']} at ranks {seen[k]} and {m['rank']}")
        seen.setdefault(k, m["rank"])
        # A real move shows two different players (or point values) each read on 2+ frames at the
        # same rank; one-off variants ('Zlaya' / 'ZlayaR') are OCR noise, not movement.
        # cluster readings by similarity, so decoration variants ('TurkishWolfOC*' / 'TurkishWolfOC*O',
        # '+SINt' / '†SIN†') count as one player
        clusters = []
        for n, c in m["diag"]["name_reads"].items():
            k = loose_key(n)
            for cl in clusters:
                if difflib.SequenceMatcher(None, k, cl[0]).ratio() >= 0.7:
                    cl[1] += c
                    break
            else:
                clusters.append([k, c])
        if sum(1 for _, c in clusters if c >= 2) > 1:
            signs.append(f"rank {m['rank']} read as {sorted(m['diag']['name_reads'])}")
        if sum(1 for c in m["diag"]["points_reads"].values() if c >= 2) > 1:
            signs.append(f"rank {m['rank']} points {sorted(m['diag']['points_reads'])}")
    return signs


def merge_live_passes(pass_lists):
    """Union of several scans of a list that changed while scanning: one entry per player
    (latest = highest points), re-ranked by points."""
    players = {}
    for lst in pass_lists:
        for m in lst:
            k = loose_key(m["player"]) or f"#rank{m['rank']}"
            cur = players.get(k)
            if cur is None or (m["points"] or 0) > (cur["points"] or 0):
                players[k] = dict(m)
    # Fold near-identical keys (an OCR variant of the same name, same alliance, close points)
    keys = sorted(players, key=lambda k: -(players[k]["points"] or 0))
    for i, a in enumerate(keys):
        if a not in players:
            continue
        for b in keys[i + 1:]:
            if b not in players:
                continue
            pa, pb = players[a], players[b]
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            same_pts = pa["points"] is not None and pa["points"] == pb["points"]
            # Same player read two ways: near-identical names, or identical points with a similar name
            if (pa["alliance_raw"][:5] == pb["alliance_raw"][:5] and ratio >= 0.85) or (same_pts and ratio >= 0.5):
                keep, drop = (a, b) if (pa["points"] or 0) >= (pb["points"] or 0) else (b, a)
                players[keep]["diag"]["folded"] = players[drop]["player"]
                del players[drop]
    ranked = sorted(players.values(), key=lambda m: -(m["points"] or 0))
    for i, m in enumerate(ranked, 1):
        m["rank"] = i
    return ranked


# ---------------------------------------------------------------- main

def week_id_for(now_server):
    """Weeks are named by their Saturday (server date)."""
    d = now_server.date()
    return (d + timedelta(days=(5 - d.weekday()) % 7)).isoformat()


def live_tabs_for(now_server, week_id):
    sat = datetime.fromisoformat(week_id).date()
    today = now_server.date()
    if today > sat or today.weekday() == 6:
        return set()
    return {DAY_TABS[today.weekday()], "week"}


def capture_tab(dev, tab, live, profile):
    view_top = VIEW_TOP_WEEK if tab == "week" else VIEW_TOP
    log(f"\n[{TAB_LABEL[tab]}]{' (live: rescanned if it changes during the scan)' if live else ''}")
    open_tab(dev, tab)
    passes = 2 if live else 1
    pass_merged = []
    qa = {"tab": tab, "live": live, "passes": []}
    frame_ranks = {}
    for pn in range(1, passes + 1):
        if pn == 2:
            moved = live_movement(pass_merged[0])
            if not moved:
                log("  live list did not change during the scan; one pass is enough")
                break
            qa["movement_seen"] = moved[:20]
            log(f"  list changed during the scan ({len(moved)} sign(s), e.g. {moved[:3]}); scanning again")
        store = Store()
        bottom = scan(dev, tab, store, pn, view_top)
        unresolved = repair(dev, tab, store, view_top, live) if bottom else {}
        merged = store.merge()
        pass_merged.append(merged)
        frame_ranks.update(store.frame_ranks())
        qa["passes"].append({"pass": pn, "bottom_rank": bottom, "ranks": len(merged),
                             "frames": len(store.frames),
                             "rejected_frames": sum(1 for f in store.frames if f.get("rejected")),
                             "unresolved": {str(k): v for k, v in unresolved.items()},
                             "finished_at": datetime.now(SERVER_TZ).isoformat(timespec="seconds")})
    if live and len(pass_merged) > 1:
        merged = merge_live_passes(pass_merged)
        qa["live_union_players"] = len(merged)
        qa["live_last_pass_bottom"] = qa["passes"][-1]["bottom_rank"]
        if len(merged) != qa["passes"][-1]["bottom_rank"]:
            qa["live_note"] = (f"{len(merged)} players across scans vs {qa['passes'][-1]['bottom_rank']} rows "
                               f"in the last scan")
    else:
        merged = pass_merged[-1]
    qa["unresolved"] = problems(merged, live=False) if not live else \
        {r: v for r, v in problems(merged, live=True).items()}
    qa["unresolved"] = {str(k): v for k, v in qa["unresolved"].items()}
    qa["diagnostics"] = [{"rank": m["rank"], "player": m["player"], **m["diag"]} for m in merged]
    records = finalize(merged, profile)
    return records, qa, frame_ranks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="p1mp")
    ap.add_argument("--device")
    ap.add_argument("--week", help="week id (its Saturday, YYYY-MM-DD); default: this week")
    ap.add_argument("--tabs", default="mon,tue,wed,thu,fri,sat,week")
    ap.add_argument("--no-navigate", action="store_true")
    ap.add_argument("--no-build", action="store_true", help="do not rebuild analytics/site bundle")
    ap.add_argument("--allow-incomplete", action="store_true")
    ap.add_argument("--no-screenshots", action="store_true", help="do not archive compressed frames into the repo")
    ap.add_argument("--opp-server", help="opponent server number, e.g. 119 (kept in data/weeks/<week>/meta.json)")
    ap.add_argument("--opp-tag", help="opponent alliance tag, e.g. JKRS (helps when OCR mangles the brackets)")
    ap.add_argument("--opp-name", help="opponent alliance name, e.g. JOKERS")
    args = ap.parse_args()

    profile = json.load(open(os.path.join(PIPELINE_DIR, "profiles", f"{args.profile}.json")))
    serial = args.device or profile["device"]
    now = datetime.now(SERVER_TZ)
    week_id = args.week or week_id_for(now)
    live = live_tabs_for(now, week_id)
    tabs = [t.strip() for t in args.tabs.split(",") if t.strip()]
    week_dir = os.path.join(WEEKS_DIR, week_id)
    os.makedirs(week_dir, exist_ok=True)

    if args.opp_server or args.opp_tag:
        meta_path = os.path.join(week_dir, "meta.json")
        meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
        if args.opp_server:
            meta["opponent_server"] = f"S{args.opp_server.lstrip('Ss')}"
        if args.opp_tag:
            meta["opponent_tag"], meta["opponent_name"] = args.opp_tag, args.opp_name or ""
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    compile_tools()
    adb = shutil.which("adb") or "/opt/homebrew/bin/adb"
    subprocess.run([adb, "connect", serial], capture_output=True)
    run_stamp = now.strftime("%Y%m%d-%H%M%S")
    shots = os.path.join(CACHE_DIR, profile["id"], week_id, run_stamp)
    dev = Device(adb, serial, shots)
    log(f"=== VS capture: profile {profile['id']} ({profile['account']}, [{profile['home_tag']}]) on {serial}, "
        f"week {week_id}, server time {now:%a %H:%M} ===")
    log(f"Live tabs (still changing): {', '.join(TAB_LABEL[t] for t in DAY_TABS + ['week'] if t in live) or 'none'}")
    log(f"Frames: {shots}")

    if profile.get("apparatchik"):
        from apparatchik_control import monitoring_paused
        guard = monitoring_paused(minutes=60, log=log)
    else:
        guard = nullcontext()

    started = datetime.now(SERVER_TZ)
    qa_path = os.path.join(week_dir, "capture_qa.json")
    all_qa = json.load(open(qa_path)) if os.path.exists(qa_path) else {"tabs": {}}
    all_qa.update({"week": week_id, "profile": profile["id"], "device": serial})
    failed = False
    with guard:
        try:
            if not args.no_navigate:
                go_to_rankings(dev)
            for tab in tabs:
                records, qa, frame_ranks = capture_tab(dev, tab, tab in live, profile)
                qa["captured_at"] = datetime.now(SERVER_TZ).isoformat(timespec="seconds")
                all_qa["tabs"][tab] = qa
                with open(os.path.join(week_dir, f"{tab}.json"), "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2, ensure_ascii=False)
                with open(qa_path, "w", encoding="utf-8") as f:
                    json.dump(all_qa, f, indent=2, ensure_ascii=False)
                n_home = sum(1 for r in records if r["alliance_tag"] == profile["home_tag"])
                log(f"  saved {len(records)} rows ({n_home} [{profile['home_tag']}]); "
                    f"unresolved: {qa['unresolved'] or 'none'}")
                if qa["unresolved"]:
                    failed = True
                if not args.no_screenshots:
                    kept, total, size = archive_screenshots(shots, week_id, tab, frame_ranks)
                    log(f"  archived {kept} of {total} frames ({size / 1e6:.1f} MB) to "
                        f"data/weeks/{week_id}/screenshots/{tab}/ (every rank on 2+ frames)")
        finally:
            if profile.get("return_to_city"):
                try:
                    return_to_city(dev)
                except Exception as e:
                    log(f"  WARNING: return to city failed ({e})")
            dev.close()

    ended = datetime.now(SERVER_TZ)
    all_qa["ok"] = all(not t.get("unresolved") for t in all_qa["tabs"].values())
    with open(qa_path, "w", encoding="utf-8") as f:
        json.dump(all_qa, f, indent=2, ensure_ascii=False)
    cap_path = os.path.join(week_dir, "capture.json")
    cap = json.load(open(cap_path)) if os.path.exists(cap_path) else {"runs": []}
    cap["runs"].append({"started_server": started.isoformat(timespec="seconds"),
                        "ended_server": ended.isoformat(timespec="seconds"),
                        "started_utc": started.astimezone(timezone.utc).isoformat(timespec="seconds"),
                        "tabs": tabs, "live_tabs": sorted(live & set(tabs)), "device": serial,
                        "profile": profile["id"], "frames": dev.n, "frames_dir": shots})
    cap["live_tabs"] = sorted(live)
    cap["last_capture_server"] = ended.isoformat(timespec="seconds")
    with open(cap_path, "w", encoding="utf-8") as f:
        json.dump(cap, f, indent=2, ensure_ascii=False)
    log(f"\nCapture finished in {(ended - started).total_seconds() / 60:.1f} min; QA: "
        f"{'all ranks resolved' if not failed else 'UNRESOLVED ranks, see capture_qa.json'}")

    if not args.no_build:
        subprocess.run([sys.executable, os.path.join(PIPELINE_DIR, "build_week.py"), week_id,
                        "--profile", profile["id"]], check=False)
    sys.exit(1 if failed and not args.allow_incomplete else 0)


if __name__ == "__main__":
    main()

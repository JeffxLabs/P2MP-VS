#!/usr/bin/env python3
"""
Frame parser for the Alliance Competition (VS) "RANK" list in Z Route: Redemption.

Screen layout (1080x1920 portrait, pixel coordinates measured from the top-left):

  RANK header / Today | This Week / MON TUE WED THUR FRI SAT / Rank Player Points
  list viewport   y ~345 .. ~1512   rows are 184 px apart, each ~166 px tall
                  rank column x < 200 (ranks 1-3 are medal icons with no readable digit)
                  player name at x ~340 (row centre - 30 px), alliance "[TAG]Name" below it (+33 px)
                  points right-aligned at x > 790 (row centre)
  pinned row      y ~1520 .. ~1685   the viewing player's own rank: NOT part of the list
  footer          "My Alliance" checkbox

Rank numbers come from the slot geometry: every row centre in a frame shares the same phase
modulo the 184 px pitch, so the slot index of each row is exact and the frame's rank offset is
the median of (OCR rank digit - slot index) over the rows whose digit was read.
"""
import re
import statistics
from typing import Any, Dict, List, Optional

W, H = 1080, 1920
PITCH = 184.0          # px between row centres
ROW_HALF = 83          # half the row box height
VIEW_TOP = 345         # first pixel of the list viewport on the Today tabs (below the column header)
VIEW_TOP_WEEK = 257    # This Week has no day-tab row, so its list starts 88 px higher
VIEW_BOT = 1512        # last pixel of the list viewport (the pinned own-rank row starts below)
EDGE_TOL = 6           # a row whose box sticks out of the viewport by more than this is cut off

BANNER_RX = re.compile(r"\s*\b(Congrat\w*|Commander|Warzone|reaches|has obtained|obtained)\b.*$", re.I)

RANK_X_MAX = 200
NAME_X_MIN = 315
POINTS_X_MIN = 760


def to_px(it: Dict[str, Any]) -> Dict[str, Any]:
    """Vision boxes are normalized with a bottom-left origin; convert to top-left pixels."""
    x0 = it["x"] * W
    x1 = (it["x"] + it["width"]) * W
    top = (1 - it["y"] - it["height"]) * H
    bot = (1 - it["y"]) * H
    return {"text": it["text"].strip(), "conf": it.get("confidence", 1.0),
            "x0": x0, "x1": x1, "cx": (x0 + x1) / 2, "top": top, "bot": bot,
            "cy": (top + bot) / 2, "h": bot - top}


def is_rank_list(items: List[Dict[str, Any]]) -> bool:
    texts = {it["text"].strip() for it in items}
    return "RANK" in texts and ("Player" in texts or "Points" in texts) and \
        any(t in texts for t in ("Today", "This Week"))


def _digits(text: str) -> str:
    return re.sub(r"[^\d]", "", text)


def parse_points(text: str) -> Optional[int]:
    """'34,239,618' -> 34239618. Vision sometimes reads ',' as '.'; group structure is checked so
    a dropped or doubled digit (wrong group length) is rejected instead of silently accepted."""
    t = text.replace(" ", "").replace(".", ",")
    if not re.fullmatch(r"\d{1,3}(,\d{3})*", t):
        d = _digits(text)
        # Accept plain digit runs only when short (no separators expected below 1,000)
        return int(d) if d and len(d) <= 3 and d == text.strip() else None
    return int(t.replace(",", ""))


class Row(dict):
    pass


class FrameResult:
    def __init__(self, rows, offset, phase, rank_digits, digit_conflicts):
        self.rows = rows
        self.offset = offset
        self.phase = phase
        self.rank_digits = rank_digits            # number of rows whose rank digit was read
        self.digit_conflicts = digit_conflicts    # rows whose digit disagrees with the fitted rank

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)

    def complete_ranks(self):
        return sorted(r["rank"] for r in self.rows if r["complete"])


def parse_frame(items: List[Dict[str, Any]], at_top_hint: bool = False, view_top: int = VIEW_TOP) -> FrameResult:
    VIEW_TOP = view_top
    boxes = [to_px(it) for it in items]
    in_view = [b for b in boxes if VIEW_TOP - 10 <= b["cy"] <= VIEW_BOT + 4]

    pts_boxes, rank_boxes, mid_boxes = [], [], []
    for b in in_view:
        t = b["text"]
        if b["x0"] >= POINTS_X_MIN and _digits(t):
            p = parse_points(t)
            if p is not None:
                pts_boxes.append((b, p))
        elif b["x1"] <= RANK_X_MAX + 20 and t.isdigit():
            rank_boxes.append((b, int(t)))
        elif b["x0"] >= NAME_X_MIN - 20 and b["x0"] < POINTS_X_MIN - 40:
            # Scrolling system announcements ("Congratulations, Commander ...") cross the list
            t2 = BANNER_RX.split(t)[0].strip()
            if t2:
                b["text"] = t2
                mid_boxes.append(b)

    # Row centres: points (row centre) and rank digits (row centre) anchor each slot.
    anchors = [b["cy"] for b, _ in pts_boxes] + [b["cy"] for b, _ in rank_boxes]
    # Name (centre - 30) and alliance (centre + 33) lines also anchor rows whose points are cut off.
    if not anchors:
        return FrameResult([], None, None, 0, 0)

    # Phase of the row grid (row centre y modulo PITCH), robust to a few odd boxes.
    phases = sorted(a % PITCH for a in anchors)
    ref = statistics.median(phases)
    # unwrap around the reference to avoid the modulo seam
    unwrapped = [p if abs(p - ref) <= PITCH / 2 else (p - PITCH if p > ref else p + PITCH) for p in phases]
    phase = statistics.median(unwrapped) % PITCH

    # Every slot whose centre lies in (or overlapping) the viewport
    first_k = int((VIEW_TOP - ROW_HALF - phase) // PITCH)
    slots = []
    k = first_k
    while True:
        cy = phase + k * PITCH
        if cy - ROW_HALF > VIEW_BOT:
            break
        if cy + ROW_HALF >= VIEW_TOP:
            slots.append(cy)
        k += 1

    def slot_of(y, tol):
        best, bd = None, tol
        for i, cy in enumerate(slots):
            d = abs(y - cy)
            if d <= bd:
                best, bd = i, d
        return best

    slot_pts: Dict[int, List] = {}
    for b, p in pts_boxes:
        i = slot_of(b["cy"], 40)
        if i is not None:
            slot_pts.setdefault(i, []).append((b, p))
    slot_rank: Dict[int, int] = {}
    for b, r in rank_boxes:
        i = slot_of(b["cy"], 40)
        if i is not None:
            slot_rank[i] = r
    slot_mid: Dict[int, List] = {}
    for b in mid_boxes:
        i = slot_of(b["cy"], PITCH / 2 - 8)
        if i is not None:
            slot_mid.setdefault(i, []).append(b)

    # Rank offset: rank = offset + slot index
    cands = [r - i for i, r in slot_rank.items()]
    offset = None
    conflicts = 0
    if cands:
        offset = int(statistics.median_low(sorted(cands)))
        conflicts = sum(1 for c in cands if c != offset)
    elif at_top_hint:
        offset = None  # resolved below from the medal layout
    # Ranks 1-3 have medal icons, no digits. When the very top of the list is showing the first
    # slot's box sits right below the column header: first full slot is rank 1.
    if offset is None:
        first_full = next((i for i, cy in enumerate(slots) if cy - ROW_HALF >= VIEW_TOP - EDGE_TOL), None)
        if at_top_hint and first_full is not None:
            offset = 1 - first_full
    if offset is None:
        return FrameResult([], None, phase, 0, 0)

    rows = []
    for i, cy in enumerate(slots):
        rank = offset + i
        if rank < 1:
            continue
        box_top, box_bot = cy - ROW_HALF, cy + ROW_HALF
        cut = box_top < VIEW_TOP - EDGE_TOL or box_bot > VIEW_BOT + EDGE_TOL
        mids = sorted(slot_mid.get(i, []), key=lambda b: b["cy"])
        name_line = [b for b in mids if b["cy"] < cy - 5]
        ally_line = [b for b in mids if b["cy"] >= cy - 5]
        # Lines that look like an alliance tag are alliance lines wherever they sit
        # The avatar's small "VS" badge (x ~300-330) is sometimes read into the name line
        name_line = [b for b in name_line if not (b["x1"] < 336 and len(b["text"]) <= 3)]
        name_txt = " ".join(b["text"] for b in sorted(name_line, key=lambda b: b["x0"])).strip()
        if name_line and min(b["x0"] for b in name_line) < 333:
            name_txt = re.sub(r"^[VUY][SE5$]\s+", "", name_txt)
        ally_txt = " ".join(b["text"] for b in sorted(ally_line, key=lambda b: b["x0"])).strip()
        if name_txt.startswith("[") and not ally_txt:
            name_txt, ally_txt = "", name_txt
        pts = slot_pts.get(i)
        points = pts[0][1] if pts else None
        name_conf = min((b["conf"] for b in name_line), default=0.0)
        pts_conf = pts[0][0]["conf"] if pts else 0.0
        if not mids and points is None and i not in slot_rank:
            continue
        complete = (not cut) and bool(name_txt) and points is not None
        rows.append(Row(rank=rank, player=name_txt, alliance=ally_txt, points=points,
                        y=round(cy, 1), complete=complete, cut=cut,
                        rank_digit=slot_rank.get(i), name_conf=round(name_conf, 3),
                        pts_conf=round(pts_conf, 3)))
    return FrameResult(rows, offset, phase, len(slot_rank), conflicts)

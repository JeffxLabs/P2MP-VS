#!/usr/bin/env python3
"""
Archive capture frames into the repo as compressed evidence.

Full-size PNG frames stay in the local cache (~/Library/Caches/s117-vs-captures/...). From the frames that
fed the data, the archive keeps the smallest set in which every rank is fully visible at least twice (or
as often as it was read), plus every repair re-read, so each published row can be checked against two
screenshots. They are compressed to 720 px wide WebP (~40 KB each, still legible) into
data/weeks/<week>/screenshots/<tab>/, and index.json lists each archived frame with its capture time
(server time, UTC-2) and the ranks it shows.

Re-archiving a tab replaces that tab's folder, so it always matches the published data.

Called by capture_all.py / reprocess.py with the per-frame rank lists from their observation store.
"""
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
WEEKS_DIR = os.path.join(os.path.dirname(PIPELINE_DIR), "data", "weeks")
SERVER_TZ = timezone(timedelta(hours=-2), "server (UTC-2)")
TABS = ["mon", "tue", "wed", "thu", "fri", "sat", "week"]
WIDTH = 720
QUALITY = 70


def _compress(src, dest):
    if shutil.which("cwebp"):
        subprocess.run(["cwebp", "-quiet", "-q", str(QUALITY), "-resize", str(WIDTH), "0", src, "-o", dest],
                       check=True)
    else:  # fallback: JPEG via sips
        dest = dest[:-5] + ".jpg"
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(QUALITY),
                        "--resampleWidth", str(WIDTH), src, "--out", dest], check=True, stdout=subprocess.DEVNULL)
    return dest


def select_frames(frame_ranks, min_views=2):
    """Greedy cover: fewest frames such that every rank appears in min(min_views, times read) of them.
    Repair re-reads are always kept."""
    need = {}
    for ranks in frame_ranks.values():
        for r in ranks:
            need[r] = need.get(r, 0) + 1
    need = {r: min(min_views, n) for r, n in need.items()}
    chosen = [f for f in frame_ranks if "_repair" in f]
    for f in chosen:
        for r in frame_ranks[f]:
            need[r] -= 1
    left = {f: set(rs) for f, rs in frame_ranks.items() if f not in chosen}
    while any(v > 0 for v in need.values()) and left:
        f = max(left, key=lambda k: (sum(1 for r in left[k] if need.get(r, 0) > 0), -len(k), k))
        gain = [r for r in left.pop(f) if need.get(r, 0) > 0]
        if not gain:
            break
        chosen.append(f)
        for r in gain:
            need[r] -= 1
    return sorted(chosen)


def archive(frames_dirs, week_id, tab, frame_ranks):
    """frames_dirs: folder(s) holding the PNGs; frame_ranks: {frame basename: [complete ranks]}."""
    if isinstance(frames_dirs, str):
        frames_dirs = [frames_dirs]
    shots_root = os.path.join(WEEKS_DIR, week_id, "screenshots")
    index_path = os.path.join(shots_root, "index.json")
    index = {}
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
    frame_ranks = {f: sorted(set(r)) for f, r in frame_ranks.items() if r}
    chosen = select_frames(frame_ranks)
    out_dir = os.path.join(shots_root, tab)
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir)
    jobs = []
    for name in chosen:
        src = next((os.path.join(d, name) for d in frames_dirs if os.path.exists(os.path.join(d, name))), None)
        if src:
            jobs.append((name, src, os.path.join(out_dir, name[:-4] + ".webp")))
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        written = list(ex.map(lambda j: (j[0], _compress(j[1], j[2]),
                                         datetime.fromtimestamp(os.stat(j[1]).st_mtime, SERVER_TZ)), jobs))
    index[tab] = [{"file": os.path.relpath(dest, shots_root), "ranks": [min(frame_ranks[n]), max(frame_ranks[n])],
                   "taken_at_server": t.isoformat(timespec="seconds")} for n, dest, t in written]
    index[tab].sort(key=lambda e: e["file"])
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1, ensure_ascii=False)
    size = sum(os.path.getsize(os.path.join(out_dir, x)) for x in os.listdir(out_dir))
    return len(written), len(frame_ranks), size

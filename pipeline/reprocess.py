#!/usr/bin/env python3
"""
Rebuild a tab's leaderboard offline from saved capture frames (no emulator needed).

Every frame is self-describing (rank numbers are fitted from the rank digits on screen), so all frames
of a tab — scan, top, gap, seek and repair reads — are parsed again with the current parser and voted
on together. Use it after a parser fix, or to audit a published board against its frames.

Usage:
  python3 pipeline/reprocess.py 2026-10-03 mon <frames_dir> [<frames_dir> ...] [--profile p1mp] [--dry-run]
Live tabs (today and This Week while the day runs) should be recaptured instead: their frames span a
changing list.
"""
import argparse
import glob
import json
import os
import re
import subprocess

from capture_all import (OCR_BIN, PIPELINE_DIR, WEEKS_DIR, Store, finalize, problems, compile_tools)
from screenshots import archive
from vs_frame_parser import parse_frame, is_rank_list, VIEW_TOP, VIEW_TOP_WEEK


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("week")
    ap.add_argument("tab")
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--profile", default="p1mp")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--archive-only", action="store_true",
                    help="only (re)build the screenshot archive for this tab (works for live tabs too)")
    args = ap.parse_args()
    compile_tools()
    profile = json.load(open(os.path.join(PIPELINE_DIR, "profiles", f"{args.profile}.json")))
    view_top = VIEW_TOP_WEEK if args.tab == "week" else VIEW_TOP
    pat = re.compile(rf"^\d{{5}}_{args.tab}_(?!tab)")
    frames = sorted(f for d in args.dirs for f in glob.glob(os.path.join(d, "*.png")) if pat.match(os.path.basename(f)))
    ocr = subprocess.Popen([OCR_BIN, "--stdin"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, text=True, bufsize=1)
    store = Store()
    skipped = 0
    for f in frames:
        ocr.stdin.write(f + "\n")
        ocr.stdin.flush()
        items = json.loads(ocr.stdout.readline())
        if not is_rank_list(items):
            skipped += 1
            continue
        store.add(parse_frame(items, view_top=view_top), f, 1)
    ocr.stdin.close()
    if args.archive_only or not args.dry_run:
        kept, total, size = archive(args.dirs, args.week, args.tab, store.frame_ranks())
        print(f"{args.tab}: archived {kept} of {total} frames ({size / 1e6:.1f} MB)")
    if args.archive_only:
        return
    merged = store.merge()
    probs = problems(merged)
    records = finalize(merged, profile)
    print(f"{args.tab}: {len(frames)} frames ({skipped} not on the list), {len(records)} ranks, "
          f"unresolved: {probs or 'none'}")
    for m in merged:
        if m["diag"]["name_agree"] < 1 or m["diag"]["points_agree"] < 1:
            print(f"   rank {m['rank']}: {m['player']!r} reads {m['diag']['name_reads']} pts {m['diag']['points_reads']}")
    if args.dry_run:
        return
    wdir = os.path.join(WEEKS_DIR, args.week)
    with open(os.path.join(wdir, f"{args.tab}.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    qa_path = os.path.join(wdir, "capture_qa.json")
    qa = json.load(open(qa_path)) if os.path.exists(qa_path) else {"week": args.week, "tabs": {}}
    qa["tabs"][args.tab] = {"tab": args.tab, "live": False, "reprocessed_from_frames": len(frames),
                            "unresolved": {str(k): v for k, v in probs.items()},
                            "diagnostics": [{"rank": m["rank"], "player": m["player"], **m["diag"]} for m in merged]}
    qa["ok"] = all(not t.get("unresolved") for t in qa["tabs"].values())
    with open(qa_path, "w", encoding="utf-8") as f:
        json.dump(qa, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()

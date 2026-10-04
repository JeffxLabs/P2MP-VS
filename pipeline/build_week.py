#!/usr/bin/env python3
"""
Build the per-week analytics bundle and the site manifest from the captured leaderboards.

Input : data/weeks/<id>/{mon,tue,wed,thu,fri,sat,week}.json   (rank, player, alliance_tag, ... points)
        data/weeks/<id>/capture.json, capture_qa.json            (optional, written by capture_all.py)
        data/weeks/<id>/duel_summary.json                        (optional legacy official totals)
        data/weeks/<id>/meta.json                                (optional overrides: opponent server, notes)
Output: data/weeks/<id>/week_summary.json   analytics for the week (the site reads the .js twin)
        data/weeks/<id>/week_data.js        window.VS_WEEKS["<id>"] = {...}
        data/manifest.json / manifest.js    window.VS_MANIFEST = [...] newest last, with data_version hashes

Usage:
  python3 pipeline/build_week.py 2026-10-03 [--profile p1mp] [--opp-server 119]
  python3 pipeline/build_week.py --all
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter

from aliases import apply as alias_name

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PIPELINE_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
WEEKS_DIR = os.path.join(DATA_DIR, "weeks")

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat"]
WINS = {"mon": 1, "tue": 2, "wed": 2, "thu": 2, "fri": 2, "sat": 4}
TOTAL_WINS = 13
QUOTA = 11_400_000
TIERS = [  # (min weekly points, id) — ids are translated on the site
    (100_000_000, "titan"), (50_000_000, "high"), (20_000_000, "core"),
    (QUOTA, "quota_met"), (11_000_000, "near_quota"), (0, "passenger"),
]


def name_key(name):
    return "".join(ch for ch in unicodedata.normalize("NFKC", name or "") if ch.isalnum()).casefold()


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tier_of(points):
    for floor, tid in TIERS:
        if points >= floor:
            return tid
    return "passenger"


def match_to_weekly(rows, weekly_by_key, weekly_rows):
    """Map each daily row to a weekly-board player key: exact letter/digit core first, then the
    most similar name in the same alliance whose weekly total can contain the day's points."""
    out = {}
    for r in rows:
        k = name_key(r["player"])
        if k and k in weekly_by_key:
            out[r["rank"]] = k
            continue
        best, best_ratio = None, 0.0
        for w in weekly_rows:
            if w["alliance_tag"] != r["alliance_tag"] or (w["points"] or 0) < (r["points"] or 0):
                continue
            ratio = difflib.SequenceMatcher(None, k, name_key(w["player"])).ratio()
            if ratio > best_ratio:
                best, best_ratio = name_key(w["player"]), ratio
        if best and best_ratio >= 0.8:
            out[r["rank"]] = best
        else:
            out[r["rank"]] = k or f"#{r['rank']}"
    return out


def set_quota(profile):
    """Weekly quota is an alliance rule: profile weekly_quota / near_quota (default 11.4M / 11.0M)."""
    global QUOTA, TIERS
    QUOTA = int(profile.get("weekly_quota", 11_400_000))
    near = int(profile.get("near_quota", QUOTA - 400_000))
    TIERS = [(100_000_000, "titan"), (50_000_000, "high"), (20_000_000, "core"),
             (QUOTA, "quota_met"), (near, "near_quota"), (0, "passenger")]


def build(week_id, profile, opp_server=None):
    set_quota(profile)
    wdir = os.path.join(WEEKS_DIR, week_id)
    meta_over = load(os.path.join(wdir, "meta.json"), {}) or {}
    home = profile["home_tag"]
    boards = {t: load(os.path.join(wdir, f"{t}.json"), []) for t in DAYS + ["week"]}
    # Opponent hint (meta.json opponent_tag/opponent_name): OCR can mangle the bracketed tag
    # (e.g. "[JKRS]JOKERS" read as "UKRSJJOKERS"), so untagged rows whose alliance text is close to the
    # hinted "[TAG]Name" are assigned to it.
    hint_tag, hint_name = meta_over.get("opponent_tag"), meta_over.get("opponent_name", "")
    hint_core = re.sub(r"[^A-Z0-9]", "", f"{hint_tag}{hint_name}".upper()) if hint_tag else ""
    for rows in boards.values():
        for r in rows:
            if hint_tag and r["alliance_tag"] != home:
                raw_core = re.sub(r"[^A-Z0-9]", "", (r.get("alliance") or "").upper())
                if r["alliance_tag"] == hint_tag or (raw_core and difflib.SequenceMatcher(
                        None, raw_core, hint_core).ratio() >= 0.75):
                    r["alliance_tag"], r["alliance_name"] = hint_tag, hint_name
                    r["alliance"] = f"[{hint_tag}] {hint_name}"
            r["player"] = alias_name(r["player"], r.get("alliance", ""))
    capture = load(os.path.join(wdir, "capture.json"), {}) or {}
    qa = load(os.path.join(wdir, "capture_qa.json"), {}) or {}
    legacy = load(os.path.join(wdir, "duel_summary.json"), {}) or {}
    meta_over = load(os.path.join(wdir, "meta.json"), {}) or {}
    home = profile["home_tag"]

    # Opponent = the non-home alliance with the most weekly points
    tag_pts = Counter()
    tag_name = {}
    for r in boards["week"]:
        if r["alliance_tag"] and r["alliance_tag"] != home:
            tag_pts[r["alliance_tag"]] += r["points"] or 0
            tag_name.setdefault(r["alliance_tag"], r["alliance_name"])
    opp = tag_pts.most_common(1)[0][0] if tag_pts else ""
    opp_name = tag_name.get(opp, "")
    opp_server = opp_server or meta_over.get("opponent_server") or \
        (legacy.get("opponent_alliance", {}) or {}).get("server") or ""
    if opp_server and not str(opp_server).upper().startswith("S"):
        opp_server = f"S{opp_server}"

    # Tabs that were still changing while being read (rescanned and merged at capture time). This only
    # affects the checksum: a capture is always the week's final record, because boards are read shortly
    # before the midnight server reset (UTC-2), after which the in-game rankings disappear.
    live = set(capture.get("live_tabs", meta_over.get("live_tabs", [])))

    # ---- stages
    stages = []
    score = {"home": 0, "opp": 0}
    for d in DAYS:
        rows = boards[d]
        hp = sum(r["points"] or 0 for r in rows if r["alliance_tag"] == home)
        op = sum(r["points"] or 0 for r in rows if r["alliance_tag"] == opp)
        hn = sum(1 for r in rows if r["alliance_tag"] == home)
        on = sum(1 for r in rows if r["alliance_tag"] == opp)
        status = "pending" if not rows else "final"
        official = next((x for x in legacy.get("daily_stages", []) if x.get("day") == d), None)
        if official and official.get("p1mp_points") is not None:
            # Legacy weeks recorded the official alliance stage scores; prefer them to leaderboard sums
            hp, op = official["p1mp_points"], official["obs_points"]
        winner = None
        if rows:
            winner = "home" if hp > op else ("opp" if op > hp else "tie")
        if status == "final" and winner in ("home", "opp"):
            score[winner] += WINS[d]
        mvp_h = next((r for r in rows if r["alliance_tag"] == home), None)
        mvp_o = next((r for r in rows if r["alliance_tag"] == opp), None)
        hpts = sorted((r["points"] or 0 for r in rows if r["alliance_tag"] == home), reverse=True)
        stages.append({
            "day": d, "stage": DAYS.index(d) + 1, "wins": WINS[d], "status": status,
            "home_points": hp, "opp_points": op, "home_players": hn, "opp_players": on,
            "winner": winner, "margin": abs(hp - op),
            "home_share": round(hp / (hp + op) * 100, 2) if hp + op else None,
            "home_top10_share": round(sum(hpts[:10]) / hp * 100, 1) if hp else None,
            "home_median": hpts[len(hpts) // 2] if hpts else 0,
            "mvp_home": {"player": mvp_h["player"], "points": mvp_h["points"], "rank": mvp_h["rank"]} if mvp_h else None,
            "mvp_opp": {"player": mvp_o["player"], "points": mvp_o["points"], "rank": mvp_o["rank"]} if mvp_o else None,
        })
    remaining = sum(WINS[s["day"]] for s in stages if s["status"] != "final")
    to_clinch = TOTAL_WINS // 2 + 1
    decided = None
    if score["home"] >= to_clinch:
        decided = "home"
    elif score["opp"] >= to_clinch:
        decided = "opp"
    leading_live = {s["day"]: s["winner"] for s in stages if s["status"] == "live"}

    # ---- players (both alliances, keyed on the weekly board)
    weekly = boards["week"]
    weekly_by_key = {name_key(r["player"]): r for r in weekly if r["player"]}
    day_maps = {d: match_to_weekly(boards[d], weekly_by_key, weekly) for d in DAYS}
    players = {}
    for r in weekly:
        k = name_key(r["player"]) or f"#{r['rank']}"
        players[k] = {"key": k, "player": r["player"], "tag": r["alliance_tag"], "alliance": r["alliance_name"],
                      "weekly_points": r["points"] or 0, "weekly_rank": r["rank"], "days": {}}
    for d in DAYS:
        tag_rank = Counter()
        for r in boards[d]:
            tag_rank[r["alliance_tag"]] += 1
            k = day_maps[d][r["rank"]]
            p = players.get(k)
            if p is None:
                # On a day board but not on the weekly board (left / renamed before the weekly capture)
                p = players[k] = {"key": k, "player": r["player"], "tag": r["alliance_tag"],
                                  "alliance": r["alliance_name"], "weekly_points": 0, "weekly_rank": None,
                                  "days": {}, "not_on_weekly": True}
            p["days"][d] = {"points": r["points"] or 0, "rank": r["rank"],
                            "alliance_rank": tag_rank[r["alliance_tag"]], "tag": r["alliance_tag"]}

    def finish(tag):
        lst = [p for p in players.values() if p["tag"] == tag]
        lst.sort(key=lambda p: (bool(p.get("not_on_weekly")), -p["weekly_points"], -p.get("sum_days", 0)))
        total = sum(p["weekly_points"] for p in lst) or 1
        rank = 0
        for p in lst:
            if p.get("not_on_weekly"):
                p["alliance_rank"] = None   # left before the weekly capture: no weekly rank
            else:
                rank += 1
                p["alliance_rank"] = rank
            p["share"] = round(p["weekly_points"] / total * 100, 2)
            pts = [p["days"].get(d, {}).get("points", 0) for d in DAYS]
            p["active_days"] = sum(1 for x in pts if x > 0)
            best = max(range(6), key=lambda i2: pts[i2])
            p["best_day"] = DAYS[best] if pts[best] > 0 else None
            p["sum_days"] = sum(pts)
            diff = p["weekly_points"] - p["sum_days"]
            # Days spent in another alliance count toward the weekly total but appear under that tag
            other = [d for d in DAYS if p["days"].get(d, {}).get("tag") not in (None, tag)]
            if p.get("not_on_weekly"):
                st = "left"         # on day boards only: no longer listed on the weekly board (left the alliance)
            elif diff == 0:
                st = "exact"
            elif diff > 0 and p["days"] and min(p["days"], key=DAYS.index) != "mon":
                st = "joined"       # first on a day board after Monday: points from before joining are in the weekly total only
            elif live and diff > 0:
                st = "live"         # today's points kept growing between the day and weekly scans
            elif other:
                st = "alliance_change"
            else:
                st = "mismatch"
            p["check"] = {"diff": diff, "status": st}
            p["tier"] = tier_of(p["weekly_points"])
            p["quota_met"] = p["weekly_points"] >= QUOTA
            p["deficit"] = max(0, QUOTA - p["weekly_points"])
            # Day-to-day consistency: coefficient of variation of the six days (lower = steadier)
            mean = sum(pts) / 6
            p["consistency"] = round((sum((x - mean) ** 2 for x in pts) / 6) ** 0.5 / mean, 3) if mean else None
        return lst

    home_members = finish(home)
    opp_members = finish(opp)
    others = [p for p in players.values() if p["tag"] not in (home, opp)]

    checks = Counter(p["check"]["status"] for p in home_members + opp_members)
    integrity = {"tabs": {}, "checksum": dict(checks),
                 "checksum_issues": [{"player": p["player"], "tag": p["tag"], "weekly": p["weekly_points"],
                                      "sum_days": p["sum_days"], "diff": p["check"]["diff"],
                                      "status": p["check"]["status"]}
                                     for p in home_members + opp_members if p["check"]["status"] not in ("exact", "live", "left", "joined")]}
    for t in DAYS + ["week"]:
        rows = boards[t]
        ranks = [r["rank"] for r in rows]
        integrity["tabs"][t] = {
            "rows": len(rows),
            "contiguous": ranks == list(range(1, len(rows) + 1)),
            "points_descending": all((a["points"] or 0) >= (b["points"] or 0) for a, b in zip(rows, rows[1:])),
            "missing_points": sum(1 for r in rows if r["points"] is None),
            "missing_names": sum(1 for r in rows if not r["player"]),
            "unresolved": (qa.get("tabs", {}).get(t, {}) or {}).get("unresolved", {}),
            "live": t in live,
        }

    current = [p for p in home_members if not p.get("not_on_weekly")]
    # ---- snapshot time of each board: last archived frame of that tab, else the QA log, else meta.json
    shots_index = load(os.path.join(wdir, "screenshots", "index.json"), {}) or {}
    snapshots = {}
    for t in DAYS + ["week"]:
        if not boards[t]:
            continue
        frames = [e["taken_at_server"] for e in shots_index.get(t, []) if e.get("taken_at_server")]
        at = max(frames) if frames else (qa.get("tabs", {}).get(t, {}) or {}).get("captured_at")
        source = "screenshots" if frames else ("capture log" if at else None)
        if not at and meta_over.get("captured_at_server"):
            at, source = meta_over["captured_at_server"], "legacy file times"
        if at:
            snapshots[t] = {"at": at, "source": source,
                            "approximate": bool(meta_over.get("captured_at_approximate")) and source == "legacy file times"}
    times = sorted(v["at"] for v in snapshots.values())
    wk_home = sum(p["weekly_points"] for p in home_members)
    wk_opp = sum(p["weekly_points"] for p in opp_members)
    summary = {
        "id": week_id,
        "home": {"tag": home, "name": profile["home_name"], "server": profile["home_server"]},
        "opponent": {"tag": opp, "name": opp_name, "server": opp_server},
        "status": "final",
        "live_tabs": sorted(live),
        "captured_at_server": times[-1] if times else capture.get("last_capture_server"),
        "capture_window_server": [times[0], times[-1]] if times else None,
        "captured_at_approximate": any(v["approximate"] for v in snapshots.values()),
        "snapshots": snapshots,
        "score": score, "wins_remaining": remaining, "decided": decided, "leading_live": leading_live,
        "total_wins": TOTAL_WINS, "wins_to_clinch": to_clinch,
        "weekly_points": {"home": wk_home, "opp": wk_opp},
        "official_points": ({"home": legacy["weekly_result"].get("p1mp_official_points"),
                             "opp": legacy["weekly_result"].get("obs_official_points")}
                            if legacy.get("weekly_result", {}).get("p1mp_official_points") else None),
        "quota": QUOTA,
        "home_quota": {"met": sum(1 for p in current if p["quota_met"]),
                       "near": sum(1 for p in current if p["tier"] == "near_quota"),
                       "below": sum(1 for p in current if p["tier"] == "passenger"),
                       "members": len(current), "left": len(home_members) - len(current)},
        "stages": stages,
        "integrity": integrity,
        "notes": meta_over.get("notes", []),
    }
    bundle = {"summary": summary, "boards": boards, "members": home_members, "opponents": opp_members,
              "others": others}
    with open(os.path.join(wdir, "week_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(os.path.join(wdir, "week_data.js"), "w", encoding="utf-8") as f:
        f.write("window.VS_WEEKS = window.VS_WEEKS || {};\n")
        f.write(f"window.VS_WEEKS[{json.dumps(week_id)}] = {json.dumps(bundle, ensure_ascii=False)};\n")
    return summary


def write_site_config(profile):
    """data/site.js: which alliance and repo this site is for (brand, links)."""
    site = {"home_tag": profile["home_tag"], "home_name": profile["home_name"],
            "server": profile["home_server"], "repo": profile.get("repo", "")}
    with open(os.path.join(DATA_DIR, "site.js"), "w", encoding="utf-8") as f:
        f.write(f"window.VS_SITE = {json.dumps(site, ensure_ascii=False)};\n")


def write_manifest():
    entries = []
    for wid in sorted(os.listdir(WEEKS_DIR)):
        wdir = os.path.join(WEEKS_DIR, wid)
        s = load(os.path.join(wdir, "week_summary.json"))
        js = os.path.join(wdir, "week_data.js")
        if not s or not os.path.exists(js):
            continue
        with open(js, "rb") as f:
            ver = hashlib.sha1(f.read()).hexdigest()[:10]
        entries.append({"id": wid, "home": s["home"], "opponent": s["opponent"], "status": s["status"],
                        "score": s["score"], "decided": s["decided"], "weekly_points": s["weekly_points"],
                        "members": s["home_quota"]["members"], "captured_at_server": s["captured_at_server"],
                        "capture_window_server": s.get("capture_window_server"),
                        "captured_at_approximate": s.get("captured_at_approximate", False),
                        "data_version": ver})
    with open(os.path.join(DATA_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    with open(os.path.join(DATA_DIR, "manifest.js"), "w", encoding="utf-8") as f:
        f.write(f"window.VS_MANIFEST = {json.dumps(entries, indent=2, ensure_ascii=False)};\n")
    stamp = os.path.join(PIPELINE_DIR, "stamp_assets.py")
    if os.path.exists(stamp):
        import subprocess, sys
        subprocess.run([sys.executable, stamp], check=False)
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("week", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--profile", default="p1mp")
    ap.add_argument("--opp-server")
    args = ap.parse_args()
    profile = load(os.path.join(PIPELINE_DIR, "profiles", f"{args.profile}.json"))
    weeks = sorted(os.listdir(WEEKS_DIR)) if args.all else [args.week]
    for w in weeks:
        if not os.path.exists(os.path.join(WEEKS_DIR, w, "week.json")):
            continue
        s = build(w, profile, args.opp_server if not args.all else None)
        integ = s["integrity"]
        print(f"[{w}] {s['home']['tag']} vs {s['opponent']['tag']} {s['opponent']['name']} {s['opponent']['server']}: "
              f"score {s['score']['home']}:{s['score']['opp']} ({s['status']}), members {s['home_quota']['members']}, "
              f"checksum {integ['checksum']}")
        for t, v in integ["tabs"].items():
            flag = "" if v["contiguous"] and v["points_descending"] and not v["missing_points"] and not v["missing_names"] else "  <-- CHECK"
            print(f"   {t}: {v['rows']} rows, contiguous={v['contiguous']}, descending={v['points_descending']}, "
                  f"missing pts={v['missing_points']} names={v['missing_names']}{flag}")
        for issue in integ["checksum_issues"][:20]:
            print(f"   checksum: {issue}")
    write_site_config(profile)
    m = write_manifest()
    print(f"manifest: {len(m)} week(s)")


if __name__ == "__main__":
    main()

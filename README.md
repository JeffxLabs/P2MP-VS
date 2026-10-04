# [P2MP] NowaPolandia — Alliance Competition (VS) tracker

Weekly Alliance Competition ("VS" / Alliance Duel) results for **[P2MP] NowaPolandia**, Server 117, in *Z Route: Redemption*:
every daily leaderboard (MON–SAT) and the weekly total, per-member performance, quota tracking, opponent scouting and
multi-week trends.

**Dashboard:** https://jeffxlabs.github.io/P2MP-VS/ — dark/light themes, 10 languages, deep links for every view.

Same pipeline and dashboard as [[P1MP] JU1CE VS](https://jeffxlabs.github.io/P1MP-VS/); this site is configured by
`pipeline/profiles/p2mp.json` (captured from the Apparatchik account's BlueStacks instance, 127.0.0.1:5565; the capture
leaves an operator pause of the Apparatchik guard alone, or pauses and resumes it, and ends on the city view).

---

## Weeks tracked

| Week (Sat) | Opponent | Score | Weekly points (leaderboard) | Data snapshot (server time, UTC−2) |
| :-- | :-- | :-: | :-- | :-- |
| 2026-10-03 | [JKRS] JOKERS | 0 : 13 | 2,238,799,329 vs 3,900,144,141 | Sat 2026-10-03 22:53–23:28 (first capture) |

Board snapshots for 2026-10-03: MON 22:53, TUE 23:00, WED 23:03, THU 23:07, FRI 23:11, SAT 23:24, This Week 23:28.

### 2026-10-03 vs [JKRS] JOKERS

| Stage | Wins | [P2MP] | [JKRS] | Players | Top [P2MP] | Top [JKRS] |
| :-- | :-: | --: | --: | :-: | :-- | :-- |
| Mon · Radar Exploration | 1 | 368,125,611 | **632,453,547** | 89 / 96 | Chungi 13.0M | Shalix 50.5M |
| Tue · Base Construction | 2 | 279,299,118 | **510,120,263** | 86 / 99 | evrenhalo 9.3M | Mydnyte 18.8M |
| Wed · Tech Research | 2 | 316,621,916 | **535,506,755** | 90 / 99 | Chungi 28.8M | Shalix 32.9M |
| Thu · Hero Training | 2 | 601,936,214 | **1,258,598,422** | 91 / 96 | Austen 23.8M | Bxom 56.7M |
| Fri · Full Military Preparation | 2 | 409,809,575 | **543,525,971** | 93 / 97 | Chungi 51.3M | Shalix 33.8M |
| Sat · Enemy Assault | 4 | 262,167,614 | **422,944,864** | 95 / 98 | Chungi 32.4M | Shalix 43.8M |

Quota (11.4M weekly, the P1MP default — set `weekly_quota` in `pipeline/profiles/p2mp.json` if P2MP uses another):
66 of 95 members met it, 1 near, 28 below.

Data checks: all seven boards contiguous with points in descending order, nothing unresolved. Weekly checksum: 181 exact,
10 joined mid-week, 6 left; 2 differences come from the game's own totals (every read agreed): ddingdongbel
(weekly 3,931,845 vs days 5,270,367) and DiRtY21B117 (−126). Decorated names OCR cannot read reliably are pinned in
`data/aliases.json` (JSP💪, °♡✧Jey✧♡°, GRIN♤♡◇♧, ALLSTAR (stylized), Babygirl100z, robOn8er) and confirmed by the checksum.
The opponent's server is not known yet (`meta.json` → `opponent_server`).

---

## Competition rules

Monday–Saturday, one stage per day. Daily wins: Mon 1, Tue–Fri 2 each, Sat 4 — 13 in total, 7 clinches the match.
Stage objectives are listed on the dashboard's **Stages** view (`data/competition_stages.json`).

---

## Data quality

Every published board is checked before it is pushed:

- **Every rank read several times.** Each rank is read on 2–4 screenshots (3.4 on average) and voted on: points must
  agree exactly, names are compared on their letters/digits with look-alike characters folded (l/I/1, O/0,
  Cyrillic/Latin twins), so a decorative symbol or one stray misread cannot win.
- **No skipped or duplicated ranks.** Ranks come from the row geometry and the rank digits on screen; every frame must
  overlap the previous one, and any gap is scrolled back to and re-read. Missing, single-read, disagreeing,
  out-of-order or repeated-player ranks are revisited (repair pass) before a board is accepted.
- **Weekly checksum.** Each player's weekly total must equal the sum of their six days; players who joined mid-week
  (points from before joining only appear in the weekly total) or left before the weekly capture are labelled as such.
- **Boards still updating.** Saturday and This Week can still change while being read: if a scan shows movement, the board is scanned again
  and merged per player, then re-ranked.
- **Evidence.** Compressed screenshots (720 px WebP) of the frames behind every board are in
  `data/weeks/<week>/screenshots/<tab>/`, chosen so each rank appears on at least two of them, with `index.json`
  (capture time and ranks on each frame). Per-rank read counts and agreement are in `capture_qa.json`.

---

## Capturing a week

Requirements: macOS with Xcode command-line tools (Swift, Vision), `adb`, `cwebp` (optional, `brew install webp`),
BlueStacks at 1080×1920 portrait with the game running.

```sh
adb connect 127.0.0.1:5565
python3 pipeline/capture_all.py --profile p2mp --opp-tag JKRS --opp-name JOKERS  # all seven tabs
python3 pipeline/capture_all.py --profile p2mp --tabs sat,week  # just today's and the weekly board
```

What it does:

1. **Navigates by OCR** from wherever the game is: backs out, taps the **VS** icon on the right-hand side of the city
   screen, then **RANKINGS** at the bottom of the Alliance Competition page.
2. For **MON, TUE, WED, THUR, FRI, SAT, This Week** in that order: taps the tab and confirms it is the highlighted one
   (pixel check), confirms the list starts at rank 1, then scrolls to the very bottom (the list lazy-loads more rows
   near its end; the bottom is only accepted after a second check). The pinned own-rank row under the list is ignored.
3. **Continuous capture:** the list is scrolled continuously while screenshots are taken back to back and read by
   Apple Vision OCR as they arrive (a screenshot is a single rendered frame, so it is sharp even mid-scroll). About
   45–55 s per tab; a full week of seven tabs is roughly 7–10 minutes including repairs.
4. Writes `data/weeks/<week>/{mon,tue,wed,thu,fri,sat,week}.json`, `capture.json`, `capture_qa.json`, the screenshot
   archive, then runs `pipeline/build_week.py` (analytics, `week_data.js`, `data/manifest.js`, cache-busting stamps).
   Exits non-zero if any rank is unresolved (`--allow-incomplete` to override).

Then publish:

```sh
git add data index.html README.md && git commit -m "data: VS week 2026-10-10" && git push
```

Useful flags: `--no-navigate` (Rankings already open), `--week YYYY-MM-DD`, `--no-screenshots`, `--no-build`.

Rebuild a board from saved frames after a parser change (no emulator): `python3 pipeline/reprocess.py <week> <tab> <frames dir>`
(full-size frames are kept in `~/Library/Caches/s117-vs-captures/`).

### Other accounts

`pipeline/profiles/*.json` holds each account's settings (home tag, device, quota, repo). The same code runs the
[P1MP] site (`--profile p1mp`, BlueStacks 127.0.0.1:5555); keep `pipeline/` and `index.html` in sync between the repos.

---

## Repository layout

```
index.html                    dashboard (single file, no build step)
data/manifest.js|json         weeks list (+ data_version for cache busting)
data/i18n.js, data/stages.js  generated by pipeline/build_i18n.py
data/competition_stages.json  stage rules and activities
data/weeks/<week>/            boards (*.json), week_summary.json, week_data.js, capture*.json, meta.json, screenshots/
pipeline/capture_all.py       capture: navigation, tabs, continuous scan, voting, repair, live-board merge
pipeline/vs_frame_parser.py   screenshot OCR boxes -> ranked rows (row geometry, pinned-row exclusion)
pipeline/build_week.py        analytics, checksum, manifest
pipeline/reprocess.py         rebuild a board from saved frames
pipeline/screenshots.py       compressed screenshot archive
pipeline/vision_ocr.swift     Apple Vision OCR worker; pixel_probe.swift: tab highlight check
pipeline/build_i18n.py        translations (10 languages); stamp_assets.py: cache busting
pipeline/tests/               node checks for translations, data files and the page scripts
```

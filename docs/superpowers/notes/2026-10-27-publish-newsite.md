# Publishing newsite to main, and rolling back

Do these in order. Production (`hourly.yml`) commits to `main` every hour, so main must not move while you work.

## Publish

1. **Disable the hourly workflow** (Actions -> Hourly price check -> Disable), so it cannot push data while you merge.
2. **Wait for any running job** of that workflow to finish (or cancel it and check `git log origin/main` for a half-written commit).
3. Fetch, then publish the branch from the current main: `git fetch origin && git checkout newsite`.
4. **Merge main into newsite**: `git merge origin/main`. Do not merge newsite into main yet.
5. **Take main's version of every `data/*` file except history** (latest.json, rates, telegram.json, caches, ...):
   `git checkout origin/main -- data/ ':!data/history'` (or file by file), then `git rm -r --cached` nothing else.
   `data/history/` is rebuilt in step 7; newsite's copy is stale.
6. **Hourly tests on main's data**: `.venv/bin/python -m pytest -q -m "not live"` passes. This is exactly what the hourly job
   runs before every price check once newsite is main; if it fails here it would block production every hour: stop.
   Run it again after step 8, on the rebuilt history.
7. **Rebuild history from main's `history.csv`**:
   `git show origin/main:data/history.csv > /tmp/h.csv && python tools/split_history.py /tmp/h.csv`
   Then remove the old single file: `git rm -f data/history.csv`.
8. **Check**:
   - row count: `tail -n +2 /tmp/h.csv | wc -l` equals the total printed by `split_history.py` and `cat data/history/20*.csv | grep -vc '^time,'`;
   - `data/history/last.json` has the same number of keys as the `split_history.py` output ("N last-known prices");
   - the month files are the expected months (first month in main's file through the current one).
9. **Full pytest with node installed**: `DOORPRICE_CHECK_BUDGETS=1 .venv/bin/python -m pytest -q` (the `live` tests included) and `node tests/js/pricing_cases.mjs`.
10. **Offline build vs main, as search engines see it**: `python tools/seo_diff.py` builds `origin/main` (in a temporary worktree) and this
    working tree offline, as production, and prints:
    - every file main builds that newsite does not (`data/` aside). Main's set of build paths must be a subset of newsite's, except
      `static/app.js` and `static/style.css` (gone on purpose). Any other "only on main" line is a page or file search engines would lose: stop.
    - for every page both have, any difference in title, canonical, meta description, robots, og:image or JSON-LD @types. With the same
      data (steps 5-7) these must be equal, apart from changes the spec makes on purpose (e.g. the stores pages' description gains
      "payment fees" and a BreadcrumbList). Anything else (a changed title or canonical, a lost description or JSON-LD type, a robots
      `noindex`): stop. `og:image`'s `?v=` changes with the card picture and is fine when the card exists.
    The rest of the pages' HTML is meant to differ (the new design).
11. **Preview pass**: push the merged branch (`git push origin newsite`); newsite.yml runs the full tests and deploys it to
    newsite.pricechecker-87q.pages.dev. Open home, a phone with both versions, a China-only phone, specs, drops, compare, a store page,
    a history page and 404 on a phone and a desktop, light and dark, and change the delivery settings once. Anything broken: stop.
12. `python -m pricechecker.telegram --dry` shows 0 drops and 0 new offers (the channel must not get a burst).
13. **Push** main (fast-forward from the merged branch): `git push origin newsite:main`.
14. **Re-enable the hourly workflow and dispatch it once** (Run workflow).
15. **Watch the first run**: the log shows the normal "history: N price changes recorded"; the deploy step succeeds; Telegram stays quiet;
    IndexNow reports a normal number of changed pages; the commit diff touches only the current month's `data/history/YYYY-MM.csv` and `last.json` (plus the usual latest.json/caches).

## newsite-preview/ is not published

`newsite-preview/` (the design mockups) is copied to `build/mock/` only by the newsite workflow. The hourly and production workflows never copy it,
so it must not exist in production's `build/`. Merging newsite into main does not publish it; check `build/mock/` is absent after the first production run.
The old `static/app.js` and `static/style.css` are gone: pages load `static/d.css` and the modules in `static/js/` (hashed in `_headers`). Nothing in these steps needs them.

## Rollback

1. **Disable the hourly workflow** and wait for running jobs.
2. On the branch you will revert from, run `python tools/join_history.py` -> writes `data/history.csv` (same header, rows in order) from `data/history/*.csv`.
3. `git rm -r data/history` and `git add data/history.csv`, commit, then `git revert` the newsite merge (or reset main to the pre-merge commit and re-apply `data/history.csv` and the latest data files on top). Check `data/history.csv` is the last file written by the hourly run.
4. Push, re-enable the hourly workflow, dispatch it, and watch one run as above.

## Known deferred visible change

Charts and statistics use a window of the newest 3 month files. Until there are 4 months of history this is the whole history,
so nothing changes. **From January 2027** (the 4th month file) the window drops the oldest month and the pages' charts and
stats cover less history than the live site's. This is intended but visible; decide then whether to widen the window.

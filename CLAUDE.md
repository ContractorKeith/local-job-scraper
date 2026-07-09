# local-job-scraper — Agent Instructions

Python tool that searches company websites directly for job openings (not job boards): finds
companies via the Google Places API (New), checks their sites for a careers page (18 URL patterns +
homepage link scanning), and scans it for target job keywords. Runs weekly via GitHub Actions.
MIT-licensed, public repo.

## Layout

- `job_scraper.py` — all logic (single script; interactive menu + `--profile` CLI)
- `config.py` — the ONLY file users edit: location lat/lng, radius, job profiles (`place_searches` + `job_keywords`)
- `.github/workflows/weekly_scraper.yml` — Monday cron (UTC), uploads results as artifacts
- `requirements.txt` — requests, beautifulsoup4, python-dotenv

## Run

```bash
pip install -r requirements.txt
cp .env.example .env        # set GOOGLE_PLACES_API_KEY
python job_scraper.py                 # interactive menu
python job_scraper.py --profile 1     # one profile
python job_scraper.py --profile all
```

Results land in `results/` as JSON (three buckets: keyword matches, has careers page, no careers
page). No test suite exists.

## Constraints

- Keep `config.py` the single place users customize — don't scatter settings into `job_scraper.py`
- Never commit `.env` or API keys; in CI the key comes from the `GOOGLE_PLACES_API_KEY` repo secret
- Results are intentionally not committed to the repo (artifacts only)
- Python 3.8+ compatibility (per README prerequisites)
- Use `logging`, not `print()` (script already configures a logger)

## Python rules (global imports)

@~/.claude/rules-python/coding-style.md
@~/.claude/rules-python/testing.md
@~/.claude/rules-python/patterns.md
@~/.claude/rules-python/security.md
@~/.claude/rules-python/hooks.md

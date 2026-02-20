# local-job-scraper

A Python tool that searches **company websites directly** for job openings — not Indeed, not ZipRecruiter.

Many companies — especially small and mid-size contractors, suppliers, and service businesses — post jobs exclusively on their own websites and never list them on job boards. This tool finds those companies in your area via Google Maps, checks their websites for career pages, and scans those pages for the job titles you're looking for.

**It runs automatically every Monday via GitHub Actions** so you always have a fresh list without thinking about it.

---

## What It Does

1. Searches Google Maps for companies matching your industry types within your radius
2. Looks up each company's website
3. Checks for a careers/jobs page (tries 18 common URL patterns + homepage link scanning)
4. Scans the career page for your target job keywords
5. Outputs three buckets: **keyword matches**, **has a careers page (worth bookmarking)**, and **no careers page (worth a cold call)**

Results are saved as JSON files and as downloadable artifacts in GitHub Actions.

---

## Prerequisites

- Python 3.8 or higher
- A Google Places API key (free tier is more than enough — see setup below)
- A GitHub account (free)

---

## Setup

### Step 1 — Get a Google Places API Key

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (name it anything, e.g. `job-scraper`)
3. Go to **APIs & Services → Library**
4. Search for **Places API (New)** — make sure it says "(New)" — and enable it
5. Go to **APIs & Services → Credentials → Create Credentials → API Key**
6. Copy the key — you'll use it in Step 3

> You'll need a billing account attached to the project, but Google gives you
> $200/month in free credits. Running this scraper weekly costs pennies.

---

### Step 2 — Clone or Fork This Repo

```bash
git clone https://github.com/ContractorKeith/local-job-scraper.git
cd local-job-scraper
pip install -r requirements.txt
```

Or click **Fork** at the top of this page to create your own copy on GitHub,
then clone your fork.

---

### Step 3 — Set Your API Key

Copy the example file and add your key:

```bash
cp .env.example .env
```

Open `.env` and replace `your_api_key_here` with your actual key:

```
GOOGLE_PLACES_API_KEY=AIzaSy...your_key_here
```

The `.env` file is listed in `.gitignore` so it will **never** be accidentally
committed to GitHub.

---

### Step 4 — Configure Your Location and Job Profiles

Open `config.py` — this is the **only file you need to edit**.

#### Set your location

```python
LOCATION_LABEL = "Austin, TX"   # Just for display
LAT  = 30.2672                  # Your latitude
LNG  = -97.7431                 # Your longitude
```

**Finding your coordinates:** Go to [maps.google.com](https://maps.google.com),
right-click on your city center, and click the latitude/longitude numbers that
appear at the top of the menu.

#### Set your search radius

```python
TOTAL_RADIUS_METERS = 96000   # ~60 miles
```

Common values:
| Miles | Meters |
|-------|--------|
| 30 mi | 48,000 |
| 60 mi | 96,000 |
| 100 mi | 160,000 |

> For radii larger than ~31 miles (50,000m), the script automatically runs
> multiple overlapping search zones to cover the full area.

#### Customize your job profiles

Each profile in `config.py` has two lists:

- **`place_searches`** — what to search for on Google Maps (company types)
- **`job_keywords`** — what to look for on their career pages (job titles)

The repo comes with three example profiles for construction/trades industries.
Edit them, delete them, or add your own for any industry.

---

### Step 5 — Run It Locally

```bash
# Interactive menu
python job_scraper.py

# Or run a specific profile directly
python job_scraper.py --profile 1
python job_scraper.py --profile all
```

Results are saved to a `results/` folder.

---

## Automated Weekly Runs via GitHub Actions

### Step 1 — Push your repo to GitHub

If you cloned this repo and want your own automated copy:

```bash
# Create a new private repo on github.com first, then:
git remote set-url origin https://github.com/YOUR_USERNAME/local-job-scraper.git
git push -u origin main
```

### Step 2 — Add your API key as a GitHub Secret

Your API key must be stored as a Secret so it's never exposed in the repo.

1. In your GitHub repo, click **Settings**
2. Click **Secrets and variables → Actions**
3. Click **New repository secret**
4. Name: `GOOGLE_PLACES_API_KEY`
5. Value: paste your API key
6. Click **Add secret**

### Step 3 — Verify the workflow file is in place

Check that `.github/workflows/weekly_scraper.yml` exists in your repo.
If it's there, GitHub automatically activates the Monday morning schedule.

### Step 4 — Test it manually

1. Click the **Actions** tab in your repo
2. Click **Weekly Job Scraper** in the left sidebar
3. Click **Run workflow → Run workflow**
4. Watch it run live or check back in a few minutes

### Changing the schedule

Edit `.github/workflows/weekly_scraper.yml` and modify the cron line.
Times are in UTC (EST = UTC-5, EDT = UTC-4).

```yaml
# Every Monday 9am Eastern (Standard Time)
- cron: "0 14 * * 1"

# Every Monday and Thursday
- cron: "0 14 * * 1,4"

# Every weekday
- cron: "0 14 * * 1-5"
```

### Viewing results

After each run, results are available two ways:

- **Artifacts:** Click any completed run in the Actions tab, scroll to the
  bottom, and download the `job-results-N` zip file. Kept for 30 days.
- **Locally:** Pull the repo after a run — results are not committed to keep
  the repo clean, so download the artifact if you want to save them.

---

## Output

Each JSON result file contains:

```json
{
  "profile": "Outside Sales — Technology & Software",
  "location": "Austin, TX",
  "run_date": "2026-02-20 09:00",
  "summary": {
    "total_companies": 94,
    "with_websites": 67,
    "keyword_matches": 3,
    "has_careers_page": 12,
    "no_careers_page": 52
  },
  "keyword_matches": [...],
  "has_careers_page": [...],
  "no_careers_page": [...]
}
```

Each company entry includes name, address, phone, website URL, and the direct
link to their careers page.

---

## Tips

**The "no career page" list is valuable too.** These companies either don't post
jobs publicly at all, or their jobs page is buried somewhere the scraper can't
find. Many small contractors hire entirely through walk-ins and word of mouth.
A well-timed visit or call with a resume in hand can be more effective than
any online application.

**Run it on demand any time** — don't wait for Monday. If you just had a great
lead fall through or you're about to update your resume, run it manually from
the Actions tab or your terminal.

**Expand your keywords broadly at first.** If you're not getting matches, add
more general terms to `job_keywords` in `config.py`. Some companies write
"Project Estimator" or "Estimating Specialist" instead of just "Estimator."

---

## Contributing

Pull requests welcome. If you add a useful industry profile or improve the
career page detection logic, feel free to open a PR.

---

## License

MIT — use it, modify it, share it freely.
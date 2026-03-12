"""
local-job-scraper
-----------------
Searches company websites directly for job openings —
no Indeed, no ZipRecruiter.

Customize everything in config.py before running.

Usage:
  Interactive menu:      python job_scraper.py
  Run specific profile:  python job_scraper.py --profile 1
  Run all profiles:      python job_scraper.py --profile all

GitHub Actions runs this automatically on your chosen schedule.
See .github/workflows/weekly_scraper.yml to change the schedule.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import argparse
import sys
import os
import math
import logging
from urllib.parse import urljoin, urlparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
log = logging.getLogger(__name__)

# Load API key — checks .env file first, then environment variable
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; env var or GitHub Secret also works

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
if not API_KEY:
    log.error("\n⚠️  No API key found.")
    log.error("   Set GOOGLE_PLACES_API_KEY in your environment or .env file.")
    log.error("   See README.md for instructions.\n")
    sys.exit(1)

# Load user config
from config import (
    LOCATION_LABEL,
    LAT,
    LNG,
    TOTAL_RADIUS_METERS,
    PROFILES,
    CAREER_PATHS,
)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

# Places API (New) caps radius at 50,000m per search
ZONE_RADIUS = 50000

# Meters per degree of latitude (approximate, constant worldwide)
METERS_PER_DEG_LAT = 111320

# How far to offset surrounding zones as a fraction of total radius
ZONE_OFFSET_FACTOR = 0.55

# Scale factor for diagonal zones (cos 45° ≈ 0.7)
DIAGONAL_SCALE = 0.7

# Browser user-agent for web scraping requests
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Career page link keywords to search for in href attributes
CAREER_LINK_KEYWORDS = ["career", "job", "hiring", "employment", "join", "apply", "work-with"]

# Minimum page size (bytes) to consider a career page valid
MIN_CAREER_PAGE_SIZE = 500

# Rate limiting delays (seconds)
DELAY_PLACES_SEARCH = 0.4
DELAY_WEBSITE_LOOKUP = 0.15
DELAY_CAREER_CHECK = 0.8

# API request timeout (seconds)
API_TIMEOUT = 10

# Web scraping request timeout (seconds)
SCRAPE_TIMEOUT = 8

# ─────────────────────────────────────────────
# BUILD SEARCH ZONES
# ─────────────────────────────────────────────


def build_search_centers(lat: float, lng: float, total_radius_meters: int) -> list[dict]:
    """Generate overlapping search centers to cover the full radius."""
    centers = [{"lat": lat, "lng": lng, "label": f"{LOCATION_LABEL} (center)"}]

    if total_radius_meters <= ZONE_RADIUS:
        return centers

    # Offset distance between center and surrounding zones
    offset_m = total_radius_meters * ZONE_OFFSET_FACTOR
    offset_deg_lat = offset_m / METERS_PER_DEG_LAT
    offset_deg_lng = offset_m / (METERS_PER_DEG_LAT * math.cos(math.radians(lat)))

    directions: list[tuple[str, float, float]] = [
        ("north", offset_deg_lat, 0),
        ("south", -offset_deg_lat, 0),
        ("east",  0,  offset_deg_lng),
        ("west",  0, -offset_deg_lng),
    ]

    if total_radius_meters > ZONE_RADIUS * 2:
        directions += [
            ("northeast",  offset_deg_lat * DIAGONAL_SCALE,  offset_deg_lng * DIAGONAL_SCALE),
            ("northwest",  offset_deg_lat * DIAGONAL_SCALE, -offset_deg_lng * DIAGONAL_SCALE),
            ("southeast", -offset_deg_lat * DIAGONAL_SCALE,  offset_deg_lng * DIAGONAL_SCALE),
            ("southwest", -offset_deg_lat * DIAGONAL_SCALE, -offset_deg_lng * DIAGONAL_SCALE),
        ]

    for direction, dlat, dlng in directions:
        centers.append({
            "lat": lat + dlat,
            "lng": lng + dlng,
            "label": f"{LOCATION_LABEL} ({direction})",
        })

    return centers


SEARCH_CENTERS = build_search_centers(LAT, LNG, TOTAL_RADIUS_METERS)


# ─────────────────────────────────────────────
# GOOGLE PLACES API (New)
# ─────────────────────────────────────────────

def search_places(query: str, lat: float, lng: float) -> list[dict]:
    """Search Places API (New) for businesses near given coordinates."""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress",
    }
    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(ZONE_RADIUS),
            }
        },
        "maxResultCount": 20,
    }
    companies: list[dict] = []
    try:
        response = requests.post(url, headers=headers, json=body, timeout=API_TIMEOUT)
        data = response.json()
        if "error" in data:
            err = data["error"]
            log.warning("    ⚠️  API Error %s: %s", err.get("code"), err.get("message"))
            return companies
        for place in data.get("places", []):
            companies.append({
                "name": place.get("displayName", {}).get("text", "Unknown"),
                "address": place.get("formattedAddress", ""),
                "place_id": place.get("id"),
                "website": None,
            })
    except Exception as e:
        log.warning("    ⚠️  Request failed: %s", e)
    return companies


def get_place_website(place_id: str) -> tuple[str | None, str | None]:
    """Get website and phone from Place Details (New API)."""
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "websiteUri,nationalPhoneNumber",
    }
    try:
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        data = response.json()
        if "error" in data:
            return None, None
        return data.get("websiteUri"), data.get("nationalPhoneNumber")
    except Exception:
        return None, None


# ─────────────────────────────────────────────
# CAREER PAGE SCRAPER
# ─────────────────────────────────────────────

def find_career_page(website_url: str) -> str | None:
    """Check homepage for career links, then try common URL patterns."""
    headers = {"User-Agent": BROWSER_USER_AGENT}
    base = f"{urlparse(website_url).scheme}://{urlparse(website_url).netloc}"

    # Scan homepage links for career-related hrefs
    try:
        resp = requests.get(website_url, headers=headers, timeout=SCRAPE_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if any(w in href for w in CAREER_LINK_KEYWORDS):
                return urljoin(website_url, a["href"])
    except Exception:
        pass

    # Try common career page URL patterns
    for path in CAREER_PATHS:
        try:
            url = base + path
            resp = requests.get(url, headers=headers, timeout=SCRAPE_TIMEOUT)
            if resp.status_code == 200 and len(resp.text) > MIN_CAREER_PAGE_SIZE:
                return url
        except Exception:
            continue

    return None


def check_for_keywords(career_url: str, keywords: list[str]) -> list[str]:
    """Scrape career page and return any matching job keywords."""
    headers = {"User-Agent": BROWSER_USER_AGENT}
    try:
        resp = requests.get(career_url, headers=headers, timeout=API_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator=" ").lower()
        return [kw for kw in keywords if kw in text]
    except Exception:
        return []


# ─────────────────────────────────────────────
# CORE RUNNER
# ─────────────────────────────────────────────

def run_profile(profile_key: str) -> dict:
    """Execute a single search profile through the 3-phase pipeline."""
    profile = PROFILES[profile_key]
    log.info("\n%s", "═" * 65)
    log.info("  PROFILE: %s", profile["name"])
    log.info("  Location: %s | Radius: %dkm (%dmi)",
             LOCATION_LABEL, TOTAL_RADIUS_METERS // 1000, round(TOTAL_RADIUS_METERS / 1609))
    log.info("  Search zones: %d", len(SEARCH_CENTERS))
    log.info("═" * 65)

    # Phase 1: Discover companies
    all_companies: dict[str, dict] = {}
    for center in SEARCH_CENTERS:
        log.info("\n  📍 Zone: %s", center["label"])
        for search_term in profile["place_searches"]:
            results = search_places(search_term, center["lat"], center["lng"])
            new = sum(
                1 for c in results
                if c["place_id"] not in all_companies
                and not all_companies.update({c["place_id"]: c})
            )
            if results:
                log.info("     '%s' → %d results, %d new", search_term, len(results), new)
            time.sleep(DELAY_PLACES_SEARCH)

    log.info("\n  ✅ %d unique companies found. Fetching websites...\n", len(all_companies))

    # Phase 2: Get websites
    companies_with_sites: list[dict] = []
    for place_id, company in all_companies.items():
        website, phone = get_place_website(place_id)
        if website:
            company["website"] = website
            company["phone"] = phone or ""
            companies_with_sites.append(company)
        time.sleep(DELAY_WEBSITE_LOOKUP)

    log.info("  %d companies have websites listed.", len(companies_with_sites))
    log.info("  %s", "─" * 60)

    # Phase 3: Check career pages
    results_with_jobs: list[dict] = []
    results_careers_only: list[dict] = []
    results_no_careers: list[dict] = []

    for company in companies_with_sites:
        log.info("  Checking: %s", company["name"])
        career_url = find_career_page(company["website"])

        if not career_url:
            results_no_careers.append(company)
            log.info("    ❌ No career page")
            time.sleep(DELAY_CAREER_CHECK / 2)
            continue

        company["career_url"] = career_url
        keywords_found = check_for_keywords(career_url, profile["job_keywords"])

        if keywords_found:
            company["keywords_found"] = keywords_found
            results_with_jobs.append(company)
            log.info("    🎯 MATCH: %s", ", ".join(keywords_found))
            log.info("       → %s", career_url)
        else:
            results_careers_only.append(company)
            log.info("    📄 Has careers page (no keyword match)")

        time.sleep(DELAY_CAREER_CHECK)

    # Print summary
    log.info("\n%s", "═" * 65)
    log.info("  RESULTS — %s", profile["name"])
    log.info("═" * 65)

    if results_with_jobs:
        log.info("\n  🎯 JOB KEYWORD MATCHES (%d)\n", len(results_with_jobs))
        for c in results_with_jobs:
            log.info("  Company  : %s", c["name"])
            log.info("  Address  : %s", c.get("address", "N/A"))
            log.info("  Phone    : %s", c.get("phone", "N/A"))
            log.info("  Website  : %s", c["website"])
            log.info("  Jobs URL : %s", c["career_url"])
            log.info("  Keywords : %s", ", ".join(c["keywords_found"]))
            log.info("")
    else:
        log.info("\n  No keyword matches found at this time.")

    if results_careers_only:
        log.info("\n  📄 HAS CAREER PAGE — Worth Bookmarking (%d)\n", len(results_careers_only))
        for c in results_careers_only:
            log.info("  %-42s %s", c["name"], c["career_url"])

    log.info("\n  ❌ No career page: %d companies", len(results_no_careers))
    log.info("     (Still worth a cold call or visit)\n")
    for c in results_no_careers:
        log.info("  %-42s %s  %s", c["name"], c.get("phone", ""), c.get("website", ""))

    # Save results
    output = {
        "profile": profile["name"],
        "location": LOCATION_LABEL,
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "summary": {
            "total_companies": len(all_companies),
            "with_websites": len(companies_with_sites),
            "keyword_matches": len(results_with_jobs),
            "has_careers_page": len(results_careers_only),
            "no_careers_page": len(results_no_careers),
        },
        "keyword_matches": results_with_jobs,
        "has_careers_page": results_careers_only,
        "no_careers_page": results_no_careers,
    }

    os.makedirs("results", exist_ok=True)
    filepath = os.path.join("results", profile["output_file"])
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    log.info("\n  💾 Saved to %s", filepath)

    return output


def run_all() -> None:
    """Run all profiles and print a combined summary."""
    all_summaries: list[dict] = []
    for key in PROFILES:
        result = run_profile(key)
        all_summaries.append({
            "profile": PROFILES[key]["name"],
            "summary": result["summary"],
            "output_file": PROFILES[key]["output_file"],
        })

    log.info("\n%s", "═" * 65)
    log.info("  ALL PROFILES COMPLETE — COMBINED SUMMARY")
    log.info("═" * 65 + "\n")
    total_matches = 0
    for s in all_summaries:
        matches = s["summary"]["keyword_matches"]
        total_matches += matches
        log.info("  %s", s["profile"])
        log.info("    Companies found : %d", s["summary"]["total_companies"])
        log.info("    With websites   : %d", s["summary"]["with_websites"])
        log.info("    Keyword matches : %d", matches)
        log.info("    Career pages    : %d", s["summary"]["has_careers_page"])
        log.info("")
    log.info("  Total keyword matches across all profiles: %d\n", total_matches)


def show_menu() -> str:
    """Display interactive profile selection menu."""
    print("\n" + "═" * 65)
    print("  LOCAL JOB SCRAPER")
    print(f"  Location: {LOCATION_LABEL} | ~{round(TOTAL_RADIUS_METERS / 1609)} mile radius")
    print("═" * 65)
    print()
    print("  Select a profile to run:")
    print()
    for key, profile in PROFILES.items():
        print(f"  [{key}] {profile['name']}")
    print()
    print(f"  [{len(PROFILES) + 1}] Run ALL profiles")
    print()
    return input("  Enter choice: ").strip()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main() -> None:
    """Parse args and run the appropriate profile(s)."""
    parser = argparse.ArgumentParser(description="Local Job Scraper")
    parser.add_argument(
        "--profile",
        help="Profile key to run, or 'all' (for GitHub Actions / non-interactive use)",
    )
    args = parser.parse_args()

    if args.profile:
        if args.profile == "all":
            run_all()
        elif args.profile in PROFILES:
            run_profile(args.profile)
        else:
            log.error("\n  Unknown profile '%s'. Check config.py for valid keys.", args.profile)
            sys.exit(1)
        return

    # Interactive menu (print stays here — user-facing prompt, not logging)
    choice = show_menu()
    all_key = str(len(PROFILES) + 1)
    if choice == all_key:
        run_all()
    elif choice in PROFILES:
        run_profile(choice)
    else:
        print("\n  Invalid choice.")
        sys.exit(1)


if __name__ == "__main__":
    main()

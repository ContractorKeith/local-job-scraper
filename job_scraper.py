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
from urllib.parse import urljoin, urlparse
from datetime import datetime

# Load API key — checks .env file first, then environment variable
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; env var or GitHub Secret also works

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
if not API_KEY:
    print("\n⚠️  No API key found.")
    print("   Set GOOGLE_PLACES_API_KEY in your environment or .env file.")
    print("   See README.md for instructions.\n")
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
# BUILD SEARCH ZONES
# ─────────────────────────────────────────────
# Places API (New) caps radius at 50,000m per search.
# We automatically generate overlapping circles to cover
# the full radius the user specified in config.py.

ZONE_RADIUS = 50000  # Max per API call

def build_search_centers(lat, lng, total_radius_meters):
    """Generate overlapping search centers to cover the full radius."""
    centers = [{"lat": lat, "lng": lng, "label": f"{LOCATION_LABEL} (center)"}]

    if total_radius_meters <= ZONE_RADIUS:
        return centers

    # Offset distance between center and surrounding zones
    offset_m = total_radius_meters * 0.55
    offset_deg_lat = offset_m / 111320
    offset_deg_lng = offset_m / (111320 * math.cos(math.radians(lat)))

    directions = [
        ("north", offset_deg_lat, 0),
        ("south", -offset_deg_lat, 0),
        ("east",  0,  offset_deg_lng),
        ("west",  0, -offset_deg_lng),
    ]

    if total_radius_meters > ZONE_RADIUS * 2:
        directions += [
            ("northeast",  offset_deg_lat * 0.7,  offset_deg_lng * 0.7),
            ("northwest",  offset_deg_lat * 0.7, -offset_deg_lng * 0.7),
            ("southeast", -offset_deg_lat * 0.7,  offset_deg_lng * 0.7),
            ("southwest", -offset_deg_lat * 0.7, -offset_deg_lng * 0.7),
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

def search_places(query, lat, lng):
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
    companies = []
    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        data = response.json()
        if "error" in data:
            err = data["error"]
            print(f"    ⚠️  API Error {err.get('code')}: {err.get('message')}")
            return companies
        for place in data.get("places", []):
            companies.append({
                "name": place.get("displayName", {}).get("text", "Unknown"),
                "address": place.get("formattedAddress", ""),
                "place_id": place.get("id"),
                "website": None,
            })
    except Exception as e:
        print(f"    ⚠️  Request failed: {e}")
    return companies


def get_place_website(place_id):
    """Get website and phone from Place Details (New API)."""
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "websiteUri,nationalPhoneNumber",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if "error" in data:
            return None, None
        return data.get("websiteUri"), data.get("nationalPhoneNumber")
    except Exception:
        return None, None


# ─────────────────────────────────────────────
# CAREER PAGE SCRAPER
# ─────────────────────────────────────────────

def find_career_page(website_url):
    """Check homepage for career links, then try common URL patterns."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    base = f"{urlparse(website_url).scheme}://{urlparse(website_url).netloc}"

    try:
        resp = requests.get(website_url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if any(w in href for w in ["career", "job", "hiring", "employment", "join", "apply", "work-with"]):
                return urljoin(website_url, a["href"])
    except Exception:
        pass

    for path in CAREER_PATHS:
        try:
            url = base + path
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200 and len(resp.text) > 500:
                return url
        except Exception:
            continue

    return None


def check_for_keywords(career_url, keywords):
    """Scrape career page and return any matching job keywords."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(career_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator=" ").lower()
        return [kw for kw in keywords if kw in text]
    except Exception:
        return []


# ─────────────────────────────────────────────
# CORE RUNNER
# ─────────────────────────────────────────────

def run_profile(profile_key):
    profile = PROFILES[profile_key]
    print(f"\n{'═' * 65}")
    print(f"  PROFILE: {profile['name']}")
    print(f"  Location: {LOCATION_LABEL} | Radius: {TOTAL_RADIUS_METERS // 1000}km ({round(TOTAL_RADIUS_METERS / 1609)}mi)")
    print(f"  Search zones: {len(SEARCH_CENTERS)}")
    print(f"{'═' * 65}")

    # Phase 1: Discover companies
    all_companies = {}
    for center in SEARCH_CENTERS:
        print(f"\n  📍 Zone: {center['label']}")
        for search_term in profile["place_searches"]:
            results = search_places(search_term, center["lat"], center["lng"])
            new = sum(
                1 for c in results
                if c["place_id"] not in all_companies
                and not all_companies.update({c["place_id"]: c})
            )
            if results:
                print(f"     '{search_term}' → {len(results)} results, {new} new")
            time.sleep(0.4)

    print(f"\n  ✅ {len(all_companies)} unique companies found. Fetching websites...\n")

    # Phase 2: Get websites
    companies_with_sites = []
    for place_id, company in all_companies.items():
        website, phone = get_place_website(place_id)
        if website:
            company["website"] = website
            company["phone"] = phone or ""
            companies_with_sites.append(company)
        time.sleep(0.15)

    print(f"  {len(companies_with_sites)} companies have websites listed.")
    print(f"  {'─' * 60}")

    # Phase 3: Check career pages
    results_with_jobs = []
    results_careers_only = []
    results_no_careers = []

    for company in companies_with_sites:
        print(f"  Checking: {company['name']}")
        career_url = find_career_page(company["website"])

        if not career_url:
            results_no_careers.append(company)
            print(f"    ❌ No career page")
            time.sleep(0.4)
            continue

        company["career_url"] = career_url
        keywords_found = check_for_keywords(career_url, profile["job_keywords"])

        if keywords_found:
            company["keywords_found"] = keywords_found
            results_with_jobs.append(company)
            print(f"    🎯 MATCH: {', '.join(keywords_found)}")
            print(f"       → {career_url}")
        else:
            results_careers_only.append(company)
            print(f"    📄 Has careers page (no keyword match)")

        time.sleep(0.8)

    # Print summary
    print(f"\n{'═' * 65}")
    print(f"  RESULTS — {profile['name']}")
    print(f"{'═' * 65}")

    if results_with_jobs:
        print(f"\n  🎯 JOB KEYWORD MATCHES ({len(results_with_jobs)})\n")
        for c in results_with_jobs:
            print(f"  Company  : {c['name']}")
            print(f"  Address  : {c.get('address', 'N/A')}")
            print(f"  Phone    : {c.get('phone', 'N/A')}")
            print(f"  Website  : {c['website']}")
            print(f"  Jobs URL : {c['career_url']}")
            print(f"  Keywords : {', '.join(c['keywords_found'])}")
            print()
    else:
        print("\n  No keyword matches found at this time.")

    if results_careers_only:
        print(f"\n  📄 HAS CAREER PAGE — Worth Bookmarking ({len(results_careers_only)})\n")
        for c in results_careers_only:
            print(f"  {c['name']:<42} {c['career_url']}")

    print(f"\n  ❌ No career page: {len(results_no_careers)} companies")
    print(f"     (Still worth a cold call or visit)\n")
    for c in results_no_careers:
        print(f"  {c['name']:<42} {c.get('phone', '')}  {c.get('website', '')}")

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
    print(f"\n  💾 Saved to {filepath}")

    return output


def run_all():
    all_summaries = []
    for key in PROFILES:
        result = run_profile(key)
        all_summaries.append({
            "profile": PROFILES[key]["name"],
            "summary": result["summary"],
            "output_file": PROFILES[key]["output_file"],
        })

    print(f"\n{'═' * 65}")
    print("  ALL PROFILES COMPLETE — COMBINED SUMMARY")
    print(f"{'═' * 65}\n")
    total_matches = 0
    for s in all_summaries:
        matches = s["summary"]["keyword_matches"]
        total_matches += matches
        print(f"  {s['profile']}")
        print(f"    Companies found : {s['summary']['total_companies']}")
        print(f"    With websites   : {s['summary']['with_websites']}")
        print(f"    Keyword matches : {matches}")
        print(f"    Career pages    : {s['summary']['has_careers_page']}")
        print()
    print(f"  Total keyword matches across all profiles: {total_matches}\n")


def show_menu():
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

def main():
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
            print(f"\n  Unknown profile '{args.profile}'. Check config.py for valid keys.")
            sys.exit(1)
        return

    # Interactive menu
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

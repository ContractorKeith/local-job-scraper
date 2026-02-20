# ─────────────────────────────────────────────────────────────────
# config.py — Your personal settings
# This is the ONLY file you need to edit to customize the scraper.
# ─────────────────────────────────────────────────────────────────

# ── YOUR LOCATION ────────────────────────────────────────────────
# Find your coordinates: go to maps.google.com, right-click your
# city center, and click the lat/lng numbers that appear.

LOCATION_LABEL = "Your City, ST"   # Just for display in output
LAT  = 00.0000                     # Latitude  (e.g. 28.9384)
LNG  = -00.0000                    # Longitude (e.g. -81.9548)

# ── SEARCH RADIUS ────────────────────────────────────────────────
# How far out to search, in meters.
# Places API (New) hard cap is 50,000m (~31 miles) per zone.
# The script runs multiple overlapping zones automatically to cover
# larger areas — just set your desired total radius below.
#
#   30 miles  =  48,000m   (within one zone, fast)
#   60 miles  =  96,000m   (uses 5 zones, ~2x longer to run)
#  100 miles  = 160,000m   (uses 9 zones, slower but thorough)

TOTAL_RADIUS_METERS = 96000


# ── JOB PROFILES ─────────────────────────────────────────────────
# Each profile = a set of company types to search + job keywords
# to look for on their career pages.
#
# You can edit existing profiles, add new ones, or delete ones
# you don't need. Profile keys must be unique strings ("1", "2", etc.)

PROFILES = {

    "1": {
        "name": "Outside Sales — Technology & Software",

        # What to search for on Google Maps/Places
        "place_searches": [
            "software company",
            "technology company",
            "IT services",
            "managed service provider",
            "SaaS company",
            "cloud services",
            "cybersecurity company",
            "telecommunications",
            "business solutions",
        ],

        # Keywords to look for on company career pages
        "job_keywords": [
            "outside sales",
            "outside sales representative",
            "account executive",
            "territory manager",
            "account manager",
            "sales representative",
            "business development",
            "business development representative",
            "regional sales manager",
            "sales manager",
        ],

        "output_file": "results_tech_sales.json",
    },

    "2": {
        "name": "Outside Sales — Medical & Healthcare",

        "place_searches": [
            "medical device company",
            "pharmaceutical company",
            "healthcare supplier",
            "medical equipment",
            "dental supplier",
            "laboratory services",
            "home health agency",
            "medical staffing",
        ],

        "job_keywords": [
            "outside sales",
            "territory sales",
            "territory manager",
            "account manager",
            "account executive",
            "sales representative",
            "medical sales",
            "device sales",
            "clinical sales",
            "business development",
        ],

        "output_file": "results_medical_sales.json",
    },

    "3": {
        "name": "Outside Sales — Industrial & Distribution",

        "place_searches": [
            "industrial distributor",
            "wholesale distributor",
            "manufacturing company",
            "industrial supply",
            "equipment dealer",
            "logistics company",
            "freight company",
            "supply chain",
            "packaging supplier",
        ],

        "job_keywords": [
            "outside sales",
            "outside sales representative",
            "territory manager",
            "account manager",
            "account executive",
            "sales representative",
            "business development",
            "regional sales",
            "distribution sales",
            "industrial sales",
        ],

        "output_file": "results_industrial_sales.json",
    },

    # ── EXAMPLE: Add your own custom profile ─────────────────────
    # "4": {
    #     "name": "Healthcare — Admin & Operations",
    #     "place_searches": [
    #         "medical clinic",
    #         "dental office",
    #         "urgent care",
    #     ],
    #     "job_keywords": [
    #         "office manager",
    #         "practice manager",
    #         "operations manager",
    #         "administrator",
    #     ],
    #     "output_file": "results_healthcare.json",
    # },
}


# ── CAREER PAGE URL PATTERNS ──────────────────────────────────────
# Common paths the scraper will try if it can't find a career link
# on the homepage. Add more here if you're finding misses.

CAREER_PATHS = [
    "/careers", "/careers/", "/jobs", "/jobs/",
    "/join-us", "/join-our-team", "/work-with-us",
    "/employment", "/opportunities", "/hiring",
    "/open-positions", "/apply", "/now-hiring",
    "/career-opportunities", "/join", "/work-here",
    "/positions", "/openings",
]
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
        "name": "Fence & Gate — Commercial Estimator Focus",

        # What to search for on Google Maps/Places
        "place_searches": [
            "fence company",
            "fencing contractor",
            "fence installation",
            "commercial fence",
            "ornamental iron fence",
            "aluminum fence",
            "vinyl fence",
            "chain link fence",
            "gate company",
            "gate operator",
            "access control gate",
            "automatic gate",
        ],

        # Keywords to look for on company career pages
        "job_keywords": [
            "commercial estimator",
            "fence estimator",
            "estimator",
            "estimating",
            "sales estimator",
            "project manager",
            "outside sales",
            "account manager",
            "sales representative",
            "bid manager",
            "take-off",
        ],

        "output_file": "results_fence.json",
    },

    "2": {
        "name": "Building Materials & Outside Sales",

        "place_searches": [
            "building materials supplier",
            "lumber yard",
            "lumber supply",
            "roofing supply",
            "roofing contractor",
            "masonry supply",
            "concrete supplier",
            "window and door distributor",
            "millwork supplier",
            "hardware distributor",
            "construction supply",
            "pool contractor",
            "pool builder",
            "screen enclosure",
            "pool enclosure",
            "irrigation contractor",
            "irrigation supply",
            "landscape supply",
            "landscape contractor",
        ],

        "job_keywords": [
            "outside sales",
            "outside sales representative",
            "territory manager",
            "account manager",
            "sales representative",
            "sales rep",
            "business development",
            "regional sales",
            "commercial sales",
            "estimator",
            "project manager",
            "sales manager",
        ],

        "output_file": "results_building_materials.json",
    },

    "3": {
        "name": "General Construction — Estimator & Project Management",

        "place_searches": [
            "general contractor",
            "commercial contractor",
            "construction company",
            "home builder",
            "residential builder",
            "remodeling contractor",
            "renovation contractor",
            "commercial construction",
            "site contractor",
            "civil contractor",
            "concrete contractor",
            "framing contractor",
        ],

        "job_keywords": [
            "estimator",
            "senior estimator",
            "junior estimator",
            "chief estimator",
            "estimating manager",
            "preconstruction",
            "pre-construction",
            "project manager",
            "project engineer",
            "assistant project manager",
            "superintendent",
            "bid coordinator",
            "bid manager",
            "take-off",
            "takeoff",
            "construction manager",
            "operations manager",
        ],

        "output_file": "results_general_construction.json",
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

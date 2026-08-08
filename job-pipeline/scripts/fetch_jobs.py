import os
import json
import requests

# ── Adzuna API credentials (injected from GitHub Secrets) ──────────────────
ADZUNA_APP_ID  = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")

# ── Adzuna India API base URL ───────────────────────────────────────────────
# "in" = India country code in Adzuna's URL scheme
BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search/1"

# ── What to search for ──────────────────────────────────────────────────────
# Each query is searched across every location below.
SEARCH_QUERIES = [
    "DevOps Engineer",
    "Site Reliability Engineer",
    "Platform Engineer",
    "Cloud Engineer DevOps",
    "SRE Kubernetes AWS",
]

LOCATIONS = [
    "Bangalore",
    "Hyderabad",
    "Pune",
    "Chennai",
    "Mumbai",
]

# ── Deduplication file ──────────────────────────────────────────────────────
# Stores job IDs already processed so reruns don't repeat the same jobs.
SEEN_JOBS_FILE = "output/seen_jobs.json"


def load_seen_job_ids():
    """
    Read the list of job IDs already processed in previous runs.
    Returns a Python set for O(1) lookup.
    If the file doesn't exist yet (first run), returns an empty set.
    """
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_job_ids(seen_ids):
    """
    Write the updated set of seen job IDs back to the file.
    This file gets committed to the repo so the next run reads it.
    """
    os.makedirs("output", exist_ok=True)
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen_ids), f)


def fetch_jobs_for_query(query, location):
    """
    Call Adzuna API for one query + location combination.
    Returns a list of job dicts, or empty list on failure.
    """
    params = {
        "app_id":           ADZUNA_APP_ID,
        "app_key":          ADZUNA_APP_KEY,
        "results_per_page": 5,        # 5 jobs per query/location combo
        "what":             query,    # job title / keyword search
        "where":            location, # city filter
        "sort_by":          "date",   # newest first
        "max_days_old":     1,        # only jobs posted in last 24 hours
        "content-type":     "application/json",
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
    except requests.exceptions.RequestException as e:
        print(f"  Network error for '{query}' in {location}: {e}")
        return []

    if response.status_code != 200:
        print(f"  Adzuna error {response.status_code} for '{query}' in {location}")
        return []

    data     = response.json()
    raw_jobs = data.get("results", [])

    formatted = []
    for job in raw_jobs:
        formatted.append({
            "id":          str(job.get("id", "")),
            "title":       job.get("title", ""),
            "company":     job.get("company", {}).get("display_name", "Unknown"),
            "location":    job.get("location", {}).get("display_name", location),
            "description": job.get("description", ""),
            "url":         job.get("redirect_url", ""),
            "posted":      job.get("created", ""),
        })

    return formatted


def fetch_all_jobs():
    """
    Main entry point. Iterates all query + location combinations,
    deduplicates, skips already-seen jobs, returns only new ones.
    """
    seen_ids = load_seen_job_ids()

    all_raw    = []
    seen_pairs = set()  # (title.lower, company.lower) — catches same job from multiple queries

    for query in SEARCH_QUERIES:
        for location in LOCATIONS:
            print(f"  Fetching: '{query}' in {location}")
            jobs = fetch_jobs_for_query(query, location)

            for job in jobs:
                pair = (job["title"].lower(), job["company"].lower())
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    all_raw.append(job)

    # Filter out jobs already processed in a previous pipeline run
    new_jobs = [j for j in all_raw if j["id"] not in seen_ids]

    print(f"  Found {len(all_raw)} total jobs, {len(new_jobs)} are new")
    return new_jobs, seen_ids

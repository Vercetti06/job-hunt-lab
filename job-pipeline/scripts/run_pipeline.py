import os
import time
from datetime import datetime, timezone

from fetch_jobs    import fetch_all_jobs, save_seen_job_ids
from tailor_resume import tailor_for_job

# ── Output directory ─────────────────────────────────────────────────────────
# Jobs are saved under output/YYYY-MM-DD/ so each day's results are grouped.
OUTPUT_BASE = "output"


def sanitize(text, max_len=35):
    """
    Strip characters that are unsafe in filenames.
    Keeps alphanumerics, spaces, hyphens, underscores.
    Caps length so filenames don't get absurdly long.
    """
    cleaned = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_"
        for c in text
    ).strip()
    return cleaned[:max_len]


def save_output(job, tailored_content, run_timestamp):
    """
    Write one markdown file per job under output/YYYY-MM-DD/.
    File is immediately readable on GitHub — GitHub renders markdown natively.
    """
    date_str  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    time_str  = datetime.now(timezone.utc).strftime("%H%M")
    date_dir  = os.path.join(OUTPUT_BASE, date_str)
    os.makedirs(date_dir, exist_ok=True)

    company  = sanitize(job["company"])
    title    = sanitize(job["title"])
    filename = f"{time_str}_{company}_{title}.md"
    filepath = os.path.join(date_dir, filename)

    content = f"""# {job['title']}
**Company:** {job['company']}  
**Location:** {job['location']}  
**Posted:** {job['posted']}  
**Apply:** {job['url']}  
**Pipeline run:** {run_timestamp} UTC  

---

## Original Job Description

{job['description']}

---

{tailored_content}
"""

    with open(filepath, "w") as f:
        f.write(content)

    print(f"    Saved → {filepath}")
    return filepath


def main():
    run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*55}")
    print(f"Pipeline started: {run_timestamp} UTC")
    print(f"{'='*55}\n")

    # ── Step 1: Fetch new jobs ───────────────────────────────────────────────
    print("STEP 1: Fetching jobs from Adzuna...")
    new_jobs, seen_ids = fetch_all_jobs()

    if not new_jobs:
        print("\nNo new jobs found this run. Exiting cleanly.")
        return

    print(f"\nSTEP 2: Tailoring resume for {len(new_jobs)} new jobs...\n")

    processed_ids = set()
    failed_ids    = set()

    for i, job in enumerate(new_jobs, start=1):
        print(f"  [{i}/{len(new_jobs)}] {job['title']} — {job['company']}")

        tailored = tailor_for_job(job)

        if tailored:
            save_output(job, tailored, run_timestamp)
            processed_ids.add(job["id"])
        else:
            print(f"    Skipped — Groq call failed")
            failed_ids.add(job["id"])

        # Sleep 3 seconds between Groq calls to stay under rate limits.
        # Groq free tier allows 30 requests/minute — 3s gap = 20 req/min, well under.
        if i < len(new_jobs):
            time.sleep(3)

    # ── Step 3: Update the seen-jobs file ───────────────────────────────────
    # Mark successfully processed jobs as seen so the next run skips them.
    # Failed jobs are NOT marked seen — they'll be retried next run.
    updated_seen = seen_ids | processed_ids
    save_seen_job_ids(updated_seen)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"Pipeline complete: {run_timestamp} UTC")
    print(f"  Processed : {len(processed_ids)}")
    print(f"  Failed    : {len(failed_ids)}")
    print(f"  Total seen: {len(updated_seen)}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()

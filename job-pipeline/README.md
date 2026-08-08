# Job Pipeline

Automated job fetching and resume tailoring for DevOps / SRE / Platform Engineer
roles in India. Runs every 5 hours via GitHub Actions. Output is committed back
to this repo as markdown files — readable directly on GitHub.

---

## How It Works

```
Every 5 hours (GitHub Actions):
  1. fetch_jobs.py   → Calls Adzuna API → filters DevOps/SRE roles in India
                     → skips jobs already processed in previous runs
  2. tailor_resume.py → Sends each JD + your background to Groq (Llama 3.1 70B)
                      → Returns: fit score, tailored summary, bullets, missing skills,
                        ATS keywords, referral note
  3. run_pipeline.py → Saves one markdown file per job under output/YYYY-MM-DD/
  4. GitHub Actions  → Commits output/ back to this repo
```

---

## One-Time Setup (Do This Once)

### Step 1 — Get Adzuna API credentials (free, no card)
1. Go to https://developer.adzuna.com
2. Click "Register" → create a free account
3. After login, go to Dashboard → your App ID and App Key are shown there

### Step 2 — Get Groq API key (free, no card)
1. Go to https://console.groq.com
2. Sign up with Google or email
3. Go to API Keys → Create API Key → copy it

### Step 3 — Add secrets to GitHub repo
In this repo on GitHub:
`Settings → Secrets and variables → Actions → New repository secret`

Add these three secrets:

| Secret Name    | Where to get it          |
|----------------|--------------------------|
| ADZUNA_APP_ID  | Adzuna dashboard         |
| ADZUNA_APP_KEY | Adzuna dashboard         |
| GROQ_API_KEY   | Groq console → API Keys  |

### Step 4 — Push this code to your new repo
```bash
# Create a new private repo on GitHub first (github.com → New repository)
# Then:

git clone https://github.com/Vercetti06/<your-new-repo-name>.git
cd <your-new-repo-name>

# Copy all files from this download into the folder, then:

git add .
git commit -m "Initial pipeline setup"
git push
```

### Step 5 — Test it manually before waiting for the schedule
1. Go to your repo on GitHub
2. Click the **Actions** tab
3. Click **Job Pipeline** in the left sidebar
4. Click **Run workflow** → **Run workflow** (green button)
5. Watch the run — it takes ~2-3 minutes
6. Check the `output/` folder for results

---

## Viewing Results

After each run, new files appear under `output/YYYY-MM-DD/`.  
Each file is a markdown document with:
- Original job description
- Fit score (out of 10)
- Tailored professional summary
- 5 tailored bullet points
- Missing skills (honest)
- ATS keywords to add
- Referral priority note

GitHub renders markdown natively — just click any `.md` file to read it.

---

## Customisation

| File | What to change |
|------|----------------|
| `scripts/background.py` | Update your skills, metrics, target companies |
| `scripts/fetch_jobs.py` | Change `SEARCH_QUERIES` or `LOCATIONS` |
| `.github/workflows/job_pipeline.yml` | Change the cron schedule |

### Changing the schedule
Current: `0 */5 * * *` = every 5 hours  
Every 6 hours: `0 */6 * * *`  
Twice a day (9am + 9pm): `0 9,21 * * *`

---

## ⚠️  Before Applying to Any Role
Review `scripts/background.py` and confirm the metrics marked
`# ⚠️  CONFIRM THESE NUMBERS` are accurate before letting the pipeline
use them in tailored content you actually submit.

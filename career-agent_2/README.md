# Career Agent

A personal career agent that runs entirely on your own machine. It interviews you to build a
profile, searches free job-board APIs for matching roles, and — its core feature — takes a link
to a specific job posting and produces a tailored CV and cover letter for it, using a
drafter → reviewer agent loop before you ever see the result. It also generates interview prep
and tracks every application you run through it.

Everything (your profile, application history, generated documents) is stored locally in a
SQLite database in `data/`. Nothing is sent anywhere except:
- to Anthropic's API (to run the agents), and
- to whatever job posting URL or job-board API you ask it to fetch.

## 1. Install

Requires Python 3.10+.

```bash
cd career-agent
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure

```bash
cp .env.example .env
```

Then edit `.env`:

- **`ANTHROPIC_API_KEY`** (required) — get one at https://console.anthropic.com/. Nothing in
  this app works without it, since it's what powers the interview, fit evaluation, drafting, and
  review agents.
- **Job board keys (all optional)** — the core "Apply" flow (paste one job link → get a tailored
  CV and cover letter) needs none of these. They only power the broader "Search" tab:
  - `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` — free at https://developer.adzuna.com/
  - `USAJOBS_API_KEY` / `USAJOBS_USER_AGENT_EMAIL` — free at https://developer.usajobs.gov/
  - `JSEARCH_API_KEY` — aggregates LinkedIn/Indeed/Glassdoor/ZipRecruiter via Google for Jobs.
    Free tier at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
  - RemoteOK and Remotive need no key and work out of the box.
- **`CAREER_AGENT_CONTACT_EMAIL`** — used as a polite User-Agent string when fetching job pages.
- **LaTeX (optional)** — if you want compiled PDFs (not just `.docx`), install a LaTeX
  distribution so `pdflatex` is on your PATH:
  - macOS: `brew install --cask mactex-no-gui` (or the full MacTeX)
  - Ubuntu/Debian: `sudo apt install texlive texlive-latex-extra texlive-fonts-recommended`
  - Windows: install [MiKTeX](https://miktex.org/) or [TeX Live](https://tug.org/texlive/)

  Without LaTeX installed, the app still writes the `.tex` source for every document (you can
  compile it later, or paste it into [Overleaf](https://overleaf.com)) and always gives you a
  polished `.docx` either way.

### Watching specific companies directly (free, no key)

Greenhouse, Lever, Ashby, and SmartRecruiters all expose public, no-key JSON endpoints for a
company's own job board — the same ones their careers page calls to render listings. In the
Search tab's "Watched companies" section, add a company with its ATS type and board slug (the
part of the careers URL identifying the company, e.g. `boards.greenhouse.io/**acme**` → slug
`acme`). Often faster than LinkedIn/Indeed, which syndicate with some lag.

### The bookmarklet clipper (free, no key)

For sites with no public API (LinkedIn, Indeed, Naukri, Instahyre, Hirist, Uplers, or anywhere
else): in the Search tab, drag the "📎 Clip jobs to Career Agent" link to your browser's bookmarks
bar. While browsing a job posting or search-results page you're already logged into, click it —
it reads whatever's already rendered on the page (no extra requests to the site) and sends it to
your local app. Per-site selectors are best-effort and may need small tweaks if a site changes its
markup — see `frontend/bookmarklet.js`, where each site's parser is isolated so one breaking
doesn't affect the others.

### Gmail job-alert ingestion (free, one-time setup)

Reads job-alert emails from your own Gmail — the alerts you set up through LinkedIn/Indeed/
Naukri/Instahyre/Hirist/Uplers's own "email me matching jobs" feature. This is push-based (often
faster than any poll/scrape) and fully within each platform's own terms, since it's their intended
notification mechanism, read via Gmail's official read-only API with your consent.

One-time setup:
1. Go to https://console.cloud.google.com/, create a new project (any name).
2. APIs & Services → Library → enable the **Gmail API**.
3. APIs & Services → OAuth consent screen → External → fill in an app name and your email → add
   yourself as a test user → save.
4. APIs & Services → Credentials → Create Credentials → OAuth client ID → Application type
   **Desktop app** → Create.
5. Download the JSON, save it as `data/gmail_credentials.json` in this project.
6. In the app's Search tab, click **Authorize Gmail** — a browser tab opens for you to grant
   read-only access to your own inbox. This happens once; after that, click **Check for new
   alerts** any time.
7. Go set up saved-search job alerts on LinkedIn/Indeed/Naukri/Instahyre/Hirist/Uplers through
   their own websites (each has this under notification/alert settings) so the emails exist to
   ingest.

Sender addresses and URL patterns per platform are in `data/gmail_alert_sources.json` — these can
drift over time, so if a platform's alerts stop producing results, open an actual alert email you
received, check the real sender address, and adjust the entry.

## 3. Run

```bash
python run.py
```

This starts the server at `http://127.0.0.1:8420` and opens it in your browser automatically.

## Running on AWS EC2 instead of a laptop (fresh instance each session)

If you don't have a persistent machine and launch a new/different EC2 instance each session,
local disk storage doesn't survive between sessions — so the workflow is: restore your last
backup on launch, use the app, download a fresh backup before you're done.

**Quick start on a fresh Ubuntu instance:**
```bash
scp career-agent.zip ubuntu@<your-instance-ip>:~
scp deploy/ec2-bootstrap.sh ubuntu@<your-instance-ip>:~   # if not already inside the zip
ssh ubuntu@<your-instance-ip>
chmod +x ec2-bootstrap.sh && ./ec2-bootstrap.sh
```
Then edit `.env` as the script instructs and run `python run.py`.

**Exposing it directly (no SSH tunnel):** set in `.env`:
```
CAREER_AGENT_HOST=0.0.0.0
BASIC_AUTH_USERNAME=pick-a-username
BASIC_AUTH_PASSWORD=pick-a-strong-password
```
Then in the EC2 console, open the app's port (8420 by default) in the instance's **security
group — restricted to your own IP**, not `0.0.0.0/0`. Basic Auth stops casual access but sends
credentials base64-encoded, not encrypted — fine behind an IP-restricted security group, but if
you want this reachable from anywhere, put a TLS reverse proxy in front (e.g. `caddy
reverse-proxy --to localhost:8420` with a domain name gets you free auto-renewing HTTPS in one
line).

**Backing up and restoring your data:** the header has **Download backup** and **Restore
backup** at all times. Download bundles your profile, applications, tracker, generated CV/cover
letters, and Gmail token into one `.zip`. Before terminating an instance, download it somewhere
you control (your phone, a personal cloud drive); after launching the next one, restore it before
you start using the app. This deliberately excludes `.env` (your API keys) — keep that in a
password manager or re-type the essentials each session.

**Making "fresh instance" launches fast:** installing Python packages (and especially LaTeX,
which can take 5-10+ minutes) from scratch every session is slow. Once you've got a working
instance, use the EC2 console (Actions → Image → Create Image) to bake an AMI with everything
already installed. Future "fresh" launches from that AMI start in about the time EC2 takes to
boot — you'll only need to restore your backup and set `.env`, not reinstall anything.

## How it works

**Profile tab** — a conversational intake interview. Answer naturally; it asks one question at a
time about your work history, skills, goals, and how you write/talk, so later documents sound
like you rather than generic corporate copy. When it has enough, it saves a structured profile.

**Search tab** — pulls listings from whichever job APIs you configured, ranks them by a free,
local keyword overlap against your profile (no API cost), and lets you send any listing straight
to Apply. Also includes: a watched-companies list hitting Greenhouse/Lever/Ashby/SmartRecruiters
directly, a bookmarklet clipper for sites with no API, and Gmail job-alert ingestion — see below.

**Apply tab** — the core feature. Paste a link to one specific posting:
1. Fetches and reads that page (only that one page — this app doesn't crawl job boards).
2. A fit-evaluation agent scores the match and flags what to emphasize.
3. A drafter agent writes a tailored CV and cover letter grounded only in facts from your profile.
4. A reviewer agent — a separate pass with no attachment to the draft — checks it for
   fabrication, generic phrasing, and voice, and sends it back for revision (up to 3 rounds) until
   it's approved.
5. Final documents are rendered as `.docx` and, if LaTeX is installed, compiled `.pdf` too (with
   `.tex` source always saved).
6. The result is saved to your Tracker automatically.

**Tracker tab** — every application you've run through Apply, with status (drafted / applied /
interviewing / offer / rejected / withdrawn), notes, document downloads, and on-demand interview
prep (likely questions specific to that posting, smart questions to ask them, and how to
proactively address any gaps the fit evaluation flagged).

## Notes on job search

This app never scrapes or crawls job boards like LinkedIn or Indeed — that violates their terms
of service and gets blocked immediately regardless. The Search tab only talks to job boards with
public, free APIs meant for this kind of use (Adzuna, USAJobs, RemoteOK, Remotive). The Apply
flow works with a link to a posting from *any* site, since fetching one specific page you provide
is just reading, not crawling.

## Project layout

```
app/
  main.py              FastAPI app + routing + CORS (for the bookmarklet) + Basic Auth middleware
  auth.py               Optional HTTP Basic Auth (for exposing on a VM)
  config.py            Settings from .env
  models.py             Shared data models
  storage.py            SQLite persistence
  agents/               Anthropic-powered agents (interview, fit, drafter, reviewer, prep)
  job_sources/           Adzuna / RemoteOK / Remotive / USAJobs / JSearch + aggregator
  job_sources/ats_watch.py   Direct Greenhouse / Lever / Ashby / SmartRecruiters integrations
  integrations/gmail_alerts.py   Gmail job-alert email ingestion
  fetchers/              Single-URL job posting fetcher
  documents/             DOCX (python-docx) and LaTeX (Jinja2 + pdflatex) rendering
  routers/               API endpoints, including backup.py (export/restore)
frontend/                Vanilla HTML/CSS/JS single-page UI (no build step)
  bookmarklet.js          Clipper bookmarklet source
deploy/ec2-bootstrap.sh   Fast provisioning script for a fresh EC2 instance
data/                    Your local SQLite DB, generated documents, Gmail credentials (created on first run)
```

## Extending it

Adding another job board is one file: implement `search(query, location, limit)` returning a
list of `JobPosting` in `app/job_sources/`, matching the interface in `base.py`, then register it
in `app/job_sources/aggregator.py`.

import os
import json
import time
import requests
from background import BACKGROUND

# ── Groq API credentials (injected from GitHub Secrets) ────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

# ── Model ───────────────────────────────────────────────────────────────────
# Groq hosts open-source models. llama-3.1-70b-versatile is their most
# capable free model. Check console.groq.com/docs/models if this changes.
MODEL = "llama-3.1-70b-versatile"

# ── System prompt — Groq receives this before every request ─────────────────
# This sets the AI's role and loads the candidate's background as context.
SYSTEM_PROMPT = f"""You are a professional DevOps resume tailor helping a candidate
named Yaswanth find and apply for Senior DevOps / SRE / Platform Engineering roles.

Here is Yaswanth's complete background:

{BACKGROUND}

Your job:
- Analyse each job description carefully.
- Produce tailored resume content using ONLY skills and experience Yaswanth actually has.
- Never fabricate experience, certifications, or tools he hasn't used.
- Match the exact language and keywords the JD uses wherever his real experience allows.
- Be direct and specific — no filler sentences."""


def tailor_for_job(job):
    """
    Sends one job's details to Groq and returns the tailored content string.
    Returns None if the API call fails.
    """

    user_prompt = f"""Analyse this job posting and produce tailored resume content for Yaswanth.

JOB TITLE:    {job['title']}
COMPANY:      {job['company']}
LOCATION:     {job['location']}
JOB POSTING URL: {job['url']}

JOB DESCRIPTION:
{job['description']}

---

Produce output in this exact format (use these exact section headers):

## FIT SCORE
Score out of 10, followed by one sentence explaining the match level and the main reason.

## TAILORED PROFESSIONAL SUMMARY
3 sentences. Rewrite Yaswanth's summary to mirror this JD's language and priorities.
Do not change what he has done — only how it is framed.

## TAILORED BULLET POINTS
5 bullet points. Each must:
- Start with a strong action verb
- Use keywords from this specific JD
- Include a metric where Yaswanth's background supports one
- Reflect only real experience

## MISSING SKILLS
Honest list of required skills from this JD that Yaswanth does NOT have.
If nothing is missing, write "None identified."

## ATS KEYWORDS TO ADD
8–10 keywords from this JD that should appear somewhere in the resume.
List only — one per line.

## APPLY VIA REFERRAL NOTE
One sentence: which of Yaswanth's target companies does this company relate to,
or is it a new target? Should he prioritise this role?
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }

    payload = {
        "model":    MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0.3,   # Low = consistent, structured output. High = creative.
        "max_tokens":  1200,  # Enough for all sections without truncating.
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"    Network error calling Groq: {e}")
        return None

    if response.status_code == 429:
        # 429 = rate limit hit. Wait 60 seconds and retry once.
        print("    Groq rate limit hit — waiting 60 seconds before retry")
        time.sleep(60)
        try:
            response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            print(f"    Retry also failed: {e}")
            return None

    if response.status_code != 200:
        print(f"    Groq error {response.status_code}: {response.text[:200]}")
        return None

    data = response.json()
    return data["choices"][0]["message"]["content"]

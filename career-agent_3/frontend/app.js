// ============================================================
// Career Agent — frontend logic (vanilla JS, no build step)
// ============================================================

const el = (sel) => document.querySelector(sel);
const els = (sel) => Array.from(document.querySelectorAll(sel));

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function api(path, options = {}) {
  const opts = { headers: { "Content-Type": "application/json" }, ...options };
  const res = await fetch(path, opts);
  let body = null;
  try { body = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) {
    const detail = (body && body.detail) ? body.detail : res.statusText;
    throw new Error(detail);
  }
  return body;
}

// ---------------- Tabs ----------------

els(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    els(".tab-btn").forEach((b) => b.classList.remove("active"));
    els(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    el(`#panel-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "tracker") loadTracker();
  });
});

// ---------------- Status strip ----------------

async function loadStatus() {
  const strip = el("#status-strip");
  try {
    const status = await api("/api/status");
    const chips = [];
    chips.push(
      status.groq_configured
        ? `<span class="status-chip ok">GROQ KEY ✓</span>`
        : `<span class="status-chip warn">NO GROQ KEY — add GROQ_API_KEY to .env (free at console.groq.com)</span>`
    );
    chips.push(
      status.job_sources_configured.length
        ? `<span class="status-chip ok">${status.job_sources_configured.length} JOB SOURCE${status.job_sources_configured.length > 1 ? "S" : ""} ✓</span>`
        : `<span class="status-chip warn">NO JOB SEARCH APIS CONFIGURED</span>`
    );
    chips.push(
      status.latex_available
        ? `<span class="status-chip ok">LATEX ✓</span>`
        : `<span class="status-chip warn">NO LATEX — DOCX only</span>`
    );
    chips.push(
      status.gmail_authorized
        ? `<span class="status-chip ok">GMAIL ALERTS ✓</span>`
        : `<span class="status-chip warn">GMAIL NOT CONNECTED</span>`
    );
    strip.innerHTML = chips.join("");
  } catch (e) {
    strip.innerHTML = `<span class="status-chip warn">Can't reach backend</span>`;
  }
}

// ---------------- Profile / interview ----------------

let chatHistory = [];

function renderChatLog() {
  const log = el("#chat-log");
  log.innerHTML = chatHistory
    .map((m) => `<div class="chat-msg ${m.role}">${escapeHtml(m.content)}</div>`)
    .join("");
  log.scrollTop = log.scrollHeight;
}

function renderProfileSummary(profile) {
  const exp = (profile.experience || [])
    .map(
      (e) => `<h3>${escapeHtml(e.title)} — ${escapeHtml(e.company)}</h3>
        <div class="card-meta">${escapeHtml(e.start_date)} – ${escapeHtml(e.end_date)}${e.location ? " · " + escapeHtml(e.location) : ""}</div>
        <ul>${(e.achievements || []).map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>`
    )
    .join("");
  const edu = (profile.education || [])
    .map((e) => `<li>${escapeHtml(e.degree)}, ${escapeHtml(e.institution)} ${e.year ? "(" + escapeHtml(e.year) + ")" : ""}</li>`)
    .join("");

  el("#profile-summary").innerHTML = `
    <div class="cv-name">${escapeHtml(profile.full_name)}</div>
    <div class="card-meta">${[profile.location, profile.email, profile.phone].filter(Boolean).map(escapeHtml).join(" · ")}</div>
    ${profile.headline ? `<p><em>${escapeHtml(profile.headline)}</em></p>` : ""}
    ${profile.career_goals ? `<h3>Goals</h3><p>${escapeHtml(profile.career_goals)}</p>` : ""}
    ${profile.skills && profile.skills.length ? `<h3>Skills</h3><div class="pill-list">${profile.skills.map((s) => `<span class="pill">${escapeHtml(s)}</span>`).join("")}</div>` : ""}
    ${exp ? `<h3>Experience</h3>${exp}` : ""}
    ${edu ? `<h3>Education</h3><ul>${edu}</ul>` : ""}
  `;
}

async function checkProfileStatus() {
  const profile = await api("/api/profile");
  if (profile.is_complete) {
    el("#profile-complete-view").style.display = "block";
    el("#profile-interview-view").style.display = "none";
    renderProfileSummary(profile);
  } else {
    el("#profile-complete-view").style.display = "none";
    el("#profile-interview-view").style.display = "block";
    chatHistory = (await api("/api/profile/interview/history")).map((h) => ({ role: h.role, content: h.content }));
    if (chatHistory.length === 0) {
      await sendInterviewTurn("");
    } else {
      renderChatLog();
    }
  }
}

async function sendInterviewTurn(message) {
  if (message) {
    chatHistory.push({ role: "user", content: message });
    renderChatLog();
  }
  const sendBtn = el("#chat-send-btn");
  sendBtn.disabled = true;
  sendBtn.textContent = "…";
  try {
    const result = await api("/api/profile/interview/turn", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    if (result.done) {
      el("#profile-complete-view").style.display = "block";
      el("#profile-interview-view").style.display = "none";
      renderProfileSummary(result.profile);
    } else {
      chatHistory.push({ role: "assistant", content: result.question });
      renderChatLog();
    }
  } catch (e) {
    chatHistory.push({ role: "assistant", content: `⚠ ${e.message}` });
    renderChatLog();
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
  }
}

el("#chat-send-btn").addEventListener("click", () => {
  const input = el("#chat-input");
  const val = input.value.trim();
  if (!val) return;
  input.value = "";
  sendInterviewTurn(val);
});
el("#chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") el("#chat-send-btn").click();
});

el("#restart-interview-btn").addEventListener("click", async () => {
  if (!confirm("This clears your saved profile and starts the interview over. Continue?")) return;
  await api("/api/profile/interview/reset", { method: "POST" });
  await api("/api/profile", { method: "PUT", body: JSON.stringify({ full_name: "", is_complete: false }) }).catch(() => {});
  chatHistory = [];
  el("#profile-complete-view").style.display = "none";
  el("#profile-interview-view").style.display = "block";
  renderChatLog();
  sendInterviewTurn("");
});

// ---------------- Search ----------------

function fitClassForScore(score) {
  if (score === null || score === undefined) return "";
  if (score >= 60) return "fit-high";
  if (score >= 30) return "fit-mid";
  return "fit-low";
}

function renderJobCard(job) {
  const scoreBadge =
    job.keyword_score !== null && job.keyword_score !== undefined
      ? `<span class="stamp ${fitClassForScore(job.keyword_score)}">${Math.round(job.keyword_score)}% match</span>`
      : "";
  return `
    <div class="card">
      <div class="card-top">
        <div>
          <p class="card-title">${escapeHtml(job.title)}</p>
          <p class="card-sub">${escapeHtml(job.company)}${job.location ? " · " + escapeHtml(job.location) : ""}</p>
        </div>
        ${scoreBadge}
      </div>
      <p>${escapeHtml((job.snippet || "").slice(0, 220))}${job.snippet && job.snippet.length > 220 ? "…" : ""}</p>
      <div class="card-meta">SOURCE: ${escapeHtml(job.source)}${job.salary ? " · " + escapeHtml(job.salary) : ""}${job.posted_date ? " · " + escapeHtml(job.posted_date) : ""}</div>
      <div class="card-actions">
        <a class="btn secondary small" href="${escapeHtml(job.url)}" target="_blank" rel="noopener">Open posting</a>
        <button class="btn small use-for-apply-btn" data-url="${escapeHtml(job.url)}">Use for Apply →</button>
      </div>
    </div>`;
}

el("#search-btn").addEventListener("click", async () => {
  const query = el("#search-query").value.trim();
  const location = el("#search-location").value.trim();
  if (!query) return;
  const results = el("#search-results");
  results.innerHTML = `<div class="loading-line">Searching configured job boards…</div>`;
  try {
    const jobs = await api(`/api/search?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`);
    if (!jobs.length) {
      results.innerHTML = `<div class="empty-state">No results. Check that at least one job source is configured in .env, or try broader keywords.</div>`;
      return;
    }
    results.innerHTML = jobs.map(renderJobCard).join("");
    els(".use-for-apply-btn").forEach((btn) =>
      btn.addEventListener("click", () => {
        el(`.tab-btn[data-tab="apply"]`).click();
        el("#apply-url").value = btn.dataset.url;
      })
    );
  } catch (e) {
    results.innerHTML = `<div class="empty-state">⚠ ${escapeHtml(e.message)}</div>`;
  }
});

// ---------------- Apply ----------------

const PIPELINE_STAGES = [
  "Fetching the job posting…",
  "Evaluating fit against your profile…",
  "Drafting a tailored CV and cover letter…",
  "Reviewing the draft for accuracy and tone…",
  "Revising based on reviewer feedback…",
  "Rendering DOCX and LaTeX/PDF documents…",
];

function renderReviewList(reviewLog) {
  return `<ul>${reviewLog.map((l) => `<li>${escapeHtml(l)}</li>`).join("")}</ul>`;
}

function renderCVPreview(cv) {
  return `
    <div class="doc-preview">
      <div class="cv-name">${escapeHtml(cv.full_name)}</div>
      <div class="card-meta">${[cv.location, cv.email, cv.phone, ...(cv.links || [])].filter(Boolean).map(escapeHtml).join(" · ")}</div>
      ${cv.summary ? `<h3>Summary</h3><p>${escapeHtml(cv.summary)}</p>` : ""}
      ${cv.skills && cv.skills.length ? `<h3>Skills</h3><div class="pill-list">${cv.skills.map((s) => `<span class="pill">${escapeHtml(s)}</span>`).join("")}</div>` : ""}
      ${(cv.experience || []).length ? `<h3>Experience</h3>${cv.experience.map((e) => `
        <strong>${escapeHtml(e.title)}</strong> — ${escapeHtml(e.company)}
        <div class="card-meta">${escapeHtml(e.start_date)} – ${escapeHtml(e.end_date)}</div>
        <ul>${(e.bullets || []).map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>
      `).join("")}` : ""}
      ${(cv.education || []).length ? `<h3>Education</h3><ul>${cv.education.map((e) => `<li>${escapeHtml(e.degree)}, ${escapeHtml(e.institution)}</li>`).join("")}</ul>` : ""}
    </div>`;
}

function renderCoverLetterPreview(cl) {
  return `
    <div class="doc-preview">
      <div class="cv-name">${escapeHtml(cl.full_name)}</div>
      <div class="card-meta">${escapeHtml(cl.contact_line || "")}</div>
      <p>${escapeHtml(cl.salutation)}</p>
      ${(cl.paragraphs || []).map((p) => `<p>${escapeHtml(p)}</p>`).join("")}
      <p>${escapeHtml(cl.closing)}<br>${escapeHtml(cl.full_name)}</p>
    </div>`;
}

async function runApplyPipeline(url) {
  const statusBox = el("#apply-status");
  const resultsBox = el("#apply-results");
  resultsBox.innerHTML = "";
  el("#apply-btn").disabled = true;

  let stageIdx = 0;
  statusBox.innerHTML = `<div class="loading-line">${PIPELINE_STAGES[0]}</div>`;
  const stageTimer = setInterval(() => {
    stageIdx = Math.min(stageIdx + 1, PIPELINE_STAGES.length - 1);
    statusBox.innerHTML = `<div class="loading-line">${PIPELINE_STAGES[stageIdx]}</div>`;
  }, 6000);

  try {
    const result = await api("/api/apply", { method: "POST", body: JSON.stringify({ job_url: url }) });
    clearInterval(stageTimer);
    statusBox.innerHTML = "";

    const fit = result.fit;
    const review = result.review;
    const docs = result.documents;
    const appId = result.application_id;

    resultsBox.innerHTML = `
      <div class="card" style="margin-bottom:18px;">
        <div class="card-top">
          <div>
            <p class="card-title">${escapeHtml(result.job.title)}</p>
            <p class="card-sub">${escapeHtml(result.job.company)}</p>
          </div>
          <span class="stamp ${fitClassForScore(fit.fit_score)}">${fit.fit_score}/100 — ${escapeHtml(fit.recommendation)}</span>
        </div>
        <p>${escapeHtml(fit.verdict)}</p>
        ${fit.strengths && fit.strengths.length ? `<strong>Strengths</strong><ul class="issue-list">${fit.strengths.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>` : ""}
        ${fit.gaps && fit.gaps.length ? `<strong>Gaps</strong><ul class="issue-list">${fit.gaps.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>` : ""}
      </div>

      <div class="card" style="margin-bottom:18px;">
        <strong>Drafter ↔ Reviewer log</strong> (${review.rounds} round${review.rounds === 1 ? "" : "s"}, ${review.approved ? "approved" : "max rounds reached"})
        ${renderReviewList(review.log)}
      </div>

      <div class="card-actions" style="margin-bottom:20px;">
        <a class="btn small" href="/api/applications/${appId}/download/cv_docx">Download CV (.docx)</a>
        ${docs.cv_pdf ? `<a class="btn small" href="/api/applications/${appId}/download/cv_pdf">Download CV (.pdf)</a>` : `<a class="btn small secondary" href="/api/applications/${appId}/download/cv_tex">Download CV (.tex)</a>`}
        <a class="btn small" href="/api/applications/${appId}/download/cover_letter_docx">Download cover letter (.docx)</a>
        ${docs.cover_letter_pdf ? `<a class="btn small" href="/api/applications/${appId}/download/cover_letter_pdf">Download cover letter (.pdf)</a>` : `<a class="btn small secondary" href="/api/applications/${appId}/download/cover_letter_tex">Download cover letter (.tex)</a>`}
      </div>
      ${!docs.latex_available ? `<p class="section-sub">No local LaTeX install was found, so PDFs weren't compiled — .tex source was still saved and can be compiled later or pasted into Overleaf.</p>` : ""}

      <h3 class="section-title" style="font-size:16px;">CV preview</h3>
      ${renderCVPreview(result.package.cv)}
      <h3 class="section-title" style="font-size:16px;">Cover letter preview</h3>
      ${renderCoverLetterPreview(result.package.cover_letter)}

      <p class="section-sub">Saved to your <strong>Tracker</strong> tab as a new application.</p>
    `;
  } catch (e) {
    clearInterval(stageTimer);
    statusBox.innerHTML = `<div class="empty-state">⚠ ${escapeHtml(e.message)}</div>`;
  } finally {
    el("#apply-btn").disabled = false;
  }
}

el("#apply-btn").addEventListener("click", () => {
  const url = el("#apply-url").value.trim();
  if (!url) return;
  runApplyPipeline(url);
});

// ---------------- Tracker ----------------

const STATUS_OPTIONS = ["drafted", "applied", "interviewing", "offer", "rejected", "withdrawn"];

function renderTrackerCard(app) {
  const fit = app.fit_json ? JSON.parse(app.fit_json) : null;
  return `
    <div class="card" data-app-id="${app.id}">
      <div class="card-top">
        <div>
          <p class="card-title">${escapeHtml(app.job_title || "(untitled role)")}</p>
          <p class="card-sub">${escapeHtml(app.company)}</p>
        </div>
        <span class="stamp ${app.status}">${escapeHtml(app.status)}</span>
      </div>
      <div class="card-meta">
        ${app.fit_score !== null ? `FIT ${app.fit_score}/100 · ` : ""}APPLIED FILE OPENED ${escapeHtml((app.created_at || "").slice(0, 10))}
      </div>
      <div class="field-row" style="margin-top:12px;">
        <select class="status-select">
          ${STATUS_OPTIONS.map((s) => `<option value="${s}" ${s === app.status ? "selected" : ""}>${s}</option>`).join("")}
        </select>
        <a class="btn secondary small" href="${escapeHtml(app.job_url)}" target="_blank" rel="noopener" style="flex:0 0 auto;">Open posting</a>
      </div>
      <textarea class="notes-area" placeholder="Notes…" rows="2">${escapeHtml(app.notes)}</textarea>
      <div class="card-actions">
        <a class="btn small" href="/api/applications/${app.id}/download/cv_docx">CV .docx</a>
        <a class="btn small" href="/api/applications/${app.id}/download/cover_letter_docx">Letter .docx</a>
        ${app.cv_pdf_path ? `<a class="btn small" href="/api/applications/${app.id}/download/cv_pdf">CV .pdf</a>` : ""}
        ${app.cover_letter_pdf_path ? `<a class="btn small" href="/api/applications/${app.id}/download/cover_letter_pdf">Letter .pdf</a>` : ""}
        <button class="btn small secondary interview-prep-btn">Interview prep</button>
        <button class="btn small secondary delete-app-btn" style="margin-left:auto; border-color:var(--rust); color:var(--rust);">Delete</button>
      </div>
      <div class="interview-prep-box" style="display:none;"></div>
    </div>`;
}

function renderInterviewPrep(prep) {
  return `
    <div class="doc-preview" style="margin-top:14px;">
      <h3>Likely questions</h3>
      ${prep.likely_questions.map((q) => `
        <p><strong>${escapeHtml(q.question)}</strong></p>
        ${q.why_theyll_ask_this ? `<p><em>${escapeHtml(q.why_theyll_ask_this)}</em></p>` : ""}
        <ul>${(q.suggested_talking_points || []).map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ul>
      `).join("")}
      <h3>Questions to ask them</h3>
      <ul>${prep.questions_to_ask_them.map((q) => `<li>${escapeHtml(q)}</li>`).join("")}</ul>
      ${prep.gaps_to_address_proactively && prep.gaps_to_address_proactively.length ? `
        <h3>Gaps to address proactively</h3>
        <ul>${prep.gaps_to_address_proactively.map((g) => `<li>${escapeHtml(g)}</li>`).join("")}</ul>` : ""}
      ${prep.company_specific_notes ? `<h3>Company notes</h3><p>${escapeHtml(prep.company_specific_notes)}</p>` : ""}
    </div>`;
}

async function loadTracker() {
  const list = el("#tracker-list");
  list.innerHTML = `<div class="loading-line">Loading applications…</div>`;
  try {
    const apps = await api("/api/applications");
    if (!apps.length) {
      list.innerHTML = `<div class="empty-state">No applications yet — run the Apply pipeline on a job posting to start your first case file.</div>`;
      return;
    }
    list.innerHTML = apps.map(renderTrackerCard).join("");
    wireTrackerCardEvents();
  } catch (e) {
    list.innerHTML = `<div class="empty-state">⚠ ${escapeHtml(e.message)}</div>`;
  }
}

function wireTrackerCardEvents() {
  els(".card[data-app-id]").forEach((card) => {
    const appId = card.dataset.appId;

    card.querySelector(".status-select").addEventListener("change", async (e) => {
      await api(`/api/applications/${appId}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value }) });
      const stamp = card.querySelector(".stamp");
      stamp.className = `stamp ${e.target.value}`;
      stamp.textContent = e.target.value;
    });

    let notesTimer;
    card.querySelector(".notes-area").addEventListener("input", (e) => {
      clearTimeout(notesTimer);
      notesTimer = setTimeout(() => {
        api(`/api/applications/${appId}`, { method: "PATCH", body: JSON.stringify({ notes: e.target.value }) });
      }, 800);
    });

    card.querySelector(".delete-app-btn").addEventListener("click", async () => {
      if (!confirm("Delete this application and its saved documents from the tracker?")) return;
      await api(`/api/applications/${appId}`, { method: "DELETE" });
      card.remove();
    });

    card.querySelector(".interview-prep-btn").addEventListener("click", async (e) => {
      const box = card.querySelector(".interview-prep-box");
      if (box.style.display === "block") {
        box.style.display = "none";
        return;
      }
      box.style.display = "block";
      box.innerHTML = `<div class="loading-line">Preparing interview material…</div>`;
      try {
        let prep;
        try {
          prep = await api(`/api/applications/${appId}/interview-prep`);
        } catch (_) {
          prep = await api(`/api/applications/${appId}/interview-prep`, { method: "POST" });
        }
        box.innerHTML = renderInterviewPrep(prep);
      } catch (err) {
        box.innerHTML = `<div class="empty-state">⚠ ${escapeHtml(err.message)}</div>`;
      }
    });
  });
}

// ---------------- Watched companies (direct ATS) ----------------

async function loadWatchedCompanies() {
  const companies = await api("/api/companies");
  const list = el("#watched-companies-list");
  if (!companies.length) {
    list.innerHTML = `<span class="section-sub">No companies watched yet.</span>`;
    return;
  }
  list.innerHTML = companies
    .map(
      (c) => `<span class="pill" data-company-id="${c.id}">${escapeHtml(c.name)} · ${escapeHtml(c.ats_type)} <a href="#" class="remove-company-btn" data-id="${c.id}" style="color:var(--rust);">✕</a></span>`
    )
    .join("");
  els(".remove-company-btn").forEach((btn) =>
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      await api(`/api/companies/${btn.dataset.id}`, { method: "DELETE" });
      loadWatchedCompanies();
    })
  );
}

el("#add-company-btn").addEventListener("click", async () => {
  const name = el("#company-name").value.trim();
  const ats_type = el("#company-ats-type").value;
  const slug = el("#company-slug").value.trim();
  if (!name || !slug) return;
  try {
    await api("/api/companies", { method: "POST", body: JSON.stringify({ name, ats_type, slug }) });
    el("#company-name").value = "";
    el("#company-slug").value = "";
    loadWatchedCompanies();
  } catch (e) {
    alert(e.message);
  }
});

el("#refresh-watched-btn").addEventListener("click", async () => {
  const box = el("#watched-postings-results");
  box.innerHTML = `<div class="loading-line">Fetching current postings from watched companies…</div>`;
  try {
    const jobs = await api("/api/companies/postings");
    if (!jobs.length) {
      box.innerHTML = `<div class="empty-state">No postings found — add a company above, or check the slug is right.</div>`;
      return;
    }
    box.innerHTML = jobs.map(renderJobCard).join("");
    els(".use-for-apply-btn").forEach((btn) =>
      btn.addEventListener("click", () => {
        el(`.tab-btn[data-tab="apply"]`).click();
        el("#apply-url").value = btn.dataset.url;
      })
    );
  } catch (e) {
    box.innerHTML = `<div class="empty-state">⚠ ${escapeHtml(e.message)}</div>`;
  }
});

// ---------------- Bookmarklet clipper ----------------

async function setupBookmarklet() {
  try {
    const code = await (await fetch("/assets/bookmarklet.js")).text();
    el("#bookmarklet-link").href = "javascript:" + encodeURIComponent(code);
  } catch (e) {
    /* if this fails, the link just won't work — not fatal */
  }
}

function renderClippedCard(item) {
  return `
    <div class="card">
      <div class="card-top">
        <div>
          <p class="card-title">${escapeHtml(item.title || "(untitled)")}</p>
          <p class="card-sub">${escapeHtml(item.company || "")}${item.location ? " · " + escapeHtml(item.location) : ""}</p>
        </div>
      </div>
      ${item.snippet ? `<p>${escapeHtml(item.snippet.slice(0, 220))}</p>` : ""}
      <div class="card-meta">SOURCE: ${escapeHtml(item.source)} · CLIPPED ${escapeHtml((item.discovered_at || "").slice(0, 10))}</div>
      <div class="card-actions">
        <a class="btn secondary small" href="${escapeHtml(item.url)}" target="_blank" rel="noopener">Open posting</a>
        <button class="btn small use-for-apply-btn" data-url="${escapeHtml(item.url)}">Use for Apply →</button>
      </div>
    </div>`;
}

el("#refresh-clipped-btn").addEventListener("click", async () => {
  const box = el("#clipped-results");
  box.innerHTML = `<div class="loading-line">Loading clipped listings…</div>`;
  try {
    const items = await api("/api/clipper/recent");
    if (!items.length) {
      box.innerHTML = `<div class="empty-state">Nothing clipped yet — drag the bookmarklet above to your bookmarks bar, then click it on a job posting or search page.</div>`;
      return;
    }
    box.innerHTML = items.map(renderClippedCard).join("");
    els(".use-for-apply-btn").forEach((btn) =>
      btn.addEventListener("click", () => {
        el(`.tab-btn[data-tab="apply"]`).click();
        el("#apply-url").value = btn.dataset.url;
      })
    );
  } catch (e) {
    box.innerHTML = `<div class="empty-state">⚠ ${escapeHtml(e.message)}</div>`;
  }
});

// ---------------- Gmail alert ingestion ----------------

async function loadGmailStatus() {
  const box = el("#gmail-status");
  try {
    const status = await api("/api/gmail/status");
    if (!status.configured) {
      box.innerHTML = `No Gmail credentials found yet — see the README's Gmail setup section to create a free one-time OAuth credential.`;
    } else if (!status.authorized) {
      box.innerHTML = `Credentials found. Click "Authorize Gmail" to grant one-time read access to your inbox.`;
    } else {
      box.innerHTML = `<span class="stamp applied">Gmail connected</span>`;
    }
  } catch (e) {
    box.innerHTML = `⚠ ${escapeHtml(e.message)}`;
  }
}

el("#gmail-authorize-btn").addEventListener("click", async () => {
  const btn = el("#gmail-authorize-btn");
  btn.disabled = true;
  btn.textContent = "Opening browser for consent…";
  try {
    await api("/api/gmail/authorize", { method: "POST" });
    await loadGmailStatus();
  } catch (e) {
    alert(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Authorize Gmail";
  }
});

el("#gmail-check-btn").addEventListener("click", async () => {
  const btn = el("#gmail-check-btn");
  btn.disabled = true;
  btn.textContent = "Checking…";
  try {
    const result = await api("/api/gmail/check", { method: "POST" });
    alert(`Scanned ${result.scanned} alert email(s), found ${result.new_count} new listing(s).`);
    el("#refresh-clipped-btn").click();
  } catch (e) {
    alert(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Check for new alerts";
  }
});

// ---------------- Backup / restore ----------------

el("#backup-restore-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  if (!confirm("Restore will overwrite your current profile, applications, and documents with the contents of this backup. Continue?")) {
    e.target.value = "";
    return;
  }
  const statusEl = el("#backup-status");
  statusEl.textContent = "Restoring…";
  const formData = new FormData();
  formData.append("file", file);
  try {
    const res = await fetch("/api/backup/restore", { method: "POST", body: formData });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "Restore failed.");
    statusEl.textContent = `Restored ${body.files.length} file(s). Reloading…`;
    setTimeout(() => location.reload(), 1200);
  } catch (err) {
    statusEl.textContent = `⚠ ${err.message}`;
  } finally {
    e.target.value = "";
  }
});

// ---------------- Boot ----------------

loadStatus();
checkProfileStatus();
loadWatchedCompanies();
setupBookmarklet();
loadGmailStatus();

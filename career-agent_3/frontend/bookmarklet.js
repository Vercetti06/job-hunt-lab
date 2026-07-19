/* Career Agent clipper — bookmarklet source.
   Runs entirely in the page you're already viewing when you click it. Makes
   zero extra requests to the job site itself — it only reads what's already
   rendered in your own logged-in browser session, then sends it to your local
   Career Agent instance.

   Per-site selectors below are best-effort and may need small updates if a
   site changes its markup — that's a normal characteristic of any tool that
   reads a page's structure, and each site's parser is isolated so one break
   doesn't affect the others. The JSON-LD path (schema.org JobPosting) is more
   durable since it's a published standard many job sites already use for SEO. */
(function () {
  var API = "http://127.0.0.1:8420/api/clipper/ingest";
  var host = location.hostname;

  function clean(t) {
    return (t || "").replace(/\s+/g, " ").trim();
  }

  function fromJsonLd() {
    var out = [];
    document.querySelectorAll('script[type="application/ld+json"]').forEach(function (tag) {
      try {
        var data = JSON.parse(tag.textContent);
        var items = Array.isArray(data) ? data : [data];
        items.forEach(function (item) {
          if (item && item["@type"] === "JobPosting") {
            var org = item.hiringOrganization || {};
            var addr = ((item.jobLocation || {}).address) || {};
            out.push({
              url: item.url || location.href,
              title: clean(item.title),
              company: clean(org.name || ""),
              location: clean(addr.addressLocality || addr.addressRegion || ""),
              snippet: clean((item.description || "").replace(/<[^>]+>/g, " ")).slice(0, 500),
              source: "clipper:jsonld",
            });
          }
        });
      } catch (e) { /* not valid JSON-LD, skip */ }
    });
    return out;
  }

  function genericJobLinkParser(tag) {
    return function () {
      var out = [];
      document.querySelectorAll('a[href*="job"]').forEach(function (a) {
        var text = clean(a.textContent);
        if (text.length > 4 && text.length < 140) {
          out.push({ url: a.href, title: text, company: "", location: "", snippet: "", source: "clipper:" + tag });
        }
      });
      return out;
    };
  }

  var SITE_PARSERS = {
    "linkedin.com": function () {
      var out = [];
      document.querySelectorAll('a.job-card-list__title, a.base-card__full-link, a[href*="/jobs/view/"]').forEach(function (a) {
        var card = a.closest("li") || a.closest("div");
        out.push({
          url: a.href.split("?")[0],
          title: clean(a.textContent),
          company: clean(card && card.querySelector(".job-card-container__company-name, .base-search-card__subtitle") ? card.querySelector(".job-card-container__company-name, .base-search-card__subtitle").textContent : ""),
          location: clean(card && card.querySelector(".job-card-container__metadata-item, .job-search-card__location") ? card.querySelector(".job-card-container__metadata-item, .job-search-card__location").textContent : ""),
          snippet: "",
          source: "clipper:linkedin",
        });
      });
      return out;
    },
    "indeed.com": function () {
      var out = [];
      document.querySelectorAll('a[href*="/rc/clk"], a[href*="/viewjob"], a.jcs-JobTitle').forEach(function (a) {
        var card = a.closest(".job_seen_beacon") || a.closest(".cardOutline");
        out.push({
          url: a.href,
          title: clean(a.textContent),
          company: clean(card && card.querySelector('[data-testid="company-name"]') ? card.querySelector('[data-testid="company-name"]').textContent : ""),
          location: clean(card && card.querySelector('[data-testid="text-location"]') ? card.querySelector('[data-testid="text-location"]').textContent : ""),
          snippet: "",
          source: "clipper:indeed",
        });
      });
      return out;
    },
    "naukri.com": function () {
      var out = [];
      document.querySelectorAll('a.title, a[href*="naukri.com/job-listings"]').forEach(function (a) {
        var card = a.closest(".cust-job-tuple") || a.closest("article");
        out.push({
          url: a.href,
          title: clean(a.textContent),
          company: clean(card && card.querySelector(".comp-name") ? card.querySelector(".comp-name").textContent : ""),
          location: clean(card && card.querySelector(".locWdth, .loc") ? card.querySelector(".locWdth, .loc").textContent : ""),
          snippet: "",
          source: "clipper:naukri",
        });
      });
      return out;
    },
    "instahyre.com": genericJobLinkParser("instahyre"),
    "hirist.tech": genericJobLinkParser("hirist"),
    "uplers.com": genericJobLinkParser("uplers"),
  };

  var results = fromJsonLd();
  Object.keys(SITE_PARSERS).forEach(function (key) {
    if (host.indexOf(key) !== -1) {
      results = results.concat(SITE_PARSERS[key]());
    }
  });

  var seen = {};
  results = results.filter(function (r) {
    if (!r.url || seen[r.url]) return false;
    seen[r.url] = true;
    return true;
  });

  if (results.length === 0) {
    alert("Career Agent clipper: no recognizable job listings found on this page.");
    return;
  }

  fetch(API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ postings: results, page_url: location.href }),
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      alert("Career Agent: sent " + results.length + " listing(s) — " + (data.new_count || 0) + " new.");
    })
    .catch(function (err) {
      alert("Career Agent clipper couldn't reach your local app at 127.0.0.1:8420. Is it running?");
    });
})();

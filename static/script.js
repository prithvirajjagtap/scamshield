const $ = (id) => document.getElementById(id);

const SCAM_EXAMPLE = `URGENT HIRING!! Work from home, no interview required. Earn Rs. 5000 per day just by typing. Limited seats, 100% placement guaranteed. Pay a registration fee of Rs. 999 to confirm your seat. Contact on WhatsApp now or mail hr.jobs2024@gmail.com`;

const LEGIT_EXAMPLE = `Software Engineer Intern at Acme Technologies, Pune. You will work with our backend team to build and test REST APIs using Python and PostgreSQL. Requirements: pursuing a B.E./B.Tech in Computer Science, good knowledge of data structures, and familiarity with Git. Selection involves an online assessment followed by two technical interviews. Stipend as per company policy. Apply through our careers page.`;

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Wrap every red-flag term in <mark>. Works on already-escaped text.
function highlight(text, terms) {
  const safe = escapeHtml(text);
  const cleaned = [...new Set(terms.map((t) => escapeHtml(t.trim())).filter((t) => t.length > 2))];
  if (!cleaned.length) return safe;
  cleaned.sort((a, b) => b.length - a.length); // longest phrase first
  const pattern = new RegExp(`(${cleaned.map(escapeRegex).join("|")})`, "gi");
  return safe.replace(pattern, "<mark>$1</mark>");
}

function showError(msg) {
  const el = $("error");
  el.textContent = msg;
  el.classList.toggle("hidden", !msg);
}

function renderResult(data, originalText) {
  $("result").classList.remove("hidden");

  const pct = data.score;
  const color = pct >= 60 ? "var(--danger)" : pct >= 30 ? "var(--warn)" : "var(--ok)";
  const gauge = $("gauge");
  gauge.style.setProperty("--pct", pct);
  gauge.style.setProperty("--color", color);

  $("scoreValue").textContent = `${Math.round(pct)}%`;
  $("verdict").textContent = data.verdict;
  $("verdict").style.color = color;
  $("mlProb").textContent = `${data.ml_probability}%`;

  // Highlighted original text
  const terms = [...data.red_words.map((w) => w.word), ...data.rule_flags.map((r) => r.match)];
  $("highlighted").innerHTML = highlight(originalText, terms);

  // Rule flags
  const ruleList = $("ruleFlags");
  ruleList.innerHTML = "";
  if (data.rule_flags.length === 0) {
    ruleList.innerHTML = `<li class="empty">No known scam patterns found.</li>`;
  } else {
    data.rule_flags.forEach((r) => {
      const li = document.createElement("li");
      li.innerHTML = `${escapeHtml(r.label)}<br><small>"${escapeHtml(r.match)}"</small>`;
      ruleList.appendChild(li);
    });
  }

  // Word chips
  fillChips($("redWords"), data.red_words, "red", "No suspicious words.");
  fillChips($("safeWords"), data.safe_words, "green", "None found.");

  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

function fillChips(container, words, cls, emptyMsg) {
  container.innerHTML = "";
  if (!words.length) {
    container.innerHTML = `<span class="empty">${emptyMsg}</span>`;
    return;
  }
  words.forEach((w) => {
    const span = document.createElement("span");
    span.className = `chip ${cls}`;
    span.textContent = w.word;
    container.appendChild(span);
  });
}

async function analyze() {
  const text = $("jobText").value.trim();
  showError("");
  const btn = $("analyzeBtn");
  btn.disabled = true;
  btn.textContent = "Analyzing...";

  try {
    const res = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || "Something went wrong.");
      return;
    }
    renderResult(data, text);
  } catch (err) {
    showError("Could not reach the server. Is app.py running?");
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyze";
  }
}

async function loadMetrics() {
  try {
    const res = await fetch("/api/metrics");
    const m = await res.json();
    if (!m.results) return;

    $("datasetInfo").textContent =
      `Trained on ${m.dataset_size.toLocaleString()} postings (${m.fake_count.toLocaleString()} fake). ` +
      `Served model: ${m.served_model} (chosen because its word weights make predictions explainable).`;

    let rows = `<tr><th>Model</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th></tr>`;
    Object.entries(m.results).forEach(([name, r]) => {
      rows += `<tr><td>${escapeHtml(name)}</td><td>${r.precision}</td><td>${r.recall}</td><td>${r.f1}</td><td>${r.roc_auc}</td></tr>`;
    });
    $("metricsTable").innerHTML = rows;
    $("metricsCard").classList.remove("hidden");
  } catch (e) {
    /* metrics are optional */
  }
}

$("analyzeBtn").addEventListener("click", analyze);
$("scamExample").addEventListener("click", () => { $("jobText").value = SCAM_EXAMPLE; });
$("legitExample").addEventListener("click", () => { $("jobText").value = LEGIT_EXAMPLE; });
$("clearBtn").addEventListener("click", () => {
  $("jobText").value = "";
  $("result").classList.add("hidden");
  showError("");
});

loadMetrics();

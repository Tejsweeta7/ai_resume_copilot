const form = document.querySelector("#analysisForm");
const intro = document.querySelector("#intro");
const analyzer = document.querySelector("#analyzer");
const fileInput = document.querySelector("#resumeFiles");
const fileList = document.querySelector("#fileList");
const loadSample = document.querySelector("#loadSample");
const sampleSelect = document.querySelector("#sampleSelect");
const jdInput = document.querySelector("#jobDescription");
const submitButton = form.querySelector(".primary");
const backToIntro = document.querySelector("#backToIntro");

const state = {
  lastResult: null,
  selectedFiles: []
};

const sampleJds = {
  genai: `AI/ML Intern - GenAI and NLP

We need a candidate with Python, FastAPI, NLP, spaCy, scikit-learn, HuggingFace transformers, LLM APIs, prompt engineering, REST APIs, SQL, Git, and cloud basics. The role needs 1+ year project experience building ML features, resume parsing, scoring logic, dashboards, and business-facing AI use cases.`,

  data: `Data Analyst Intern - Business Intelligence

We need a candidate with SQL, Python, pandas, numpy, Excel, Power BI or Tableau, data cleaning, data visualization, statistics, dashboards, stakeholder reporting, and business analysis skills. Experience with KPI tracking, customer data, and presenting insights is preferred.`,

  backend: `Backend AI Engineer - API Platform

We need a candidate with Python, FastAPI, REST APIs, SQL, PostgreSQL, Docker, Git, cloud deployment, authentication, API design, and LLM integration experience. The role involves building reliable backend services for AI products, integrating HuggingFace or OpenAI APIs, and writing clean production-ready code.`,

  mlops: `ML Platform Intern - MLOps and Model Deployment

We need a candidate with Python, machine learning, scikit-learn, Docker, FastAPI, GitHub Actions, cloud basics, model serving, monitoring, data pipelines, APIs, and MLOps fundamentals. Experience deploying ML models and building reproducible workflows is a plus.`
};

document.querySelectorAll("[data-explore]").forEach((button) => {
  button.addEventListener("click", () => {
    intro.hidden = true;
    analyzer.hidden = false;
    analyzer.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

backToIntro.addEventListener("click", () => {
  analyzer.hidden = true;
  intro.hidden = false;
  intro.scrollIntoView({ behavior: "smooth", block: "start" });
});

fileInput.addEventListener("change", () => {
  const incomingFiles = [...fileInput.files];
  incomingFiles.forEach((file) => {
    const alreadyAdded = state.selectedFiles.some((savedFile) => {
      return savedFile.name === file.name && savedFile.size === file.size && savedFile.lastModified === file.lastModified;
    });

    if (!alreadyAdded) {
      state.selectedFiles.push(file);
    }
  });

  renderSelectedFiles();
  fileInput.value = "";
});

loadSample.addEventListener("click", () => {
  jdInput.value = sampleJds[sampleSelect.value];
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".tab-page").forEach((page) => page.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`#${button.dataset.tab}`).classList.add("active");
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!state.selectedFiles.length) {
    renderError("Upload at least one resume to analyze.");
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Analyzing...";

  const payload = new FormData();
  payload.append("job_description", jdInput.value);
  state.selectedFiles.forEach((file) => payload.append("resumes", file));

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: payload
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Analysis failed.");
    }

    state.lastResult = await response.json();
    renderResult(state.lastResult);
  } catch (error) {
    renderError(error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Analyze";
  }
});

function renderSelectedFiles() {
  if (!state.selectedFiles.length) {
    fileList.textContent = "No files selected";
    return;
  }

  fileList.innerHTML = state.selectedFiles.map((file, index) => `
    <span class="selected-file">
      ${escapeHtml(file.name)}
      <button type="button" aria-label="Remove ${escapeHtml(file.name)}" data-remove-file="${index}">Remove</button>
    </span>
  `).join("");

  fileList.querySelectorAll("[data-remove-file]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedFiles.splice(Number(button.dataset.removeFile), 1);
      renderSelectedFiles();
    });
  });
}

function renderResult(result) {
  const topCandidate = result.candidates[0];
  setText("#candidateName", topCandidate.name);
  setScore(topCandidate.ats_score);
  setText("#skillMatch", `${topCandidate.breakdown.skill_match}%`);
  setText("#experienceScore", `${topCandidate.breakdown.experience}%`);
  setText("#keywordScore", `${topCandidate.breakdown.keywords}%`);

  renderPills("#parsedSkills", topCandidate.parsed.skills, "No skills found");
  setText("#parsedEducation", topCandidate.parsed.education || "Not detected");
  setText("#parsedExperience", topCandidate.parsed.experience || "Not detected");
  renderPills("#missingSkills", topCandidate.missing_skills, "No major gaps detected");
  renderSuggestions(topCandidate.suggestions);
  renderRanking(result.candidates);
}

function renderError(message) {
  setText("#candidateName", "Needs attention");
  setScore(0);
  renderPills("#parsedSkills", [], message);
  renderPills("#missingSkills", [], "--");
  setText("#parsedEducation", "--");
  setText("#parsedExperience", "--");
  document.querySelector("#suggestions").innerHTML = `<li>${escapeHtml(message)}</li>`;
  document.querySelector("#rankingList").innerHTML = `<p class="empty-state">${escapeHtml(message)}</p>`;
}

function setScore(score) {
  const ring = document.querySelector("#scoreRing");
  const value = Math.max(0, Math.min(100, Math.round(score)));
  ring.textContent = "";
  ring.dataset.score = `${value}`;
  ring.style.background = `conic-gradient(var(--accent) ${value * 3.6}deg, #e8f0f3 0deg)`;
}

function setText(selector, value) {
  document.querySelector(selector).textContent = value;
}

function renderPills(selector, items, emptyText) {
  const container = document.querySelector(selector);
  if (!items || !items.length) {
    container.innerHTML = `<p class="empty-state">${escapeHtml(emptyText)}</p>`;
    return;
  }

  container.innerHTML = items.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
}

function renderSuggestions(items) {
  const list = document.querySelector("#suggestions");
  if (!items || !items.length) {
    list.innerHTML = `<li>No suggestion generated.</li>`;
    return;
  }

  list.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderRanking(candidates) {
  const container = document.querySelector("#rankingList");
  container.innerHTML = candidates.map((candidate, index) => `
    <article class="ranking-item">
      <span class="rank-badge">${index + 1}</span>
      <div>
        <strong>${escapeHtml(candidate.name)}</strong>
        <small>${candidate.missing_skills.length} missing skills</small>
      </div>
      <strong>${Math.round(candidate.ats_score)}</strong>
    </article>
  `).join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

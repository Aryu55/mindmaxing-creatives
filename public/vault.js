import { CASE_STUDIES } from "./case-studies-data.js";

const categoryNames = {
  shopify: "Commerce & storefronts",
  growth: "Creative & growth",
  software: "Software & systems",
  motion: "3D & Commercial motion",
};
const featuredSlugs = ["saffron-origins", "knittire-3d", "abx-engine", "bukl", "whatsapp-autopilot", "safespot"];
const artWords = {
  "saffron-origins": "Saffron<br>Origins",
  "knittire-3d": "Knittire<br>3D",
  "abx-engine": "ABX<br>Engine",
  bukl: "BUKL",
  "whatsapp-autopilot": "WhatsApp<br>Autopilot",
  safespot: "Safe<br>Spot",
};
const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));

function artMarkup(study, index, featured = false) {
  const slug = escapeHtml(study.slug);
  const category = escapeHtml(study.category);
  const word = artWords[study.slug] || escapeHtml(study.title.replace(/:.*/, ""));
  const label = featured ? "Studio visual study" : "Project visual study";
  return `<div class="${featured ? "feature-art" : "archive-art"} ${featured ? `feature-art--${slug}` : `archive-art--${category} archive-art--${index % 6}`}" role="img" aria-label="Illustrative visual study for ${escapeHtml(study.title)}">
    <span class="${featured ? "feature-art-mark" : "archive-art-index"}">${String(index + 1).padStart(2, "0")} / ${label}</span>
    <span class="${featured ? "feature-art-word" : "archive-art-word"}">${word}</span>
    <span class="${featured ? "feature-art-foot" : "archive-art-note"}"><span>${escapeHtml(categoryNames[study.category] || "Studio project")}</span><span>Mindmaxing Studio</span></span>
  </div>`;
}

function featuredMarkup(study, index) {
  return `<article class="feature-card">
    <a class="feature-link" href="./case-studies.html#${encodeURIComponent(study.slug)}" aria-label="Open ${escapeHtml(study.title)} in the studio vault">
      ${artMarkup(study, index, true)}
      <div class="feature-caption"><div><span class="feature-category">${escapeHtml(categoryNames[study.category] || "Studio project")}</span><h3 class="feature-title">${escapeHtml(study.title.replace(/:.*/, ""))}</h3></div><span class="feature-arrow" aria-hidden="true">↗</span></div>
    </a>
  </article>`;
}

function renderFeatured() {
  const grid = document.querySelector("#featured-projects");
  if (!grid) return;
  grid.innerHTML = featuredSlugs
    .map((slug) => CASE_STUDIES.find((study) => study.slug === slug))
    .filter(Boolean)
    .map((study, index) => featuredMarkup(study, index))
    .join("");
}

function renderArchiveCard(study, index) {
  const tags = (study.techStack || []).slice(0, 2).map((tag) => `<span class="archive-tag">${escapeHtml(tag)}</span>`).join("");
  return `<article class="archive-card" data-slug="${escapeHtml(study.slug)}" data-category="${escapeHtml(study.category)}">
    ${artMarkup(study, index)}
    <div class="archive-card-body">
      <div class="archive-card-meta"><span>${escapeHtml(study.num || String(index + 1).padStart(2, "0"))}</span><span>${escapeHtml(categoryNames[study.category] || "Studio project")}</span></div>
      <h2>${escapeHtml(study.title)}</h2>
      <p>${escapeHtml(study.pitch || study.tagline || "A project from the Mindmaxing Studio archive.")}</p>
      <div class="archive-card-foot"><div class="archive-tags">${tags}</div><button class="text-action" type="button" data-open-case="${escapeHtml(study.slug)}">Open project ↗</button></div>
    </div>
  </article>`;
}

function showToast(message) {
  const toast = document.querySelector("#copy-toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.setTimeout(() => toast.classList.remove("is-visible"), 1900);
}

async function copyLink(slug) {
  const url = `${window.location.origin}${window.location.pathname}#${slug}`;
  try {
    await navigator.clipboard.writeText(url);
  } catch {
    const input = document.createElement("textarea");
    input.value = url;
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.append(input);
    input.select();
    document.execCommand("copy");
    input.remove();
  }
  showToast("Project link copied");
}

function openProject(study, updateHistory = true) {
  if (!study) return;
  const dialog = document.querySelector("#case-dialog");
  if (!dialog) return;
  dialog.dataset.slug = study.slug;
  dialog.querySelector("[data-dialog-number]").textContent = study.num || "Project record";
  dialog.querySelector("#dialog-title").textContent = study.title;
  dialog.querySelector("#dialog-tagline").textContent = study.tagline || study.pitch || "A project from the Mindmaxing Studio archive.";
  dialog.querySelector("#dialog-problem").textContent = study.problem || "No problem statement is attached to this project record.";
  dialog.querySelector("#dialog-solution").textContent = study.solution || "No build notes are attached to this project record.";

  const metrics = dialog.querySelector("#dialog-metrics");
  metrics.replaceChildren();
  (study.heroMetrics || []).forEach((metric) => {
    const item = document.createElement("div");
    item.className = "reported-metric";
    const value = document.createElement("strong");
    value.textContent = metric.val;
    const label = document.createElement("span");
    label.textContent = metric.lbl;
    item.append(value, label);
    metrics.append(item);
  });

  const results = dialog.querySelector("#dialog-results");
  results.replaceChildren();
  (study.results || []).forEach((result) => {
    const item = document.createElement("li");
    item.textContent = result;
    results.append(item);
  });

  const tech = dialog.querySelector("#dialog-tech");
  tech.replaceChildren();
  (study.techStack || []).forEach((tag) => {
    const item = document.createElement("span");
    item.textContent = tag;
    tech.append(item);
  });

  const liveLink = dialog.querySelector("#dialog-live-link");
  if (study.liveUrl && study.liveUrl !== "#" && !study.liveUrl.startsWith("mailto:")) {
    liveLink.href = study.liveUrl;
    liveLink.hidden = false;
  } else {
    liveLink.hidden = true;
  }

  const currentIndex = CASE_STUDIES.findIndex((entry) => entry.slug === study.slug);
  dialog.querySelector("#dialog-prev").disabled = currentIndex <= 0;
  dialog.querySelector("#dialog-next").disabled = currentIndex >= CASE_STUDIES.length - 1;
  if (!dialog.open) dialog.showModal();
  if (updateHistory && window.location.hash !== `#${study.slug}`) history.pushState(null, "", `#${study.slug}`);
}

function initArchive() {
  const grid = document.querySelector("#archive-grid");
  if (!grid) return;
  grid.innerHTML = CASE_STUDIES.map(renderArchiveCard).join("");

  const search = document.querySelector("#project-search");
  const count = document.querySelector("#archive-count");
  const empty = document.querySelector("#empty-state");
  const filters = [...document.querySelectorAll("[data-filter]")];
  let activeFilter = "all";

  function applyFilters() {
    const query = (search.value || "").trim().toLocaleLowerCase();
    let visible = 0;
    for (const card of grid.querySelectorAll(".archive-card")) {
      const study = CASE_STUDIES.find((entry) => entry.slug === card.dataset.slug);
      const haystack = [study.title, study.pitch, study.tagline, study.problem, study.solution, study.categoryLabel, ...(study.techStack || []), ...(study.results || [])].join(" ").toLocaleLowerCase();
      const matches = (activeFilter === "all" || study.category === activeFilter) && (!query || haystack.includes(query));
      card.hidden = !matches;
      if (matches) visible += 1;
    }
    count.textContent = `${String(visible).padStart(2, "0")} / ${CASE_STUDIES.length} project files`;
    empty.classList.toggle("is-visible", visible === 0);
    grid.hidden = visible === 0;
  }

  filters.forEach((button) => button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    filters.forEach((filter) => filter.setAttribute("aria-pressed", String(filter === button)));
    applyFilters();
  }));
  search.addEventListener("input", applyFilters);
  grid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-open-case]");
    if (button) openProject(CASE_STUDIES.find((study) => study.slug === button.dataset.openCase));
  });
  applyFilters();
}

function initDialog() {
  const dialog = document.querySelector("#case-dialog");
  if (!dialog) return;
  dialog.querySelector("[data-close-dialog]").addEventListener("click", () => dialog.close());
  dialog.querySelector("[data-copy-dialog]").addEventListener("click", () => copyLink(dialog.dataset.slug));
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    if (window.location.hash) history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  });
  dialog.querySelector("#dialog-prev").addEventListener("click", () => {
    const index = CASE_STUDIES.findIndex((study) => study.slug === dialog.dataset.slug);
    if (index > 0) openProject(CASE_STUDIES[index - 1]);
  });
  dialog.querySelector("#dialog-next").addEventListener("click", () => {
    const index = CASE_STUDIES.findIndex((study) => study.slug === dialog.dataset.slug);
    if (index < CASE_STUDIES.length - 1) openProject(CASE_STUDIES[index + 1]);
  });
  window.addEventListener("keydown", (event) => {
    if (!dialog.open) return;
    if (event.key === "ArrowLeft") dialog.querySelector("#dialog-prev").click();
    if (event.key === "ArrowRight") dialog.querySelector("#dialog-next").click();
  });
}

function handleHash() {
  const slug = decodeURIComponent(window.location.hash.slice(1));
  const study = CASE_STUDIES.find((entry) => entry.slug === slug);
  const dialog = document.querySelector("#case-dialog");
  if (study && dialog) openProject(study, false);
  else if (!study && dialog?.open) dialog.close();
}

renderFeatured();
initArchive();
initDialog();
handleHash();
window.addEventListener("hashchange", handleHash);

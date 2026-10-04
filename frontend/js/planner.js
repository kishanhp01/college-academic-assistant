import { api, requireAuth, bindLogout, showError, clearError } from "./api.js";

bindLogout();
try { await requireAuth(); } catch { /* The form remains visible; API calls will show an error. */ }

const subjects = document.querySelector("#subjects");
const planForm = document.querySelector("#plan-form");
const modifyForm = document.querySelector("#modify-form");
const resultSection = document.querySelector("#plan-result");
const generateError = document.querySelector("#plan-error");
const modifyError = document.querySelector("#modify-error");
let currentPlan = null;

function addSubject(values = {}) {
  const row = document.createElement("fieldset");
  row.className = "subject-row";
  const legend = document.createElement("legend");
  legend.textContent = `Subject ${subjects.children.length + 1}`;
  const grid = document.createElement("div");
  grid.className = "subject-fields";
  const nameWrap = document.createElement("div");
  const nameLabel = document.createElement("label");
  nameLabel.textContent = "Subject name";
  const name = document.createElement("input");
  name.type = "text"; name.required = true; name.maxLength = 100; name.placeholder = "e.g. Data Structures"; name.value = values.name || "";
  nameLabel.append(name); nameWrap.append(nameLabel);
  const difficultyWrap = document.createElement("div");
  const difficultyLabel = document.createElement("label");
  difficultyLabel.textContent = "Difficulty";
  const difficulty = document.createElement("select"); difficulty.required = true;
  for (const [level, score] of [["Easy", 1], ["Medium", 3], ["Hard", 5]]) {
    const item = document.createElement("option"); item.value = String(score); item.textContent = level; difficulty.append(item);
  }
  difficulty.value = String(values.difficulty ?? 3); difficultyLabel.append(difficulty); difficultyWrap.append(difficultyLabel);
  const priorityWrap = document.createElement("div");
  const priorityLabel = document.createElement("label"); priorityLabel.textContent = "Priority (1–5)";
  const priority = document.createElement("input"); priority.type = "number"; priority.min = "1"; priority.max = "5"; priority.step = "1"; priority.value = values.priority ?? 3;
  priorityLabel.append(priority); priorityWrap.append(priorityLabel);
  const remove = document.createElement("button"); remove.className = "button text-button remove-subject"; remove.type = "button"; remove.textContent = "Remove"; remove.setAttribute("aria-label", "Remove this subject");
  remove.addEventListener("click", () => { row.remove(); renumberSubjects(); });
  grid.append(nameWrap, difficultyWrap, priorityWrap);
  row.append(legend, grid, remove);
  subjects.append(row);
}

function renumberSubjects() {
  [...subjects.querySelectorAll("legend")].forEach((legend, index) => { legend.textContent = `Subject ${index + 1}`; });
}

document.querySelector("#add-subject").addEventListener("click", () => addSubject());
addSubject();

planForm.addEventListener("submit", async (event) => {
  event.preventDefault(); clearError(generateError);
  const rows = [...subjects.querySelectorAll(".subject-row")];
  const payload = {
    subjects: rows.map((row) => {
      const fields = row.querySelectorAll("input, select");
      return { name: fields[0].value.trim(), difficulty: Number(fields[1].value), priority: Number(fields[2].value) };
    }),
    exam_date: document.querySelector("#exam-date").value,
    available_hours_per_day: Number(document.querySelector("#hours").value),
    preferences: document.querySelector("#preferences").value.trim() || null,
  };
  if (!payload.subjects.length || payload.subjects.some((subject) => !subject.name)) {
    showError(generateError, "Add at least one subject and give each one a name."); return;
  }
  const button = document.querySelector("#generate-button"); button.disabled = true; button.textContent = "Building your plan…";
  try {
    const response = await api.generatePlan(payload);
    currentPlan = response.plan;
    document.querySelector("#modify-button").disabled = false;
    renderPlan(currentPlan);
  } catch (error) { showError(generateError, error.message); }
  finally { button.disabled = false; button.textContent = "Generate plan"; }
});

modifyForm.addEventListener("submit", async (event) => {
  event.preventDefault(); clearError(modifyError);
  if (!currentPlan) { showError(modifyError, "Generate a plan before making changes."); return; }
  const missedText = document.querySelector("#missed").value.trim();
  const priorities = {};
  const priorityText = document.querySelector("#priorities").value.trim();
  if (priorityText) {
    for (const line of priorityText.split("\n")) {
      const match = line.match(/^\s*(.+?)\s*=\s*([1-5])\s*$/);
      if (!match) { showError(modifyError, "Enter priorities as Subject=1 to 5, one per line."); return; }
      priorities[match[1]] = Number(match[2]);
    }
  }
  const hours = document.querySelector("#new-hours").value;
  const examDate = document.querySelector("#new-exam-date").value;
  const payload = {
    plan: currentPlan,
    missed_sessions: missedText ? missedText.split(",").map((name) => name.trim()).filter(Boolean) : [],
    ...(hours ? { available_hours_per_day: Number(hours) } : {}),
    ...(examDate ? { exam_date: examDate } : {}),
    ...(Object.keys(priorities).length ? { changed_priorities: priorities } : {}),
  };
  const button = document.querySelector("#modify-button"); button.disabled = true; button.textContent = "Updating plan…";
  try {
    const response = await api.modifyPlan(payload);
    currentPlan = response.plan; renderPlan(currentPlan);
  } catch (error) { showError(modifyError, error.message); }
  finally { button.disabled = false; button.textContent = "Update plan"; }
});

function renderPlan(plan) {
  resultSection.replaceChildren();
  const heading = document.createElement("div"); heading.className = "section-heading compact";
  const title = document.createElement("h2"); title.textContent = "Your study plan";
  const subtitle = document.createElement("p"); subtitle.className = "muted"; subtitle.textContent = `Exam date: ${plan.exam_date}`;
  heading.append(title, subtitle); resultSection.append(heading);
  if (Array.isArray(plan.assumptions) && plan.assumptions.length) {
    const assumptions = document.createElement("p"); assumptions.className = "planner-assumptions"; assumptions.textContent = plan.assumptions.join(" "); resultSection.append(assumptions);
  }
  const list = document.createElement("div"); list.className = "session-list";
  for (const session of plan.sessions || []) {
    const card = document.createElement("article"); card.className = "session-card";
    const date = document.createElement("time"); date.textContent = session.date;
    const subject = document.createElement("h3"); subject.textContent = session.subject;
    const detail = document.createElement("p"); detail.textContent = `${session.hours} hours · ${session.activity}`;
    card.append(date, subject, detail); list.append(card);
  }
  resultSection.append(list); resultSection.hidden = false; resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

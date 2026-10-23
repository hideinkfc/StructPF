#!/usr/bin/env python3
"""Build a self-contained, blinded interactive HTML human-evaluation app for Study A."""

from __future__ import annotations

import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[1]
STRUCTPF_DIR = (
    ROOT
    / "experiments/results/pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021/rahimi_cells_v30"
)
ONESHOT_DIR = (
    ROOT
    / "experiments/results/pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021/main30_oneshot_v30"
)
OUT_HTML = ROOT / "docs/status/STUDY_A_HUMAN_EVAL.html"
OUT_MANIFEST = ROOT / "experiments/configs/pf_study_a_human_eval_sample_24.json"

CELL_LABELS = {
    "sports_basketball_ratio": {
        "short": "Basketball Ratios",
        "grade": "Grade 7",
        "theme": "Sports (Basketball)",
    },
    "shopping_percent": {
        "short": "Phone Plans & Linear Equations",
        "grade": "Grade 7",
        "theme": "Everyday Shopping / Plans",
    },
    "music_compare_distributions": {
        "short": "Music Sample Distributions",
        "grade": "Grade 7",
        "theme": "Music (Song Durations)",
    },
    "garden_composite_area": {
        "short": "Garden Composite Area",
        "grade": "Grade 7",
        "theme": "Home & Garden Geometry",
    },
}

ARM_LABELS = {
    "pipeline_lc": "StructPF (GPT-5 mini)",
    "gpt5mini": "One-Shot (GPT-5 mini)",
    "gpt41": "One-Shot (GPT-4.1)",
}

MEASURE_KEYS = [
    "target_alignment",
    "mathematical_validity",
    "prior_knowledge_accessibility",
    "familiar_approach_limits",
    "room_for_invention",
]


def load_record(path: pathlib.Path, arm: str) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    res = raw["result"]
    tj_in = res["task_judge"]["input"]
    lt = tj_in.get("learning_target", "")
    target_str = (
        (lt.get("concept") or lt.get("target_concept") or str(lt))
        if isinstance(lt, dict)
        else str(lt)
    )
    lc = tj_in.get("learner_context", {})
    prior_list = []
    for item in lc.get("assumed_prior_knowledge", []):
        if isinstance(item, dict):
            res_name = item.get("resource", "")
            taught_as = item.get("taught_as", "")
            prior_list.append(f"{res_name}: {taught_as}" if taught_as else res_name)
        elif isinstance(item, str):
            prior_list.append(item)

    measures = {}
    reasons = {}
    for k in MEASURE_KEYS:
        m = res["measures"].get(k, {})
        val = m.get("value", "no")
        measures[k] = "yes" if val == "yes" else "no"
        ev = m.get("evidence") or {}
        if k == "familiar_approach_limits":
            atts = ev.get("attempts") or []
            reasons[k] = " | ".join(
                f"[{a.get('status')}] {a.get('reason', '')}" for a in atts[:2]
            )
        else:
            reasons[k] = ev.get("reason", "")

    return {
        "key": raw["key"],
        "cell_id": raw["cell_id"],
        "setting_name": CELL_LABELS[raw["cell_id"]]["short"],
        "theme": CELL_LABELS[raw["cell_id"]]["theme"],
        "arm": arm,
        "arm_label": ARM_LABELS[arm],
        "student_task": tj_in.get("student_task", "").strip(),
        "target_concept": target_str,
        "prior_knowledge": prior_list,
        "pf_eval_measures": measures,
        "pf_eval_all5": all(measures[k] == "yes" for k in MEASURE_KEYS),
        "pf_eval_reasons": reasons,
    }


def build_sample(seed: int = 42, per_cell_arm: int = 2) -> list[dict]:
    rng = random.Random(seed)
    by_cell_arm: dict[tuple[str, str], list[dict]] = {}

    for p in sorted(STRUCTPF_DIR.glob("*.json")):
        rec = load_record(p, "pipeline_lc")
        by_cell_arm.setdefault((rec["cell_id"], "pipeline_lc"), []).append(rec)

    for p in sorted(ONESHOT_DIR.glob("*.json")):
        name = p.name
        arm = "gpt5mini" if "__gpt5mini__" in name else "gpt41"
        rec = load_record(p, arm)
        by_cell_arm.setdefault((rec["cell_id"], arm), []).append(rec)

    sampled = []
    for cell_id in CELL_LABELS:
        for arm in ["pipeline_lc", "gpt5mini", "gpt41"]:
            pool = by_cell_arm[(cell_id, arm)]
            chosen = rng.sample(pool, per_cell_arm)
            sampled.extend(chosen)

    rng.shuffle(sampled)
    for idx, item in enumerate(sampled, start=1):
        item["blind_id"] = f"T{idx:02d}"
        item["display_index"] = idx
    return sampled


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Study A Blinded Human Evaluation — PF Eval (24 Tasks)</title>
<style>
  :root {
    --bg: #f6f8fb;
    --card: #ffffff;
    --border: #dce3ec;
    --text: #1b2430;
    --muted: #5b6777;
    --blue: #2f5597;
    --blue-light: #e9f0fb;
    --green: #2e7d32;
    --green-light: #e8f5e9;
    --red: #c62828;
    --red-light: #ffebee;
    --amber: #ef6c00;
    --amber-light: #fff3e0;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }
  header {
    background: #1b2430;
    color: #fff;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
  }
  header h1 {
    margin: 0;
    font-size: 17px;
    font-weight: 600;
  }
  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .progress-pill {
    background: rgba(255,255,255,0.14);
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 500;
  }
  .btn {
    border: 1px solid transparent;
    background: var(--blue);
    color: #fff;
    padding: 7px 13px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn:hover { opacity: 0.92; }
  .btn-outline {
    background: transparent;
    border-color: rgba(255,255,255,0.35);
    color: #fff;
  }
  .btn-outline:hover { background: rgba(255,255,255,0.1); }
  .btn-secondary {
    background: #eef2f7;
    color: var(--text);
    border-color: var(--border);
  }
  .btn-secondary:hover { background: #e2e8f0; }
  .btn-success {
    background: var(--green);
    color: #fff;
  }
  .container {
    max-width: 1280px;
    margin: 18px auto;
    padding: 0 20px 40px;
  }
  /* Task grid strip */
  .task-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    background: var(--card);
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid var(--border);
    margin-bottom: 16px;
    align-items: center;
  }
  .task-pill {
    width: 38px;
    height: 32px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: #f8fafc;
    color: var(--muted);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.12s;
  }
  .task-pill:hover { border-color: var(--blue); color: var(--blue); }
  .task-pill.done {
    background: var(--green-light);
    border-color: #81c784;
    color: var(--green);
  }
  .task-pill.active {
    outline: 2px solid var(--blue);
    outline-offset: 1px;
    font-weight: 700;
  }
  /* Two-column layout */
  .workspace {
    display: grid;
    grid-template-columns: 1.22fr 1fr;
    gap: 18px;
    align-items: start;
  }
  @media (max-width: 960px) {
    .workspace { grid-template-columns: 1fr; }
  }
  .panel {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px 22px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
  }
  .meta-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
  }
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    background: var(--blue-light);
    color: var(--blue);
  }
  .badge-unblind {
    background: var(--amber-light);
    color: var(--amber);
  }
  .context-box {
    background: #f8fafd;
    border: 1px solid #e1e8f2;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 16px;
    font-size: 13.5px;
  }
  .context-box h4 {
    margin: 0 0 6px 0;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--blue);
  }
  .context-box ul {
    margin: 4px 0 0 18px;
    padding: 0;
  }
  .context-box li { margin-bottom: 3px; }
  .task-body {
    font-size: 15.5px;
    line-height: 1.65;
    white-space: pre-wrap;
    background: #fff;
    padding: 16px 18px;
    border-radius: 8px;
    border: 1px solid #cfd8e3;
    color: #111827;
  }
  .helper-toggle {
    margin-top: 12px;
  }
  .helper-box {
    margin-top: 8px;
    padding: 12px 14px;
    background: #fffdf5;
    border: 1px dashed #e0b450;
    border-radius: 8px;
    font-size: 13px;
    color: #443716;
    display: none;
  }
  .helper-box.open { display: block; }
  /* Rating checklist */
  .preset-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }
  .measure-item {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 11px 14px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    background: #fafbfd;
    transition: border-color 0.12s, background 0.12s;
  }
  .measure-item.rated-yes {
    border-color: #a5d6a7;
    background: #f4fbf5;
  }
  .measure-item.rated-no {
    border-color: #ef9a9a;
    background: #fff8f8;
  }
  .measure-info { flex: 1; }
  .measure-title {
    font-weight: 600;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .measure-group-tag {
    font-size: 11px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 4px;
    background: #e5eaf2;
    color: #3f4d63;
  }
  .measure-desc {
    font-size: 12.5px;
    color: var(--muted);
    margin-top: 2px;
  }
  .yn-group {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }
  .yn-btn {
    min-width: 56px;
    padding: 7px 12px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: #fff;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.1s;
  }
  .yn-btn.yes.selected {
    background: var(--green);
    color: #fff;
    border-color: var(--green);
  }
  .yn-btn.no.selected {
    background: var(--red);
    color: #fff;
    border-color: var(--red);
  }
  .nav-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  textarea.notes {
    width: 100%;
    min-height: 54px;
    margin-top: 8px;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 13px;
    font-family: inherit;
  }
  /* Results modal / view */
  .results-section {
    display: none;
    margin-top: 20px;
  }
  .results-section.open { display: block; }
  table.res-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13.5px;
    margin: 10px 0 20px;
  }
  table.res-table th, table.res-table td {
    border-bottom: 1px solid var(--border);
    padding: 9px 10px;
    text-align: center;
  }
  table.res-table th:first-child, table.res-table td:first-child {
    text-align: left;
  }
  table.res-table thead th {
    background: #f1f5f9;
    font-weight: 600;
  }
  pre.latex-box {
    background: #1e293b;
    color: #f8fafc;
    padding: 14px;
    border-radius: 8px;
    font-size: 12.5px;
    overflow-x: auto;
  }
  .kbd {
    display: inline-block;
    padding: 1px 5px;
    font-size: 11px;
    background: #e2e8f0;
    border-radius: 4px;
    color: #334155;
    font-family: monospace;
  }
</style>
</head>
<body>

<header>
  <div>
    <h1>Study A Human Evaluation (24 Stratified Tasks, Blinded)</h1>
  </div>
  <div class="header-right">
    <span class="progress-pill" id="progressText">0 / 24 rated</span>
    <button class="btn btn-outline" onclick="toggleResultsView()" id="toggleResBtn">Show Results & Agreement</button>
    <button class="btn btn-outline" onclick="exportRatingsJSON()">Export JSON</button>
    <button class="btn btn-outline" onclick="importRatingsPrompt()">Import JSON</button>
  </div>
</header>

<div class="container">
  <div class="task-strip" id="taskStrip"></div>

  <div class="workspace" id="ratingWorkspace">
    <!-- Left: Student Task & Setting Context -->
    <div class="panel">
      <div class="meta-bar">
        <div>
          <strong id="taskTitle" style="font-size: 17px;">Task T01</strong>
          <span class="badge" id="settingBadge" style="margin-left: 8px;">Setting</span>
          <span class="badge badge-unblind" id="armBadge" style="display:none; margin-left: 6px;">Arm</span>
        </div>
        <div style="font-size: 12.5px; color: var(--muted);">
          Keys: <span class="kbd">←</span> <span class="kbd">→</span> nav &middot; <span class="kbd">A</span> All Yes &middot; <span class="kbd">F</span> Only #4 No
        </div>
      </div>

      <div class="context-box">
        <h4>Target Concept (Untaught in Phase 1)</h4>
        <div id="targetConceptText" style="margin-bottom: 8px; font-weight: 500;"></div>
        <h4>Assumed Grade 7 Prior Knowledge</h4>
        <ul id="priorKnowledgeList"></ul>
      </div>

      <div style="font-size: 12.5px; font-weight: 600; text-transform: uppercase; color: var(--muted); margin-bottom: 6px;">
        Student-Facing Problem Text
      </div>
      <div class="task-body" id="studentTaskText"></div>

      <div class="helper-toggle">
        <button class="btn btn-secondary" onclick="toggleHelper()" id="helperBtn" style="font-size:12.5px;">
          Show Automated Solver & Math Check (After / During Rating)
        </button>
        <div class="helper-box" id="helperBox"></div>
      </div>
    </div>

    <!-- Right: 5 PF Eval Measures -->
    <div class="panel">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <strong style="font-size: 15.5px;">Rate the 5 PF Task-Design Measures</strong>
        <span id="taskStatusLabel" style="font-size:12.5px; color:var(--muted);">Incomplete</span>
      </div>

      <div class="preset-row">
        <button class="btn btn-secondary" onclick="applyPreset('all_yes')" title="Shortcut: A">
          ✓ Quick Fill: All 5 Yes
        </button>
        <button class="btn btn-secondary" onclick="applyPreset('only_4_no')" title="Shortcut: F">
          ✗ Quick Fill: Only #4 (Familiar Methods) = No
        </button>
        <button class="btn btn-secondary" onclick="applyPreset('4_and_5_no')">
          ✗ Quick Fill: #4 & #5 = No
        </button>
      </div>

      <div id="measuresContainer"></div>

      <label style="font-size: 12.5px; font-weight: 600; color: var(--muted); display:block; margin-top:10px;">
        Optional Note (e.g., why it failed):
      </label>
      <textarea class="notes" id="taskNotes" placeholder="Optional brief note..." oninput="saveNote(this.value)"></textarea>

      <div class="nav-row">
        <button class="btn btn-secondary" onclick="prevTask()" id="prevBtn">← Previous</button>
        <button class="btn" onclick="nextUnratedOrNext()" id="nextBtn">Next Task →</button>
      </div>
    </div>
  </div>

  <!-- Results & Agreement Panel -->
  <div class="panel results-section" id="resultsSection">
    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:12px; margin-bottom:14px;">
      <div>
        <h2 style="margin:0; font-size:18px;">Unblinded Summary: Human vs. PF Eval (Study A Sample, N = 24)</h2>
        <div style="font-size:13px; color:var(--muted);">Automatically computed from your ratings below.</div>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-secondary" onclick="toggleUnblindBadges()">Toggle Arm Labels on Task Cards</button>
        <button class="btn btn-success" onclick="exportRatingsJSON()">Download Results JSON</button>
      </div>
    </div>

    <h3>1. Pass Rates by Generator Arm (Human vs. PF Eval)</h3>
    <div id="armTableWrap"></div>

    <h3>2. Human vs. PF Eval Agreement & Cohen's κ</h3>
    <div id="agreementTableWrap"></div>

    <h3>3. Ready-to-Paste LaTeX Table for Chapter 6</h3>
    <pre class="latex-box" id="latexOutput"></pre>
  </div>
</div>

<script>
const TASKS = __TASKS_JSON__;
const DEFAULT_RATINGS = __DEFAULT_RATINGS_JSON__;

const MEASURES = [
  {
    key: "target_alignment",
    num: 1,
    group: "Task Soundness",
    title: "1. Target Alignment",
    desc: "Does the problem genuinely target the intended concept (rather than an unrelated topic)?"
  },
  {
    key: "mathematical_validity",
    num: 2,
    group: "Task Soundness",
    title: "2. Mathematical Validity",
    desc: "Are the given numbers, units, and conditions mathematically consistent and solvable?"
  },
  {
    key: "prior_knowledge_accessibility",
    num: 3,
    group: "PF Req 1",
    title: "3. Accessible Start",
    desc: "Can Grade 7 students make a meaningful start using the listed prior skills?"
  },
  {
    key: "familiar_approach_limits",
    num: 4,
    group: "PF Req 2",
    title: "4. Familiar Methods Fall Short",
    desc: "Do simple prior shortcuts (e.g., comparing averages/rates alone) hit a tie or fail so the target concept is needed?"
  },
  {
    key: "room_for_invention",
    num: 5,
    group: "PF Req 3",
    title: "5. Room for Invention",
    desc: "Does the prompt stay open-ended without giving away the target formula or a step-by-step recipe?"
  }
];

const STORAGE_KEY = "structpf_study_a_human_eval_v1";
let state = {
  currentIndex: 0,
  unblindCards: false,
  helperOpen: false,
  ratings: {} // blind_id -> { target_alignment: 'yes'|'no', ..., note: '' }
};

function loadState() {
  state.ratings = JSON.parse(JSON.stringify(DEFAULT_RATINGS));
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed && parsed.ratings && Object.keys(parsed.ratings).length > 0) {
        state.ratings = Object.assign({}, state.ratings, parsed.ratings);
      }
    }
  } catch (e) {
    console.error(e);
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ ratings: state.ratings }));
}

function isTaskComplete(blindId) {
  const r = state.ratings[blindId];
  if (!r) return false;
  return MEASURES.every(m => r[m.key] === "yes" || r[m.key] === "no");
}

function getCompletedCount() {
  return TASKS.filter(t => isTaskComplete(t.blind_id)).length;
}

function renderStrip() {
  const strip = document.getElementById("taskStrip");
  strip.innerHTML = "";
  TASKS.forEach((t, idx) => {
    const btn = document.createElement("button");
    const done = isTaskComplete(t.blind_id);
    btn.className = "task-pill" + (done ? " done" : "") + (idx === state.currentIndex ? " active" : "");
    btn.textContent = t.blind_id;
    btn.onclick = () => { state.currentIndex = idx; renderAll(); };
    strip.appendChild(btn);
  });
  const doneCount = getCompletedCount();
  document.getElementById("progressText").textContent = `${doneCount} / ${TASKS.length} rated`;
}

function renderTask() {
  const t = TASKS[state.currentIndex];
  const r = state.ratings[t.blind_id] || {};

  document.getElementById("taskTitle").textContent = `Task ${t.blind_id} (${state.currentIndex + 1} of ${TASKS.length})`;
  document.getElementById("settingBadge").textContent = `${t.setting_name}`;

  const armBadge = document.getElementById("armBadge");
  if (state.unblindCards) {
    armBadge.style.display = "inline-block";
    armBadge.textContent = t.arm_label;
  } else {
    armBadge.style.display = "none";
  }

  document.getElementById("targetConceptText").textContent = t.target_concept;
  const ul = document.getElementById("priorKnowledgeList");
  ul.innerHTML = "";
  t.prior_knowledge.forEach(pk => {
    const li = document.createElement("li");
    li.textContent = pk;
    ul.appendChild(li);
  });

  document.getElementById("studentTaskText").textContent = t.student_task;

  // Helper box with number & solver check notes (without showing generator arm!)
  const helperBox = document.getElementById("helperBox");
  helperBox.className = "helper-box" + (state.helperOpen ? " open" : "");
  document.getElementById("helperBtn").textContent = state.helperOpen
    ? "Hide Automated Math & Solver Notes"
    : "Show Automated Math & Solver Notes (Quick Calculation Aid)";
  helperBox.innerHTML = `
    <div style="margin-bottom:6px;"><strong>Math Check:</strong> ${escapeHtml(t.pf_eval_reasons.mathematical_validity || "")}</div>
    <div style="margin-bottom:6px;"><strong>Prior-Knowledge Solver Check:</strong> ${escapeHtml(t.pf_eval_reasons.familiar_approach_limits || "")}</div>
    <div><strong>Giveaway Check:</strong> ${escapeHtml(t.pf_eval_reasons.room_for_invention || "")}</div>
  `;

  // Measures
  const container = document.getElementById("measuresContainer");
  container.innerHTML = "";
  MEASURES.forEach(m => {
    const val = r[m.key];
    const row = document.createElement("div");
    row.className = "measure-item" + (val === "yes" ? " rated-yes" : val === "no" ? " rated-no" : "");
    row.innerHTML = `
      <div class="measure-info">
        <div class="measure-title">
          <span>${m.title}</span>
          <span class="measure-group-tag">${m.group}</span>
        </div>
        <div class="measure-desc">${m.desc}</div>
      </div>
      <div class="yn-group">
        <button class="yn-btn yes ${val === 'yes' ? 'selected' : ''}" onclick="setRating('${m.key}', 'yes')">Yes</button>
        <button class="yn-btn no ${val === 'no' ? 'selected' : ''}" onclick="setRating('${m.key}', 'no')">No</button>
      </div>
    `;
    container.appendChild(row);
  });

  const done = isTaskComplete(t.blind_id);
  const statusEl = document.getElementById("taskStatusLabel");
  if (done) {
    const all5 = MEASURES.every(m => r[m.key] === "yes");
    statusEl.textContent = all5 ? "✓ Rated (Passes All 5)" : "✓ Rated (Fails ≥1 measure)";
    statusEl.style.color = "var(--green)";
    statusEl.style.fontWeight = "600";
  } else {
    statusEl.textContent = "Select Yes/No for all 5";
    statusEl.style.color = "var(--muted)";
    statusEl.style.fontWeight = "400";
  }

  document.getElementById("taskNotes").value = r.note || "";
  document.getElementById("prevBtn").disabled = state.currentIndex === 0;
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function setRating(measureKey, value) {
  const t = TASKS[state.currentIndex];
  if (!state.ratings[t.blind_id]) state.ratings[t.blind_id] = {};
  state.ratings[t.blind_id][measureKey] = value;
  saveState();
  renderAll();
}

function applyPreset(presetName) {
  const t = TASKS[state.currentIndex];
  if (!state.ratings[t.blind_id]) state.ratings[t.blind_id] = {};
  const r = state.ratings[t.blind_id];
  if (presetName === "all_yes") {
    MEASURES.forEach(m => { r[m.key] = "yes"; });
  } else if (presetName === "only_4_no") {
    MEASURES.forEach(m => {
      r[m.key] = (m.key === "familiar_approach_limits") ? "no" : "yes";
    });
  } else if (presetName === "4_and_5_no") {
    MEASURES.forEach(m => {
      r[m.key] = (m.key === "familiar_approach_limits" || m.key === "room_for_invention") ? "no" : "yes";
    });
  }
  saveState();
  renderAll();
}

function saveNote(val) {
  const t = TASKS[state.currentIndex];
  if (!state.ratings[t.blind_id]) state.ratings[t.blind_id] = {};
  state.ratings[t.blind_id].note = val;
  saveState();
}

function prevTask() {
  if (state.currentIndex > 0) {
    state.currentIndex--;
    renderAll();
  }
}

function nextUnratedOrNext() {
  if (state.currentIndex < TASKS.length - 1) {
    state.currentIndex++;
    renderAll();
  } else {
    const firstUnrated = TASKS.findIndex(t => !isTaskComplete(t.blind_id));
    if (firstUnrated !== -1) {
      state.currentIndex = firstUnrated;
      renderAll();
    } else {
      const sec = document.getElementById("resultsSection");
      sec.classList.add("open");
      renderResultsTables();
      sec.scrollIntoView({ behavior: "smooth" });
    }
  }
}

function toggleHelper() {
  state.helperOpen = !state.helperOpen;
  renderTask();
}

function toggleResultsView() {
  const sec = document.getElementById("resultsSection");
  sec.classList.toggle("open");
  if (sec.classList.contains("open")) {
    renderResultsTables();
    sec.scrollIntoView({ behavior: "smooth" });
  }
}

function toggleUnblindBadges() {
  state.unblindCards = !state.unblindCards;
  renderTask();
}

function computeKappa(pairs) {
  // pairs: array of [humanBool, autoBool]
  const n = pairs.length;
  if (n === 0) return { acc: 0, kappa: 0 };
  let yy = 0, yn = 0, ny = 0, nn = 0;
  pairs.forEach(([h, a]) => {
    if (h && a) yy++;
    else if (h && !a) yn++;
    else if (!h && a) ny++;
    else nn++;
  });
  const po = (yy + nn) / n;
  const pYesH = (yy + yn) / n;
  const pYesA = (yy + ny) / n;
  const pe = pYesH * pYesA + (1 - pYesH) * (1 - pYesA);
  const kappa = Math.abs(1 - pe) < 1e-9 ? 1.0 : (po - pe) / (1 - pe);
  return { acc: po * 100, kappa, n, yy, yn, ny, nn };
}

function renderResultsTables() {
  const arms = [
    { id: "gpt41", label: "One-Shot (GPT-4.1)" },
    { id: "gpt5mini", label: "One-Shot (GPT-5 mini)" },
    { id: "pipeline_lc", label: "StructPF (GPT-5 mini)" }
  ];

  // Table 1: Pass rates by arm
  let html1 = `<table class="res-table"><thead><tr>
    <th>Measure</th>
    ${arms.map(a => `<th>${a.label}<br><small>Human / PF Eval</small></th>`).join("")}
  </tr></thead><tbody>`;

  const armRowsLatex = [];

  MEASURES.forEach(m => {
    html1 += `<tr><td><strong>${m.title}</strong></td>`;
    arms.forEach(a => {
      const sub = TASKS.filter(t => t.arm === a.id && isTaskComplete(t.blind_id));
      const hYes = sub.filter(t => state.ratings[t.blind_id][m.key] === "yes").length;
      const eYes = sub.filter(t => t.pf_eval_measures[m.key] === "yes").length;
      const denom = sub.length;
      html1 += `<td>${denom ? `${hYes}/${denom} (${Math.round(100*hYes/denom)}%) &middot; <span style="color:var(--muted)">${eYes}/${denom}</span>` : "—"}</td>`;
    });
    html1 += `</tr>`;
  });

  // Passes all 5
  html1 += `<tr style="background:#f8fafc; font-weight:700;"><td>Passes All 5 Measures</td>`;
  arms.forEach(a => {
    const sub = TASKS.filter(t => t.arm === a.id && isTaskComplete(t.blind_id));
    const hAll = sub.filter(t => MEASURES.every(m => state.ratings[t.blind_id][m.key] === "yes")).length;
    const eAll = sub.filter(t => t.pf_eval_all5).length;
    const denom = sub.length;
    html1 += `<td>${denom ? `${hAll}/${denom} (${Math.round(100*hAll/denom)}%) &middot; <span style="color:var(--muted)">${eAll}/${denom}</span>` : "—"}</td>`;
  });
  html1 += `</tr></tbody></table>`;
  document.getElementById("armTableWrap").innerHTML = html1;

  // Table 2: Agreement per measure
  let html2 = `<table class="res-table"><thead><tr>
    <th>Measure</th><th>Rated N</th><th>Exact Agreement</th><th>Cohen's κ</th><th>Both Yes / Both No / Disagreements</th>
  </tr></thead><tbody>`;

  let allPairs = [];
  MEASURES.forEach(m => {
    const completed = TASKS.filter(t => isTaskComplete(t.blind_id));
    const pairs = completed.map(t => [
      state.ratings[t.blind_id][m.key] === "yes",
      t.pf_eval_measures[m.key] === "yes"
    ]);
    allPairs = allPairs.concat(pairs);
    const st = computeKappa(pairs);
    html2 += `<tr>
      <td><strong>${m.title}</strong></td>
      <td>${st.n}</td>
      <td><strong>${st.acc.toFixed(1)}%</strong></td>
      <td>${st.kappa.toFixed(2)}</td>
      <td>${st.yy} Yes / ${st.nn} No / ${st.yn + st.ny} diff</td>
    </tr>`;
  });

  // All 5 pass agreement
  const completedAll = TASKS.filter(t => isTaskComplete(t.blind_id));
  const all5Pairs = completedAll.map(t => [
    MEASURES.every(m => state.ratings[t.blind_id][m.key] === "yes"),
    t.pf_eval_all5
  ]);
  const stAll5 = computeKappa(all5Pairs);
  const stPooled = computeKappa(allPairs);

  html2 += `<tr style="background:#f8fafc; font-weight:700;">
    <td>Passes All 5 Measures (Task-Level)</td>
    <td>${stAll5.n}</td>
    <td>${stAll5.acc.toFixed(1)}%</td>
    <td>${stAll5.kappa.toFixed(2)}</td>
    <td>${stAll5.yy} Yes / ${stAll5.nn} No / ${stAll5.yn + stAll5.ny} diff</td>
  </tr>`;
  html2 += `<tr style="background:#eef2f7; font-weight:700;">
    <td>Pooled Across All 5 Measures</td>
    <td>${stPooled.n}</td>
    <td>${stPooled.acc.toFixed(1)}%</td>
    <td>${stPooled.kappa.toFixed(2)}</td>
    <td>${stPooled.yy} Yes / ${stPooled.nn} No / ${stPooled.yn + stPooled.ny} diff</td>
  </tr></tbody></table>`;
  document.getElementById("agreementTableWrap").innerHTML = html2;

  // Generate LaTeX snippet
  function fmtCell(armId, mKey) {
    const sub = TASKS.filter(t => t.arm === armId && isTaskComplete(t.blind_id));
    if (!sub.length) return "--";
    const hYes = sub.filter(t => mKey === "ALL5"
      ? MEASURES.every(m => state.ratings[t.blind_id][m.key] === "yes")
      : state.ratings[t.blind_id][mKey] === "yes"
    ).length;
    return `${hYes}/${sub.length} (${Math.round(100*hYes/sub.length)}\\%)`;
  }

  const latex = `% Human evaluation on stratified Study A sample (N = ${completedAll.length})
\\begin{table}[!htb]
\\centering
\\caption[Study A: Blinded Human Evaluation and Agreement with \\textsc{PF Eval}]{Study A: Blinded Human Evaluation and Agreement with \\textsc{PF Eval}}
\\label{tab:res-human-eval}
\\footnotesize
\\setlength{\\tabcolsep}{6pt}
\\renewcommand{\\arraystretch}{1.2}
\\begin{tabular}{@{} l c c c c @{}}
\\toprule
\\textbf{Measure} & \\textbf{One-Shot (GPT-4.1)} & \\textbf{One-Shot (GPT-5 mini)} & \\textbf{\\textsc{StructPF} (GPT-5 mini)} & \\textbf{Human--\\textsc{PF Eval} Agr.} \\\\
\\midrule
Target Alignment & ${fmtCell('gpt41','target_alignment')} & ${fmtCell('gpt5mini','target_alignment')} & ${fmtCell('pipeline_lc','target_alignment')} & ${computeKappa(completedAll.map(t=>[state.ratings[t.blind_id].target_alignment==='yes', t.pf_eval_measures.target_alignment==='yes'])).acc.toFixed(0)}\\% \\\\
Mathematical Validity & ${fmtCell('gpt41','mathematical_validity')} & ${fmtCell('gpt5mini','mathematical_validity')} & ${fmtCell('pipeline_lc','mathematical_validity')} & ${computeKappa(completedAll.map(t=>[state.ratings[t.blind_id].mathematical_validity==='yes', t.pf_eval_measures.mathematical_validity==='yes'])).acc.toFixed(0)}\\% \\\\
Accessible Start & ${fmtCell('gpt41','prior_knowledge_accessibility')} & ${fmtCell('gpt5mini','prior_knowledge_accessibility')} & ${fmtCell('pipeline_lc','prior_knowledge_accessibility')} & ${computeKappa(completedAll.map(t=>[state.ratings[t.blind_id].prior_knowledge_accessibility==='yes', t.pf_eval_measures.prior_knowledge_accessibility==='yes'])).acc.toFixed(0)}\\% \\\\
Familiar Methods Fall Short & ${fmtCell('gpt41','familiar_approach_limits')} & ${fmtCell('gpt5mini','familiar_approach_limits')} & ${fmtCell('pipeline_lc','familiar_approach_limits')} & ${computeKappa(completedAll.map(t=>[state.ratings[t.blind_id].familiar_approach_limits==='yes', t.pf_eval_measures.familiar_approach_limits==='yes'])).acc.toFixed(0)}\\% \\\\
Room for Invention & ${fmtCell('gpt41','room_for_invention')} & ${fmtCell('gpt5mini','room_for_invention')} & ${fmtCell('pipeline_lc','room_for_invention')} & ${computeKappa(completedAll.map(t=>[state.ratings[t.blind_id].room_for_invention==='yes', t.pf_eval_measures.room_for_invention==='yes'])).acc.toFixed(0)}\\% \\\\
\\midrule
\\textbf{Passes All Five Measures} & \\textbf{${fmtCell('gpt41','ALL5')}} & \\textbf{${fmtCell('gpt5mini','ALL5')}} & \\textbf{${fmtCell('pipeline_lc','ALL5')}} & \\textbf{${stAll5.acc.toFixed(0)}\\% ($\\kappa = ${stAll5.kappa.toFixed(2)}$)} \\\\
\\bottomrule
\\end{tabular}
\\end{table}`;
  document.getElementById("latexOutput").textContent = latex;
}

function exportRatingsJSON() {
  const payload = {
    exported_at: new Date().toISOString(),
    sample_size: TASKS.length,
    completed_count: getCompletedCount(),
    items: TASKS.map(t => ({
      blind_id: t.blind_id,
      key: t.key,
      cell_id: t.cell_id,
      arm: t.arm,
      human_ratings: state.ratings[t.blind_id] || null,
      pf_eval_measures: t.pf_eval_measures,
      pf_eval_all5: t.pf_eval_all5
    }))
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "study_a_human_eval_results.json";
  a.click();
}

function importRatingsPrompt() {
  const inp = document.createElement("input");
  inp.type = "file";
  inp.accept = ".json";
  inp.onchange = e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      try {
        const data = JSON.parse(ev.target.result);
        if (data.items) {
          data.items.forEach(it => {
            if (it.human_ratings) state.ratings[it.blind_id] = it.human_ratings;
          });
          saveState();
          renderAll();
        }
      } catch (err) {
        alert("Invalid JSON file");
      }
    };
    reader.readAsText(file);
  };
  inp.click();
}

document.addEventListener("keydown", e => {
  if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
  if (e.key === "ArrowRight") nextUnratedOrNext();
  else if (e.key === "ArrowLeft") prevTask();
  else if (e.key === "a" || e.key === "A") applyPreset("all_yes");
  else if (e.key === "f" || e.key === "F") applyPreset("only_4_no");
});

function renderAll() {
  renderStrip();
  renderTask();
  if (document.getElementById("resultsSection").classList.contains("open")) {
    renderResultsTables();
  }
}

loadState();
renderAll();
</script>
</body>
</html>
"""


DEFAULT_RATINGS = {
    "T01": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "no", "note": "Prescribes discount-then-tax order and bullet steps; direct arithmetic solves."},
    "T02": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "no", "note": "Numbered 1-2-3 worksheet names target proportionality and methods; unit rates solve directly."},
    "T03": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "no", "note": "Explicitly reminds discounts come before tax; naive and exact percent give same affordable pairs."},
    "T04": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "no", "note": "Outlier 6.30 distorts mean vs median/IQR, but 4-bullet worksheet prescribes exact steps and target."},
    "T05": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "yes", "note": "Compares center and spread of two sets, though Owls > Pandas on every measure with no tie."},
    "T06": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "yes", "note": "Bounding 12x8 rectangle ties for both beds; requires decomposing L-shape (68) vs trapezoid (76)."},
    "T07": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "no", "note": "Pooled rate ties at 3/9 = 1/3 while session rates differ for Jordan; but prompt prescribes shots = k * minutes."},
    "T08": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "yes", "note": "Routine single-item calculation ($38.52 vs $47 cash); any reasonable calculation easily settles affordability."},
    "T09": {"target_alignment": "no",  "mathematical_validity": "no",  "prior_knowledge_accessibility": "no",  "familiar_approach_limits": "no", "room_for_invention": "yes", "note": "Asks to split 24 individual campers fairly using only group totals (individual stats missing, blocking a valid start)."},
    "T10": {"target_alignment": "no",  "mathematical_validity": "no",  "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "yes", "note": "Asks which group matches Curry's style without giving Curry's pace; Groups A and C tie at 3 shots/min."},
    "T11": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "no", "note": "Text explicitly gives the decomposition of the L-patio and 5-sided herb garden; direct area formulas solve."},
    "T12": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "no", "note": "Multi-part numbered worksheet; unit rates per drill directly scale to 120 attempts."},
    "T13": {"target_alignment": "yes", "mathematical_validity": "no",  "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "yes", "note": "Attachment placement of the L-walkway is underspecified/ambiguous; simple component sum solves."},
    "T14": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "yes", "note": "Tests friend's outer bounding-box shortcut (14*6=84) vs composite decomposition (60+12=72)."},
    "T15": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "yes", "note": "Both bands have exact same mean (3.0 min) and median (3.0 vs 2.5), forcing variability/spread analysis."},
    "T16": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "no", "note": "Step-by-step store rules and multi-bullet instructions; direct arithmetic compares the stores."},
    "T17": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "no", "note": "Good outlier/skew contrast between bands, but (a)-(d) worksheet prescribes every step."},
    "T18": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "yes", "note": "Store A (-20%, +10%) and Store B (-15%, +5%) tie under additive -10% shortcut, requiring compound multiplier."},
    "T19": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "yes", "note": "Extreme outlier (1000s) makes Band A mean higher (282.5 vs 187.5) while median is tied/lower (185 vs 187.5)."},
    "T20": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "yes", "note": "Direct rectangle minus triangle plus barbecue rectangle (96 - 6 + 15 = 105 sq ft) solves immediately."},
    "T21": {"target_alignment": "yes", "mathematical_validity": "no",  "prior_knowledge_accessibility": "no",  "familiar_approach_limits": "no", "room_for_invention": "no", "note": "Self-contradictory boundary walk vs parenthetical cutout description blocks a clear start; multi-step worksheet giveaway."},
    "T22": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "yes", "room_for_invention": "yes", "note": "Store A (+30%, -20%) and Store B (+20%, -10%) tie at +10% under additive shortcut (104 vs 108 actual)."},
    "T23": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "yes", "note": "Compares center and variability of two playlists, though one band has clearly higher mean (7.75 vs 7.06)."},
    "T24": {"target_alignment": "yes", "mathematical_validity": "yes", "prior_knowledge_accessibility": "yes", "familiar_approach_limits": "no", "room_for_invention": "yes", "note": "Direct session unit rates (6/15 = 12/30 = 0.4 vs 5/10 != 12/40) settle proportionality immediately."},
}


def main() -> None:
    sampled = build_sample(seed=42, per_cell_arm=2)
    for item in sampled:
        item["human_ratings"] = DEFAULT_RATINGS[item["blind_id"]]
        item["human_all5"] = all(
            item["human_ratings"][k] == "yes" for k in MEASURE_KEYS
        )
    OUT_MANIFEST.write_text(json.dumps(sampled, indent=2, ensure_ascii=False), encoding="utf-8")
    html = (
        HTML_TEMPLATE.replace("__TASKS_JSON__", json.dumps(sampled, ensure_ascii=False))
        .replace("__DEFAULT_RATINGS_JSON__", json.dumps(DEFAULT_RATINGS, ensure_ascii=False))
    )
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {len(sampled)} sampled tasks to {OUT_HTML} and {OUT_MANIFEST}")


if __name__ == "__main__":
    main()

import {
  CORE,
  MODEL_IDS,
  METRIC_LABELS,
  TASK_LABELS,
  initialState,
  esc,
  fmt,
  pct,
  signed,
  promptName,
  selectCells,
  aggregate,
  selectedMetric,
  metricLabel,
  csvString,
  validateCodingPayload,
  codingSummary,
} from "./model.js";
import * as charts from "./charts.js";
import * as codeStudy from "./code-study.js";

const data = window.COURSE_SUMMARY,
  evidence = window.COURSE_EVIDENCE;
const $ = (s) => document.querySelector(s);
const chapters = ["输出长度", "提示策略", "效率折衷", "资料位置", "异常案例"];
const params = new URLSearchParams(location.search);
let chapter = Math.min(
  4,
  Math.max(0, Number(location.hash.match(/^#case-(\d)$/)?.[1] || 1) - 1),
);
let mode =
  location.hash === "#code" || (params.get("mode")==="explore" && params.get("dataset")==="code") ? "code" :
  params.get("mode") === "explore"
    ? "explore"
    : location.hash === "#position"
      ? "position"
      : /^#case-/.test(location.hash)
        ? "demo"
        : "overview";
let state = initialState(),
  demoModel = "qwen",
  positionMetric = 0,
  positionScope = "main19",
  positionView = "curves",
  highlightTruncated = false,
  libraryChart = "model",
  heatScope = "core";
let rowsPromise,
  rows = [],
  byId = new Map(),
  version = 0,
  lastFocused,
  toastTimer,
  recordSelection = [],
  recordPage = 0;
let codePayload = { schema_version: "code-test-v1", runs: [] },
  codeModel = "__all", codeTask = "__all", codeError = "__all";
let behaviorSelection = null, lastRecordQuery = null;
let codeStudyState=codeStudy.codeRoute(params);
const model = (id) => data.models.find((m) => m.id === id),
  name = (id) => model(id)?.name || id;
const taskShort = (id) => id === "mmlu" ? "MMLU-Pro" : id.toUpperCase();
const legend = (ids = MODEL_IDS) =>
  ids
    .map(
      (id) =>
        `<span class="legend-item"><i class="legend-dot" style="background:${model(id).color}"></i>${esc(name(id))}</span>`,
    )
    .join("");
function notify(text) {
  clearTimeout(toastTimer);
  $("#toast").textContent = text;
  $("#toast").classList.add("visible");
  toastTimer = setTimeout(() => $("#toast").classList.remove("visible"), 2700);
}
function download(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.target = "_blank";
  a.rel = "noopener";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function syncUrl() {
  const p = new URLSearchParams();
  if (mode === "explore") {
    p.set("mode", "explore");
    p.set("chart", libraryChart);
    p.set("dataset", state.dataset);
    p.set("task", state.task);
    p.set("prompt", state.prompt);
    p.set("metric", state.metric);
    p.set("models",state.models.join(","));
    if (state.documents !== "all") p.set("documents",state.documents);
    if (state.position !== "all") p.set("position",state.position);
    if (libraryChart === "behavior" && behaviorSelection) {p.set("family",behaviorSelection.family);p.set("style",behaviorSelection.style);}
  }
  if (mode === "code") { for (const [k,v] of codeStudy.codeQuery(codeStudyState)) p.set(k,v); }
  if (mode === "overview") {
    if (efficiencyView === "prompts") {
      p.set("view", "prompts");
      p.set("model", budgetModel);
    }
  }
  if (mode === "position") {
    p.set("scope", researchScope);
    p.set("score", researchMetric);
    p.set("figure", researchPositionView);
  }
  history.replaceState(
    null,
    "",
    `${location.pathname}${p.size ? "?" + p : ""}${mode === "code" ? "#code" : mode === "overview" ? "#budget" : mode === "position" ? "#position" : `#case-${chapter + 1}`}`,
  );
}
function fixed(overrides = {}) {
  return { ...initialState(), ...overrides };
}
const icon = (id) =>
  `<img src="assets/ui/${id}.svg" class="icon" width="20" height="20" alt="" aria-hidden="true">`;
function heading(dim, title, context, tools = "") {
  return `<div class="page-header"><div class="row align-items-center"><div class="col"><h1 class="page-title">${title}</h1>${dim.includes("/") ? `<span class="analysis-type">${dim.split("/").at(-1).trim()}</span>` : ""}${context.length ? `<div class="scene-context">${context.join('<span class="context-divider">/</span>')}</div>` : ""}</div>${tools ? `<div class="col-auto scene-tools">${tools}</div>` : ""}</div></div>`;
}
function source(text, note = "") {
  return `<figcaption class="figure-note"><span>${text}</span>${note ? `<span>${note}</span>` : ""}</figcaption>`;
}
function chart(id, label) {
  return `<div id="${id}" class="chart" role="img" aria-label="${esc(label)}"></div>`;
}
function stat(value, label, detail, symbol = "chart-bar", tone = "blue") {
  return `<div class="card metric-card"><div class="card-body"><div><div class="subheader">${label}</div><div class="metric-value">${value}</div><div class="metric-detail">${detail}</div></div></div></div>`;
}
function stats(items) {
  return `<div class="metric-grid">${items.join("")}</div>`;
}
function finding(text, detail = "") {
  return `<div class="finding"><span class="finding-icon">${icon("circle-check")}</span><div><p>${text}</p>${detail ? `<small>${detail}</small>` : ""}</div></div>`;
}
function plot(title, content, foot, tools = "") {
  return `<figure class="card plot-surface"><div class="card-header"><h2 class="card-title">${title}</h2>${tools ? `<div class="card-actions">${tools}</div>` : ""}</div>${content}${foot}</figure>`;
}
function modelSelect() {
  return `<label class="control-label">模型<select id="demo-model" class="form-select">${MODEL_IDS.map((id) => `<option value="${id}" ${demoModel === id ? "selected" : ""}>${esc(name(id))}</option>`).join("")}</select></label>`;
}
const research = window.COURSE_RESEARCH,
  publication = window.COURSE_PUBLICATION;
const compactEfficiency = window.matchMedia("(max-width: 1100px)");
compactEfficiency.addEventListener("change", () => { if (mode === "overview" && efficiencyView === "evidence") render(); });
let budgetModel = MODEL_IDS.includes(params.get("model"))
    ? params.get("model")
    : "qwen",
  efficiencyView = params.get("view") === "prompts" ? "prompts" : "evidence";
let researchScope = [
    "DefaultCoT",
    "NoCoT",
    "BeConcise",
    "main19",
    "core8",
  ].includes(params.get("scope"))
    ? params.get("scope")
    : "DefaultCoT",
  researchMetric = ["0", "1", "2", "3"].includes(params.get("score"))
    ? +params.get("score")
    : 0,
  researchPositionView =
    params.get("figure") === "profile" ? "profile" : "matrix";
const researchScopes = {
  DefaultCoT: "逐步推理",
  NoCoT: "直接回答",
  BeConcise: "简洁推理",
  main19: "常规 19 策略",
  core8: "核心 8 策略",
};
const pubKey = () =>
  mode === "position"
    ? researchPositionView === "matrix"
      ? `position-matrix-${researchMetric}`
      : `position-${researchScope}-${researchMetric}`
    : efficiencyView === "prompts" ? `efficiency-${budgetModel}` : compactEfficiency.matches ? "efficiency-overview-compact" : "efficiency-overview";
function publicationFigure(key) {
  return `<div class="publication-frame"><div class="publication-svg${key === "efficiency-overview-compact" ? " efficiency-compact" : ""}" id="publication-root" tabindex="0" role="region" aria-label="科学图表，可横向滚动查看完整图">${publication.figures[key] || ""}</div><p class="publication-scroll-hint">横向滚动查看完整图 · 聚焦图表后可使用左右方向键</p></div>`;
}
function publicationTools() {
  return `<div class="publication-actions"><button class="text-action" data-action="publication-method">${mode === "overview" ? "统计口径" : "方法"}</button><button class="text-action" data-action="export-publication">${icon("download")} SVG</button></div>`;
}
function drawBudget() {
  const comparisons = evidence.efficiency,
    savings = comparisons.map((r) => r.token_saving_pct),
    nondecreasing = comparisons.filter((r) => r.difference_pp >= 0).length,
    prompts = efficiencyView === "prompts";
  $("#stage").innerHTML =
    `<div class="research-heading"><div><h1>简洁推理：更少输出，评分多数不降</h1><p>4 个模型、3 个任务；每组 200 道同题，比较简洁推理与默认逐步推理。</p></div>${publicationTools()}</div>
 <div class="research-toolbar efficiency-toolbar"><div class="efficiency-views" role="group" aria-label="输出效率视图"><button data-efficiency-view="evidence" aria-pressed="${!prompts}">跨任务证据</button><button data-efficiency-view="prompts" aria-pressed="${prompts}">31 种提示对比</button></div>${prompts ? `<div class="model-tabs" role="group" aria-label="选择模型">${MODEL_IDS.map((mid) => `<button data-budget-model="${mid}" aria-pressed="${budgetModel === mid}"><img src="assets/logos/${model(mid).logo}" width="18" height="18" alt="">${esc(name(mid))}</button>`).join("")}</div>` : '<span class="efficiency-key">BeConcise 相对 DefaultCoT</span>'}</div>
 ${publicationFigure(pubKey())}
 <div class="efficiency-finding"><p>平均输出减少 <strong>${fmt(Math.min(...savings), 1)}%–${fmt(Math.max(...savings), 1)}%</strong>；<strong>${nondecreasing} / ${comparisons.length}</strong> 组实测评分持平或提高。</p><span>${prompts ? "每点是一种实测提示；箭头连接默认与简洁推理，点击点可查看记录。" : "Qwen3 / GSM8K 是唯一评分点估计下降的条件（−1.0 个百分点）；区间跨 0 的条件尚不能确认提升。"}</span></div>
 <div class="research-foot"><span>${prompts ? "各任务采用独立的线性 token 横轴；纵轴均为同一评分通过率。" : "左图比较实际输出开销，右图比较同题评分差；点击条形或评分点查看配对证据。"}</span></div>`;
}
function drawResearchPosition() {
  const entries = research.positions.filter(
      (r) => r.scope === researchScope && r.metric === researchMetric,
    ),
    inter = research.interactions.find(
      (r) => r.scope === researchScope && r.metric === researchMetric,
    );
  const one = entries.find((r) => r.model === "qwen").contrasts.back_mid,
    two = entries.find((r) => r.model === "qwen3").contrasts.back_mid;
  const lowest = (mid) =>
    research.position_matrix.filter(
      (r) =>
        r.model === mid &&
        r.positions[1].scores[researchMetric] <
          r.positions[0].scores[researchMetric] &&
        r.positions[1].scores[researchMetric] <
          r.positions[2].scores[researchMetric],
    ).length;
  const matrix = researchPositionView === "matrix";
  $("#stage").innerHTML =
    `<div class="research-heading"><div><h1>资料位置与答案命中</h1><p>${matrix ? "跨 31 种提示比较前、中、后三处的实测命中率。" : "当前测量前、中、后三处；20 篇条件尚缺原论文第 5、15 位。"}</p></div>${publicationTools()}</div>
 <div class="research-toolbar position-controls"><label>视图<select id="research-position-view" class="form-select form-select-sm"><option value="matrix" ${matrix ? "selected" : ""}>策略 × 位置</option><option value="profile" ${!matrix ? "selected" : ""}>三点位置剖面</option></select></label>${
   !matrix
     ? `<label>提示条件<select id="research-scope" class="form-select form-select-sm">${Object.entries(
         researchScopes,
       )
         .map(
           ([k, v]) =>
             `<option value="${k}" ${researchScope === k ? "selected" : ""}>${v}</option>`,
         )
         .join("")}</select></label>`
     : ""
 }<label>评分口径<select id="research-metric" class="form-select form-select-sm">${METRIC_LABELS.map((t, i) => `<option value="${i}" ${researchMetric === i ? "selected" : ""}>${t}</option>`).join("")}</select></label><span>200 道配对题目 / 文档数 10、20 等权</span></div>
 ${publicationFigure(pubKey())}
 <div class="research-caption"><span class="caption-index">发现</span><div><h2>${matrix ? "位置效应会随提示策略改变。" : researchScope === "DefaultCoT" && researchMetric === 0 ? "尾部是否恢复，两个模型给出了不同的轮廓。" : "位置模式依赖模型、提示与评分条件。"}</h2><p>${matrix ? `中部低于两端的提示条件：Qwen2.5 为 <strong>${lowest("qwen")} / 31</strong>，Qwen3 为 <strong>${lowest("qwen3")} / 31</strong>。这些是当前评分口径下的描述性计数，不代表每组差异都已获统计确认。` : `尾部 − 中部：Qwen2.5 <strong>${signed(one.delta * 100, 2)} pp</strong>，Qwen3 <strong>${signed(two.delta * 100, 2)} pp</strong>；恢复幅度之差为 <strong>${signed(inter.delta * 100, 2)} pp</strong>（95% 区间 ${signed(inter.lo * 100, 2)} 至 ${signed(inter.hi * 100, 2)}）。`}</p></div></div>
 <div class="research-foot"><span>${matrix ? "每个数字对应 400 次响应，来自相同的 200 道题；点击数字查看该条件的匿名记录。" : researchScope === "DefaultCoT" && researchMetric === 0 ? "Qwen2.5 的曲线呈浅 U 形，但尾部回升的单独区间仍跨 0；三个位置不足以刻画连续 U 形。" : "差值按同一道题配对，保留文档数与提示范围的重复测量。"}</span></div>`;
}
function publicationMethod() {
  if (mode === "position")
    openInspector(
      "位置实验的比较口径",
      `<p class="subline">同题配对 / 5,000 次 bootstrap / 200 道独立题</p><h3>曲线与矩阵</h3><p>曲线按 10、20 篇资料分面，横轴标实际文档序号。每条线只有三处实测值；20 篇条件的第 5、15 位未测。误差棒为按题重抽样的逐点 95% 区间。矩阵则将两个文档数等权汇总，每格 400 次响应、200 道题。</p><h3>配对差值</h3><p>右图先对每道题等权汇总两个文档数的“尾部 − 中部”，再比较两个模型的恢复幅度。模型间差值另行配对计算。</p><h3>解释范围</h3><p>提示和评分口径可切换。探索性区间没有作多重比较校正；字符串命中不等同于人工确认的语义正确。</p>`,
    );
  else {
    openInspector(
      "输出效率的统计口径",
      `<p class="subline">BeConcise − DefaultCoT / 每组 200 道同题</p><h3>两个实测指标</h3><p>输出减少率 = 1 − 简洁推理平均返回 token / 默认逐步推理平均返回 token。评分差 = 简洁推理通过率 − 默认逐步推理通过率，以百分点表示。比较对象是两种完整提示策略。</p><h3>配对与区间</h3><p>每个模型与任务内按同一道题配对，5,000 次按题 bootstrap，种子 20261023，取百分位 95% 区间。区间为逐条件探索性结果，未作多重比较校正。12 组是 4 个模型与 3 个任务，不能当成 12 组完全独立的新题。</p><h3>发现的边界</h3><p>“11 / 12 组不降”统计的是点估计，区间跨 0 不代表已经证明等效。保留原始评分；输出截断与答案提取也会随提示变化，不能把评分变化全部归因于推理能力。输出 token 是实际返回长度，不是事前设定的预算或完整调用费用。</p><h3>31 种提示对比</h3><p>每个点对应一种提示下的 200 次实际回答。三个任务的横轴分别使用线性 token 刻度，纵轴统一为 0–100% 评分通过率。箭头只连接 DefaultCoT 与 BeConcise 两个实测条件。</p>`,
    );
  }
}
function positionState() {
  return fixed({
    dataset: "document_qa",
    task: "document_qa",
    prompt:
      positionScope === "NoCoT"
        ? "NoCoT"
        : positionScope === "core8"
          ? "__core"
          : "__main",
    metric: positionMetric,
    models: ["qwen", "qwen3"],
  });
}
function drawDemo() {
  if (chapter === 0) {
    const v = evidence.length;
    $("#stage").innerHTML =
      heading("01 / 一维分布", "输出长度", [
        "Qwen2.5 7B",
        "直接回答",
        "NQ-Open 带资料问答",
      ]) +
      stats([
        stat(
          `${fmt(v.median)}<small> token</small>`,
          "中位数",
          "一半回答不超过 13 token",
          "chart-histogram",
        ),
        stat(
          `${fmt(v.mean, 1)}<small> token</small>`,
          "平均长度",
          "少量长回答抬高均值",
          "chart-line",
          "purple",
        ),
        stat(
          `${fmt(v.p95)}<small> token</small>`,
          "95% 分位数",
          "最长回答为 168 token",
          "chart-bar",
          "teal",
        ),
      ]) +
      plot(
        "返回 token 的频率分布",
        `<div class="plot-content"><div class="chart-shell">${chart("length-histogram", "返回 token 的频率分布")}</div></div>`,
        source(
          "document_qa · 1,200 次响应 / 200 道独立题",
          "横轴：返回 token · 纵轴：响应数",
        ),
      ) +
      finding(
        "多数回答很短，少数长回答拉高了均值。",
        "典型回答的长度更接近中位数 13 token；平均值为 21.9 token。",
      );
    charts.lengthHistogram("length-histogram", v, (meta) =>
      inspectRows(
        {
          dataset: "document_qa",
          model: "qwen",
          task: "document_qa",
          prompt: "NoCoT",
          tokenLo: meta.lo,
          tokenHi: meta.hi,
        },
        `${meta.lo}–${meta.hi - 1} token`,
      ),
    );
  } else if (chapter === 1) {
    const c = evidence.prompt.find((r) => r.model_id === demoModel);
    $("#stage").innerHTML =
      heading(
        "02 / 二维关系",
        "提示策略",
        [esc(name(demoModel)), "GSM8K", "相同 200 道题"],
        modelSelect(),
      ) +
      stats([
        stat(
          pct(c.second_rate),
          "直接回答",
          "当前规则评分",
          "chart-bar",
          "purple",
        ),
        stat(
          pct(c.first_rate),
          "逐步推理",
          "当前规则评分",
          "chart-bar",
          "blue",
        ),
        stat(
          `${signed(c.difference_pp, 1)}<small> pp</small>`,
          "配对评分差",
          `95% 区间 ${signed(c.ci_low_pp, 1)} 至 ${signed(c.ci_high_pp, 1)} pp`,
          "chart-line",
          "teal",
        ),
      ]) +
      plot(
        "提示策略 × 规则评分",
        `<div class="plot-content"><div class="chart-shell">${chart("prompt-bars", "固定模型下三种提示策略的规则评分")}</div></div>`,
        source("reasoning 当前源评分快照 · 每种提示 200 次响应", "固定模型与题集"),
      ) +
      finding(
        `逐步推理的当前评分高出 ${fmt(c.difference_pp, 1)} 个百分点。`,
        c.ci_low_pp <= 0
          ? "配对区间跨 0，尚不能确认总体增益。"
          : "同题配对区间高于 0；这项结果适用于当前模型与题集。",
      );
    charts.promptCase("prompt-bars", data, demoModel, (meta) =>
      inspectRows(
        {
          dataset: "reasoning",
          model: demoModel,
          task: "gsm8k",
          prompt: meta.prompt,
        },
        promptName(meta.prompt),
      ),
    );
  } else if (chapter === 2) {
    const list = evidence.efficiency,
      min = Math.min(...list.map((r) => r.token_saving_pct)),
      max = Math.max(...list.map((r) => r.token_saving_pct));
    $("#stage").innerHTML =
      heading("03 / 多维关系", "效率折衷", [
        "简洁推理 vs 逐步推理",
        "4 个模型 × 3 类任务",
        "每组 200 道同题",
      ]) +
      stats([
        stat(
          `${fmt(min, 1)}–${fmt(max, 1)}<small>%</small>`,
          "平均输出降幅",
          "12 组均减少返回 token",
          "chart-bar",
        ),
        stat(
          "11 / 12",
          "评分不下降的组合",
          "当前样本的描述性结果",
          "circle-check",
          "teal",
        ),
        stat(
          "−1.0<small> pp</small>",
          "Qwen3 · GSM8K",
          "95% 区间 −5.5 至 +3.5 pp",
          "chart-scatter",
          "orange",
        ),
      ]) +
      plot(
        "输出节省与评分变化",
        `<div class="plot-content"><div class="chart-shell">${chart("efficiency-case", "模型、任务与提示差异的四维散点图")}</div></div>`,
        source("reasoning · 4,800 次响应 / 600 道独立题", "同模型、同任务内配对"),
        `<div class="header-legend">${legend()}<span class="legend-item"><i class="shape circle"></i>GSM8K</span><span class="legend-item"><i class="shape diamond"></i>MATH500</span><span class="legend-item"><i class="shape rect"></i>MMLU-Pro</span></div>`,
      ) +
      finding(
        "简洁提示在 12 组条件下都减少了输出。",
        "评分变化依赖模型与任务；现有结果尚未证明准确率等效。",
      );
    charts.efficiencyCase("efficiency-case", data, list, (meta) =>
      inspectEfficiency(meta.model, meta.task),
    );
  } else if (chapter === 3) {
    const s = positionState(),
      scope =
        positionScope === "main19"
          ? "常规 19 策略"
          : positionScope === "core8"
            ? "核心 8 策略"
            : "直接回答";
    const contrasts = evidence.position.filter(
      (r) =>
        r.scope === positionScope &&
        r.documents === "pooled" &&
        r.metric ===
          [
            "paper_firstline",
            "strict_final_em",
            "final_contains",
            "full_response_contains",
          ][positionMetric] &&
        r.first === "front" &&
        r.second === "middle",
    );
    const n =
      positionScope === "main19"
        ? 45600
        : positionScope === "core8"
          ? 19200
          : 2400;
    $("#stage").innerHTML =
      heading(
        "04 / 多维关系",
        "资料位置",
        [scope, "10 / 20 篇资料", "200 道同题"],
        `<label class="control-label">指标<select id="position-metric" class="form-select">${METRIC_LABELS.map((m, i) => `<option value="${i}" ${i === positionMetric ? "selected" : ""}>${m}</option>`).join("")}</select></label><label class="control-label">范围<select id="position-scope" class="form-select"><option value="main19" ${positionScope === "main19" ? "selected" : ""}>常规 19 策略</option><option value="core8" ${positionScope === "core8" ? "selected" : ""}>核心 8 策略</option><option value="NoCoT" ${positionScope === "NoCoT" ? "selected" : ""}>直接回答</option></select></label>`,
      ) +
      stats(
        contrasts
          .map((r, i) =>
            stat(
              `${signed(r.difference_pp, 2)}<small> pp</small>`,
              `${name(r.model_id)} · 前部 − 中部`,
              `95% 区间 ${signed(r.ci_low_pp, 2)} 至 ${signed(r.ci_high_pp, 2)}`,
              "chart-line",
              i ? "teal" : "blue",
            ),
          )
          .concat(
            stat(
              "200",
              "独立题目",
              `${fmt(n)} 次响应 · 按题聚类配对`,
              "chart-dots-3",
              "purple",
            ),
          ),
      ) +
      plot(
        "资料位置与答案命中",
        `${positionView === "curves" ? `<div class="figure-legend"><span class="legend-item"><i class="legend-dot" style="background:#4263eb"></i>10 篇资料</span><span class="legend-item"><i class="legend-dot" style="background:#f59f00"></i>20 篇资料</span></div><div class="plot-content dual"><div class="chart-shell"><h3>Qwen2.5 7B</h3>${chart("position-qwen", "Qwen2.5 的文档数量与资料位置")}</div><div class="chart-shell"><h3>Qwen3 8B</h3>${chart("position-qwen3", "Qwen3 的文档数量与资料位置")}</div></div>` : `<div class="plot-content"><div class="chart-shell">${chart("position-intervals", "位置差值与95%区间")}</div></div>`}`,
        source(
          `document_qa · ${fmt(n)} 次响应 / 200 道独立题`,
          "曲线为描述；差值图给出 95% 区间",
        ),
        `<select id="position-view" class="form-select form-select-sm" aria-label="位置图形"><option value="curves" ${positionView === "curves" ? "selected" : ""}>位置曲线</option><option value="intervals" ${positionView === "intervals" ? "selected" : ""}>配对差值与区间</option></select>`,
      ) +
      finding(
        positionScope === "main19" && positionMetric === 0
          ? "前部优势可见，尾部回升并不一致。"
          : "位置模式随模型与条件变化。",
        "当前数据不支持所有模型都呈现统一的 U 形位置效应。",
      );
    if (positionView === "curves")
      for (const mid of ["qwen", "qwen3"])
        charts.positionFacet(`position-${mid}`, data, s, mid, (meta) =>
          inspectRows(
            {
              dataset: "document_qa",
              model: mid,
              task: "document_qa",
              scope: s.prompt,
              documents: meta.documents,
              position: meta.position,
            },
            `${name(mid)} · ${meta.documents} 篇 · ${positionLabel(meta.position)}`,
          ),
        );
    else
      charts.positionIntervals(
        "position-intervals",
        data,
        evidence.position.filter(
          (r) =>
            r.scope === positionScope &&
            r.documents === "pooled" &&
            r.metric ===
              [
                "paper_firstline",
                "strict_final_em",
                "final_contains",
                "full_response_contains",
              ][positionMetric],
        ),
        (meta) =>
          inspectRows(
            {
              dataset: "document_qa",
              model: meta.model,
              task: "document_qa",
              scope: s.prompt,
            },
            name(meta.model),
          ),
      );
  } else {
    const a = evidence.anomaly;
    $("#stage").innerHTML =
      heading("05 / 异常与局限", "分数背后的未完成回答", [
        "Qwen3 8B",
        "非标准语法提示",
        "1,200 次带资料问答",
      ]) +
      stats([
        stat(
          "74.1<small>%</small>",
          "首行答案命中率",
          "889 / 1,200 次响应",
          "chart-bar",
        ),
        stat(
          "40.6<small>%</small>",
          "最终答案包含率",
          "487 / 1,200 次响应",
          "chart-bar",
          "purple",
        ),
        stat(
          "311",
          "截断且首行命中",
          "来自 115 道不同题目",
          "alert-triangle",
          "orange",
        ),
      ]) +
      plot(
        "评分命中 × 输出完整性",
        `<div class="plot-toolbar"><span>每个方块 = 1 次真实响应</span><label><input type="checkbox" id="highlight-truncated" class="form-check-input" ${highlightTruncated ? "checked" : ""}>突出截断</label></div><div class="plot-content"><div id="anomaly-waffle" class="chart-shell"></div></div><div class="figure-legend">${[
          ["#2fb8ac", "完整 · 命中", a.joint[0]],
          ["#dce4ed", "完整 · 未命中", a.joint[1]],
          ["#f59f00", "截断 · 命中", a.joint[2]],
          ["#f5d8ba", "截断 · 未命中", a.joint[3]],
        ]
          .map(
            ([color, label, n]) =>
              `<span class="legend-item"><i class="legend-dot" style="background:${color}"></i>${label} ${n}</span>`,
          )
          .join("")}</div>`,
        source(
          "document_qa · 1,200 次响应 / 200 道独立题",
          "“命中”仅指首行包含标准答案",
        ),
        `<button class="btn btn-sm btn-outline-secondary" data-action="anomaly-records">查看 311 条记录 ${icon("arrow-up-right")}</button>`,
      ) +
      finding(
        "424 条截断中，311 条仍被首行判为命中。",
        "这些截断记录的最终答案包含命中为 0；高首行分数可能掩盖未完成输出。",
      );
    renderWaffle();
  }
}
function positionLabel(p) {
  return { front: "前部", middle: "中部", back: "尾部", none: "无资料" }[p] || p;
}
async function loadRows() {
  if (!rowsPromise)
    rowsPromise = new Promise((resolve, reject) => {
      if (window.COURSE_FEATURES) return resolve(window.COURSE_FEATURES);
      const script = document.createElement("script");
      script.src = "runtime/features.js?v="+encodeURIComponent(window.COURSE_FEATURE_VERSION || "1");
      script.onload = () =>
        window.COURSE_FEATURES
          ? resolve(window.COURSE_FEATURES)
          : reject(new Error("记录未能打开"));
      script.onerror = () => reject(new Error("记录文件未找到"));
      document.head.append(script);
    })
      .then((p) => {
        const labels = window.COURSE_METHOD_FEATURES;
        const lookup = new Map((labels?.rows || []).map(row=>[row[0],Object.fromEntries(labels.fields.map((k,i)=>[k,row[i]]))]));
        rows = p.rows.map((row) =>
          Object.fromEntries(p.fields.map((k, i) => [k, row[i]])),
        );
        rows = rows.map(r=>({...r,...(lookup.get(r.id) || {})}));
        byId = new Map(rows.map((r) => [r.id, r]));
        return rows;
      })
      .catch((e) => {
        rowsPromise = null;
        throw e;
      });
  return rowsPromise;
}
function matches(r, q) {
  return (
    (!q.dataset || r.dataset === q.dataset) &&
    (!q.model || r.model === q.model) &&
    (!q.outputStyle || r.output_style === q.outputStyle) &&
    (!q.promptFamily || r.prompt_family === q.promptFamily) &&
    (!q.task || r.task === q.task) &&
    (!q.prompt || r.prompt === q.prompt) &&
    (!q.documents || r.documents === q.documents) &&
    (!q.position || r.position === q.position) &&
    ((!q.tokenLo && q.tokenLo !== 0) || r.tokens >= q.tokenLo) &&
    (!q.tokenHi || r.tokens < q.tokenHi) &&
    (!q.scope ||
      q.scope === "__all" ||
      (q.scope === "__core" && CORE.includes(r.prompt)) ||
      (q.scope === "__main" &&
        data.cells.some(
          (c) =>
            c.dataset === r.dataset &&
            c.prompt === r.prompt &&
            c.scope === "main_comparison",
        )) ||
      q.scope === r.prompt)
  );
}
async function renderWaffle() {
  const current = version;
  try {
    const all = await loadRows();
    if (current !== version || !$("#anomaly-waffle")) return;
    const selected = all.filter((r) =>
      matches(r, {
        dataset: "document_qa",
        model: "qwen3",
        task: "document_qa",
        prompt: "NoProperGrammar",
      }),
    );
    const color = (r) =>
      r.truncated
        ? r.scores[0]
          ? "#f59f00"
          : "#f5d8ba"
        : r.scores[0]
          ? "#2fb8ac"
          : "#dce4ed";
    selected.sort(
      (a, b) =>
        a.truncated * 2 +
        (a.scores[0] ? 0 : 1) -
        (b.truncated * 2 + (b.scores[0] ? 0 : 1)),
    );
    const holder = $("#anomaly-waffle"),
      ratio = Math.max(
        1,
        holder.clientWidth / Math.max(1, holder.clientHeight),
      );
    const cols = [40, 50, 60, 75, 80, 100].reduce(
      (best, n) =>
        Math.abs(n / (1200 / n) - ratio) <
        Math.abs(best / (1200 / best) - ratio)
          ? n
          : best,
      60,
    );
    const gridRows = 1200 / cols;
    $("#anomaly-waffle").innerHTML =
      `<svg class="waffle" viewBox="0 0 ${cols * 12 + 20} ${gridRows * 12 + 20}" role="img" aria-label="1200次响应中，完整且首行命中578次，完整未命中198次，截断且首行命中311次，截断未命中113次">${selected.map((r, i) => `<rect x="${10 + (i % cols) * 12}" y="${10 + Math.floor(i / cols) * 12}" width="10" height="10" rx="1" fill="${color(r)}" opacity="${highlightTruncated && !r.truncated ? 0.18 : 1}" data-record="${r.id}"><title>${r.id} · ${r.truncated ? "截断" : "完整"} · 首行${r.scores[0] ? "命中" : "未命中"}</title></rect>`).join("")}</svg>`;
  } catch (e) {
    $("#anomaly-waffle").innerHTML = `<p class="error">${esc(e.message)}</p>`;
  }
}
const STYLE_LABELS = {empty:"空输出",explicit_step_markers:"显式步骤标记",bullet_list:"列表标记",multiline_unmarked:"多行未标记",singleline:"单行输出"};
const FAMILY_LABELS = {answer_only:"直接回答要求",step_by_step_requested:"分步要求",concise_steps_requested:"简洁分步要求",bullet_format:"列表格式",numeric_format:"仅数字格式",space_format:"去空格格式",grammar_format:"语法扰动",abbreviation_format:"缩写格式",word_budget:"词数约束",character_budget:"字符约束",token_budget:"Token约束",step_budget:"步骤数约束",chinese_language:"中文输出",chinese_character_budget:"中文字符约束",unknown:"其他/未识别"};
const RESULT_LABELS = {request_failed:"请求失败",truncated:"输出截断",extraction_unresolved:"答案提取未解析",scored_source:"完整且有源评分"};
function codeFilters() {
  if (!codePayload.runs.length) return "";
  const values=(key)=>[...new Set(codePayload.runs.map(r=>r[key]))].sort();
  const errors=[...new Set(codePayload.runs.flatMap(r=>r.events.map(e=>e.error_type).filter(Boolean)))].sort();
  const select=(id,label,items,current)=>`<label>${label}<select id="${id}"><option value="__all">全部</option>${items.map(v=>`<option value="${esc(v)}" ${v===current?"selected":""}>${esc(v)}</option>`).join("")}</select></label>`;
  return select("code-model","模型",values("model_id"),codeModel)+select("code-task","任务",values("task_type"),codeTask)+select("code-error","已记录错误",errors,codeError);
}
async function renderBehavior() {
  const current=version;
  try {
    const all=await loadRows();
    if (current !== version || libraryChart !== "behavior") return;
    const selected=all.filter(r=>state.models.includes(r.model) && matches(r,{dataset:state.dataset,task:state.task === "all"?null:state.task,scope:state.prompt,documents:state.documents === "all"?null:+state.documents,position:state.position === "all"?null:state.position}));
    if (selected.some(r=>!r.output_style)) {
      charts.emptyChart("library-main","分类快照尚未构建","请先运行离线数据补全脚本。");return;
    }
    const families=[...new Set(selected.map(r=>r.prompt_family))].sort();
    const styles=Object.keys(STYLE_LABELS);
    const cells=[];
    for (let j=0;j<families.length;j++) {
      const group=selected.filter(r=>r.prompt_family===families[j]);
      for (let i=0;i<styles.length;i++) {
        const n=group.filter(r=>r.output_style===styles[i]).length;
        cells.push({value:[i,j,group.length?n/group.length*100:0],n,total:group.length,meta:{family:families[j],style:styles[i]}});
      }
    }
    const pick=(q)=>{behaviorSelection=q;syncUrl();renderBehavior();};
    charts.behaviorMatrix("library-main",families.map(k=>FAMILY_LABELS[k] || k),styles.map(k=>STYLE_LABELS[k]),cells,behaviorSelection,pick);
    const subset=behaviorSelection?selected.filter(r=>r.prompt_family===behaviorSelection.family && r.output_style===behaviorSelection.style):selected;
    const statuses=Object.keys(RESULT_LABELS).map(k=>({key:k,label:RESULT_LABELS[k],n:subset.filter(r=>r.result_state===k).length}));
    charts.behaviorStates("library-side",statuses,subset.length,meta=>openBehaviorRecords(subset.filter(r=>r.result_state===meta.status),RESULT_LABELS[meta.status]));
    const title=behaviorSelection?`${FAMILY_LABELS[behaviorSelection.family]} / ${STYLE_LABELS[behaviorSelection.style]}`:"全部格式";
    $("#behavior-selection").setAttribute("role","status");
    $("#behavior-selection").setAttribute("aria-live","polite");
    $("#behavior-selection").innerHTML=`<span>${esc(title)} · ${fmt(subset.length)} 次响应</span><button class="text-action" id="behavior-records">查看记录</button>${behaviorSelection?'<button class="text-action" data-action="behavior-clear">清除点选</button>':""}`;
    $("#behavior-records").onclick=()=>openBehaviorRecords(subset,title);
    let keyboard=$("#behavior-keyboard");
    if (!keyboard) {
      $("#behavior-selection").closest(".plot-content").insertAdjacentHTML("afterend",`<fieldset id="behavior-keyboard" class="keyboard-cohort"><legend>键盘筛选</legend><label>提示类别<select id="keyboard-family" aria-label="键盘筛选：提示类别"></select></label><label>输出形态<select id="keyboard-style" aria-label="键盘筛选：输出形态"></select></label><button class="text-action" id="keyboard-apply">应用选择</button><button class="text-action" id="keyboard-all">全部格式</button><label>结束状态<select id="keyboard-status" aria-label="键盘筛选：结束状态"><option value="">全部状态</option>${Object.entries(RESULT_LABELS).map(([k,v])=>`<option value="${k}">${esc(v)}</option>`).join("")}</select></label><button class="text-action" id="keyboard-records">打开记录</button></fieldset>`);
      keyboard=$("#behavior-keyboard");
    }
    const familyControl=$("#keyboard-family"),styleControl=$("#keyboard-style");
    if (familyControl.dataset.items !== families.join(",")) {
      familyControl.innerHTML='<option value="">选择类别</option>'+families.map(k=>`<option value="${k}">${esc(FAMILY_LABELS[k] || k)}</option>`).join("");
      familyControl.dataset.items=families.join(",");
      styleControl.innerHTML='<option value="">选择形态</option>'+styles.map(k=>`<option value="${k}">${esc(STYLE_LABELS[k])}</option>`).join("");
    }
    familyControl.value=behaviorSelection?.family || "";styleControl.value=behaviorSelection?.style || "";
    $("#keyboard-apply").onclick=()=>{
      if (familyControl.value && styleControl.value) behaviorSelection={family:familyControl.value,style:styleControl.value};
      else return notify("请同时选择提示类别和输出形态。");
      syncUrl();renderBehavior();
    };
    $("#keyboard-all").onclick=()=>{behaviorSelection=null;syncUrl();renderBehavior();};
    $("#keyboard-records").onclick=()=>{
      const status=$("#keyboard-status").value;
      openBehaviorRecords(status?subset.filter(r=>r.result_state===status):subset,status?RESULT_LABELS[status]:title);
    };
  } catch(e) { charts.emptyChart("library-main",e.message,""); }
}
function openBehaviorRecords(selected,title) {
  recordSelection=selected;recordPage=0;lastRecordQuery=null;
  openInspector(title,"");drawRecordList(title);
}

const library = {
  model: "模型柱图",
  radar: "雷达图",
  heatmap: "策略热力图",
  bubble: "规模 / 开销气泡图",
  radial: "分组环形柱图",
  position: "资料位置曲线",
  box: "分组箱线图",
  parallel: "平行坐标图",
  distribution: "状态饼图与堆叠图",
  behavior: "输出形态与约束",
  timeline: "请求时间线",
  tree: "重试路径树",
  flow: "评分分歧流图",
};
const libraryNotes = {
  model: "同模型源评分可比较；跨模型口径待统一",
  radar: "前三轴跨任务 / 位置，后两轴汇总；均为 0–100%",
  heatmap: "色深 = 当前评分；核心策略或全部策略可切换",
  bubble: "已核实参数仅两个模型，不能推断规模定律",
  radial: "半径 = 评分（0–100%）；各组刻度相同",
  position: "实线 = 10 篇，虚线 = 20 篇资料",
  box: "箱体 = Q1–Q3；须 = 1.5 IQR 内最远观测；拖动缩放，双击复位，点箱体或图例查看记录",
  parallel: "每条线 = 模型 × 核心提示；各轴独立单位",
  distribution: "截断 / 完整且命中 / 完整未命中，三类互斥",
  behavior: "规则标注可见格式；不推断模型内部推理。点选矩阵联动状态分布与记录。",
  timeline: "前 12 个重试运行；横轴为距首次请求开始的秒数",
  tree: "HTTP 请求重试路径，不代表模型修改代码",
  flow: "同一回答的两种判定，流宽表示响应数",
};
function drawExplore() {
  const isCode = state.dataset === "code";
  const metric = selectedMetric(state),
    a = !isCode ? aggregate(selectCells(data, state), metric) : null;
  $("#stage").innerHTML =
    heading(
      "自由探索",
      isCode ? "代码测试" : library[libraryChart],
      !isCode && state.dataset === "document_qa" && (state.documents !== "all" || state.position !== "all") ? [state.documents === "all" ? "全部文档数" : `${state.documents} 篇资料`,state.position === "all" ? "全部位置" : positionLabel(state.position)] : [],
      `${state.dataset === "document_qa" && (state.documents !== "all" || state.position !== "all") ? '<button class="text-action" data-action="clear-cohort">清除位置筛选</button>' : ""}<button class="plain-button" data-action="export-chart">导出图 ↗</button>`,
    ) +
    `<div class="explore-controls"><label>数据<select id="dataset-select"><option value="reasoning" ${state.dataset === "reasoning" ? "selected" : ""}>推理与提示</option><option value="document_qa" ${state.dataset === "document_qa" ? "selected" : ""}>带资料问答</option><option value="code" ${isCode ? "selected" : ""}>代码生成</option></select></label>${
      isCode
        ? `<label>图形<select id="code-chart">${[
            ["rates", "首次 / 最终通过"],
            ["events", "交互事件分布"],
            ["scatter", "工具调用与通过"],
            ["tree", "错误恢复与交互树"],
            ["errors", "已记录错误类型"],
          ]
            .map(
              ([k, v]) =>
                `<option value="${k}" ${libraryChart === k ? "selected" : ""}>${v}</option>`,
            )
            .join(
              "",
            )}</select></label><label class="mini-button file-label">载入数据<input id="code-upload" type="file" accept=".json,application/json"></label>`
        : `<label>图形<select id="library-chart">${Object.entries(library)
            .map(
              ([k, v]) =>
                `<option value="${k}" ${libraryChart === k ? "selected" : ""}>${v}</option>`,
            )
            .join(
              "",
            )}</select></label>${state.dataset === "reasoning" ? `<label>任务<select id="task-select">${["gsm8k", "math500", "mmlu", "all"].map((t) => `<option value="${t}" ${state.task === t ? "selected" : ""}>${libraryChart==='box' && t==='all'?'三类任务并列':TASK_LABELS[t]}</option>`).join("")}</select></label>` : `<label>指标<select id="metric-select">${METRIC_LABELS.map((m, i) => `<option value="${i}" ${state.metric === i ? "selected" : ""}>${m}</option>`).join("")}</select></label>`}<label>提示<select id="prompt-select">${data.prompts.map((p) => `<option value="${p.id}" ${state.prompt === p.id ? "selected" : ""}>${esc(promptName(p.id))}</option>`).join("")}<option value="__core" ${state.prompt === "__core" ? "selected" : ""}>核心 8 策略</option>${state.dataset === "document_qa" ? `<option value="__main" ${state.prompt === "__main" ? "selected" : ""}>常规 19 策略</option>` : ""}<option value="__all" ${state.prompt === "__all" ? "selected" : ""}>全部策略</option></select></label>`
    }${!isCode ? `<label>模型<select id="shared-model"><option value="__all" ${state.models.length > 1 ? "selected" : ""}>全部模型</option>${(state.dataset === "document_qa" ? ["qwen","qwen3"] : MODEL_IDS).map(mid=>`<option value="${mid}" ${state.models.length === 1 && state.models[0] === mid ? "selected" : ""}>${esc(name(mid))}</option>`).join("")}</select></label>` : codeFilters()}</div><figure class="plot-surface">${!isCode && libraryChart!=="box" ? `<div class="figure-legend">${legend(state.models.filter(m=>state.dataset !== "document_qa" || ["qwen","qwen3"].includes(m)))}</div>` : ""}${!isCode && libraryChart === "box" ? `<div class="plot-toolbar"><span>拖动缩放 · 双击复位</span><button class="text-action" id="box-selected-records" disabled>查看筛选记录</button></div>` : ""}${!isCode && libraryChart === "heatmap" ? `<div class="plot-toolbar"><span></span><select id="heat-scope" aria-label="热力图范围"><option value="core" ${heatScope === "core" ? "selected" : ""}>核心 8 策略</option><option value="all" ${heatScope === "all" ? "selected" : ""}>全部 31 策略</option></select></div>` : ""}${!isCode && libraryChart === "bubble" ? `<div class="plot-toolbar"><span></span><select id="bubble-mode" aria-label="气泡图横轴"><option value="tokens" ${state.bubble === "tokens" ? "selected" : ""}>横轴：平均返回 token</option><option value="parameters" ${state.bubble === "parameters" ? "selected" : ""}>横轴：公开参数量（B）</option></select></div>` : ""}${!isCode && libraryChart === "radial" ? `<div class="plot-toolbar"><span></span><select id="radial-mode" aria-label="环形图布局"><option value="radial" ${state.radial === "radial" ? "selected" : ""}>环形</option><option value="bars" ${state.radial === "bars" ? "selected" : ""}>展开</option></select></div>` : ""}<div class="plot-content ${["distribution", "behavior"].includes(libraryChart) && !isCode ? "dual" : ""} ${libraryChart === "behavior" ? "behavior-plot" : ""} ${libraryChart === "heatmap" && heatScope === "all" ? "scroll-chart" : ""}"><div id="library-main" class="${libraryChart === "radial" ? "radial-container" : "chart"}" role="img" aria-label="${esc(isCode ? "代码测试图形" : library[libraryChart])}"></div>${["distribution", "behavior"].includes(libraryChart) && !isCode ? chart("library-side", libraryChart === "behavior" ? "所选格式的输出状态" : "按模型堆叠的输出状态") : ""}</div>${source(isCode ? "来源：代码测试记录" : `来源：${state.dataset === "reasoning" ? "reasoning" : "document_qa"} 清洗快照 · ${fmt(a.n)} 次响应 / ${fmt(a.questions)} 道独立题`, isCode ? "" : libraryNotes[libraryChart])}</figure>`;
  if (isCode) return renderCodeChart();
  if (libraryChart === "behavior") {
    $("#library-side").insertAdjacentHTML("afterend",`<div id="behavior-selection" class="figure-note"></div>`);
    return renderBehavior();
  }
  const pick = (meta) => {
    if (meta.prompt && !meta.prompt.startsWith("__"))
      state.prompt = meta.prompt;
    state.focus = meta.model;
    render();
    inspectRows(
      {
        dataset: state.dataset,
        model: meta.model,
        task: state.task === "all" ? null : state.task,
        scope: state.prompt,
        documents: meta.documents || (state.documents === "all" ? null : +state.documents),
        position: meta.position || (state.position === "all" ? null : state.position),
      },
      `${name(meta.model)} · ${promptName(state.prompt)}`,
    );
  };
  if (libraryChart === "model")
    charts.modelBars("library-main", data, state, pick);
  if (libraryChart === "radar") charts.radar("library-main", data, state, pick);
  if (libraryChart === "heatmap")
    charts.heatmap("library-main", data, { ...state, heatScope }, pick);
  if (libraryChart === "bubble")
    charts.bubble("library-main", data, state, pick);
  if (libraryChart === "radial")
    charts.radial("library-main", data, state, pick);
  if (libraryChart === "position") {
    if (state.dataset !== "document_qa")
      charts.emptyChart("library-main", "请选择带资料问答", "");
    else charts.positionLines("library-main", data, state, pick);
  }
  if (libraryChart === "parallel") charts.parallel("library-main", data, state);
  if (libraryChart === "flow") {
    if (state.dataset === "document_qa")
      charts.disagreement("library-main", data, state);
    else charts.emptyChart("library-main", "请选择带资料问答", "");
  }
  if (["box", "distribution", "timeline", "tree"].includes(libraryChart))
    renderLibraryRows();
}
async function renderLibraryRows() {
  const current = version;
  try {
    const all = await loadRows();
    if (current !== version) return;
    const selected = all.filter((r) =>
      state.models.includes(r.model) && matches(r, {
        dataset: state.dataset,
        task: state.task === "all" ? null : state.task,
        scope: state.prompt,
        documents: state.documents === "all" ? null : +state.documents,
        position: state.position === "all" ? null : state.position,
      }),
    );
    if (libraryChart === "box"){
      const recordButton=$("#box-selected-records");if(recordButton){recordButton.disabled=false;recordButton.onclick=()=>openBehaviorRecords(selected,"返回 token / 当前筛选记录");}
      charts.boxplot("library-main",data,state,selected,meta=>inspectRows({dataset:state.dataset,model:meta.model,task:meta.task || (state.task==='all'?null:state.task),scope:state.prompt,documents:state.documents==='all'?null:+state.documents,position:state.position==='all'?null:state.position},`${name(meta.model)} / ${TASK_LABELS[meta.task || state.task] || "全部任务"} / 返回 token 分布`));
    }
    if (libraryChart === "distribution")
      charts.distribution(
        "library-main",
        "library-side",
        data,
        state,
        selected,
      );
    if (libraryChart === "timeline")
      charts.retryTimeline("library-main", data, selected, inspectRecord);
    if (libraryChart === "tree")
      charts.retryTree("library-main", data, selected, inspectRecord);
  } catch (e) {
    charts.emptyChart("library-main", e.message, "");
  }
}
function renderCodeChart() {
  const runs = codingSummary(codePayload.runs).filter(r=>(codeModel === "__all" || r.model_id === codeModel) && (codeTask === "__all" || r.task_type === codeTask) && (codeError === "__all" || r.events.some(e=>e.error_type === codeError)));
  if (!runs.length) {
    charts.emptyChart("library-main", "尚无代码测试数据", "");
    return;
  }
  if (libraryChart === "rates") charts.codingBars("library-main", runs);
  if (libraryChart === "errors") charts.codingErrors("library-main", runs);
  if (libraryChart === "events")
    charts.codingEventDistribution("library-main", runs);
  if (libraryChart === "scatter") charts.codingScatter("library-main", runs);
  if (libraryChart === "tree")
    charts.codingTree("library-main", runs, (i) => inspectCode(runs[i]));
}
function render() {
  version++;
  charts.disposeCharts();
  codeStudy.disposeCodeStudy();
  document.body.classList.toggle("mode-explore", mode === "explore");
  document.body.classList.toggle(
    "mode-publication",
    ["overview", "position", "code"].includes(mode),
  );
  for (const [id, m] of [
    ["overview-mode", "overview"],
    ["position-mode", "position"],
    ["code-mode", "code"],
    ["demo-mode", "demo"],
    ["explore-mode", "explore"],
  ]) {
    const b = $("#" + id);
    b.setAttribute("aria-current", mode === m ? "page" : "false");
  }
  $("#chapter-nav").hidden = mode !== "demo";
  $("#chapter-nav").innerHTML = chapters
    .map(
      (t, i) =>
        `<button data-chapter="${i}" ${chapter === i ? 'aria-current="page"' : ""}>${t}</button>`,
    )
    .join("");
  syncUrl();
  if (mode === "overview") drawBudget();
  else if (mode === "position") drawResearchPosition();
  else if (mode === "code") codeStudy.renderCodeStudy(codeStudyState,{root:$("#stage"),openInspector,download,onState:(next,options)=>{codeStudyState=next;if(options?.url!==false)syncUrl();},onChange:next=>{codeStudyState=next;render();}});
  else if (mode === "demo") drawDemo();
  else drawExplore();
  document
    .querySelectorAll("#stage select:not(.form-select)")
    .forEach((el) => el.classList.add("form-select", "form-select-sm"));
  document
    .querySelectorAll("#stage button.plain-button")
    .forEach((el) => el.classList.add("text-action"));
  window.scrollTo({ top: 0, behavior: "instant" });
  requestAnimationFrame(charts.resizeCharts);
}
function openInspector(title, body) {
  if($("#inspector").hidden)lastFocused = document.activeElement;
  $("#inspector-body").innerHTML =
    `<h2 id="inspector-title">${esc(title)}</h2>${body}`;
  $("#backdrop").hidden = false;
  $("#inspector").hidden = false;
  $("#close-inspector").focus();
}
function closeInspector() {
  $("#backdrop").hidden = true;
  $("#inspector").hidden = true;
  if (lastFocused?.isConnected) lastFocused.focus();
}
async function inspectRows(query, title) {
  lastRecordQuery = query;
  openInspector(title, '<p class="subline">正在打开记录…</p>');
  try {
    const all = await loadRows();
    recordSelection = all.filter((r) => matches(r, query));
    recordPage = 0;
    drawRecordList(title);
  } catch (e) {
    $("#inspector-body").innerHTML = `<p class="error">${esc(e.message)}</p>`;
  }
}
function drawRecordList(title) {
  const selected = recordSelection,
    recordMetric =
      mode === "position"
        ? researchMetric
        : mode === "demo"
          ? chapter === 3
            ? positionMetric
            : 0
          : selectedMetric(state),
    recordDataset = selected[0]?.dataset || state.dataset,
    average =
      selected
        .filter((r) => r.tokens != null)
        .reduce((a, r) => a + r.tokens, 0) /
      Math.max(1, selected.filter((r) => r.tokens != null).length),
    pages = Math.max(1, Math.ceil(selected.length / 20));
  recordPage = Math.min(recordPage, pages - 1);
  $("#inspector-body").innerHTML =
    `<h2 id="inspector-title">${esc(title)}</h2><p class="subline">${fmt(selected.length)} 次响应 / ${new Set(selected.map((r) => r.question)).size} 道独立题</p><div class="metric-pair"><div><strong>${pct(selected.length ? selected.reduce((a, r) => a + r.scores[recordDataset === "document_qa" ? recordMetric : 0], 0) / selected.length : NaN)}</strong><span>${esc(recordDataset === "document_qa" ? METRIC_LABELS[recordMetric] : "当前规则评分")}</span></div><div><strong>${fmt(average, 1)}</strong><span>平均返回 token</span></div></div><div class="table-wrap"><table><thead><tr><th>匿名记录</th><th>题号</th><th class="numeric">评分</th><th class="numeric">token</th><th>输出</th></tr></thead><tbody>${selected
      .slice(recordPage * 20, (recordPage + 1) * 20)
      .map(
        (r) =>
          `<tr tabindex="0" data-record="${r.id}"><td>${r.id}</td><td>${r.question}</td><td class="numeric">${r.scores[r.dataset === "document_qa" ? recordMetric : 0]}</td><td class="numeric">${fmt(r.tokens)}</td><td>${r.truncated ? "截断" : "完整"}</td></tr>`,
      )
      .join(
        "",
      )}</tbody></table></div><div class="record-actions"><button class="plain-button" data-action="export-records">导出筛选</button><button class="plain-button" data-action="explore-selection">联动探索</button><button class="plain-button" data-page="${recordPage - 1}" ${recordPage === 0 ? "disabled" : ""}>上一页</button><span>${recordPage + 1} / ${pages}</span><button class="plain-button" data-page="${recordPage + 1}" ${recordPage >= pages - 1 ? "disabled" : ""}>下一页</button></div>`;
}
function inspectRecord(id) {
  const r = byId.get(id);
  if (!r) return;
  const seq = data.attempts[id];
  openInspector(
    id,
    `<p class="subline">${esc(name(r.model))} · ${esc(TASK_LABELS[r.task])} · ${esc(promptName(r.prompt))}</p><div class="metric-pair"><div><strong>${fmt(r.tokens)}</strong><span>返回 token</span></div><div><strong>${r.truncated ? "截断" : "完整"}</strong><span>输出状态</span></div></div><div class="facts"><div class="fact"><span>匿名题号</span><strong>${r.question}</strong></div>${(r.dataset === "reasoning" ? ["当前规则评分"] : METRIC_LABELS).map((l, i) => `<div class="fact"><span>${l}</span><strong>${r.scores[i] ? "命中 / 通过" : "未命中 / 未通过"}</strong></div>`).join("")}${r.output_style ? `<div class="fact"><span>可见输出形态</span><strong>${STYLE_LABELS[r.output_style] || esc(r.output_style)}</strong></div><div class="fact"><span>提示约束类别</span><strong>${FAMILY_LABELS[r.prompt_family] || esc(r.prompt_family)}</strong></div><div class="fact"><span>派生结束状态</span><strong>${RESULT_LABELS[r.result_state] || esc(r.result_state)}</strong></div>` : ""}<div class="fact"><span>结束原因</span><strong>${esc(r.finish || "未记录")}</strong></div><div class="fact"><span>请求次数</span><strong>${r.attempts}</strong></div></div>${seq ? `<h3>请求时间线</h3><div class="timeline">${seq.map((a) => `<div class="timeline-item"><h4>第 ${a.attempt} 次 · ${a.http_status == null ? "状态未记录" : "HTTP " + a.http_status}</h4><p>${esc(a.started_at)}<br>${fmt(a.latency_seconds, 2)} 秒</p></div>`).join("")}</div>` : ""}`,
  );
}
function inspectEfficiency(mid, task) {
  const r = evidence.efficiency.find(
    (r) => r.model_id === mid && r.benchmark === task,
  );
  openInspector(
    `${name(mid)} · ${taskShort(task)}`,
    `<p class="subline">简洁推理 − 逐步推理 · 200 道同题</p><div class="metric-pair"><div><strong>${fmt(r.token_saving_pct, 1)}%</strong><span>平均返回 token 减少</span></div><div><strong>${signed(r.difference_pp, 1)} pp</strong><span>当前规则评分差</span></div></div><div class="facts">${[
      ["规则评分", `${pct(r.second_rate)} → ${pct(r.first_rate)}`],
      [
        "平均返回 token",
        `${fmt(r.second_mean_tokens, 1)} → ${fmt(r.first_mean_tokens, 1)}`,
      ],
      [
        "输出截断率",
        `${pct(r.second_truncation_rate)} → ${pct(r.first_truncation_rate)}`,
      ],
      [
        "提取未可用",
        `${pct(r.second_unresolved_rate)} → ${pct(r.first_unresolved_rate)}`,
      ],
      [
        "评分差 95% 区间",
        `${signed(r.ci_low_pp, 1)} 至 ${signed(r.ci_high_pp, 1)} pp`,
      ],
    ]
      .map(
        ([a, b]) =>
          `<div class="fact"><span>${a}</span><strong>${b}</strong></div>`,
      )
      .join(
        "",
      )}</div><p class="tiny-note">源评分未统一；分数变化可能伴随截断与答案提取变化。区间跨 0 不等于两种策略已证明等效。</p><div class="record-actions">${["DefaultCoT", "BeConcise"].map((prompt) => `<button class="plain-button" data-pub-prompt="${prompt}" data-pub-model="${mid}" data-pub-task="${task}" data-pub-dataset="reasoning">${prompt === "BeConcise" ? "简洁推理" : "默认推理"}记录</button>`).join("")}</div>`,
  );
}
function inspectCode(r) {
  if (!r) return;
  openInspector(
    r.run_id,
    `<p class="subline">${esc(r.model_id)} · ${esc(r.task_type)}</p><div class="metric-pair"><div><strong>${r.firstPassed ? "通过" : "失败"}</strong><span>首次测试</span></div><div><strong>${r.finalPassed ? "通过" : "失败"}</strong><span>最终测试</span></div></div><div class="timeline">${r.events.map((e) => `<div class="timeline-item"><h4>第 ${e.turn} 轮 · ${{ test: "测试", edit: "修改", tool: "工具", error: "错误" }[e.event_type]}${e.event_type === "test" ? " · " + (e.test_passed ? "通过" : "失败") : ""}</h4><p>${esc(e.error_type || "")}${e.duration_seconds == null ? "" : " · " + fmt(e.duration_seconds, 2) + " 秒"}</p></div>`).join("")}</div>`,
  );
}
function exportFigure() {
  try {
    const id =
      mode === "explore"
        ? "library-main"
        : [
            "length-histogram",
            "prompt-bars",
            "efficiency-case",
            positionView === "curves" ? "position-qwen" : "position-intervals",
            "anomaly-waffle",
          ][chapter];
    if (charts.exportChart(id)) return;
    const svg = document.getElementById(id)?.querySelector("svg");
    if (svg) {
      const copy = svg.cloneNode(true);
      copy.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      download(
        "figure.svg",
        new XMLSerializer().serializeToString(copy),
        "image/svg+xml",
      );
    }
  } catch {
    notify("请通过启动脚本打开后导出此图。");
  }
}
$(".brand").addEventListener("click", (event) => {
  event.preventDefault();
  chapter = 0;
  mode = "overview";
  render();
});
$("#overview-mode").addEventListener("click", () => {
  mode = "overview";
  render();
});
$("#position-mode").addEventListener("click", () => {
  mode = "position";
  render();
});
$("#code-mode").addEventListener("click", () => {
  mode = "code";
  render();
});
$("#demo-mode").addEventListener("click", () => {
  mode = "demo";
  render();
});
$("#explore-mode").addEventListener("click", () => {
  mode = "explore";
  render();
});
$("#fullscreen").addEventListener("click", async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch {
    notify("当前窗口不支持全屏。");
  }
});
$("#close-inspector").addEventListener("click", closeInspector);
$("#backdrop").addEventListener("click", closeInspector);
document.addEventListener("click", async (e) => {
  const el = e.target.closest(
    "[data-chapter],[data-record],[data-page],[data-action],[data-budget-model],[data-pub-prompt],[data-efficiency-view],[data-efficiency-model]",
  );
  if (!el) return;
  if (el.dataset.efficiencyView) {
    efficiencyView = el.dataset.efficiencyView;
    render();
  }
  if (el.dataset.efficiencyModel) inspectEfficiency(el.dataset.efficiencyModel, el.dataset.efficiencyTask);
  if (el.dataset.budgetModel) {
    budgetModel = el.dataset.budgetModel;
    demoModel = budgetModel;
    state.models = [budgetModel];
    render();
  }
  if (el.dataset.pubPrompt) {
    inspectRows(
      {
        dataset: el.dataset.pubDataset || "reasoning",
        position: el.dataset.pubPosition || null,
        model: el.dataset.pubModel,
        task: el.dataset.pubTask,
        prompt: el.dataset.pubPrompt,
      },
      `${name(el.dataset.pubModel)} · ${promptName(el.dataset.pubPrompt)}`,
    );
  }
  if (el.dataset.action === "behavior-clear") { behaviorSelection=null; syncUrl();renderBehavior(); }
  if (el.dataset.action === "clear-cohort") { state.documents="all";state.position="all";behaviorSelection=null;render(); }
  if (el.dataset.action === "export-records") download("lens-selection.csv",csvString([["id","question","dataset","model","task","prompt","documents","position","source_score_0","score_1","score_2","score_3","tokens","truncated","output_style","prompt_family","result_state"],...recordSelection.map(r=>[r.id,r.question,r.dataset,r.model,r.task,r.prompt,r.documents,r.position,...r.scores,r.tokens,r.truncated,r.output_style,r.prompt_family,r.result_state])]),"text/csv;charset=utf-8");
  if (el.dataset.action === "explore-selection" && recordSelection.length) {
    const first=recordSelection[0], one=key=>new Set(recordSelection.map(r=>r[key])).size===1;
    state.dataset=first.dataset; state.task=one("task")?first.task:"all"; state.prompt=one("prompt")?first.prompt:"__all"; state.models=[...new Set(recordSelection.map(r=>r.model))];
    state.documents=first.dataset === "document_qa" && one("documents")?String(first.documents):"all"; state.position=first.dataset === "document_qa" && one("position")?(first.position || "all"):"all"; state.metric=mode === "position"?researchMetric:state.metric;
    behaviorSelection=one("prompt_family") && one("output_style")?{family:first.prompt_family,style:first.output_style}:null;
    libraryChart="behavior"; mode="explore"; closeInspector(); render();
  }
  if (el.dataset.action === "publication-method") publicationMethod();
  if (el.dataset.action === "export-publication")
    download(
      pubKey() + ".svg",
      publication.figures[pubKey()],
      "image/svg+xml;charset=utf-8",
    );
  if (el.dataset.chapter != null) {
    e.preventDefault();
    chapter = +el.dataset.chapter;
    mode = "demo";
    render();
  }
  if (el.dataset.record) inspectRecord(el.dataset.record);
  if (el.dataset.page != null) {
    recordPage = +el.dataset.page;
    drawRecordList($("#inspector-title").textContent);
  }
  if (el.dataset.action === "anomaly-records") {
    await loadRows();
    recordSelection = rows.filter(
      (r) =>
        matches(r, {
          dataset: "document_qa",
          model: "qwen3",
          task: "document_qa",
          prompt: "NoProperGrammar",
        }) &&
        r.truncated &&
        r.scores[0],
    );
    recordPage = 0;
    openInspector("截断且首行命中", "");
    drawRecordList("截断且首行命中");
  }
  if (el.dataset.action === "export-chart") exportFigure();
});
document.addEventListener("change", async (e) => {
  const el = e.target;
  if (el.id === "shared-model") {
    state.models=el.value === "__all" ? [...MODEL_IDS] : [el.value];
    if (el.value !== "__all") { budgetModel=el.value; demoModel=el.value; }
    behaviorSelection=null; render();
  }
  if (["code-model","code-task","code-error"].includes(el.id)) {
    if (el.id === "code-model") codeModel=el.value;
    if (el.id === "code-task") codeTask=el.value;
    if (el.id === "code-error") codeError=el.value;
    render();
  }
  if (el.id === "research-position-view") {
    researchPositionView = el.value;
    render();
  }
  if (el.id === "research-scope") {
    researchScope = el.value;
    render();
  }
  if (el.id === "research-metric") {
    researchMetric = +el.value;
    render();
  }
  if (el.id === "demo-model") {
    demoModel = el.value;
    budgetModel = demoModel;
    state.models = [demoModel];
    render();
  }
  if (el.id === "position-metric") {
    positionMetric = +el.value;
    render();
  }
  if (el.id === "position-scope") {
    positionScope = el.value;
    render();
  }
  if (el.id === "position-view") {
    positionView = el.value;
    render();
  }
  if (el.id === "highlight-truncated") {
    highlightTruncated = el.checked;
    renderWaffle();
  }
  if (el.id === "dataset-select") {
    state.dataset = el.value;
    state.task = el.value === "reasoning" ? "gsm8k" : "document_qa";
    state.models = el.value === "document_qa" && !["qwen","qwen3"].includes(budgetModel) ? ["qwen","qwen3"] : state.models;
    state.focus = null;
    behaviorSelection=null;
    state.documents="all"; state.position="all";
    state.prompt = "DefaultCoT";
    if (el.value === "code") {state.dataset="reasoning";state.task="gsm8k";mode="code";render();return;}
    else if (!library[libraryChart]) libraryChart = "model";
    render();
  }
  if (el.id === "library-chart" || el.id === "code-chart") {
    libraryChart = el.value;
    behaviorSelection=null;
    render();
  }
  if (el.id === "task-select") {
    state.task = el.value;
    state.focus = null;
    behaviorSelection=null;
    render();
  }
  if (el.id === "metric-select") {
    state.metric = +el.value;
    render();
  }
  if (el.id === "prompt-select") {
    state.prompt = el.value;
    state.focus = null;
    behaviorSelection=null;
    render();
  }
  if (el.id === "heat-scope") {
    heatScope = el.value;
    render();
  }
  if (el.id === "bubble-mode") {
    state.bubble = el.value;
    render();
  }
  if (el.id === "radial-mode") {
    state.radial = el.value;
    render();
  }
  if (el.id === "code-upload") {
    const file = el.files[0];
    if (!file) return;
    try {
      if (file.size > 10 * 1024 * 1024) throw new Error("文件过大");
      const next = validateCodingPayload(JSON.parse(await file.text()));
      if (!next.runs.length) throw new Error("文件中没有运行记录");
      codePayload = next;
      render();
    } catch (error) {
      notify("数据无法载入，请检查文件格式。");
    }
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#inspector").hidden) {
    closeInspector();
    return;
  }
  if (e.key === "Tab" && !$("#inspector").hidden) {
    const list = [
        ...$("#inspector").querySelectorAll(
          'button:not(:disabled),a,[tabindex="0"]',
        ),
      ],
      first = list[0],
      last = list.at(-1);
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
    return;
  }
  if (e.target.matches("select,input,textarea") || !$("#inspector").hidden)
    return;
  if (mode === "demo" && ["ArrowLeft", "ArrowRight"].includes(e.key)) {
    e.preventDefault();
    chapter = Math.min(
      4,
      Math.max(0, chapter + (e.key === "ArrowRight" ? 1 : -1)),
    );
    render();
  }
  if (["Enter", " "].includes(e.key) && e.target.matches("[data-pub-prompt],[data-efficiency-model]")) {
    e.preventDefault();
    e.target.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  }
  if (e.key === "Enter" && e.target.matches("[data-record]"))
    inspectRecord(e.target.dataset.record);
});
try {
  if (!data || !evidence) throw new Error("请双击“启动系统.command”打开。");
  if (mode === "explore") {
    if (library[params.get("chart")]) libraryChart = params.get("chart");
    if (["reasoning", "document_qa"].includes(params.get("dataset")))
      state.dataset = params.get("dataset");
    state.task =
      state.dataset === "document_qa"
        ? "document_qa"
        : ["gsm8k", "math500", "mmlu", "all"].includes(params.get("task"))
          ? params.get("task")
          : "gsm8k";
    if (
      [...data.prompts.map((p) => p.id), "__core", "__main", "__all"].includes(
        params.get("prompt"),
      )
    )
      state.prompt = params.get("prompt");
    const requestedModels=(params.get("models") || "").split(",").filter(m=>MODEL_IDS.includes(m));
    if (requestedModels.length) state.models=requestedModels;
    if (["0", "1", "2", "3"].includes(params.get("metric")))
      state.metric = +params.get("metric");
    if (["0","10","20"].includes(params.get("documents"))) state.documents=params.get("documents");
    if (["none","front","middle","back"].includes(params.get("position"))) state.position=params.get("position");
    if (libraryChart === "behavior" && Object.hasOwn(FAMILY_LABELS,params.get("family")) && Object.hasOwn(STYLE_LABELS,params.get("style"))) behaviorSelection={family:params.get("family"),style:params.get("style")};
  }
  render();
} catch (e) {
  $("#stage").innerHTML = `<p class="error">${esc(e.message)}</p>`;
}

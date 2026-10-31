(()=>{
"use strict";
const _libraries = (() => {
const inflight = new Map();
const specs = {
 d3:{file:'d3-7.9.0.min.js',global:'d3'},
 vega:{file:'vega-5.30.0.min.js',global:'vega'},
 vegaLite:{file:'vega-lite-5.23.0.min.js',global:'vegaLite'},
 plotly:{file:'plotly-cartesian-3.1.1.min.js',global:'Plotly'},
};
function ready(name,value){return name==='vegaLite'?typeof value?.compile==='function':name==='vega'?typeof value?.parse==='function':name==='d3'?typeof value?.select==='function':typeof value?.newPlot==='function';}
function load(name){
 const spec=specs[name];
 if(!spec)return Promise.reject(new Error('未知图形组件'));
 if(ready(name,window[spec.global]))return Promise.resolve(window[spec.global]);
 if(!inflight.has(name))inflight.set(name,new Promise((resolve,reject)=>{
  const script=document.createElement('script');script.src='assets/vendor/'+spec.file;script.async=true;
  script.onload=()=>{if(ready(name,window[spec.global]))resolve(window[spec.global]);else{inflight.delete(name);script.remove();reject(new Error('图形组件未完成加载'));}};
  script.onerror=()=>{inflight.delete(name);script.remove();reject(new Error('本地图形组件未找到，请重新启动系统'));};
  document.head.append(script);
 }));
 return inflight.get(name);
}
function reducedMotion(){return window.matchMedia('(prefers-reduced-motion: reduce)').matches;}

return {load,reducedMotion};
})();
const _model = (() => {
const CORE = [
  "NoCoT",
  "DefaultCoT",
  "BeConcise",
  "BulletPoints",
  "WordLimit(25)",
  "WordLimit(100)",
  "TokenLimit(100)",
  "StepLimit(2)",
];
const MODEL_IDS = ["deepseek", "hy4", "qwen", "qwen3"];
const METRICS = [
  "paper_firstline",
  "strict_final_em",
  "final_contains",
  "full_response_contains",
];
const METRIC_LABELS = [
  "首行答案命中率",
  "最终答案严格匹配率",
  "最终答案包含率",
  "全文答案包含率",
];
const TASK_LABELS = {
  gsm8k: "GSM8K · 算术推理",
  math500: "MATH500 · 数学解题",
  mmlu: "MMLU-Pro · 选择题",
  document_qa: "NQ-Open · 带资料问答",
  closedbook_control: "无资料对照",
  all: "三类任务等权",
};
const PROMPT_LABELS = {
  NoCoT: "直接回答",
  DefaultCoT: "逐步推理",
  BeConcise: "简洁推理",
  BulletPoints: "项目符号",
  "WordLimit(25)": "25 词限制",
  "WordLimit(50)": "50 词限制",
  "WordLimit(100)": "100 词限制",
  "TokenLimit(100)": "100 token 限制",
  "StepLimit(2)": "2 步限制",
  NoProperGrammar: "非标准语法",
  NoSpaces: "无空格",
  OnlyNumbers: "仅数字",
};
const initialState = () => ({
  route: "overview",
  dataset: "reasoning",
  task: "gsm8k",
  prompt: "DefaultCoT",
  metric: 0,
  models: [...MODEL_IDS],
  focus: null,
  documents: "all",
  position: "all",
  bubble: "tokens",
  radial: "radial",
  recordFlag: "all",
  recordPage: 0,
});
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const fmt = (v, d = 0) =>
  Number.isFinite(v)
    ? Number(v).toLocaleString("en-US", {
        minimumFractionDigits: d,
        maximumFractionDigits: d,
      })
    : "—";
const pct = (v, d = 1) =>
  Number.isFinite(v) ? `${fmt(v * 100, d)}%` : "—";
const signed = (v, d = 1) =>
  Number.isFinite(v) ? `${v > 0 ? "+" : ""}${fmt(v, d)}` : "—";
const promptName = (p) => PROMPT_LABELS[p] || p;

function matchesPrompt(cell, prompt) {
  if (prompt === "__all") return true;
  if (prompt === "__core") return CORE.includes(cell.prompt);
  if (prompt === "__main") return cell.scope === "main_comparison";
  return cell.prompt === prompt;
}
function selectCells(data, state, overrides = {}) {
  const s = { ...state, ...overrides };
  return data.cells.filter(
    (c) =>
      c.dataset === s.dataset &&
      s.models.includes(c.model) &&
      (s.task === "all" || c.task === s.task) &&
      matchesPrompt(c, s.prompt) &&
      (s.dataset === "reasoning" ||
        s.documents === "all" ||
        c.documents === Number(s.documents)) &&
      (s.dataset === "reasoning" ||
        s.position === "all" ||
        c.position === s.position),
  );
}
function aggregate(cells, metric = 0) {
  const a = {
    n: 0,
    score: 0,
    tokens: 0,
    tokenN: 0,
    truncated: 0,
    unresolved: 0,
    review: 0,
    scores: [0, 0, 0, 0],
    disagreement: [0, 0, 0, 0],
    questions: 0,
  };
  const tasks = new Map();
  for (const c of cells) {
    a.n += c.n;
    a.score += c.scores[metric];
    a.tokens += c.tokens;
    a.tokenN += c.token_n;
    a.truncated += c.truncated;
    a.unresolved += c.unresolved;
    a.review += c.review;
    for (let i = 0; i < 4; i++) {
      a.scores[i] += c.scores[i];
      a.disagreement[i] += c.disagreement[i];
    }
    // The same complete question set is reused across every prompt/model/setup.
    const key = c.dataset === "document_qa" ? "document_qa" : c.task;
    tasks.set(key, Math.max(tasks.get(key) || 0, c.questions));
  }
  a.questions = [...tasks.values()].reduce((x, y) => x + y, 0);
  a.rate = a.n ? a.score / a.n : NaN;
  a.meanTokens = a.tokenN ? a.tokens / a.tokenN : NaN;
  return a;
}
function groupCells(cells, key, metric = 0) {
  const groups = new Map();
  for (const c of cells) {
    const k = typeof key === "function" ? key(c) : c[key];
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(c);
  }
  return [...groups].map(([key, rows]) => ({
    key,
    ...aggregate(rows, metric),
    cells: rows,
  }));
}
function selectedMetric(state) {
  return state.dataset === "reasoning" ? 0 : state.metric;
}
function metricLabel(state) {
  return state.dataset === "reasoning"
    ? "当前规则评分通过率"
    : METRIC_LABELS[state.metric];
}
function csvString(rows) {
  const cell = (v) => {
    let s = v == null ? "" : String(v);
    if (typeof v === "string" && /^[=+@\-]/.test(s)) s = "'" + s;
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  return "\ufeff" + rows.map((r) => r.map(cell).join(",")).join("\r\n");
}
function validateCodingPayload(payload) {
  if (
    !payload ||
    payload.schema_version !== "code-test-v1" ||
    !Array.isArray(payload.runs)
  )
    throw new Error("需要 schema_version=code-test-v1 和 runs 数组。");
  if (Object.keys(payload).some((k) => !["schema_version", "runs"].includes(k)))
    throw new Error("顶层仅接受 schema_version 与 runs，请移除其他内容。");
  if (payload.runs.length > 5000)
    throw new Error("一次最多导入 5,000 个运行。");
  const ids = new Set();
  const safeString = (v, label, max = 100) => {
    if (typeof v !== "string" || !v.trim() || v.length > max)
      throw new Error(`${label} 应为 1–${max} 字符的非空文本。`);
    return v.trim();
  };
  const nullableNumber = (v, label) => {
    if (v == null) return null;
    if (typeof v !== "number" || !Number.isFinite(v) || v < 0)
      throw new Error(`${label} 应为非负数或 null。`);
    return v;
  };
  const runs = payload.runs.map((run, i) => {
    const id = safeString(run.run_id, `第 ${i + 1} 个 run_id`);
    if (ids.has(id)) throw new Error(`run_id 重复：${id}`);
    ids.add(id);
    const allowedRun = ["run_id", "model_id", "task_type", "events"];
    if (Object.keys(run).some((k) => !allowedRun.includes(k)))
      throw new Error(
        "运行仅接受 run_id、model_id、task_type、events 特征，请先移除原文和其他字段。",
      );
    if (
      !Array.isArray(run.events) ||
      !run.events.length ||
      run.events.length > 500
    )
      throw new Error(`${id} 需要 1–500 个事件。`);
    const turns = new Set();
    const events = run.events
      .map((e) => {
        if (
          Object.keys(e).some(
            (k) =>
              ![
                "turn",
                "event_type",
                "test_passed",
                "error_type",
                "output_tokens",
                "duration_seconds",
              ].includes(k),
          )
        )
          throw new Error("事件含不支持字段；请仅保留模板中的匿名特征。");
        if (!Number.isInteger(e.turn) || e.turn < 1 || turns.has(e.turn))
          throw new Error(`${id} 的 turn 应为不重复的正整数。`);
        turns.add(e.turn);
        if (!["test", "edit", "tool", "error"].includes(e.event_type))
          throw new Error("event_type 应为 test/edit/tool/error。");
        if (e.event_type === "test" && typeof e.test_passed !== "boolean")
          throw new Error("test 事件必须具有布尔值 test_passed。");
        if (e.event_type !== "test" && e.test_passed != null)
          throw new Error("非 test 事件的 test_passed 请留 null。");
        if (e.output_tokens != null && !Number.isInteger(e.output_tokens))
          throw new Error("output_tokens 应为非负整数或 null。");
        if (
          e.error_type != null &&
          (typeof e.error_type !== "string" || e.error_type.length > 100)
        )
          throw new Error("error_type 应为简短分类或 null。");
        return {
          turn: e.turn,
          event_type: e.event_type,
          test_passed: e.test_passed ?? null,
          error_type: e.error_type || null,
          output_tokens: nullableNumber(e.output_tokens, "output_tokens"),
          duration_seconds: nullableNumber(
            e.duration_seconds,
            "duration_seconds",
          ),
        };
      })
      .sort((a, b) => a.turn - b.turn);
    if (!events.some((e) => e.event_type === "test"))
      throw new Error(`${id} 至少需要一个 test 事件。`);
    return {
      run_id: id,
      model_id: safeString(run.model_id, "model_id"),
      task_type: safeString(run.task_type, "task_type"),
      events,
    };
  });
  return { schema_version: "code-test-v1", runs };
}
function codingSummary(runs) {
  return runs.map((r) => {
    const tests = r.events.filter((e) => e.event_type === "test");
    return {
      ...r,
      firstPassed: tests[0].test_passed,
      finalPassed: tests.at(-1).test_passed,
      testCount: tests.length,
      additionalTests: Math.max(0, tests.length - 1),
      editEvents: r.events.filter((e) => e.event_type === "edit").length,
      // Test repetitions do not establish code-repair attempts.
      repairRounds: null,
      outputTokens: r.events.some((e) => e.output_tokens != null)
        ? r.events.reduce((s, e) => s + (e.output_tokens ?? 0), 0)
        : null,
    };
  });
}

return {CORE,MODEL_IDS,METRICS,METRIC_LABELS,TASK_LABELS,PROMPT_LABELS,initialState,esc,fmt,pct,signed,promptName,matchesPrompt,selectCells,aggregate,groupCells,selectedMetric,metricLabel,csvString,validateCodingPayload,codingSummary};
})();
const _charts = (() => {
const {
  aggregate,
  groupCells,
  selectCells,
  selectedMetric,
  metricLabel,
  fmt,
  pct,
  esc,
  promptName,
  CORE,
  MODEL_IDS,
} = _model;
const libraries = _libraries;

const mounted = new Map();
let chartEpoch=0;
const font = '"Times New Roman", "Songti SC", serif';
const ink = "#526174",
  muted = "#68788d",
  grid = "#e9eef5";
let tooltip;
function disposeCharts() {
  chartEpoch++;
  for (const c of mounted.values()) c.dispose();
  mounted.clear();
  document.querySelector(".svg-tooltip")?.remove();
  tooltip = null;
}
function resizeCharts() {
  for (const c of mounted.values()) c.resize();
}
window.addEventListener("resize", resizeCharts);
const model = (data, id) => data.models.find((m) => m.id === id);
function base() {
  return {
    animation: !libraries.reducedMotion(),
    animationDuration: 250,
    animationDurationUpdate: 220,
    textStyle: { fontFamily: font, color: ink, fontSize: 12 },
    tooltip: {
      trigger: "item",
      confine: true,
      backgroundColor: "#fff",
      borderColor: "#e4e9f0",
      borderWidth: 1,
      padding: [10, 13],
      textStyle: { color: "#3f526c", fontSize: 12, fontFamily: font },
      extraCssText:
        "box-shadow:0 5px 25px #17352012;border-radius:8px;line-height:1.8",
    },
    aria: { enabled: true, decal: { show: false } },
  };
}
const axis = (name) => ({
  type: "value",
  name,
  nameLocation: "middle",
  nameGap: 29,
  nameTextStyle: { fontSize: 12, color: muted },
  axisLine: { show: false },
  axisTick: { show: false },
  axisLabel: { fontSize: 12, color: muted },
  splitLine: { lineStyle: { color: grid, type: "dashed" } },
});
function mount(id, option, onClick) {
  const el = document.getElementById(id);
  if (!el) return null;
  if (mounted.has(id)) {
    mounted.get(id).dispose();
    mounted.delete(id);
  }
  const c = window.echarts.init(el, null, {
    renderer: "svg",
    devicePixelRatio: Math.min(window.devicePixelRatio || 1, 2),
  });
  c.setOption({ ...base(), ...option });
  if (onClick)
    c.on("click", (p) => {
      if (p.data?.meta) onClick(p.data.meta);
    });
  mounted.set(id, c);
  return c;
}
function exportChart(id) {
  const c = mounted.get(id);
  if (!c) return false;
  if(c.exportSvg){c.exportSvg();return true;}
  const a = document.createElement("a");
  a.href = c.getDataURL({
    type: "svg",
    pixelRatio: 3,
    backgroundColor: "#fff",
  });
  a.download = `LENS-${id}.svg`;
  a.click();
  return true;
}
function emptyChart(id, title, body) {
  const el = document.getElementById(id);
  if (el)
    el.innerHTML = `<div class="chart-empty"><strong>${esc(title)}</strong><span>${esc(body)}</span></div>`;
}

function modelBars(id, data, state, onSelect) {
  const rows = groupCells(
    selectCells(data, state),
    "model",
    selectedMetric(state),
  );
  const ordered = MODEL_IDS.map((m) => rows.find((r) => r.key === m)).filter(
    Boolean,
  );
  if (!ordered.length)
    return emptyChart(id, "当前条件没有数据", "请选择至少一个已接入模型。");
  const values = ordered.map((r) => ({
    value: r.rate * 100,
    meta: { model: r.key, prompt: state.prompt },
    itemStyle: {
      color:
        state.focus && r.key !== state.focus
          ? "#dfe5da"
          : model(data, r.key).color,
      borderRadius: [4, 4, 0, 0],
    },
    raw: r,
  }));
  mount(
    id,
    {
      grid: { left: 48, right: 24, top: 71, bottom: 46 },
      xAxis: {
        type: "category",
        data: ordered.map((r) => model(data, r.key).name),
        axisLine: { lineStyle: { color: "#cbd5c2" } },
        axisTick: { show: false },
        axisLabel: { color: ink, fontSize: 12, interval: 0, margin: 14 },
      },
      yAxis: {
        ...axis(
          state.dataset === "reasoning" ? "规则评分（%）" : "命中 / 匹配率（%）",
        ),
        nameLocation: "end",
        nameGap: 17,
        nameTextStyle: { align: "left", fontSize: 12, color: muted },
        min: 0,
        max: 100,
        interval: 25,
        axisLabel: { color: muted, fontSize: 12, formatter: "{value}%" },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) => {
          const r = p.data.raw;
          if (!r) return "";
          return `<b>${esc(model(data, r.key).name)}</b><br>${esc(metricLabel(state))}：${pct(r.rate)}<br>响应 ${fmt(r.n)} 条 · 独立题 ${fmt(r.questions)} 道<br>平均返回 ${fmt(r.meanTokens, 1)} token<br>截断 ${pct(r.truncated / r.n)}<br><span style="color:#9ca88f">点击查看条件与记录特征</span>`;
        },
      },
      series: [
        {
          name: metricLabel(state),
          type: "bar",
          barMaxWidth: 48,
          data: values,
          label: {
            show: true,
            position: "top",
            distance: 9,
            formatter: (p) => `${fmt(p.value, 1)}`,
            fontWeight: 600,
            color: "#677588",
            fontSize: 12,
          },
          z: 2,
        },
        {
          name: "模型标识",
          type: "scatter",
          clip: false,
          silent: true,
          symbolSize: 25,
          symbolOffset: [0, -43],
          data: ordered.map((r, i) => ({
            value: [i, r.rate * 100],
            symbol: `image://${window.COURSE_LOGOS?.[model(data, r.key).logo] || "assets/logos/" + model(data, r.key).logo}`,
          })),
          tooltip: { show: false },
          z: 5,
        },
      ],
    },
    onSelect,
  );
}

function radar(id, data, state, onSelect) {
  const metric = selectedMetric(state),
    isZ = state.dataset === "reasoning";
  const dimensions = isZ
    ? ["GSM8K 评分", "MATH500 评分", "MMLU-Pro 评分", "输出完整率", "提取可用率"]
    : ["前部命中率", "中部命中率", "尾部命中率", "输出完整率", "提取可用率"];
  const profiles = [];
  for (const m of data.models.filter((m) => state.models.includes(m.id))) {
    const all = selectCells(data, state, {
      models: [m.id],
      task: isZ ? "all" : "document_qa",
      position: "all",
    });
    if (!all.length) continue;
    const combined = aggregate(all, metric);
    const rates = isZ
      ? ["gsm8k", "math500", "mmlu"].map(
          (t) =>
            aggregate(
              all.filter((c) => c.task === t),
              metric,
            ).rate * 100,
        )
      : ["front", "middle", "back"].map(
          (p) =>
            aggregate(
              all.filter((c) => c.position === p),
              metric,
            ).rate * 100,
        );
    profiles.push({
      name: m.name,
      value: [
        ...rates,
        (1 - combined.truncated / combined.n) * 100,
        (1 - combined.unresolved / combined.n) * 100,
      ],
      meta: { model: m.id, prompt: state.prompt },
      lineStyle: {
        width: 1.6,
        color: m.color,
        opacity: state.focus && state.focus !== m.id ? 0.3 : 1,
      },
      itemStyle: { color: m.color },
      areaStyle: {
        color: m.color,
        opacity: state.focus && state.focus !== m.id ? 0.015 : 0.055,
      },
      symbolSize: 4,
    });
  }
  mount(
    id,
    {
      radar: {
        center: ["50%", "51%"],
        radius: "65%",
        splitNumber: 4,
        shape: "polygon",
        indicator: dimensions.map((name) => ({ name, max: 100 })),
        axisName: { color: "#8b95a3", fontSize: 12 },
        axisLine: { lineStyle: { color: "#e1e9d8" } },
        splitLine: { lineStyle: { color: "#e6ecdf" } },
        splitArea: { areaStyle: { color: ["#fff", "#fafcf7"] } },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) =>
          `<b>${esc(p.name)}</b><br>${dimensions.map((d, i) => `${d}：${fmt(p.value[i], 1)}%`).join("<br>")}`,
      },
      series: [{ type: "radar", data: profiles }],
    },
    onSelect,
  );
}

function bubble(id, data, state, onSelect) {
  const metric = selectedMetric(state),
    sizeMode = state.bubble === "parameters";
  const rows = groupCells(
    selectCells(data, state, { prompt: sizeMode ? state.prompt : "__all" }),
    sizeMode ? "model" : (c) => `${c.model}|${c.prompt}`,
    metric,
  );
  const series = [];
  for (const m of data.models.filter((m) => state.models.includes(m.id))) {
    if (sizeMode && m.parameters_b == null) continue;
    const points = rows
      .filter((r) => r.cells[0].model === m.id)
      .map((r) => {
        const p = sizeMode ? state.prompt : r.cells[0].prompt;
        return {
          name: promptName(p),
          value: [
            sizeMode ? m.parameters_b : r.meanTokens,
            r.rate * 100,
            r.meanTokens,
          ],
          meta: { model: m.id, prompt: p },
          raw: r,
          symbolSize: sizeMode
            ? Math.sqrt(r.meanTokens) * 2.2
            : m.parameters_b
              ? Math.sqrt(m.parameters_b) * 9
              : 17,
          itemStyle: {
            color: m.parameters_b || sizeMode ? m.color : "#fff",
            opacity: sizeMode || p === state.prompt ? 0.85 : 0.36,
            borderColor: m.color,
            borderWidth: p === state.prompt ? 2 : 1.1,
          },
          label: sizeMode
            ? {
                show: true,
                formatter: `${m.name}\n${m.parameters_b}B · ${fmt(r.rate * 100, 1)}%`,
                position: m.id === "qwen" ? "left" : "right",
                color: "#7c8797",
                fontSize: 12,
                lineHeight: 16,
                distance: 8,
              }
            : { show: false },
        };
      });
    series.push({
      name: m.name,
      type: "scatter",
      data: points,
      emphasis: { scale: 1.15, itemStyle: { opacity: 1 } },
      clip: false,
    });
  }
  if (!series.length)
    return emptyChart(
      id,
      "当前所选模型没有可核实的参数量",
      "切换到输出开销视图，或选择 Qwen2.5 / Qwen3。",
    );
  mount(
    id,
    {
      grid: { left: 53, right: sizeMode ? 56 : 26, top: 38, bottom: 57 },
      xAxis: {
        ...axis(sizeMode ? "公开总参数量（B）" : "平均返回 token / 条"),
        min: 0,
        max: sizeMode ? 11 : null,
        interval: sizeMode ? 2 : undefined,
      },
      yAxis: {
        ...axis("评分 / 命中率（%）"),
        min: 0,
        max: 100,
        nameLocation: "end",
        nameGap: 15,
        axisLabel: { fontSize: 12, color: muted, formatter: "{value}" },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) => {
          const r = p.data.raw,
            m = model(data, p.data.meta.model);
          return `<b>${esc(m.name)}</b> · ${esc(promptName(p.data.meta.prompt))}<br>评分 / 命中率：${pct(r.rate)}<br>平均返回：${fmt(r.meanTokens, 1)} token<br>公开总参数：${m.parameters_b == null ? "未核实" : m.parameters_b + "B"}<br>截断：${pct(r.truncated / r.n)}<br>${fmt(r.n)} 响应 · ${fmt(r.questions)} 独立题`;
        },
      },
      series,
    },
    onSelect,
  );
}

const polarPoint = (cx, cy, r, deg) => [
  cx + r * Math.sin((deg * Math.PI) / 180),
  cy - r * Math.cos((deg * Math.PI) / 180),
];
function annular(cx, cy, inner, outer, start, end) {
  const a = polarPoint(cx, cy, outer, start),
    b = polarPoint(cx, cy, outer, end),
    c = polarPoint(cx, cy, inner, end),
    d = polarPoint(cx, cy, inner, start);
  return `M${a} A${outer},${outer} 0 ${end - start > 180 ? 1 : 0},1 ${b} L${c} A${inner},${inner} 0 ${end - start > 180 ? 1 : 0},0 ${d} Z`;
}
function showTip(event, text) {
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.className = "svg-tooltip";
    document.body.append(tooltip);
  }
  tooltip.innerHTML = text;
  const r = event.target.getBoundingClientRect();
  tooltip.style.left = `${Math.min(event.clientX || r.x, window.innerWidth - 245) + 10}px`;
  tooltip.style.top = `${Math.min(event.clientY || r.y, window.innerHeight - 125) + 10}px`;
  tooltip.hidden = false;
}
function radial(id, data, state, onSelect) {
  const el = document.getElementById(id);
  if (!el) return;
  const metric = selectedMetric(state),
    models = data.models.filter(
      (m) =>
        state.models.includes(m.id) &&
        data.cells.some((c) => c.dataset === state.dataset && c.model === m.id),
    );
  const rows = groupCells(
    selectCells(data, state, { prompt: "__core" }),
    (c) => `${c.model}|${c.prompt}`,
    metric,
  );
  if (state.radial === "bars") {
    el.classList.add("chart");
    mount(
      id,
      {
        grid: { left: 48, right: 18, top: 27, bottom: 75 },
        xAxis: {
          type: "category",
          data: CORE.map(promptName),
          axisLine: { lineStyle: { color: "#d4dec9" } },
          axisTick: { show: false },
          axisLabel: { fontSize: 12, color: muted, rotate: 25, interval: 0 },
        },
        yAxis: {
          ...axis(""),
          min: 0,
          max: 100,
          axisLabel: { fontSize: 12, color: muted, formatter: "{value}%" },
        },
        tooltip: {
          ...base().tooltip,
          formatter: (p) =>
            `${esc(p.seriesName)} · ${esc(p.name)}<br>${fmt(p.value, 1)}%`,
        },
        series: models.map((m) => ({
          type: "bar",
          name: m.name,
          barMaxWidth: 15,
          itemStyle: { color: m.color, borderRadius: [2, 2, 0, 0] },
          data: CORE.map((p) => ({
            value:
              (rows.find((r) => r.key === `${m.id}|${p}`)?.rate ?? 0) * 100,
            meta: { model: m.id, prompt: p },
          })),
        })),
      },
      onSelect,
    );
    return;
  }
  const cx = 270,
    cy = 244,
    inner = 62,
    outer = 184,
    band = 360 / CORE.length;
  let svg = `<svg viewBox="0 0 540 485" role="group" aria-label="八种提示策略与所选模型的环形柱状对比，半径表示百分比"><g>`;
  for (const v of [25, 50, 75, 100]) {
    const r = inner + ((outer - inner) * v) / 100;
    svg += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#e9edf3" stroke-dasharray="2 4"/><text x="${cx + 4}" y="${cy - r - 3}" fill="#bac4aa" font-size="7">${v}%</text>`;
  }
  const familyColors = [
    "#dde7d3",
    "#dde7d3",
    "#dde8e1",
    "#dde8e1",
    "#e9e4f1",
    "#e9e4f1",
    "#e9e4f1",
    "#f0e7d8",
  ];
  for (let i = 0; i < CORE.length; i++) {
    const prompt = CORE[i],
      start = i * band + 5,
      end = (i + 1) * band - 5,
      w = (end - start) / models.length;
    svg += `<path d="${annular(cx, cy, 201, 204, start, end)}" fill="${familyColors[i]}"/>`;
    for (let j = 0; j < models.length; j++) {
      const m = models[j],
        r = rows.find((r) => r.key === `${m.id}|${prompt}`);
      if (!r) continue;
      const value = r.rate * 100,
        rad = inner + ((outer - inner) * value) / 100;
      const active = state.focus === m.id && state.prompt === prompt;
      svg += `<path class="radial-bar" tabindex="0" role="button" aria-label="${esc(m.name)} ${esc(promptName(prompt))} ${fmt(value, 1)}%，点击联动" data-model="${m.id}" data-prompt="${esc(prompt)}" data-rate="${value}" data-n="${r.n}" d="${annular(cx, cy, inner, rad, start + j * w + 0.5, start + (j + 1) * w - 1)}" fill="${m.color}" opacity="${state.focus && m.id !== state.focus ? 0.32 : 0.85}" ${active ? 'stroke="#33552c" stroke-width="1.5"' : ""}/>`;
    }
    const [x, y] = polarPoint(cx, cy, 222, (start + end) / 2);
    const labels = {
      NoCoT: "直接回答",
      DefaultCoT: "逐步推理",
      BeConcise: "简洁推理",
      BulletPoints: "项目符号",
      "WordLimit(25)": "25 词限制",
      "WordLimit(100)": "100 词限制",
      "TokenLimit(100)": "100 token",
      "StepLimit(2)": "2 步限制",
    };
    svg += `<text x="${x}" y="${y}" class="radial-label" text-anchor="middle" dominant-baseline="central">${labels[prompt]}</text>`;
  }
  svg += `<circle cx="${cx}" cy="${cy}" r="55" fill="#fff"/><text x="${cx}" y="${cy - 5}" text-anchor="middle" fill="#65758b" font-size="16" font-weight="600" letter-spacing="2">STRATEGY</text><text x="${cx}" y="${cy + 16}" text-anchor="middle" fill="#a7afba" font-size="9">8 策略 × ${models.length} 模型</text></g></svg>`;
  el.innerHTML = svg;
  el.querySelectorAll(".radial-bar").forEach((path) => {
    const action = () =>
      onSelect({ model: path.dataset.model, prompt: path.dataset.prompt });
    path.addEventListener("click", action);
    path.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        action();
      }
    });
    const tip = (e) =>
      showTip(
        e,
        `<b>${esc(model(data, path.dataset.model).name)}</b> · ${esc(promptName(path.dataset.prompt))}<br>评分 / 命中率：${fmt(Number(path.dataset.rate), 1)}%<br>${fmt(Number(path.dataset.n))} 条响应；点击联动`,
      );
    path.addEventListener("pointermove", tip);
    path.addEventListener("focus", tip);
    path.addEventListener("pointerleave", () => {
      if (tooltip) tooltip.hidden = true;
    });
    path.addEventListener("blur", () => {
      if (tooltip) tooltip.hidden = true;
    });
  });
}

function heatmap(id, data, state, onSelect) {
  const models = data.models.filter(
    (m) =>
      state.models.includes(m.id) &&
      data.cells.some((c) => c.dataset === state.dataset && c.model === m.id),
  );
  const prompts =
      state.heatScope === "all" ? data.prompts.map((p) => p.id) : CORE,
    metric = selectedMetric(state);
  const grouped = groupCells(
    selectCells(data, state, { prompt: "__all" }),
    (c) => `${c.model}|${c.prompt}`,
    metric,
  );
  const cells = [];
  for (let y = 0; y < prompts.length; y++)
    for (let x = 0; x < models.length; x++) {
      const r = grouped.find((r) => r.key === `${models[x].id}|${prompts[y]}`);
      if (r)
        cells.push({
          value: [x, y, r.rate * 100],
          meta: { model: models[x].id, prompt: prompts[y] },
          raw: r,
          label: { color: r.rate >= 0.6 ? "#ffffff" : "#4f637e" },
        });
    }
  mount(
    id,
    {
      grid: { left: 126, right: 53, top: 43, bottom: 24 },
      xAxis: {
        type: "category",
        position: "top",
        data: models.map(
          (m) =>
            ({
              deepseek: "DeepSeek",
              hy4: "HY4",
              qwen: "Qwen2.5",
              qwen3: "Qwen3",
            })[m.id] || m.name,
        ),
        splitArea: { show: true },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontSize: 12, color: ink, interval: 0 },
      },
      yAxis: {
        type: "category",
        data: prompts.map(promptName),
        inverse: true,
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { fontSize: 12, color: "#879878", interval: 0 },
      },
      visualMap: {
        min: 0,
        max: 100,
        show: true,
        calculable: true,
        orient: "vertical",
        right: 5,
        top: "center",
        itemHeight: 140,
        itemWidth: 8,
        text: ["100%", "0%"],
        textStyle: { fontSize: 8, color: muted },
        inRange: {
          color: ["#f4f6fb", "#e0e7f2", "#bdcde3", "#819cbe", "#526b9c"],
        },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) =>
          `${esc(models[p.value[0]].name)} · ${esc(promptName(prompts[p.value[1]]))}<br>评分 / 命中率：${fmt(p.value[2], 1)}%<br>平均返回：${fmt(p.data.raw.meanTokens, 1)} token<br>截断：${pct(p.data.raw.truncated / p.data.raw.n)}<br>点击联动并查看记录`,
      },
      series: [
        {
          type: "heatmap",
          data: cells,
          label: {
            show: true,
            formatter: (p) => `${fmt(p.value[2], 1)}`,
            fontSize: 12,
            color: "#4f637e",
          },
          itemStyle: { borderWidth: 3, borderColor: "#fff", borderRadius: 4 },
          emphasis: { itemStyle: { borderColor: "#315e40", borderWidth: 2 } },
        },
      ],
    },
    onSelect,
  );
}

function positionLines(id, data, state, onSelect) {
  const cells = selectCells(data, state, {
      dataset: "document_qa",
      task: "document_qa",
      position: "all",
    }),
    series = [];
  for (const m of data.models.filter((m) => state.models.includes(m.id))) {
    for (const docs of [10, 20]) {
      const subset = cells.filter(
        (c) => c.model === m.id && c.documents === docs,
      );
      if (!subset.length) continue;
      series.push({
        name: `${m.name} · ${docs} 篇`,
        type: "line",
        smooth: false,
        symbol: "circle",
        symbolSize: 6,
        lineStyle: {
          color: m.color,
          width: 2,
          type: docs === 10 ? "solid" : "dashed",
        },
        itemStyle: { color: m.color },
        label: { show: false },
        data: ["front", "middle", "back"].map((p) => ({
          value:
            aggregate(
              subset.filter((c) => c.position === p),
              state.metric,
            ).rate * 100,
          meta: {
            model: m.id,
            position: p,
            documents: docs,
            prompt: state.prompt,
          },
        })),
      });
    }
  }
  mount(
    id,
    {
      grid: { left: 50, right: 30, top: 95, bottom: 43 },
      legend: {
        top: 12,
        left: 45,
        right: 15,
        itemGap: 12,
        itemWidth: 14,
        itemHeight: 5,
        textStyle: { fontSize: 12, color: muted },
      },
      xAxis: {
        type: "category",
        data: ["前部", "中部", "尾部"],
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#d2ddc6" } },
        axisLabel: { fontSize: 12, color: ink, margin: 13 },
      },
      yAxis: {
        ...axis("命中率（%）"),
        min: 0,
        max: 100,
        nameLocation: "end",
        nameGap: 15,
      },
      tooltip: { ...base().tooltip, trigger: "axis" },
      series,
    },
    onSelect,
  );
}

function controlsBars(id, data, state) {
  const models = data.models.filter(
    (m) => ["qwen", "qwen3"].includes(m.id) && state.models.includes(m.id),
  );
  const rows = ["无资料", "带资料"];
  const cells = selectCells(data, state, {
    dataset: "document_qa",
    task: "all",
    prompt: "NoCoT",
    documents: "all",
    position: "all",
  });
  const series = models.map((m) => ({
    name: m.name,
    type: "bar",
    barMaxWidth: 32,
    itemStyle: { color: m.color, borderRadius: [3, 3, 0, 0] },
    label: {
      show: true,
      position: "top",
      fontSize: 12,
      color: "#738661",
      formatter: (p) => `${fmt(p.value, 1)}%`,
    },
    data: ["closedbook_control", "document_qa"].map(
      (task) =>
        aggregate(
          cells.filter((c) => c.model === m.id && c.task === task),
          state.metric,
        ).rate * 100,
    ),
  }));
  mount(id, {
    grid: { left: 46, right: 25, top: 54, bottom: 40 },
    legend: {
      top: 12,
      textStyle: { fontSize: 12, color: muted },
      itemHeight: 6,
      itemWidth: 12,
    },
    xAxis: {
      type: "category",
      data: rows,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "#d7e0ce" } },
      axisLabel: { color: ink, fontSize: 12, margin: 12 },
    },
    yAxis: {
      ...axis(""),
      min: 0,
      max: 100,
      axisLabel: { fontSize: 12, color: muted, formatter: "{value}%" },
    },
    tooltip: { ...base().tooltip, trigger: "axis" },
    series,
  });
}

function metricComparison(id, data, state) {
  const mid =
    state.focus && ["qwen", "qwen3"].includes(state.focus)
      ? state.focus
      : state.models.includes("qwen3")
        ? "qwen3"
        : "qwen";
  const colors = ["#93a983", "#4d6bfe", "#d6a768"];
  const labels = ["首行包含", "最终严格匹配", "最终答案包含", "全文包含"];
  const series = ["NoCoT", "DefaultCoT", "BeConcise"].map((p, i) => {
    const a = aggregate(
      selectCells(data, state, {
        dataset: "document_qa",
        task: "document_qa",
        models: [mid],
        prompt: p,
      }),
      0,
    );
    return {
      name: promptName(p),
      type: "bar",
      barMaxWidth: 22,
      itemStyle: { color: colors[i], borderRadius: [3, 3, 0, 0] },
      data: a.scores.map((s) => (a.n ? (s / a.n) * 100 : 0)),
    };
  });
  mount(id, {
    grid: { left: 48, right: 20, top: 58, bottom: 48 },
    legend: {
      top: 15,
      textStyle: { fontSize: 12, color: muted },
      itemWidth: 10,
      itemHeight: 6,
    },
    xAxis: {
      type: "category",
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "#d6e0cd" } },
      axisLabel: { fontSize: 12, color: ink, interval: 0 },
    },
    yAxis: {
      ...axis(""),
      min: 0,
      max: 100,
      axisLabel: { fontSize: 12, color: muted, formatter: "{value}%" },
    },
    tooltip: { ...base().tooltip, trigger: "axis" },
    series,
  });
}

function disagreement(id, data, state) {
  const a = aggregate(selectCells(data, state), 0),
    j = a.disagreement;
  const nodes = [
    { name: "首行未命中", value: j[0] + j[1], itemStyle: { color: "#d6ba97" } },
    { name: "首行命中", value: j[2] + j[3], itemStyle: { color: "#8fae82" } },
    {
      name: "最终答案未命中",
      value: j[0] + j[2],
      itemStyle: { color: "#d6ba97" },
    },
    {
      name: "最终答案命中",
      value: j[1] + j[3],
      itemStyle: { color: "#8fae82" },
    },
  ];
  const links = [
    { source: 0, target: 2, value: j[0] },
    { source: 0, target: 3, value: j[1] },
    { source: 1, target: 2, value: j[2] },
    { source: 1, target: 3, value: j[3] },
  ].filter((l) => l.value > 0);
  mount(id, {
    tooltip: {
      ...base().tooltip,
      formatter: (p) =>
        p.dataType === "edge"
          ? `${esc(nodes[p.data.source]?.name ?? p.data.source)} → ${esc(nodes[p.data.target]?.name ?? p.data.target)}<br>${fmt(p.value)} 条响应`
          : esc(p.name),
    },
    series: [
      {
        type: "sankey",
        top: 30,
        bottom: 30,
        left: 95,
        right: 112,
        nodeWidth: 9,
        nodeGap: 27,
        data: nodes,
        links,
        lineStyle: { color: "source", opacity: 0.22, curveness: 0.5 },
        label: { color: ink, fontSize: 12 },
        emphasis: { focus: "adjacency" },
        draggable: false,
      },
    ],
  });
}

function truncationBars(id, data, state, onSelect) {
  const prompts = [
    "NoCoT",
    "DefaultCoT",
    "BeConcise",
    "NoProperGrammar",
    "BulletPoints",
    "NoSpaces",
  ];
  const chosen =
    state.focus && state.models.includes(state.focus)
      ? [state.focus]
      : state.models;
  const rows = groupCells(
    selectCells(data, state, { prompt: "__all", models: chosen }),
    (c) => `${c.model}|${c.prompt}`,
  );
  const series = data.models
    .filter((m) => chosen.includes(m.id))
    .map((m) => ({
      name: m.name,
      type: "bar",
      barMaxWidth: 22,
      itemStyle: { color: m.color, borderRadius: [2, 2, 0, 0] },
      data: prompts.map((p) => {
        const r = rows.find((r) => r.key === `${m.id}|${p}`);
        return {
          value: r ? (r.truncated / r.n) * 100 : 0,
          meta: { model: m.id, prompt: p },
        };
      }),
    }));
  mount(
    id,
    {
      grid: { left: 47, right: 22, top: 45, bottom: 55 },
      legend: {
        top: 10,
        itemWidth: 10,
        itemHeight: 6,
        textStyle: { fontSize: 8, color: muted },
      },
      xAxis: {
        type: "category",
        data: prompts.map(promptName),
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#d6dfce" } },
        axisLabel: { fontSize: 12, color: ink, interval: 0, rotate: 15 },
      },
      yAxis: {
        ...axis("截断率（%）"),
        min: 0,
        max: 100,
        nameLocation: "end",
        nameGap: 15,
      },
      tooltip: { ...base().tooltip, trigger: "axis" },
      series,
    },
    onSelect,
  );
}

function reasoningStatus(id, data, state) {
  const cells = selectCells(data, state),
    g = groupCells(cells, "model");
  mount(id, {
    grid: { left: 102, right: 35, top: 35, bottom: 39 },
    legend: {
      bottom: 4,
      textStyle: { fontSize: 12, color: muted },
      itemWidth: 9,
      itemHeight: 6,
    },
    xAxis: { ...axis("响应数量（条）") },
    yAxis: {
      type: "category",
      data: g.map((r) => model(data, r.key).name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 12, color: ink },
    },
    tooltip: {
      ...base().tooltip,
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    series: [
      {
        type: "bar",
        stack: "records",
        name: "已解析",
        barMaxWidth: 23,
        itemStyle: { color: "#9caf88" },
        data: g.map((r) => r.n - r.unresolved),
      },
      {
        type: "bar",
        stack: "records",
        name: "未解析",
        itemStyle: { color: "#d8b793" },
        data: g.map((r) => r.unresolved),
      },
    ],
  });
}

function codingBars(id, runs) {
  const groups = [...new Set(runs.map((r) => r.model_id))];
  mount(id, {
    grid: { left: 46, right: 20, top: 50, bottom: 50 },
    legend: {
      top: 12,
      textStyle: { fontSize: 12, color: muted },
      itemWidth: 10,
      itemHeight: 6,
    },
    xAxis: {
      type: "category",
      data: groups,
      axisTick: { show: false },
      axisLabel: { fontSize: 12, color: ink },
      axisLine: { lineStyle: { color: "#d8e1cd" } },
    },
    yAxis: {
      ...axis(""),
      min: 0,
      max: 100,
      axisLabel: { fontSize: 12, color: muted, formatter: "{value}%" },
    },
    tooltip: { ...base().tooltip, trigger: "axis" },
    series: [
      {
        name: "首次测试通过",
        type: "bar",
        barMaxWidth: 30,
        itemStyle: { color: "#9aaf8b", borderRadius: [3, 3, 0, 0] },
        data: groups.map((m) => {
          const g = runs.filter((r) => r.model_id === m);
          return (g.filter((r) => r.firstPassed).length / g.length) * 100;
        }),
      },
      {
        name: "最终测试通过",
        type: "bar",
        barMaxWidth: 30,
        itemStyle: { color: "#4d6bfe", borderRadius: [3, 3, 0, 0] },
        data: groups.map((m) => {
          const g = runs.filter((r) => r.model_id === m);
          return (g.filter((r) => r.finalPassed).length / g.length) * 100;
        }),
      },
    ],
  });
}

function codingErrors(id, runs) {
  const errors = new Map();
  for (const r of runs)
    for (const e of r.events)
      if (e.event_type === "test" && !e.test_passed) {
        const k = e.error_type || "未分类";
        errors.set(k, (errors.get(k) || 0) + 1);
      }
  const rows = [...errors].sort((a, b) => b[1] - a[1]);
  if (!rows.length)
    return emptyChart(
      id,
      "本次导入没有失败的测试事件",
      "没有失败记录时不绘制错误分布。",
    );
  mount(id, {
    grid: { left: 105, right: 32, top: 28, bottom: 40 },
    xAxis: { ...axis("失败测试事件（次）"), minInterval: 1 },
    yAxis: {
      type: "category",
      data: rows.map((r) => r[0]),
      inverse: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 12, color: ink },
    },
    series: [
      {
        type: "bar",
        barMaxWidth: 24,
        itemStyle: { color: "#b6bc8c", borderRadius: [0, 3, 3, 0] },
        label: { show: true, position: "right", color: ink, fontSize: 12 },
        data: rows.map((r) => r[1]),
      },
    ],
  });
}

function heroGain(id, data, onSelect) {
  const s = {
    dataset: "reasoning",
    task: "gsm8k",
    models: MODEL_IDS,
    documents: "all",
    position: "all",
    prompt: "NoCoT",
  };
  const rows = MODEL_IDS.map((mid) => {
    const from = aggregate(selectCells(data, s, { models: [mid] }));
    const to = aggregate(
      selectCells(data, s, { models: [mid], prompt: "DefaultCoT" }),
    );
    return { m: model(data, mid), from: from.rate * 100, to: to.rate * 100 };
  });
  mount(
    id,
    {
      grid: { left: 105, right: 32, top: 32, bottom: 56 },
      xAxis: {
        ...axis("GSM8K 源规则评分（%）"),
        min: 0,
        max: 100,
        interval: 25,
      },
      yAxis: {
        type: "category",
        inverse: true,
        data: rows.map((r) => r.m.name),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: ink, fontSize: 12, margin: 15 },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) => {
          const r = p.data.raw;
          return r
            ? `<b>${esc(r.m.name)}</b><br>直接回答 ${fmt(r.from, 1)}% → 逐步推理 ${fmt(r.to, 1)}%<br>变化 +${fmt(r.to - r.from, 1)} 个百分点<br>每种提示 200 道同题`
            : "";
        },
      },
      series: [
        ...rows.map((r, i) => ({
          type: "line",
          silent: true,
          lineStyle: { color: r.m.color, width: 2, opacity: 0.45 },
          symbol: "none",
          data: [
            [r.from, i],
            [r.to, i],
          ],
        })),
        {
          name: "直接回答",
          type: "scatter",
          symbolSize: 9,
          data: rows.map((r, i) => ({
            value: [r.from, i],
            raw: r,
            meta: { model: r.m.id, prompt: "NoCoT" },
            itemStyle: {
              color: "#fff",
              borderColor: r.m.color,
              borderWidth: 1.6,
            },
          })),
        },
        {
          name: "逐步推理",
          type: "scatter",
          symbolSize: 10,
          data: rows.map((r, i) => ({
            value: [r.to, i],
            raw: r,
            meta: { model: r.m.id, prompt: "DefaultCoT" },
            itemStyle: { color: r.m.color },
            label: {
              show: true,
              position: "right",
              formatter: `+${fmt(r.to - r.from, 1)}`,
              fontSize: 12,
              color: r.m.color,
              distance: 8,
            },
          })),
        },
      ],
      graphic: [
        {
          type: "text",
          left: 107,
          bottom: 10,
          style: {
            text: "空心：直接回答    实心：逐步推理    标注：增量（pp）",
            font: `9px ${font}`,
            fill: muted,
          },
        },
      ],
    },
    onSelect,
  );
}
function quantile(sorted, p) {
  const pos = (sorted.length - 1) * p,
    lo = Math.floor(pos),
    hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}
function echartsBoxplot(id, data, state, rows) {
  const groups = new Map();
  for (const r of rows) {
    if (r.tokens == null || !Number.isFinite(r.tokens)) continue;
    const key = `${r.model}|${r.task}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r.tokens);
  }
  const boxes = [...groups].map(([key, v]) => {
    v.sort((a, b) => a - b);
    const [mid, task] = key.split("|"),
      q1 = quantile(v, 0.25),
      med = quantile(v, 0.5),
      q3 = quantile(v, 0.75),
      iqr = q3 - q1,
      inside = v.filter((x) => x >= q1 - 1.5 * iqr && x <= q3 + 1.5 * iqr);
    return {
      name: `${model(data, mid).name}\n${task === "document_qa" ? "NQ-Open" : (task === "mmlu" ? "MMLU-Pro" : task.toUpperCase())}`,
      model: mid,
      task,
      value: [inside[0], q1, med, q3, inside.at(-1)],
      raw: {
        n: v.length,
        outliers: v.length - inside.length,
        min: v[0],
        max: v.at(-1),
      },
      itemStyle: {
        color: model(data, mid).color + "22",
        borderColor: model(data, mid).color,
        borderWidth: 1.5,
      },
    };
  });
  if (!boxes.length)
    return emptyChart(id, "当前条件没有 token 记录", "更换实验条件。");
  const tasks = ["gsm8k", "math500", "mmlu", "document_qa"].filter((t) =>
    boxes.some((b) => b.task === t),
  );
  mount(id, {
    legend: {
      top: 0,
      textStyle: { fontSize: 12, color: muted },
      itemWidth: 10,
      itemHeight: 6,
    },
    grid: { left: 55, right: 22, top: 55, bottom: 55 },
    xAxis: {
      type: "category",
      data: tasks.map((t) =>
        t === "document_qa" ? "NQ-Open" : t.toUpperCase(),
      ),
      axisLine: { lineStyle: { color: "#d8dfe8" } },
      axisTick: { show: false },
      axisLabel: {
        fontSize: 12,
        color: ink,
        interval: 0,
        rotate: 0,
        lineHeight: 15,
      },
    },
    yAxis: {
      ...axis("返回 token / 条"),
      min: 0,
      nameLocation: "end",
      nameGap: 16,
    },
    tooltip: {
      ...base().tooltip,
      formatter: (p) => {
        const b = p.data;
        return `<b>${esc(b.name)}</b><br>有效记录 ${fmt(b.raw.n)} 条<br>中位数 ${fmt(b.value[2], 1)}<br>Q1–Q3：${fmt(b.value[1], 1)}–${fmt(b.value[3], 1)}<br>须：${fmt(b.value[0], 1)}–${fmt(b.value[4], 1)}<br>离群 ${fmt(b.raw.outliers)} 条（未逐点绘制）<br>实际最小 / 最大：${fmt(b.raw.min)} / ${fmt(b.raw.max)}`;
      },
    },
    series: MODEL_IDS.filter((mid) => boxes.some((b) => b.model === mid)).map(
      (mid) => ({
        name: model(data, mid).name,
        type: "boxplot",
        boxWidth: [12, 40],
        data: tasks.map(
          (task) =>
            boxes.find((b) => b.model === mid && b.task === task) ?? "-",
        ),
      }),
    ),
  });
}
async function boxplot(id,data,state,rows,onSelect){
  // Keep a useful SVG visible while the local statistical renderer loads.
  echartsBoxplot(id,data,state,rows);
  const el=document.getElementById(id),epoch=chartEpoch;
  let Plotly;try{Plotly=await libraries.load('plotly');}catch{return;}
  if(epoch!==chartEpoch || !el?.isConnected || document.getElementById(id)!==el)return;
  const groups=new Map();
  for(const r of rows){if(r.tokens==null || !Number.isFinite(r.tokens))continue;const k=r.model+'|'+r.task;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r.tokens);}
  const label=t=>t==='document_qa'?'NQ-Open':t==='mmlu'?'MMLU-Pro':t.toUpperCase();
  const tasks=['gsm8k','math500','mmlu','document_qa'].filter(t=>[...groups.keys()].some(k=>k.endsWith('|'+t)));
  const traces=MODEL_IDS.filter(mid=>[...groups.keys()].some(k=>k.startsWith(mid+'|'))).map(mid=>{
    const boxes=tasks.filter(t=>groups.has(mid+'|'+t)).map(task=>{const v=groups.get(mid+'|'+task).sort((a,b)=>a-b);const q1=quantile(v,.25),q3=quantile(v,.75),iqr=q3-q1,inside=v.filter(x=>x>=q1-1.5*iqr && x<=q3+1.5*iqr);return {task,q1,median:quantile(v,.5),q3,low:inside[0],high:inside.at(-1),n:v.length,outliers:v.length-inside.length};});
    const m=model(data,mid),rgb=m.color.match(/[a-f\d]{2}/gi).map(v=>parseInt(v,16));
    return {type:'box',name:m.name,x:boxes.map(b=>label(b.task)),q1:boxes.map(b=>b.q1),median:boxes.map(b=>b.median),q3:boxes.map(b=>b.q3),lowerfence:boxes.map(b=>b.low),upperfence:boxes.map(b=>b.high),boxpoints:false,line:{color:m.color,width:1.6},fillcolor:'rgba('+rgb.join(',')+',0.14)',whiskerwidth:.55,meta:{model:mid,boxes},text:boxes.map(b=>fmt(b.n)+' responses; '+fmt(b.outliers)+' outliers outside the whiskers'),hoverinfo:'all',hoverlabel:{font:{family:'Times New Roman',size:13},namelength:-1}};
  });
  if(!traces.length)return;
  mounted.get(id)?.dispose();mounted.delete(id);el.innerHTML='';el.dataset.renderer='plotly';el.setAttribute('aria-label','按模型和任务比较返回 token 分布；拖动缩放，双击复位，点箱体查看记录。键盘可用上方筛选和查看筛选记录。');
  let ready=false,disposed=false;
  const adapter={dispose:()=>{disposed=true;Plotly.purge(el);},resize:()=>{if(ready && !disposed && el.isConnected)Plotly.Plots.resize(el);},exportSvg:()=>{if(ready)Plotly.toImage(el,{format:'svg',width:Math.max(900,el.clientWidth),height:540}).then(url=>{
    const payload=url.slice(url.indexOf(',')+1),text=url.slice(0,url.indexOf(',')).includes('base64')?atob(payload):decodeURIComponent(payload),doc=new DOMParser().parseFromString(text,'image/svg+xml'),original=doc.documentElement,w=+original.getAttribute('width'),h=+original.getAttribute('height');
    const source=state.dataset==='document_qa'?'document_qa / NQ-Open':'reasoning / GSM8K, MATH500, MMLU-Pro';
    const body=`<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${w}" height="${h+100}" viewBox="0 0 ${w} ${h+100}"><rect width="100%" height="100%" fill="white"/><text x="45" y="30" font-family="Times New Roman" font-size="21" font-weight="bold">Output token distribution by model and task</text><svg x="0" y="43" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${original.innerHTML}</svg><text x="45" y="${h+72}" font-family="Times New Roman" font-size="12" fill="#60606a">Source: ${source}; ${rows.length} anonymous responses / ${new Set(rows.map(r=>r.question)).size} questions.</text><text x="45" y="${h+91}" font-family="Times New Roman" font-size="12" fill="#60606a">Boxes: Q1-Q3; median line; whiskers within 1.5 IQR. Outliers omitted. Current chart viewport retained.</text></svg>`;
    const objectUrl=URL.createObjectURL(new Blob([body],{type:'image/svg+xml;charset=utf-8'})),a=document.createElement('a');a.href=objectUrl;a.download='LENS-token-distribution.svg';a.target='_blank';a.rel='noopener';a.click();setTimeout(()=>URL.revokeObjectURL(objectUrl),2000);
   });}};
  mounted.set(id,adapter);
  try{
   await Plotly.newPlot(el,traces,{paper_bgcolor:'#fff',plot_bgcolor:'#fff',font:{family:'Times New Roman',color:'#353842',size:13},margin:{l:75,r:22,t:50,b:55},boxmode:'group',boxgap:.35,boxgroupgap:.18,dragmode:'zoom',hovermode:'closest',legend:{orientation:'h',x:0,y:1.16,font:{size:12}},xaxis:{type:'category',categoryorder:'array',categoryarray:tasks.map(label),showline:true,linecolor:'#8a8a93',tickfont:{size:13},fixedrange:false},yaxis:{title:{text:'Returned output tokens / response',font:{size:14}},rangemode:'tozero',gridcolor:'#e8e7ed',zeroline:false,showline:false,tickfont:{size:12}},transition:{duration:libraries.reducedMotion()?0:220}},{responsive:false,displayModeBar:false,scrollZoom:false,showTips:false});
   if(disposed || epoch!==chartEpoch){Plotly.purge(el);return;}ready=true;
   el.on('plotly_click',event=>{const p=event.points?.[0];if(!p)return;const task=p.data.meta.boxes.find(b=>label(b.task)===String(p.x))?.task;onSelect?.({model:p.data.meta.model,task});});
   el.on('plotly_legendclick',event=>{onSelect?.({model:traces[event.curveNumber].meta.model});return false;});
  }catch{if(!disposed && epoch===chartEpoch){mounted.delete(id);Plotly.purge(el);echartsBoxplot(id,data,state,rows);}}
}
function parallel(id, data, state) {
  const rows = groupCells(
    selectCells(data, state, { prompt: "__core" }),
    (c) => `${c.model}|${c.prompt}`,
    selectedMetric(state),
  );
  const tokenMax = Math.max(100, ...rows.map((r) => r.meanTokens));
  const series = data.models
    .filter((m) => state.models.includes(m.id))
    .map((m) => ({
      name: m.name,
      type: "parallel",
      lineStyle: { color: m.color, width: 1.3, opacity: 0.42 },
      emphasis: { lineStyle: { width: 3, opacity: 1 } },
      data: rows
        .filter((r) => r.cells[0].model === m.id)
        .map((r) => ({
          value: [
            r.rate * 100,
            r.meanTokens,
            (r.truncated / r.n) * 100,
            (r.review / r.n) * 100,
          ],
          name: promptName(r.cells[0].prompt),
        })),
    }));
  mount(id, {
    legend: {
      top: 5,
      textStyle: { fontSize: 12, color: muted },
      itemWidth: 12,
      itemHeight: 5,
    },
    parallel: {
      left: 55,
      right: 70,
      top: 85,
      bottom: 35,
      parallelAxisDefault: {
        type: "value",
        axisLine: { lineStyle: { color: "#c4cddb" } },
        axisTick: { show: false },
        axisLabel: { fontSize: 12, color: muted },
        nameTextStyle: { fontSize: 12, color: ink },
        nameGap: 20,
      },
    },
    parallelAxis: [
      { dim: 0, name: "当前评分（%）", min: 0, max: 100 },
      {
        dim: 1,
        name: "平均返回 token",
        min: 0,
        max: Math.ceil(tokenMax / 100) * 100,
      },
      { dim: 2, name: "截断（%）", min: 0, max: 100 },
      { dim: 3, name: "需复核（%）", min: 0, max: 100 },
    ],
    series,
  });
}
function distribution(pieId, stackId, data, state, rows) {
  const labels = ["完整且命中", "完整但未命中", "输出截断"],
    colors = ["#3f9c91", "#b8c3d2", "#df964c"],
    counts = [0, 0, 0],
    byModel = new Map();
  for (const r of rows) {
    const status = r.truncated
      ? 2
      : r.scores[selectedMetric(state)] === 1
        ? 0
        : 1;
    counts[status]++;
    if (!byModel.has(r.model)) byModel.set(r.model, [0, 0, 0]);
    byModel.get(r.model)[status]++;
  }
  if (!rows.length) {
    emptyChart(pieId, "当前筛选没有记录", "更换条件。");
    return;
  }
  mount(pieId, {
    legend: {
      bottom: 2,
      textStyle: { fontSize: 12, color: muted },
      itemWidth: 8,
      itemHeight: 8,
    },
    tooltip: {
      ...base().tooltip,
      formatter: (p) =>
        `${esc(p.name)}：${fmt(p.value)} 条（${fmt(p.percent, 1)}%）`,
    },
    series: [
      {
        type: "pie",
        radius: "63%",
        center: ["50%", "45%"],
        startAngle: 90,
        label: { fontSize: 12, color: ink, formatter: "{d}%" },
        labelLine: { length: 12, length2: 8 },
        itemStyle: { borderWidth: 3, borderColor: "#fff" },
        data: labels.map((name, i) => ({
          name,
          value: counts[i],
          itemStyle: { color: colors[i] },
        })),
      },
    ],
  });
  const ids = MODEL_IDS.filter((m) => byModel.has(m));
  mount(stackId, {
    grid: { left: 46, right: 20, top: 45, bottom: 65 },
    xAxis: {
      type: "category",
      data: ids.map((m) => model(data, m).name),
      axisLabel: {
        fontSize: 12,
        color: muted,
        interval: 0,
        rotate: ids.length > 2 ? 15 : 0,
      },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      ...axis("响应占比（%）"),
      max: 100,
      min: 0,
      nameLocation: "end",
      nameGap: 18,
    },
    tooltip: {
      ...base().tooltip,
      trigger: "axis",
      valueFormatter: (v) => fmt(v, 1) + "%",
    },
    series: labels.map((name, i) => ({
      name,
      type: "bar",
      stack: "status",
      barMaxWidth: 40,
      itemStyle: { color: colors[i] },
      data: ids.map((mid) => {
        const c = byModel.get(mid),
          n = c.reduce((a, b) => a + b, 0);
        return (c[i] / n) * 100;
      }),
    })),
  });
}
function retryTimeline(id, data, rows, onRecord) {
  const retry = rows.filter((r) => data.attempts[r.id]).slice(0, 12);
  if (!retry.length)
    return emptyChart(
      id,
      "当前条件没有多次请求记录",
      "在带资料问答中更换提示，或选择全部 31 策略。",
    );
  const segments = [];
  for (let i = 0; i < retry.length; i++) {
    const r = retry[i],
      seq = data.attempts[r.id],
      start = Date.parse(seq[0].started_at);
    for (const a of seq) {
      const begin = (Date.parse(a.started_at) - start) / 1000,
        end = (Date.parse(a.ended_at) - start) / 1000;
      if (!Number.isFinite(begin) || !Number.isFinite(end) || end < begin)
        continue;
      segments.push({
        value: [i, begin, end],
        raw: { id: r.id, ...a },
        itemStyle: {
          color:
            a.http_status >= 200 && a.http_status < 300 ? "#7c9dac" : "#dfaa72",
        },
        meta: { record: r.id },
      });
    }
  }
  if (!segments.length)
    return emptyChart(
      id,
      "请求时间戳不可解析",
      "可从匿名记录查看原始日志特征。",
    );
  mount(
    id,
    {
      grid: { left: 75, right: 22, top: 40, bottom: 55 },
      xAxis: { ...axis("距首次请求开始（秒）"), min: 0 },
      yAxis: {
        type: "category",
        inverse: true,
        data: retry.map((r) => r.id),
        axisLabel: { fontSize: 12, color: muted },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) => {
          const a = p.data.raw;
          return `${esc(a.id)} · 第 ${a.attempt} 次请求<br>HTTP ${a.http_status ?? "未记录"}<br>${esc(a.started_at)}<br>耗时 ${fmt(a.latency_seconds, 3)} 秒<br>点击查看完整序列`;
        },
      },
      graphic: [
        {
          type: "text",
          left: 75,
          top: 5,
          style: {
            text: "按匿名编号取前 12 个重试运行 · 蓝灰：成功，杏色：失败 / 状态未记录",
            font: `9px ${font}`,
            fill: muted,
          },
        },
      ],
      series: [
        {
          type: "custom",
          renderItem: (params, api) => {
            const y = api.value(0),
              start = api.coord([api.value(1), y]),
              end = api.coord([api.value(2), y]),
              h = api.size([0, 1])[1] * 0.5;
            return {
              type: "rect",
              shape: window.echarts.graphic.clipRectByRect(
                {
                  x: start[0],
                  y: start[1] - h / 2,
                  width: Math.max(2, end[0] - start[0]),
                  height: h,
                },
                {
                  x: params.coordSys.x,
                  y: params.coordSys.y,
                  width: params.coordSys.width,
                  height: params.coordSys.height,
                },
              ),
              style: api.style(),
            };
          },
          encode: { x: [1, 2], y: 0 },
          data: segments,
        },
      ],
    },
    (meta) => onRecord(meta.record),
  );
}
function prefixTree(sequences) {
  const root = { name: "运行", count: 0, children: [] };
  for (const { labels, meta } of sequences) {
    root.count++;
    let node = root;
    for (const label of labels) {
      let next = node.children.find((c) => c.label === label);
      if (!next) {
        next = { name: label, label, count: 0, children: [] };
        node.children.push(next);
      }
      next.count++;
      next.meta = meta;
      node = next;
    }
  }
  function finish(node) {
    node.name = `${node.label || "运行"} · ${node.count}`;
    node.value = node.count;
    if (node.children.length) {
      delete node.meta;
      node.children.forEach(finish);
    } else delete node.children;
    return node;
  }
  return finish(root);
}
function drawTree(id, tree, onClick) {
  mount(
    id,
    {
      tooltip: {
        ...base().tooltip,
        formatter: (p) =>
          `${esc(p.data.label || "所有运行")}<br>经过运行 ${fmt(p.data.count)} 个${p.data.meta ? "<br>点击查看一条对应运行" : ""}`,
      },
      series: [
        {
          type: "tree",
          data: [tree],
          left: 80,
          right: 115,
          top: 25,
          bottom: 25,
          symbolSize: 5,
          edgeShape: "polyline",
          edgeForkPosition: "40%",
          initialTreeDepth: 4,
          expandAndCollapse: true,
          lineStyle: { color: "#d3dce9", width: 1.1 },
          itemStyle: { color: "#8a9bb5", borderWidth: 0 },
          label: { position: "left", align: "right", fontSize: 12, color: ink },
          leaves: { label: { position: "right", align: "left" } },
          emphasis: { focus: "descendant" },
          roam: true,
        },
      ],
    },
    onClick,
  );
  const label = `事件路径树，共 ${tree.count} 个真实运行；节点标注经过运行数。`;
  const applyLabel = () =>
    document.getElementById(id)?.setAttribute("aria-label", label);
  applyLabel();
  mounted.get(id)?.on("finished", applyLabel);
}
function retryTree(id, data, rows, onRecord) {
  const retry = rows.filter((r) => data.attempts[r.id]);
  if (!retry.length)
    return emptyChart(
      id,
      "当前条件没有重试路径",
      "选择有请求日志的 document_qa 实验条件。",
    );
  const tree = prefixTree(
    retry.map((r) => ({
      labels: data.attempts[r.id].map((a) =>
        a.http_status == null ? "状态未记录" : `HTTP ${a.http_status}`,
      ),
      meta: { record: r.id },
    })),
  );
  drawTree(id, tree, (meta) => onRecord(meta.record));
}
function codingEventDistribution(id, runs) {
  const labels = {
      test: "执行测试",
      edit: "代码修改",
      tool: "工具调用",
      error: "错误记录",
    },
    colors = ["#819cbe", "#8774d9", "#3f9c91", "#df964c"];
  const counts = { test: 0, edit: 0, tool: 0, error: 0 };
  for (const r of runs) for (const e of r.events) counts[e.event_type]++;
  mount(id, {
    legend: { bottom: 0, textStyle: { fontSize: 12, color: muted } },
    tooltip: { ...base().tooltip, formatter: "{b}：{c} 个事件（{d}%）" },
    series: [
      {
        type: "pie",
        radius: "60%",
        center: ["50%", "45%"],
        label: { fontSize: 12, color: muted, formatter: "{d}%" },
        itemStyle: { borderColor: "#fff", borderWidth: 3 },
        data: Object.entries(counts).map(([k, value], i) => ({
          name: labels[k],
          value,
          itemStyle: { color: colors[i] },
        })),
      },
    ],
  });
}
function codingScatter(id, runs) {
  const grouped = new Map();
  for (const r of runs) {
    const calls = r.events.filter((e) => e.event_type === "tool").length,
      key = `${r.model_id}|${calls}|${r.finalPassed}`;
    if (!grouped.has(key))
      grouped.set(key, {
        model: r.model_id,
        calls,
        passed: r.finalPassed,
        n: 0,
      });
    grouped.get(key).n++;
  }
  const models = [...new Set(runs.map((r) => r.model_id))],
    colors = ["#4d6bfe", "#df964c", "#8774d9", "#3f9c91"];
  mount(id, {
    legend: {
      top: 0,
      type: "scroll",
      textStyle: { color: muted, fontSize: 12 },
    },
    grid: { left: 50, right: 35, top: 55, bottom: 55 },
    xAxis: { ...axis("实际工具调用次数 / 运行"), min: 0, minInterval: 1 },
    yAxis: {
      ...axis("最终测试状态"),
      min: -0.15,
      max: 1.15,
      interval: 1,
      axisLabel: {
        fontSize: 12,
        color: muted,
        formatter: (v) => (v === 0 ? "失败" : v === 1 ? "通过" : ""),
      },
      nameLocation: "end",
      nameGap: 20,
    },
    tooltip: {
      ...base().tooltip,
      formatter: (p) =>
        `${esc(p.seriesName)}<br>工具调用 ${p.data.value[0]} 次<br>最终${p.data.value[1] ? "通过" : "失败"}<br>同坐标 ${p.data.n} 个运行`,
    },
    series: models.map((name, i) => ({
      name,
      type: "scatter",
      symbolSize: (val) => 12 + Math.sqrt(val[2]) * 4,
      itemStyle: { color: colors[i % 4], opacity: 0.65 },
      data: [...grouped.values()]
        .filter((v) => v.model === name)
        .map((v) => ({
          value: [v.calls, v.passed ? 1 : 0, v.n],
          n: v.n,
          label: {
            show: true,
            formatter: String(v.n),
            position: "right",
            fontSize: 12,
            color: muted,
          },
        })),
    })),
  });
}
function codingTree(id, runs, onRun) {
  const labels = { edit: "修改", tool: "工具", error: "错误" };
  const tree = prefixTree(
    runs.map((r, i) => ({
      labels: r.events
        .slice(0, 10)
        .map((e) =>
          e.event_type === "test"
            ? e.test_passed
              ? "测试通过"
              : "测试失败" + (e.error_type ? " / " + e.error_type : "")
            : labels[e.event_type],
        )
        .concat(r.events.length > 10 ? ["后续事件（详情）"] : ["运行结束"]),
      meta: { run: i },
    })),
  );
  drawTree(id, tree, (meta) => onRun(meta.run));
}

function lengthHistogram(id, stats, onPick) {
  const el = document.getElementById(id),
    barWidth = Math.max(
      5,
      Math.min(
        34,
        (((el?.clientWidth || 800) - 110) / stats.histogram.length) * 0.82,
      ),
    );
  mount(
    id,
    {
      grid: { left: 65, right: 25, top: 38, bottom: 62 },
      xAxis: {
        ...axis("返回 token / 条"),
        min: 0,
        max: Math.ceil(stats.max / 10) * 10,
        interval: 50,
        nameGap: 37,
        axisLabel: { fontSize: 12, color: muted },
      },
      yAxis: {
        ...axis("响应数（次）"),
        min: 0,
        nameLocation: "end",
        nameTextStyle: { align: "left", fontSize: 12, color: muted },
        nameGap: 18,
        axisLabel: { fontSize: 12, color: muted },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) =>
          `${p.data.meta.lo}–${p.data.meta.hi - 1} token<br>${fmt(p.data.raw)} 次响应（${fmt((p.data.raw / stats.valid) * 100, 1)}%）<br>点击查看记录`,
      },
      series: [
        {
          type: "bar",
          barWidth,
          data: stats.histogram.map((b) => ({
            value: [b.lo + 5, b.n],
            meta: { lo: b.lo, hi: b.hi },
            raw: b.n,
            itemStyle: {
              color:
                b.lo <= stats.median && stats.median < b.hi
                  ? "#4263eb"
                  : "#c4d2f4",
              borderRadius: [2, 2, 0, 0],
            },
          })),
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#9dabc2", type: "dashed", width: 1 },
            label: {
              show: true,
              fontSize: 11,
              color: "#8d9bb1",
              formatter: `中位数 ${fmt(stats.median)}`,
              position: "insideEndTop",
            },
            data: [{ xAxis: stats.median }],
          },
        },
      ],
    },
    onPick,
  );
}
function promptCase(id, data, mid, onPick) {
  const prompts = ["NoCoT", "DefaultCoT", "BeConcise"],
    colors = ["#bac7dd", "#4263eb", "#12a89d"];
  const s = {
    dataset: "reasoning",
    models: [mid],
    task: "gsm8k",
    prompt: "NoCoT",
    documents: "all",
    position: "all",
  };
  const points = prompts.map((prompt, i) => {
    const a = aggregate(selectCells(data, s, { prompt }));
    return {
      value: a.rate * 100,
      raw: a,
      meta: { model: mid, prompt },
      itemStyle: { color: colors[i], borderRadius: [3, 3, 0, 0] },
    };
  });
  mount(
    id,
    {
      grid: { left: 68, right: 40, top: 45, bottom: 60 },
      xAxis: {
        type: "category",
        data: prompts.map(promptName),
        axisLine: { lineStyle: { color: "#dbe2ed" } },
        axisTick: { show: false },
        axisLabel: { fontSize: 14, color: ink, margin: 18 },
      },
      yAxis: {
        ...axis("当前规则评分（%）"),
        min: 0,
        max: 100,
        interval: 25,
        nameLocation: "end",
        nameTextStyle: { fontSize: 12, align: "left", color: muted },
        nameGap: 20,
        axisLabel: { fontSize: 12, color: muted, formatter: "{value}%" },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) =>
          `${esc(p.name)}<br>评分通过 ${fmt(p.data.raw.score)} / ${p.data.raw.n}<br>${pct(p.data.raw.rate)}`,
      },
      series: [
        {
          type: "bar",
          barMaxWidth: 85,
          data: points,
          label: {
            show: true,
            position: "top",
            distance: 12,
            fontSize: 20,
            color: "#657fa7",
            formatter: (p) => fmt(p.value, 1) + "%",
          },
        },
      ],
    },
    onPick,
  );
}
function efficiencyCase(id, data, list, onPick) {
  const shapes = { gsm8k: "circle", math500: "diamond", mmlu: "rect" },
    bottom =
      Math.floor((Math.min(0, ...list.map((r) => r.difference_pp)) - 2) / 5) *
      5,
    top =
      Math.ceil((Math.max(...list.map((r) => r.difference_pp)) + 2) / 5) * 5;
  mount(
    id,
    {
      grid: { left: 76, right: 55, top: 35, bottom: 62 },
      xAxis: {
        ...axis("平均返回 token 减少（%）"),
        min: 0,
        max: 50,
        interval: 10,
        nameGap: 37,
        axisLabel: { fontSize: 12, color: muted },
      },
      yAxis: {
        ...axis("规则评分变化（pp）"),
        min: bottom,
        max: top,
        interval: 5,
        nameLocation: "end",
        nameTextStyle: { align: "left", fontSize: 12, color: muted },
        nameGap: 17,
        axisLabel: { fontSize: 12, color: muted },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) => {
          const r = p.data.raw;
          return `<b>${esc(nameOf(data, r.model_id))} · ${(r.benchmark === "mmlu" ? "MMLU-Pro" : r.benchmark.toUpperCase())}</b><br>平均返回 ${fmt(r.second_mean_tokens, 1)} → ${fmt(r.first_mean_tokens, 1)} token<br>减少 ${fmt(r.token_saving_pct, 1)}%<br>规则评分 ${pct(r.second_rate)} → ${pct(r.first_rate)}<br>评分差 ${r.difference_pp > 0 ? "+" : ""}${fmt(r.difference_pp, 1)} pp<br>95% 区间 ${fmt(r.ci_low_pp, 1)} 至 ${fmt(r.ci_high_pp, 1)} pp`;
        },
      },
      series: MODEL_IDS.map((mid, i) => ({
        name: nameOf(data, mid),
        type: "scatter",
        symbolSize: 17,
        clip: false,
        itemStyle: {
          color: model(data, mid).color,
          opacity: 0.85,
          borderWidth: 2,
          borderColor: "#fff",
        },
        data: list
          .filter((r) => r.model_id === mid)
          .map((r) => ({
            value: [r.token_saving_pct, r.difference_pp],
            symbol: shapes[r.benchmark],
            raw: r,
            meta: { model: mid, task: r.benchmark },
            label:
              r.model_id === "qwen3" && r.benchmark === "math500"
                ? {
                    show: true,
                    position: "top",
                    formatter: "Qwen3 · MATH500",
                    fontSize: 11,
                    color: model(data, mid).color,
                    distance: 12,
                  }
                : { show: false },
          })),
        markLine:
          i === 0
            ? {
                silent: true,
                symbol: "none",
                lineStyle: { type: "dashed", color: "#b4bfce" },
                label: {
                  show: true,
                  position: "insideEndTop",
                  formatter: "评分不变",
                  fontSize: 11,
                  color: muted,
                },
                data: [{ yAxis: 0 }],
              }
            : undefined,
      })),
    },
    onPick,
  );
}
function nameOf(data, id) {
  return model(data, id)?.name || id;
}
function positionFacet(id, data, state, mid, onPick) {
  const all = selectCells(data, state),
    allRates = [];
  for (const m of ["qwen", "qwen3"])
    for (const docs of [10, 20])
      for (const pos of ["front", "middle", "back"])
        allRates.push(
          aggregate(
            all.filter(
              (c) =>
                c.model === m && c.documents === docs && c.position === pos,
            ),
            state.metric,
          ).rate * 100,
        );
  const min = Math.max(0, Math.floor((Math.min(...allRates) - 5) / 10) * 10),
    max = Math.min(100, Math.ceil((Math.max(...allRates) + 5) / 10) * 10);
  mount(
    id,
    {
      grid: { left: 58, right: 63, top: 38, bottom: 53 },
      xAxis: {
        type: "category",
        data: ["前部", "中部", "尾部"],
        axisLine: { lineStyle: { color: "#dbe3ee" } },
        axisTick: { show: false },
        axisLabel: { fontSize: 13, color: ink, margin: 16 },
      },
      yAxis: {
        ...axis("命中 / 匹配率（%）"),
        min,
        max,
        interval: 10,
        nameLocation: "end",
        nameTextStyle: { fontSize: 11, align: "left", color: muted },
        nameGap: 18,
        axisLabel: { fontSize: 12, color: muted },
      },
      tooltip: {
        ...base().tooltip,
        trigger: "axis",
        valueFormatter: (v) => fmt(v, 2) + "%",
      },
      series: [10, 20].map((docs, i) => ({
        type: "line",
        name: docs + " 篇",
        symbol: "circle",
        symbolSize: 8,
        lineStyle: { width: 2.5, color: i ? "#f59f00" : "#4263eb" },
        itemStyle: {
          color: i ? "#f59f00" : "#4263eb",
          borderColor: "#fff",
          borderWidth: 1,
        },
        endLabel: {
          show: true,
          formatter: docs + " 篇",
          fontSize: 11,
          color: i ? "#f59f00" : "#4263eb",
          distance: 10,
          offset: [0, i ? 7 : -7],
        },
        data: ["front", "middle", "back"].map((position) => ({
          value:
            aggregate(
              all.filter(
                (c) =>
                  c.model === mid &&
                  c.documents === docs &&
                  c.position === position,
              ),
              state.metric,
            ).rate * 100,
          meta: { model: mid, documents: docs, position, prompt: state.prompt },
        })),
      })),
    },
    onPick,
  );
}
function positionIntervals(id, data, contrasts, onPick) {
  const selected = [];
  for (const mid of ["qwen", "qwen3"])
    for (const first of ["front", "back"]) {
      const r = contrasts.find(
        (r) => r.model_id === mid && r.first === first && r.second === "middle",
      );
      if (r) selected.push(r);
    }
  const min =
      Math.floor(Math.min(0, ...selected.map((r) => r.ci_low_pp)) / 5) * 5,
    max = Math.ceil(Math.max(0, ...selected.map((r) => r.ci_high_pp)) / 5) * 5;
  const points = selected.map((r, i) => ({
    value: [r.difference_pp, i, r.ci_low_pp, r.ci_high_pp],
    raw: r,
    meta: { model: r.model_id },
    itemStyle: { color: r.first === "front" ? "#6984bb" : "#b9c5d7" },
  }));
  mount(
    id,
    {
      grid: { left: 172, right: 90, top: 35, bottom: 60 },
      xAxis: {
        ...axis("相对中部的命中 / 匹配率差（pp）"),
        min,
        max,
        nameGap: 36,
        axisLabel: { fontSize: 12, color: muted },
      },
      yAxis: {
        type: "category",
        inverse: true,
        data: selected.map(
          (r) =>
            `${nameOf(data, r.model_id).replace(" 7B", "").replace(" 8B", "")} · ${r.first === "front" ? "前−中" : "尾−中"}`,
        ),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: ink, fontSize: 12, margin: 20 },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) => {
          const r = p.data.raw;
          return `${esc(nameOf(data, r.model_id))}<br>差值 ${fmt(r.difference_pp, 2)} pp<br>95% 区间 ${fmt(r.ci_low_pp, 2)} 至 ${fmt(r.ci_high_pp, 2)} pp<br>200 道同题`;
        },
      },
      series: [
        {
          type: "custom",
          silent: true,
          renderItem: (p, api) => {
            const a = api.coord([api.value(2), api.value(1)]),
              b = api.coord([api.value(3), api.value(1)]);
            return {
              type: "group",
              children: [
                {
                  type: "line",
                  shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] },
                  style: { stroke: "#b4c2d7", lineWidth: 2 },
                },
                {
                  type: "line",
                  shape: { x1: a[0], y1: a[1] - 5, x2: a[0], y2: a[1] + 5 },
                  style: { stroke: "#b4c2d7" },
                },
                {
                  type: "line",
                  shape: { x1: b[0], y1: b[1] - 5, x2: b[0], y2: b[1] + 5 },
                  style: { stroke: "#b4c2d7" },
                },
              ],
            };
          },
          data: points,
        },
        {
          type: "scatter",
          symbolSize: 12,
          data: points,
          label: {
            show: true,
            fontSize: 13,
            color: "#7187aa",
            position: "top",
            distance: 13,
            formatter: (p) =>
              (p.data.raw.difference_pp > 0 ? "+" : "") +
              fmt(p.data.raw.difference_pp, 2),
          },
          markLine: {
            silent: true,
            symbol: "none",
            label: { show: false },
            lineStyle: { color: "#d5dce7", type: "dashed" },
            data: [{ xAxis: 0 }],
          },
        },
      ],
    },
    onPick,
  );
}

function overviewPrompts(id, data, onPick) {
  const prompts = ["NoCoT", "DefaultCoT", "BeConcise"],
    colors = ["#c4cedf", "#4263eb", "#12a89d"];
  const cells = (mid, prompt) =>
    aggregate(
      selectCells(data, {
        dataset: "reasoning",
        models: [mid],
        task: "gsm8k",
        prompt,
        documents: "all",
        position: "all",
      }),
    );
  mount(
    id,
    {
      grid: { left: 48, right: 20, top: 35, bottom: 75 },
      legend: {
        bottom: 6,
        itemWidth: 9,
        itemHeight: 9,
        textStyle: { color: ink, fontSize: 10 },
        data: prompts.map(promptName),
      },
      xAxis: {
        type: "category",
        data: MODEL_IDS.map((mid) =>
          model(data, mid)
            .name.replace("DeepSeek Flash", "DeepSeek")
            .replace("HY4 preview", "HY4")
            .replace("Qwen2.5 7B", "Qwen2.5")
            .replace("Qwen3 8B", "Qwen3"),
        ),
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { fontSize: 11, color: ink, interval: 0, margin: 12 },
      },
      yAxis: {
        ...axis("规则评分（%）"),
        min: 0,
        max: 100,
        interval: 25,
        nameLocation: "end",
        nameGap: 15,
        nameTextStyle: { align: "left", fontSize: 10, color: muted },
        axisLabel: { fontSize: 10, color: muted, formatter: "{value}%" },
      },
      tooltip: {
        ...base().tooltip,
        formatter: (p) => {
          const r = p.data.raw;
          return `${esc(nameOf(data, p.data.meta.model))}<br>${esc(p.seriesName)}：${pct(r.rate)}<br>${fmt(r.score)} / ${r.n} 次评分通过`;
        },
      },
      series: prompts.map((prompt, i) => ({
        name: promptName(prompt),
        type: "bar",
        barMaxWidth: 22,
        barGap: "12%",
        itemStyle: { color: colors[i], borderRadius: [3, 3, 0, 0] },
        data: MODEL_IDS.map((mid) => {
          const a = cells(mid, prompt);
          return { value: a.rate * 100, raw: a, meta: { model: mid, prompt } };
        }),
      })),
    },
    onPick,
  );
}

function behaviorMatrix(id,families,styles,cells,selection,onPick) {
  mount(id,{
    media:[{query:{maxWidth:500},option:{grid:{left:105,right:15},title:{left:0,textStyle:{fontSize:15}},xAxis:{axisLabel:{fontSize:10,rotate:35}},yAxis:{axisLabel:{fontSize:10}}}}],
    title:{text:"提示约束与实际输出形态",left:20,top:8,textStyle:{fontFamily:font,fontSize:17,color:ink,fontWeight:600}},
    grid:{left:130,right:35,top:62,bottom:96},
    xAxis:{type:"category",data:styles,axisTick:{show:false},axisLine:{show:false},axisLabel:{interval:0,rotate:22,fontSize:12,color:ink}},
    yAxis:{type:"category",data:families,inverse:true,axisTick:{show:false},axisLine:{show:false},axisLabel:{fontSize:12,color:ink}},
    visualMap:{min:0,max:100,calculable:false,orient:"horizontal",left:"center",bottom:8,itemWidth:14,itemHeight:130,text:["100%","0%"],inRange:{color:["#f5f2fa","#c9b8dd","#8958b4","#4c2678"]},textStyle:{fontFamily:font,color:ink}},
    tooltip:{formatter:p=>`${families[p.value[1]]}<br>${styles[p.value[0]]}<br>${fmt(p.data.n)} / ${fmt(p.data.total)} 次响应 (${fmt(p.value[2],1)}%)`},
    series:[{type:"heatmap",data:cells.map(c=>({...c,label:{color:c.value[2]>=55?"#fff":"#252830"},itemStyle:{borderWidth:selection?.family===c.meta.family&&selection?.style===c.meta.style?2:1,borderColor:selection?.family===c.meta.family&&selection?.style===c.meta.style?"#252830":"#fff"}})),label:{show:true,formatter:p=>`${fmt(p.value[2],0)}%`,fontFamily:font,fontSize:11,color:"#252830"},emphasis:{itemStyle:{borderColor:"#252830",borderWidth:2}}}]
  },onPick);
}
function behaviorStates(id,items,total,onPick) {
  mount(id,{
    media:[{query:{maxWidth:500},option:{grid:{left:130,right:50,top:60,bottom:55},title:{left:0,textStyle:{fontSize:15}},yAxis:{axisLabel:{fontSize:11}}}}],
    title:{text:"点选条件的结束状态",left:20,top:8,textStyle:{fontFamily:font,fontSize:17,color:ink,fontWeight:600}},
    grid:{left:145,right:70,top:75,bottom:85},
    xAxis:{...axis("响应占比 (%)"),min:0,max:100},
    yAxis:{type:"category",data:items.map(r=>r.label),inverse:true,axisLine:{show:false},axisTick:{show:false},axisLabel:{fontSize:12,color:ink}},
    tooltip:{formatter:p=>`${items[p.dataIndex].label}<br>${fmt(items[p.dataIndex].n)} / ${fmt(total)} 次响应`},
    series:[{type:"bar",barMaxWidth:36,data:items.map(r=>({value:total?r.n/total*100:0,meta:{status:r.key}})),itemStyle:{color:"#8958b4"},label:{show:true,position:"right",formatter:p=>`${fmt(p.value,1)}%`,fontFamily:font,color:ink}}]
  },onPick);
}

return {disposeCharts,resizeCharts,mount,exportChart,emptyChart,modelBars,radar,bubble,radial,heatmap,positionLines,controlsBars,metricComparison,disagreement,truncationBars,reasoningStatus,codingBars,codingErrors,heroGain,boxplot,parallel,distribution,retryTimeline,retryTree,codingEventDistribution,codingScatter,codingTree,lengthHistogram,promptCase,efficiencyCase,positionFacet,positionIntervals,overviewPrompts,behaviorMatrix,behaviorStates};
})();
const _codeInteractions = (() => {
const {esc, fmt, pct} = _model;
const libraries = _libraries;

let generation=0, cleanups=[], selection=[], snapshotExport=null,stopPlayback=null;
const names={deepseek:'DeepSeek Flash',qwen:'Qwen2.5 7B',qwen3:'Qwen3 8B'};
const errors={assertion_failure:'Assertion failure',attribute_error:'Attribute error',type_error:'Type error',syntax_error:'Syntax error',extraction_error:'Extraction error',dependency_error:'Dependency error',name_error:'Name error',timeout:'Timeout',runtime_error:'Runtime error',file_error:'File error',index_error:'Index error',key_error:'Key error',value_error:'Value error',resource_error:'Resource error'};
const namespace='http://www.w3.org/2000/svg';
function pause(){stopPlayback?.();document.querySelectorAll(".code-hover-tip").forEach(el=>{el.hidden=true;});}
function dispose(){generation++;stopPlayback=null;for(const f of cleanups.splice(0))f();document.querySelector('.code-hover-tip')?.remove();snapshotExport=null;}
function selectedConditions(){return selection.map(r=>({model:r.model,prompt:r.prompt}));}
function svgSnapshot(){return snapshotExport?.() || null;}
function playbackControls(step=5){return `<div class="code-playback"><button id="code-play" class="text-action" aria-pressed="false" disabled><svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M6 3.5 16 10 6 16.5Z"/></svg><span>播放</span></button><label for="code-sample-step">独立采样</label><input id="code-sample-step" type="range" min="1" max="5" step="1" value="${step}" aria-valuetext="显示至第 ${step} 次"><output id="code-sample-label" for="code-sample-step">${step} / 5</output><div id="code-sample-values" class="code-sample-values" aria-live="polite"></div></div>`;}
function tokenTools(brush){return `<span class="code-gesture-note">拖动框选条件 · 双击清除</span><button class="text-action" id="code-clear-brush" ${brush?'':'hidden'}>清除框选</button>`;}
function numericControls(brush,categories,labels){const b=brush || [0,700,0,100];return `<details class="code-numeric-filter"><summary>精确范围筛选</summary><form id="code-range-form"><label>最少 token<input name="xmin" type="number" min="0" step="any" value="${b[0]}" required></label><label>最多 token<input name="xmax" type="number" min="0" step="any" value="${b[1]}" required></label><label>最低通过率 %<input name="ymin" type="number" min="0" max="100" step="any" value="${b[2]}" required></label><label>最高通过率 %<input name="ymax" type="number" min="0" max="100" step="any" value="${b[3]}" required></label><button class="text-action" type="submit">应用范围</button><button class="text-action" id="code-reset-range" type="button">全部条件</button></form><div class="code-error-keyboard"><label for="code-keyboard-error">错误类型</label><select id="code-keyboard-error" class="form-select form-select-sm">${categories.map(c=>`<option value="${c}">${esc(labels[c] || c)}</option>`).join('')}</select><button class="text-action" id="code-keyboard-error-open">查看错误记录</button></div></details>`;}
function makeTip(){const el=document.createElement('div');el.className='code-hover-tip';el.setAttribute('role','tooltip');el.hidden=true;document.body.append(el);return el;}
function showTip(el,event,html){el.innerHTML=html;el.hidden=false;const box=el.getBoundingClientRect();el.style.left=Math.max(8,Math.min((event?.clientX || 40)+14,window.innerWidth-box.width-12))+'px';el.style.top=Math.max(8,Math.min((event?.clientY || 80)+14,window.innerHeight-box.height-12))+'px';}
function viewText(svg){const clone=svg.cloneNode(true);clone.querySelectorAll('[tabindex]').forEach(e=>e.removeAttribute('tabindex'));clone.setAttribute('xmlns',namespace);return new XMLSerializer().serializeToString(clone);}
async function enhanceStatic(root){
 const ticket=generation;
 try{const d3=await libraries.load('d3');if(ticket!==generation || !root.isConnected)return;
  const tip=makeTip();const svg=root.querySelector('#code-publication > svg');if(!svg)return;
  const items=d3.select(svg).selectAll('[data-code-model]');
  const focus=model=>{
   items.each(function(){const other=this.dataset.codeModel!==model;d3.select(this).style('opacity',other?.25:1);const hit=this.id.endsWith('-hit');if(hit)d3.select(this).selectAll('path').style('fill',other?'white':'black').style('fill-opacity',other?.7:.001);});
   d3.select(svg).selectAll('[id^="code-trend-"], [id^="code-band-"]').style('opacity',function(){return this.id.endsWith(model)?1:.18;});
  };
  const clear=()=>{tip.hidden=true;items.style('opacity',null);items.filter(function(){return this.id.endsWith('-hit');}).selectAll('path').style('fill',null).style('fill-opacity',null);d3.select(svg).selectAll('[id^="code-trend-"], [id^="code-band-"]').style('opacity',null);};
  items.on('pointerenter.focus',function(event){focus(this.dataset.codeModel);showTip(tip,event,esc(this.dataset.codeLabel || this.getAttribute('aria-label') || ''));}).on('pointermove.focus',function(event){showTip(tip,event,esc(this.dataset.codeLabel || this.getAttribute('aria-label') || ''));}).on('pointerleave.focus',clear).on('focus.focus',function(){focus(this.dataset.codeModel);}).on('blur.focus',clear);
  cleanups.push(()=>{items.on('.focus',null);tip.remove();});
 }catch{ /* The original SVG and record controls remain usable. */ }
}
async function enhanceSampling(root,state,data,onStep){
 const ticket=generation,svg=root.querySelector('#code-publication > svg');
 if(!svg)return;
 let d3;try{d3=await libraries.load('d3');}catch{return;}
 if(ticket!==generation || !root.isConnected)return;
 const button=root.querySelector('#code-play'),slider=root.querySelector('#code-sample-step'),out=root.querySelector('#code-sample-label'),values=root.querySelector('#code-sample-values');
 const points=[...svg.querySelectorAll('[id^="pass-"]')];const xs=[0,1,2,3,4].map(i=>+(points.find(p=>p.id.endsWith('-'+i))?.querySelector('use')?.getAttribute('x') || 0));
 if(xs.some(x=>!Number.isFinite(x)) || xs[4]<=xs[0])return;
 const clipId='code-reveal-'+ticket;const defs=d3.select(svg).append('defs');const clip=defs.append('clipPath').attr('id',clipId).attr('clipPathUnits','userSpaceOnUse').append('rect').attr('x',xs[0]-8).attr('y',0).attr('height',10000);
 d3.select(svg).selectAll('[id^="code-trend-"], [id^="code-band-"]').attr('clip-path','url(#'+clipId+')');
 let step=state.step || 5, timer=null;
 const stop=()=>{if(timer)clearInterval(timer);timer=null;button.setAttribute('aria-pressed','false');button.querySelector('span').textContent='播放';button.querySelector('svg').innerHTML='<path d="M6 3.5 16 10 6 16.5Z"/>';};
 const draw=(next,animate=true)=>{
  step=next;slider.value=step;slider.setAttribute('aria-valuetext','显示至第 '+step+' 次');out.value=step+' / 5';out.textContent=step+' / 5';
  const width=xs[step-1]-xs[0]+16;clip.interrupt('reveal');
  if(animate && !libraries.reducedMotion())clip.transition('reveal').duration(260).ease(d3.easeCubicOut).attr('width',width);else clip.attr('width',width);
  d3.select(svg).selectAll('[id^="pass-"], [id^="gain-"], [id^="code-lastgain-"]').each(function(){let sample=this.id.startsWith('pass-')?+this.id.split('-').at(-1)+1:this.id.startsWith('gain-')?+this.id.split('-').at(-1):5;const hidden=sample>step;d3.select(this).style('visibility',hidden?'hidden':null).attr('aria-hidden',hidden?'true':null);if(this.hasAttribute('data-code-action'))this.setAttribute('tabindex',hidden?'-1':'0');});
  const ms=state.model==='all'?data.models.map(m=>m.id):[state.model];values.innerHTML=`<span>Pass@${step}</span>`+ms.map(mid=>{const r=data.stats.find(r=>r.model===mid && r.prompt===state.prompt),m=data.models.find(m=>m.id===mid);return `<span title="${esc(m.name)}"><i style="background:${m.color}"></i><span class="visually-hidden">${esc(m.name)}</span><strong>${pct(r.pass[step-1],2)}</strong></span>`;}).join('');
  onStep(step);
 };
 stopPlayback=stop;
 const visibleObserver=new IntersectionObserver(entries=>{if(!entries[0].isIntersecting)stop();});visibleObserver.observe(root.querySelector(".code-playback"));cleanups.push(()=>visibleObserver.disconnect());
 button.disabled=false;button.onclick=()=>{if(timer){stop();return;}if(step===5)draw(1,false);button.setAttribute('aria-pressed','true');button.querySelector('span').textContent='暂停';button.querySelector('svg').innerHTML='<path d="M6 4v12M14 4v12"/>';timer=setInterval(()=>{if(document.hidden){stop();return;}draw(Math.min(5,step+1));if(step===5)stop();},1100);};
 slider.oninput=()=>{stop();draw(+slider.value);};
 const onVisibility=()=>{if(document.hidden)stop();};document.addEventListener('visibilitychange',onVisibility);
 draw(step,false);snapshotExport=()=>{stop();clip.interrupt('reveal').attr('width',xs[step-1]-xs[0]+16);return viewText(svg);};
 cleanups.push(()=>{stop();clip.interrupt('reveal');document.removeEventListener('visibilitychange',onVisibility);});
}
function pointsFor(data,k){return data.stats.filter(r=>r.prompt!=='__all').map(r=>({model:r.model,model_name:names[r.model],prompt:r.prompt,tokens:r.mean_output_tokens,score:r.pass[k-1]*100,extraction:(r.errors.extraction_error || 0)/r.n*100,n:r.n}));}
function selectionFor(data,k,brush){return data.stats.filter(r=>r.prompt!=='__all' && (!brush || (r.mean_output_tokens>=brush[0] && r.mean_output_tokens<=brush[1] && r.pass[k-1]*100>=brush[2] && r.pass[k-1]*100<=brush[3])));}
function compositeSvg(left,right,summary){const w=1600,h=650;return `<svg xmlns="${namespace}" xmlns:xlink="http://www.w3.org/1999/xlink" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><rect width="100%" height="100%" fill="white"/><text x="40" y="35" font-family="Times New Roman" font-size="23" font-weight="bold">Output length, test performance and failure rates</text><svg x="25" y="60" width="970" height="510" viewBox="0 0 ${left.getAttribute('width')} ${left.getAttribute('height')}">${left.innerHTML}</svg><text x="1015" y="83" font-family="Times New Roman" font-size="18" font-weight="bold">Failure rates</text><svg x="1015" y="60" width="560" height="510" viewBox="0 0 ${right.getAttribute('width')} ${right.getAttribute('height')}">${right.innerHTML}</svg><text x="45" y="595" font-family="Times New Roman" font-size="15">${esc(summary)}</text><text x="45" y="624" font-family="Times New Roman" font-size="13" fill="#60606a">Source: code-generation@9dfc592. 193 matched tasks; 5 independent samples. Environment exclusions omitted. Exploratory selection.</text></svg>`;}
async function enhanceTokens(root,state,data,callbacks){
 const ticket=generation,host=root.querySelector('#code-publication');
 selection=selectionFor(data,state.k,state.brush);
 let vega,vl;try{vega=await libraries.load('vega');vl=await libraries.load('vegaLite');}catch(e){callbacks.onUnavailable(e.message);return;}
 if(ticket!==generation || !root.isConnected)return;
 const nodes=pointsFor(data,state.k), ymax=Math.max(50,Math.ceil(Math.max(...nodes.map(r=>r.score))/10)*10);
 const spec=JSON.parse(JSON.stringify(data.scatter_spec));spec.data={values:nodes};spec.encoding.y.axis.title=`Pass@${state.k} (%)`;spec.encoding.y.scale.domain=[0,ymax];
 if(state.brush)spec.params[0].value={x:state.brush.slice(0,2),y:state.brush.slice(2,4)};
 const scaffold=document.createElement('div');scaffold.className='code-linked-surface';scaffold.innerHTML='<div class="code-scatter-panel"><h2>Output length and test performance</h2><div id="code-vega-scatter"></div></div><div class="code-error-panel"><h2>Failure rates</h2><div id="code-linked-errors" role="img" aria-label="所选条件的错误率，点柱查看对应评分"></div></div><p class="code-linked-summary" id="code-brush-summary" role="status" aria-live="polite"></p>';
 let compiled;try{compiled=vl.compile(spec).spec;}catch(e){callbacks.onUnavailable(e.message);return;}
 host.replaceChildren(scaffold);host.classList.add('code-interactive-host');
 const chart=window.echarts.init(scaffold.querySelector('#code-linked-errors'),null,{renderer:'svg'});
 const tip=makeTip();let pending=null,persistTimer=null,dragStart=null,disposed=false;
 const view=new vega.View(vega.parse(compiled),{renderer:'svg',hover:true}).initialize(scaffold.querySelector('#code-vega-scatter'));
 const refresh=()=>{
  if(disposed)return;selection=selectionFor(data,state.k,state.brush);const n=selection.reduce((a,r)=>a+r.n,0);const mean=n?selection.reduce((a,r)=>a+r.pass[state.k-1],0)/selection.length:0;
  const cats=data.error_categories.map(cat=>({cat,count:selection.reduce((a,r)=>a+(r.errors[cat] || 0),0)})).sort((a,b)=>b.count-a.count);
  const summary=`${selection.length} / 93 个条件 · ${fmt(n)} 条可评回答${n?` · 平均 Pass@${state.k} ${pct(mean,2)}`:''}`;
  scaffold.querySelector('#code-brush-summary').textContent=summary;callbacks.onSelection(selection,state.brush);
  chart.setOption({aria:{enabled:true,description:`${selection.length} 个条件、${n} 条可评回答。`+cats.map(r=>`${errors[r.cat]} ${r.count} 条，${n?(r.count/n*100).toFixed(2):0}%。`).join(' ')},animation:!libraries.reducedMotion(),animationDuration:0,animationDurationUpdate:220,textStyle:{fontFamily:'Times New Roman',color:'#353842',fontSize:12},grid:{left:128,right:20,top:51,bottom:53},xAxis:{type:'value',min:0,max:100,name:'Share of selected responses (%)',nameLocation:'middle',nameGap:30,nameTextStyle:{fontSize:12},axisLabel:{fontSize:11},splitLine:{lineStyle:{color:'#e8e7ed'}}},yAxis:{type:'category',inverse:true,data:cats.map(r=>errors[r.cat]),axisLine:{show:false},axisTick:{show:false},axisLabel:{fontSize:12,color:'#54545b'}},tooltip:{confine:true,backgroundColor:'#fff',borderColor:'#e5e3eb',textStyle:{color:'#252830',fontFamily:'Times New Roman',fontSize:12},formatter:p=>`${esc(errors[cats[p.dataIndex].cat])}<br>${fmt(cats[p.dataIndex].count)} / ${fmt(n)} (${pct(n?cats[p.dataIndex].count/n:0,1)})`},series:[{id:'selected-errors',type:'bar',barMaxWidth:13,data:cats.map(r=>({value:n?r.count/n*100:0,category:r.cat,itemStyle:{color:r.cat==='extraction_error'?'#8958b4':'#a9a1b9'}})),emphasis:{itemStyle:{color:'#65428d'}}}]});
  chart.off('click');chart.on('click',p=>{if(p.data?.category)callbacks.onRecords({conditions:selectedConditions(),error:p.data.category},errors[p.data.category]+' / 框选条件');});
  snapshotExport=()=>{const left=scaffold.querySelector('#code-vega-scatter svg'),right=scaffold.querySelector('#code-linked-errors svg');return left && right?compositeSvg(left,right,summary):null;};
 };
 const schedule=value=>{
  const x=value?.tokens || value?.x,y=value?.score || value?.y;
  state.brush=Array.isArray(x) && Array.isArray(y) && x.length===2 && y.length===2 && x[0]!==x[1] && y[0]!==y[1]?[...x,...y].map(v=>+v.toFixed(6)):null;
  if(pending)cancelAnimationFrame(pending);pending=requestAnimationFrame(()=>{pending=null;refresh();});
  callbacks.onState({...state},false);if(persistTimer)clearTimeout(persistTimer);persistTimer=setTimeout(()=>callbacks.onState({...state},true),140);
 };
 view.addSignalListener('codeBrush',(_,value)=>schedule(value));
 view.addEventListener('pointerdown',event=>{dragStart=[event.clientX,event.clientY];});
 view.addEventListener('pointerup',()=>{if(persistTimer)clearTimeout(persistTimer);queueMicrotask(()=>{if(!disposed)callbacks.onState({...state},true);});});
 view.addEventListener('click',(event,item)=>{const r=item?.datum;if(r?.model && r?.prompt && (!dragStart || Math.hypot(event.clientX-dragStart[0],event.clientY-dragStart[1])<4)){tip.hidden=true;callbacks.onCondition({model:r.model,prompt:r.prompt,k:state.k});}});
 view.addEventListener('pointermove',(event,item)=>{const r=item?.datum;if(r?.model && r?.prompt)showTip(tip,event,`<strong>${esc(r.model_name)}</strong><br>${esc(r.prompt)}<br>${fmt(r.tokens,1)} output tokens · Pass@${state.k} ${fmt(r.score,2)}%<br>Extraction failure ${fmt(r.extraction,1)}%`);else tip.hidden=true;});
 view.addEventListener('pointerout',()=>{tip.hidden=true;});
 cleanups.push(()=>{disposed=true;if(pending)cancelAnimationFrame(pending);if(persistTimer)clearTimeout(persistTimer);view.finalize();chart.dispose();tip.remove();});
 try{await view.runAsync();if(ticket!==generation || !root.isConnected)return;refresh();}catch(e){callbacks.onUnavailable(e.message);return;}
 const observer=new ResizeObserver(()=>{if(!disposed)chart.resize();});observer.observe(scaffold);cleanups.push(()=>observer.disconnect());
 // Native buttons are available when direct manipulation is inconvenient.
 const svg=scaffold.querySelector('#code-vega-scatter svg');if(svg){svg.setAttribute('role','img');svg.setAttribute('aria-label','93 个模型与提示条件。拖动框选；精确范围筛选提供键盘替代。');}
}

return {pause,dispose,selectedConditions,svgSnapshot,playbackControls,tokenTools,numericControls,enhanceStatic,enhanceSampling,enhanceTokens};
})();
const _codeStudy = (() => {
const { esc, fmt, pct, signed, csvString, promptName } = _model;
const interact = _codeInteractions;
const libraries = _libraries;

const D = window.COURSE_CODE;
const VIEWS = {sampling:"采样收益",prompts:"提示差异",errors:"错误类型",tokens:"输出开销"};
const ERROR_LABELS = {assertion_failure:"测试断言失败",attribute_error:"属性或接口错误",type_error:"类型错误",syntax_error:"语法错误",extraction_error:"代码提取失败",dependency_error:"依赖错误",name_error:"名称未定义",timeout:"执行超时",runtime_error:"其他运行错误",file_error:"文件错误",index_error:"索引错误",key_error:"键错误",value_error:"值错误",resource_error:"资源限制",environment_error:"环境排除",success:"测试通过"};
let previousSignature;
let featurePromise, featureRows=[], activeRecords=[], recordPage=0, environment, currentState;
const name=(m)=>D?.models.find(r=>r.id===m)?.name || m;
const label=(p)=>p==="__all"?"全部 31 种提示":promptName(p);
const stat=(m,p="__all")=>D.stats.find(r=>r.model===m && r.prompt===p);
const button=(action,text)=>`<button class="text-action" data-code-action="${action}">${text}</button>`;
const form=(id,title,options,value)=>`<label for="${id}">${title}<select class="form-select form-select-sm" id="${id}">${options.map(([v,t])=>`<option value="${v}" ${String(value)===String(v)?"selected":""}>${esc(t)}</option>`).join("")}</select></label>`;
const icon=()=>'<img src="assets/ui/download.svg" width="17" height="17" alt="">';

function parseBrush(value){if(!value)return null;const b=value.split(",").map(Number);return b.length===4 && b.every(Number.isFinite) && b[0]>=0 && b[0]<b[1] && b[2]>=0 && b[2]<b[3] && b[3]<=100?b:null;}
function disposeCodeStudy(){interact.dispose();}
function codeRoute(params) {
 return {view:Object.hasOwn(VIEWS,params.get("codeView"))?params.get("codeView"):"sampling",
  model:["all","deepseek","qwen","qwen3"].includes(params.get("codeModel"))?params.get("codeModel"):"all",
  prompt:D?.prompts.includes(params.get("codePrompt"))?params.get("codePrompt"):"__all",
  k:["0","1","3","5"].includes(params.get("codeK"))?+params.get("codeK"):1,
  scope:params.get("codeScope")==="all"?"all":"core",
  error:D?.error_categories.includes(params.get("codeError"))?params.get("codeError"):"extraction_error",
  step:[1,2,3,4,5].includes(+params.get("codeStep"))?+params.get("codeStep"):5,
  brush:parseBrush(params.get("codeBrush"))};
}
function codeQuery(s) {
 const p=new URLSearchParams();p.set("codeView",s.view);
 if(s.view==="sampling"){p.set("codeModel",s.model);p.set("codePrompt",s.prompt);if(s.step!==5)p.set("codeStep",s.step);}
 if(["prompts","tokens"].includes(s.view))p.set("codeK",s.k);
 if(["prompts","errors"].includes(s.view))p.set("codeScope",s.scope);
 if(s.view==="errors")p.set("codeError",s.error);
 if(s.view==="tokens" && s.brush)p.set("codeBrush",s.brush.join(","));
 return p;
}
function figureKey(s) {
 if(s.view==="sampling")return `code-sampling-${s.model}-${s.prompt==="__all"?"all":D.prompts.indexOf(s.prompt)}`;
 if(s.view==="prompts")return `code-prompts-${s.k}-${s.scope}`;
 if(s.view==="errors")return `code-errors-${s.error}-${s.scope}`;
 return `code-tokens-${s.k || 1}`;
}
function caption(s) {
 if(s.view==="sampling"){
  if((s.step || 5)<5)return `<h2>逐次查看独立采样的覆盖变化。</h2><p>当前显示至第 ${s.step} 次；每个点都是由五次已保存结果计算的 Pass@k 估计，右侧为固定次序中的新增成功。采样之间没有测试反馈。</p>`;
  const ms=s.model==="all"?D.models.map(m=>m.id):[s.model];
  const gains=ms.map(m=>stat(m,s.prompt).marginal[3]*100);
  return `<h2>${s.prompt==="__all"?"第 5 次独立生成，新增收益已明显收窄。":"当前提示下的独立采样收益。"}</h2><p>当前范围的第 5 次新增为 ${fmt(Math.min(...gains),2)}${gains.length>1?`–${fmt(Math.max(...gains),2)}`:""} 个百分点。左图估计任取 k 个答案至少一个通过的概率；右图按本次实际生成次序统计新增。</p>`;
 }
 if(s.view==="prompts"){
  const k=s.k || 1;const values=D.models.map(m=>{const r=D.contrasts.find(r=>r.model===m.id && r.prompt==='DefaultCoT');return `${m.name} ${signed(r.difference[k-1]*100,2)} pp`;});
  return `<h2>同一提示，对不同模型的作用方向也会改变。</h2><p>右图 DefaultCoT 相对 NoCoT 的 Pass@${k}：${values.join('，')}。区间按题配对；Qwen3 的差异还包含代码提取是否成功。</p>`;
 }
 if(s.view==="errors" && s.error!=="extraction_error"){
  const candidates=D.stats.filter(r=>r.prompt!=="__all" && (s.scope==="all" || D.core.includes(r.prompt))).map(r=>({...r,rate:(r.errors[s.error] || 0)/r.n})).sort((a,b)=>b.rate-a.rate);const r=candidates[0];
  return `<h2>${esc(ERROR_LABELS[s.error])}在不同提示条件下的分布。</h2><p>当前展示范围中，最高为 ${esc(name(r.model))} / ${esc(r.prompt)}：${pct(r.rate,1)}。每个提示×模型条件的分母均为 965 条可评回答。</p>`;
 }
 if(s.view==="errors")return `<h2>格式压力会影响能否得到可提取的 Python 函数。</h2><p>环境排除后，Qwen2.5 / NoProperGrammar 的提取失败为 ${pct(stat('qwen','NoProperGrammar').errors.extraction_error/stat('qwen','NoProperGrammar').n,1)}；Qwen3 / OnlyNumbers 为 ${pct(stat('qwen3','OnlyNumbers').errors.extraction_error/stat('qwen3','OnlyNumbers').n,1)}。分母为各条件的 965 条可评回答。</p>`;
 if(s.view==='tokens' && s.brush){
  const b=s.brush,rs=D.stats.filter(r=>r.prompt!=='__all' && r.mean_output_tokens>=b[0] && r.mean_output_tokens<=b[1] && r.pass[s.k-1]*100>=b[2] && r.pass[s.k-1]*100<=b[3]);
  const n=rs.reduce((a,r)=>a+r.n,0);if(!n)return '<h2>这个范围内没有实测条件。</h2><p>扩大范围或清除框选，可返回全部 93 个模型与提示条件。</p>';
  const rates=D.error_categories.map(error=>({error,count:rs.reduce((a,r)=>a+(r.errors[error] || 0),0)})).sort((a,b)=>b.count-a.count),top=rates[0];
  return `<h2>${top.error==='extraction_error' && top.count/n>.5?'所选范围的失败，主要集中在代码提取环节。':'结合输出开销，进一步区分失败发生的环节。'}</h2><p>${rs.length} 个条件中，${esc(ERROR_LABELS[top.error])}为 ${fmt(top.count)} / ${fmt(n)}（${pct(top.count/n,2)}）。这些条件由交互选择，属于探索性描述；点击右图可追溯对应评分。</p>`;
 }
 return '<h2>更多输出，没有对应统一的通过率提升。</h2><p>每个点保留模型与提示条件；开销采用返回 token，评分来自 193 道共同题。点选后可同时查看提取错误、截断和测试结果。</p>';
}
function tools(s){
 if(s.view==="sampling")return `<div class="model-tabs" role="group" aria-label="代码实验模型"><button data-code-model="all" aria-pressed="${s.model==="all"}">全部模型</button>${D.models.map(m=>`<button data-code-model="${m.id}" aria-pressed="${s.model===m.id}"><img src="assets/logos/${m.id==='deepseek'?'deepseek.svg':'qwen.svg'}" width="18" height="18" alt="">${esc(m.name)}</button>`).join("")}</div>${form("code-study-prompt","提示",[["__all","全部 31 种提示"],...D.prompts.map(p=>[p,label(p)])],s.prompt)}`;
 if(s.view==="prompts")return form("code-study-k","指标",[[1,"Pass@1"],[3,"Pass@3"],[5,"Pass@5"],[0,"Pass@5 − Pass@1"]],s.k)+form("code-study-scope","范围",[["core","8 种对照提示"],["all","全部 31 种提示"]],s.scope);
 if(s.view==="errors")return form("code-study-error","右图错误",D.error_categories.map(k=>[k,ERROR_LABELS[k] || k]),s.error)+form("code-study-scope","范围",[["core","8 种对照提示"],["all","全部 31 种提示"]],s.scope);
 return form("code-study-k","通过指标",[[1,"Pass@1"],[3,"Pass@3"],[5,"Pass@5"]],s.k)+interact.tokenTools(s.brush);
}
function method() {
 interact.pause();
 const rows=D.models.map(m=>{const s=stat(m.id);return `<tr><td>${esc(m.name)}</td>${[1,3,5].map(k=>`<td class="numeric">${pct(s.pass[k-1],2)}</td>`).join("")}</tr>`;}).join("");
 environment.openInspector("代码生成实验",`<p class="subline">CodePromptEval · code-generation@9dfc592</p><p>194 道保留题 × 31 种提示 × 5 次独立生成 × 3 个模型，共 90,210 条。共同排除 1 道环境预检不稳定的题，465 条记录保留但不进入性能分母；有效范围为 193 题、89,745 条。</p><h3>独立采样与 Pass@k</h3><p>每次生成都没有前次回答或测试反馈。Pass@k 使用全部 5 次已保存结果，估计任取 k 次至少一次通过的概率：1 − C(5−c,k)/C(5,k)。观测累计按本次次序计算，和 Pass@k 估计分别保留。k=2、4 由同一批结果计算。</p><table><thead><tr><th>模型</th><th>Pass@1</th><th>Pass@3</th><th>Pass@5</th></tr></thead><tbody>${rows}</tbody></table><h3>评分与区间</h3><p>保留 target-function-ast-v2 的单元测试结果；193 道题为重抽样簇，5,000 次、种子 91。置信区间未作多重比较校正。单元测试通过表示通过当前测试。此次接入没有调用模型，也没有重新执行生成代码。</p><h3>错误率分母</h3><p>图中的错误率以可评回答为分母。源交付部分错误表采用含环境排除的全部记录：Qwen2.5 / NoProperGrammar 为 94.5%，Qwen3 / OnlyNumbers 为 78.7%；换成可评口径分别为 95.0% 和 79.1%。环境记录未被计为模型错误。</p><h3>Prompt 适配</h3><p>长度与格式限制作用于代码前的可选说明，完整 Python 代码要求保持一致。31 种提示的探索性排名取决于模型和当前题集。</p><div class="record-actions">${button("export-summary","导出当前统计 CSV")}${button("excluded","查看 465 条环境排除")}</div>`);
 wireActions(document.getElementById("inspector-body"));
}
async function loadFeatures() {
 if(!featurePromise)featurePromise=new Promise((resolve,reject)=>{
  if(window.COURSE_CODE_FEATURES)return resolve(window.COURSE_CODE_FEATURES);
  const script=document.createElement("script");script.src="runtime/code-features.js?v="+encodeURIComponent(D.feature_version);
  script.onload=()=>window.COURSE_CODE_FEATURES?resolve(window.COURSE_CODE_FEATURES):reject(new Error("评分记录未能打开"));
  script.onerror=()=>reject(new Error("评分文件未找到，请重新启动系统"));document.head.append(script);
 }).then(p=>featureRows=p.rows.map(r=>Object.fromEntries(p.fields.map((k,i)=>[k,r[i]]))));
 return featurePromise;
}
function matches(r,q){return (!q.conditionKeys || q.conditionKeys.has(r.model+"|"+r.prompt)) && (!q.model || q.model==="all" || r.model===q.model) && (!q.prompt || q.prompt==="__all" || r.prompt===q.prompt) && (!q.question || r.question===q.question) && (!q.prompts || q.prompts.includes(r.prompt)) && (!q.error || r.error===q.error) && (q.excluded?r.environment_excluded:!r.environment_excluded);}
async function records(q,title) {
 interact.pause();
 if(q.conditions)q={...q,conditionKeys:new Set(q.conditions.map(r=>r.model+"|"+r.prompt))};
 environment.openInspector(title,'<p class="subline">正在打开已保存评分…</p>');
 try {
  let rs=(await loadFeatures()).filter(r=>matches(r,q));
  if(q.sample){
   const first=new Map();
   for(const r of await loadFeatures())if(r.passed && !r.environment_excluded){const key=r.model+'|'+r.question+'|'+r.prompt;first.set(key,Math.min(first.get(key) || 6,r.sample));}
   rs=rs.filter(r=>r.passed && r.sample===+q.sample && first.get(r.model+'|'+r.question+'|'+r.prompt)===+q.sample);
  }
  activeRecords=rs;recordPage=0;drawRecords(title,q);
 } catch(e){environment.openInspector("评分记录未能打开",`<p>${esc(e.message)}</p>`);}
}
function drawRecords(title,q){
 const pages=Math.max(1,Math.ceil(activeRecords.length/20));recordPage=Math.min(recordPage,pages-1);
 const text=q.excluded?'这些记录由共同环境规则排除，测试结果保留为空，不计为模型失败。':q.sample?'这里只列出该次独立采样首次通过的条件记录；采样之间没有测试反馈。':'同一题目、模型和提示下的 5 次是独立生成；采样序号不表示修复轮次。';
 environment.openInspector(title,`<p class="subline">${fmt(activeRecords.length)} 条已保存评分 · ${new Set(activeRecords.map(r=>r.question)).size} 道题</p><p>${text}</p><div class="table-wrap"><table><thead><tr><th>匿名记录</th><th>题号</th><th>采样</th><th>结果</th><th class="numeric">输出 token</th></tr></thead><tbody>${activeRecords.slice(recordPage*20,(recordPage+1)*20).map(r=>`<tr><td><button class="text-action" data-code-record="${r.id}" aria-label="查看评分 ${r.id}">${r.id}</button></td><td>${r.question}</td><td>${r.sample}</td><td>${esc(r.environment_excluded?'环境排除':r.passed?'通过':ERROR_LABELS[r.error] || r.error)}</td><td class="numeric">${fmt(r.output_tokens)}</td></tr>`).join("")}</tbody></table></div><div class="record-actions"><button class="plain-button" id="code-export-records">导出筛选</button><button class="plain-button" id="code-previous" ${recordPage===0?'disabled':''}>上一页</button><span>${recordPage+1} / ${pages}</span><button class="plain-button" id="code-next" ${recordPage+1>=pages?'disabled':''}>下一页</button></div>`);
 const body=document.getElementById("inspector-body");
 body.querySelector("#code-export-records").onclick=()=>environment.download("code-selection.csv",csvString([Object.keys(activeRecords[0] || featureRows[0] || {}).map(k=>k),...activeRecords.map(r=>Object.values(r))]),"text/csv;charset=utf-8");
 body.querySelector("#code-previous").onclick=()=>{recordPage--;drawRecords(title,q);};body.querySelector("#code-next").onclick=()=>{recordPage++;drawRecords(title,q);};
 body.querySelectorAll("[data-code-record]").forEach(el=>{el.onclick=()=>recordDetail(el.dataset.codeRecord);el.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();recordDetail(el.dataset.codeRecord);}};});
}
function recordDetail(id){
 const r=featureRows.find(r=>r.id===id);if(!r)return;
 const siblings=featureRows.filter(v=>v.question===r.question && v.model===r.model && v.prompt===r.prompt).sort((a,b)=>a.sample-b.sample);
 environment.openInspector(id,`<p class="subline">${esc(name(r.model))} / ${esc(label(r.prompt))} / ${r.question}</p><div class="facts">${[["独立采样序号",r.sample],["源结果",r.environment_excluded?'环境排除':r.passed?'测试通过':ERROR_LABELS[r.error] || r.error],["输出 token",fmt(r.output_tokens)],["输入 token",fmt(r.input_tokens)],["生成延迟",`${fmt(r.latency_seconds,2)} 秒`],["结束原因",r.finish || '未记录'],["评分器","target-function-ast-v2"]].map(([k,v])=>`<div class="fact"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join("")}</div><h3>相同条件的 5 次独立结果</h3><table><thead><tr><th>采样</th><th>结果</th><th>返回 token</th></tr></thead><tbody>${siblings.map(a=>`<tr><td>${a.sample}</td><td>${esc(a.environment_excluded?'环境排除':a.passed?'通过':ERROR_LABELS[a.error] || a.error)}</td><td>${fmt(a.output_tokens)}</td></tr>`).join("")}</tbody></table><p>模型没有看到其他采样的回答或测试反馈。此处仅展示保存的评分与匿名特征。</p><div class="record-actions">${button('record-condition','查看同条件全部评分')}</div>`);
 document.getElementById("inspector-body").querySelector('[data-code-action="record-condition"]').onclick=()=>records({model:r.model,prompt:r.prompt,excluded:r.environment_excluded},`${name(r.model)} / ${label(r.prompt)}`);
}
function condition(meta){
 interact.pause();
 const s=stat(meta.model,meta.prompt || "__all");const k=+meta.k || currentState.k || 1;
 const contrast=D.contrasts.find(r=>r.model===meta.model && r.prompt===(meta.prompt || '__all'));
 const rows=[1,2,3,4,5].map(i=>`<tr><td>${i}</td><td class="numeric">${pct(s.pass[i-1],2)}</td><td class="numeric">${pct(s.pass_low[i-1],2)}–${pct(s.pass_high[i-1],2)}</td><td class="numeric">${pct(s.cumulative[i-1],2)}</td></tr>`).join("");
 environment.openInspector(`${name(meta.model)} / ${label(s.prompt)}`,`<p class="subline">${fmt(s.n)} 条可评回答 / 193 道题 / ${fmt(s.units)} 个题目×提示条件</p><div class="metric-pair"><div><strong>${pct(s.pass[k-1],2)}</strong><span>Pass@${k}</span></div><div><strong>${fmt(s.mean_output_tokens,1)}</strong><span>平均返回 token</span></div></div><table><thead><tr><th>k</th><th>Pass@k</th><th>按题 95% 区间</th><th>观测累计</th></tr></thead><tbody>${rows}</tbody></table>${contrast && s.prompt!=='NoCoT'?`<p>当前提示相对 NoCoT 的 Pass@${k} 差为 ${signed(contrast.difference[k-1]*100,2)} pp，95% 区间 ${signed(contrast.low[k-1]*100,2)} 至 ${signed(contrast.high[k-1]*100,2)} pp。</p>`:""}<p>提取失败 ${fmt(s.errors.extraction_error || 0)} 条；输出截断 ${fmt(s.truncated)} 条。Pass@k 估计使用全部 5 次保存结果，观测累计采用本次固定次序。</p><div class="record-actions">${button('condition-records','查看评分记录')}${button('condition-extraction','仅看提取失败')}</div>`);
 const body=document.getElementById("inspector-body");body.querySelector('[data-code-action="condition-records"]').onclick=()=>records({model:s.model,prompt:s.prompt},`${name(s.model)} / ${label(s.prompt)}`);body.querySelector('[data-code-action="condition-extraction"]').onclick=()=>records({model:s.model,prompt:s.prompt,error:'extraction_error'},`${name(s.model)} / 提取失败`);
}
function contrast(meta){
 const k=+meta.k || 1;
 environment.openInspector(`DefaultCoT − NoCoT / Pass@${k}`,`<p>相同的 193 道共同题目；模型内配对。提示适配只改变代码前说明要求。</p><table><thead><tr><th>模型</th><th>差值 / pp</th><th>95% 区间 / pp</th></tr></thead><tbody>${D.models.map(m=>{const r=D.contrasts.find(r=>r.model===m.id && r.prompt==='DefaultCoT');return `<tr><td>${m.name}</td><td>${signed(r.difference[k-1]*100,2)}</td><td>${signed(r.low[k-1]*100,2)} 至 ${signed(r.high[k-1]*100,2)}</td></tr>`;}).join("")}</tbody></table><p>Qwen3 / NoCoT 的代码提取失败率为 ${pct(stat('qwen3','NoCoT').errors.extraction_error/stat('qwen3','NoCoT').n,1)}，因此这项差异同时包含是否输出可提取函数的影响。</p>${button('contrast-records','查看所选模型 NoCoT 评分')}`);
 document.getElementById("inspector-body").querySelector('[data-code-action="contrast-records"]').onclick=()=>records({model:meta.model,prompt:'NoCoT'},`${name(meta.model)} / NoCoT`);
}
function wireActions(root){
 root.querySelectorAll('[data-code-action]').forEach(el=>{
  const action=()=>{
   const m=el.dataset;
   if(m.codeAction==='method')method();
   else if(m.codeAction==='excluded')records({excluded:true},'共同环境排除');
   else if(m.codeAction==='records'){
    const s=currentState;const q=s.view==='sampling'?{model:s.model,prompt:s.prompt}:s.view==='tokens'?{conditions:interact.selectedConditions()}:{prompts:s.scope==='core'?D.core:D.prompts,...(s.view==='errors'?{error:s.error}:{})};
    records(q,s.view==='errors'?'所选错误类型的评分记录':'当前范围的评分记录');
   }
   else if(m.codeAction==='condition')condition({model:m.codeModel,prompt:m.codePrompt,k:m.codeK});
   else if(m.codeAction==='contrast')contrast({model:m.codeModel,k:m.codeK});
   else if(m.codeAction==='gains')records({model:m.codeModel,prompt:m.codePrompt,sample:+m.codeSample},`${name(m.codeModel)} / 第 ${m.codeSample} 次首次通过`);
   else if(m.codeAction==='errors')records({model:m.codeModel,prompt:m.codePrompt,error:m.codeError},`${name(m.codeModel)} / ${ERROR_LABELS[m.codeError] || m.codeError}`);
   else if(m.codeAction==='svg')environment.download(figureKey(currentState)+'.svg',interact.svgSnapshot() || D.figures[figureKey(currentState)],'image/svg+xml;charset=utf-8');
   else if(m.codeAction==='export-summary'){
    const chosen=interact.selectedConditions();
    const rs=D.stats.filter(r=>(currentState.view!=='tokens' || chosen.some(c=>c.model===r.model && c.prompt===r.prompt)) && (currentState.view!=='sampling' || ((currentState.model==='all' || r.model===currentState.model) && r.prompt===currentState.prompt)));
    environment.download('code-study-summary.csv',csvString([['model','prompt','eligible_responses','question_clusters','pass_1','pass_2','pass_3','pass_4','pass_5','mean_output_tokens'],...rs.map(r=>[r.model,r.prompt,r.n,r.questions,...r.pass,r.mean_output_tokens])]),'text/csv;charset=utf-8');
   }
  };
  el.onclick=action;
  if(el.tagName.toLowerCase()!=='button')el.onkeydown=e=>{if(e.key==='Enter' || e.key===' '){e.preventDefault();action();}};
 });
}
function renderCodeStudy(s,env){
 environment=env;currentState=s;
 const root=env.root;
 if(!D){root.innerHTML='<h1>代码实验快照未构建</h1><p>请运行离线构建后重新打开系统。</p>';return;}
 if(s.view==='tokens' && s.k===0)s.k=1;
 const titles={sampling:'独立采样的收益',prompts:'提示策略与代码通过率',errors:'代码失败的来源',tokens:'输出开销与测试表现'};
 root.innerHTML=`<div class="research-heading"><div><h1>${titles[s.view]}</h1><p>193 道共同可评题 / 31 种提示 / 每条件 5 次独立生成</p></div><div class="publication-actions">${button('method','方法')}${button('svg',icon()+' SVG')}</div></div><nav class="code-view-nav" aria-label="代码生成视图">${Object.entries(VIEWS).map(([k,v])=>`<button data-code-view="${k}" aria-current="${s.view===k?'page':'false'}">${v}</button>`).join('')}</nav><div class="research-toolbar code-study-toolbar">${tools(s)}</div>${s.view==='sampling'?interact.playbackControls(s.step):''}<div class="publication-frame"><div class="publication-svg" id="code-publication" role="region" tabindex="0" aria-label="代码生成科学图表，可横向滚动查看完整图">${D.figures[figureKey(s)] || ''}</div><p class="publication-scroll-hint">横向滚动查看完整图 · 聚焦图表后可使用左右方向键</p></div><div class="research-caption"><span class="caption-index">发现</span><div id="code-finding">${caption(s)}</div></div>${s.view==='tokens'?interact.numericControls(s.brush,D.error_categories,ERROR_LABELS):''}<div class="research-foot"><span>code-generation · 90,210 条已保存回答 / 89,745 条进入统计 · 5 次独立采样</span><div class="code-source-actions">${button('records','评分记录')}${button('excluded','465 条环境排除')}</div></div><div class="code-keyboard-tools"><label for="code-keyboard-model">记录模型</label><select id="code-keyboard-model" class="form-select">${D.models.map(m=>`<option value="${m.id}">${esc(m.name)}</option>`).join('')}</select><label for="code-keyboard-prompt">记录提示</label><select id="code-keyboard-prompt" class="form-select">${D.prompts.map(p=>`<option value="${p}">${esc(label(p))}</option>`).join('')}</select><button class="text-action" id="code-keyboard-open">查看条件与评分</button></div>`;
 root.querySelectorAll('[data-code-view]').forEach(el=>el.onclick=()=>env.onChange({...s,view:el.dataset.codeView}));
 root.querySelectorAll('[data-code-model]:not([data-code-action])').forEach(el=>el.onclick=()=>env.onChange({...s,model:el.dataset.codeModel}));
 const change=(id,key)=>{const el=root.querySelector('#'+id);if(el)el.onchange=()=>env.onChange({...s,[key]:key==='k'?+el.value:el.value,...(key==='k'?{brush:null}:{})});};
 change('code-study-prompt','prompt');change('code-study-k','k');change('code-study-scope','scope');change('code-study-error','error');
 wireActions(root);
 root.querySelector('#code-keyboard-open').onclick=()=>condition({model:root.querySelector('#code-keyboard-model').value,prompt:root.querySelector('#code-keyboard-prompt').value,k:s.k || 1});
 const persist=(next,url=true)=>{currentState=next;env.onState(next,{url});};
 if(s.view==='sampling')interact.enhanceSampling(root,s,D,step=>{s.step=step;persist({...s});root.querySelector('#code-finding').innerHTML=caption(s);});
 if(s.view!=='tokens')interact.enhanceStatic(root);
 if(s.view==='tokens'){
  const updateSelection=(selected,brush)=>{
   s.brush=brush;root.querySelector("#code-finding").innerHTML=caption(s);const clear=root.querySelector('#code-clear-brush');if(clear)clear.hidden=!brush;
   const form=root.querySelector('#code-range-form');if(form){const b=brush || [0,700,0,100];['xmin','xmax','ymin','ymax'].forEach((key,i)=>{if(document.activeElement!==form.elements[key])form.elements[key].value=b[i];});}
  };
  interact.enhanceTokens(root,s,D,{onState:persist,onCondition:condition,onRecords:records,onSelection:updateSelection,onUnavailable:message=>{const note=root.querySelector('.code-gesture-note');if(note)note.textContent='框选未启用；可用下方精确范围筛选';}});
  root.querySelector('#code-clear-brush').onclick=()=>env.onChange({...s,brush:null});
  root.querySelector('#code-keyboard-error-open').onclick=()=>{const error=root.querySelector('#code-keyboard-error').value;records({conditions:interact.selectedConditions(),error},ERROR_LABELS[error]+' / 当前框选');};
  root.querySelector('#code-reset-range').onclick=()=>env.onChange({...s,brush:null});
  root.querySelector('#code-range-form').oninput=event=>{const f=event.currentTarget;f.elements.xmax.setCustomValidity('');f.elements.ymax.setCustomValidity('');};
  root.querySelector('#code-range-form').onsubmit=event=>{event.preventDefault();const f=event.currentTarget,b=['xmin','xmax','ymin','ymax'].map(k=>+f.elements[k].value);f.elements.xmax.setCustomValidity(b[1]>b[0]?'':'最多 token 应大于最少 token');f.elements.ymax.setCustomValidity(b[3]>b[2]?'':'最高通过率应大于最低通过率');if(f.reportValidity())env.onChange({...s,brush:b});};
 }
 const signature=JSON.stringify(s),frame=root.querySelector('.publication-frame');if(previousSignature && previousSignature!==signature && !libraries.reducedMotion())frame.animate([{opacity:.65},{opacity:1}],{duration:180,easing:'ease-out'});previousSignature=signature;

}

return {disposeCodeStudy,codeRoute,codeQuery,renderCodeStudy};
})();
const {
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
} = _model;
const charts = _charts;
const codeStudy = _codeStudy;

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

})();

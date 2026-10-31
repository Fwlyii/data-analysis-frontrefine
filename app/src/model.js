export const CORE = [
  "NoCoT",
  "DefaultCoT",
  "BeConcise",
  "BulletPoints",
  "WordLimit(25)",
  "WordLimit(100)",
  "TokenLimit(100)",
  "StepLimit(2)",
];
export const MODEL_IDS = ["deepseek", "hy4", "qwen", "qwen3"];
export const METRICS = [
  "paper_firstline",
  "strict_final_em",
  "final_contains",
  "full_response_contains",
];
export const METRIC_LABELS = [
  "首行答案命中率",
  "最终答案严格匹配率",
  "最终答案包含率",
  "全文答案包含率",
];
export const TASK_LABELS = {
  gsm8k: "GSM8K · 算术推理",
  math500: "MATH500 · 数学解题",
  mmlu: "MMLU-Pro · 选择题",
  document_qa: "NQ-Open · 带资料问答",
  closedbook_control: "无资料对照",
  all: "三类任务等权",
};
export const PROMPT_LABELS = {
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
export const initialState = () => ({
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
export const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export const fmt = (v, d = 0) =>
  Number.isFinite(v)
    ? Number(v).toLocaleString("en-US", {
        minimumFractionDigits: d,
        maximumFractionDigits: d,
      })
    : "—";
export const pct = (v, d = 1) =>
  Number.isFinite(v) ? `${fmt(v * 100, d)}%` : "—";
export const signed = (v, d = 1) =>
  Number.isFinite(v) ? `${v > 0 ? "+" : ""}${fmt(v, d)}` : "—";
export const promptName = (p) => PROMPT_LABELS[p] || p;

export function matchesPrompt(cell, prompt) {
  if (prompt === "__all") return true;
  if (prompt === "__core") return CORE.includes(cell.prompt);
  if (prompt === "__main") return cell.scope === "main_comparison";
  return cell.prompt === prompt;
}
export function selectCells(data, state, overrides = {}) {
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
export function aggregate(cells, metric = 0) {
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
export function groupCells(cells, key, metric = 0) {
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
export function selectedMetric(state) {
  return state.dataset === "reasoning" ? 0 : state.metric;
}
export function metricLabel(state) {
  return state.dataset === "reasoning"
    ? "当前规则评分通过率"
    : METRIC_LABELS[state.metric];
}
export function csvString(rows) {
  const cell = (v) => {
    let s = v == null ? "" : String(v);
    if (typeof v === "string" && /^[=+@\-]/.test(s)) s = "'" + s;
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  return "\ufeff" + rows.map((r) => r.map(cell).join(",")).join("\r\n");
}
export function validateCodingPayload(payload) {
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
export function codingSummary(runs) {
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

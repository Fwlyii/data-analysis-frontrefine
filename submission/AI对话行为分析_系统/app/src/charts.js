import {
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
} from "./model.js";
import * as libraries from "./libraries.js";

const mounted = new Map();
let chartEpoch=0;
const font = '"Times New Roman", "Songti SC", serif';
const ink = "#526174",
  muted = "#68788d",
  grid = "#e9eef5";
let tooltip;
export function disposeCharts() {
  chartEpoch++;
  for (const c of mounted.values()) c.dispose();
  mounted.clear();
  document.querySelector(".svg-tooltip")?.remove();
  tooltip = null;
}
export function resizeCharts() {
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
export function mount(id, option, onClick) {
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
export function exportChart(id) {
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
export function emptyChart(id, title, body) {
  const el = document.getElementById(id);
  if (el)
    el.innerHTML = `<div class="chart-empty"><strong>${esc(title)}</strong><span>${esc(body)}</span></div>`;
}

export function modelBars(id, data, state, onSelect) {
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

export function radar(id, data, state, onSelect) {
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

export function bubble(id, data, state, onSelect) {
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
export function radial(id, data, state, onSelect) {
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

export function heatmap(id, data, state, onSelect) {
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

export function positionLines(id, data, state, onSelect) {
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

export function controlsBars(id, data, state) {
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

export function metricComparison(id, data, state) {
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

export function disagreement(id, data, state) {
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

export function truncationBars(id, data, state, onSelect) {
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

export function reasoningStatus(id, data, state) {
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

export function codingBars(id, runs) {
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

export function codingErrors(id, runs) {
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

export function heroGain(id, data, onSelect) {
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
export async function boxplot(id,data,state,rows,onSelect){
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
export function parallel(id, data, state) {
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
export function distribution(pieId, stackId, data, state, rows) {
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
export function retryTimeline(id, data, rows, onRecord) {
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
export function retryTree(id, data, rows, onRecord) {
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
export function codingEventDistribution(id, runs) {
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
export function codingScatter(id, runs) {
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
export function codingTree(id, runs, onRun) {
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

export function lengthHistogram(id, stats, onPick) {
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
export function promptCase(id, data, mid, onPick) {
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
export function efficiencyCase(id, data, list, onPick) {
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
export function positionFacet(id, data, state, mid, onPick) {
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
export function positionIntervals(id, data, contrasts, onPick) {
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

export function overviewPrompts(id, data, onPick) {
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

export function behaviorMatrix(id,families,styles,cells,selection,onPick) {
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
export function behaviorStates(id,items,total,onPick) {
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

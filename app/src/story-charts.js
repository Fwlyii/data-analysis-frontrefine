(() => {
  "use strict";
  const C = {
    ink: "#203b50",
    muted: "#4d6579",
    faint: "#708694",
    grid: "#d8e4ea",
    accent: "#147b7b",
    blue: "#315c6b",
    gold: "#a2763c",
    pale: "#e7f3f2",
  };
  const esc = (x) =>
    String(x ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const f = (x, n = 1) => Number(x).toFixed(n);
  const X = (v, min, max, left, width) =>
    left + ((v - min) / (max - min || 1)) * width;
  const Y = (v, min, max, top, height) =>
    top + height - ((v - min) / (max - min || 1)) * height;
  const txt = (
    x,
    y,
    value,
    size = 13,
    fill = C.muted,
    anchor = "start",
    weight = "400",
  ) =>
    `<text x="${x}" y="${y}" font-size="${size}" fill="${fill}" text-anchor="${anchor}" font-weight="${weight}">${esc(value)}</text>`;
  const line = (x1, y1, x2, y2, stroke = C.grid, width = 1, dash = "") =>
    `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}" ${dash ? `stroke-dasharray="${dash}"` : ""}/>`;
  const circle = (x, y, r, fill, extra = "") =>
    `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" ${extra}/>`;
  const path = (d, stroke = C.ink, width = 2, extra = "") =>
    `<path d="${d}" fill="none" stroke="${stroke}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round" ${extra}/>`;
  const svg = (w, h, body, label) =>
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}" font-family="Times New Roman, Times, serif">${body}</svg>`;
  const pointsPath = (pts) =>
    pts
      .map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(2)} ${p[1].toFixed(2)}`)
      .join(" ");
  const modelNames = {
    deepseek: "DeepSeek",
    hy4: "HY4",
    qwen: "Qwen2.5",
    qwen3: "Qwen3",
  };
  const taskNames = { gsm8k: "GSM8K", math500: "MATH500", mmlu: "MMLU-Pro" };
  function mix(a, b, t) {
    const p = (s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16));
    const A = p(a),
      B = p(b);
    return (
      "#" +
      A.map((v, i) =>
        Math.round(v + (B[i] - v) * t)
          .toString(16)
          .padStart(2, "0"),
      ).join("")
    );
  }
  function trend(rows) {
    const pts = rows
      .filter((r) => r.mean_tokens > 0)
      .map((r) => [Math.log(r.mean_tokens), r.score_pct]);
    const n = pts.length;
    if (!n) return [];
    const mx = pts.reduce((s, p) => s + p[0], 0) / n,
      my = pts.reduce((s, p) => s + p[1], 0) / n;
    let num = 0,
      den = 0;
    pts.forEach((p) => {
      num += (p[0] - mx) * (p[1] - my);
      den += (p[0] - mx) ** 2;
    });
    const b = den ? num / den : 0,
      a = my - b * mx;
    return rows
      .map((r) => ({
        tokens: r.mean_tokens,
        y: a + b * Math.log(Math.max(1, r.mean_tokens)),
      }))
      .sort((a, b) => a.tokens - b.tokens);
  }

  function landscape(D, state) {
    const tasks = D.directions[state.direction].groups,
      models = D.directions[state.direction].models;
    if (!models.includes(state.model)) state.model = models[0];
    const rows = (D.profiles_by_direction?.[state.direction] || []).filter(
      (r) => r.model === state.model && tasks.includes(r.task),
    );
    if (state.view === "heatmap") {
      const w = 1120,
        h = 300,
        left = 118,
        top = 44,
        cw = (w - left - 28) / 31,
        rh = 58;
      let body =
        txt(0, 20, "31 prompt strategies", 14, C.ink) +
        txt(w, 20, "Low → high score", 12, C.muted, "end");
      tasks.forEach((task, j) => {
        body += txt(
          left - 14,
          top + j * rh + 35,
          task === "Position 1"
            ? "Beginning"
            : task === "Position 10"
              ? "Middle"
              : task === "Position 20"
                ? "End"
                : taskNames[task] || task,
          13,
          C.ink,
          "end",
        );
        D.prompts.forEach((p, i) => {
          const r = rows.find(
            (x) => x.task === task && x.prompt === p.prompt_id,
          );
          const score = r?.score_pct;
          const color = r
            ? mix("#e9f3f4", "#294f5d", Math.max(0, Math.min(1, score / 100)))
            : C.pale;
          const x = left + i * cw,
            y = top + j * rh;
          const label = `${p.prompt_id} · ${task} · ${r ? f(score) + "%" : "Not available"}`;
          body += `<g ${r ? `role="button" tabindex="0" data-profile-prompt="${esc(p.prompt_id)}" data-profile-task="${esc(task)}"` : ""} aria-label="${esc(label)}"><rect x="${x + 1}" y="${y}" width="${cw - 3}" height="${rh - 8}" rx="3" fill="${color}"/><title>${esc(label)}</title></g>`;
        });
      });
      [1, 5, 10, 15, 20, 25, 31].forEach((n) => {
        body += txt(
          left + (n - 0.5) * cw,
          top + tasks.length * rh + 18,
          String(n),
          11,
          C.faint,
          "middle",
        );
      });
      body +=
        txt(left, top + tasks.length * rh + 45, "Prompt index", 12, C.muted) +
        txt(
          w - 28,
          top + tasks.length * rh + 45,
          "Select a cell for prompt and score",
          12,
          C.muted,
          "end",
        );
      return svg(w, h, body, "Score matrix for 31 prompts").replace(
        'role="img"',
        'role="group"',
      );
    }
    const w = 1120,
      h = 400,
      pw = w / tasks.length,
      top = 62,
      ph = 265;
    let body =
      txt(0, 22, "Each point is one prompt strategy", 13, C.muted) +
      circle(w - 238, 17, 5, C.ink) +
      txt(w - 226, 22, "DefaultCoT", 12) +
      `<rect x="${w - 127}" y="12" width="9" height="9" transform="rotate(45 ${w - 122.5} 16.5)" fill="${C.accent}"/>` +
      txt(w - 108, 22, "BeConcise", 12);
    tasks.forEach((task, j) => {
      const data = rows.filter((r) => r.task === task),
        left = j * pw + 58,
        width = pw - 88,
        maxX = Math.max(1, ...data.map((r) => r.mean_tokens)) * 1.08;
      body += txt(left, 39, taskNames[task] || task, 17, C.ink);
      const fit = D.fits.find(
        (x) =>
          x.direction === state.direction &&
          x.model === state.model &&
          x.benchmark === task,
      );
      if (fit)
        body += txt(
          left + width,
          39,
          `${fit.slope >= 0 ? "+" : ""}${f(fit.slope)} slope · R² ${f(fit.r2, 2)}`,
          11,
          fit.slope >= 0 ? C.accent : C.muted,
          "end",
        );
      [0, 50, 100].forEach((v) => {
        const y = Y(v, 0, 100, top, ph);
        body +=
          line(left, y, left + width, y) +
          txt(left - 10, y + 4, String(v), 11, C.faint, "end");
      });
      const tr = trend(data);
      if (tr.length > 1) {
        const pts = tr.map((r) => [
          X(r.tokens, 0, maxX, left, width),
          Y(Math.max(0, Math.min(100, r.y)), 0, 100, top, ph),
        ]);
        body += path(pointsPath(pts), C.ink, 1.8, 'opacity=".72"');
      }
      data.forEach((r) => {
        const x = X(r.mean_tokens, 0, maxX, left, width),
          y = Y(r.score_pct, 0, 100, top, ph),
          special = r.prompt === "DefaultCoT" || r.prompt === "BeConcise";
        if (r.prompt === "BeConcise")
          body += `<rect x="${x - 5}" y="${y - 5}" width="10" height="10" transform="rotate(45 ${x} ${y})" fill="${C.accent}"><title>${esc(r.prompt)} · ${f(r.mean_tokens)} tokens · ${f(r.score_pct)}%</title></rect>`;
        else
          body += circle(
            x,
            y,
            special ? 5.5 : 4,
            special ? C.ink : "#829396",
            `opacity="${special ? 1 : 0.52}"><title>${esc(r.prompt)} · ${f(r.mean_tokens)} tokens · ${f(r.score_pct)}%</title></circle>`,
          );
      });
      [0, 0.5, 1].forEach((t) => {
        const v = maxX * t;
        body += txt(
          X(v, 0, maxX, left, width),
          top + ph + 23,
          String(Math.round(v)),
          11,
          C.faint,
          "middle",
        );
      });
      body += txt(
        left + width / 2,
        top + ph + 48,
        "Mean output tokens",
        12,
        C.muted,
        "middle",
      );
      if (j === 0)
        body += `<text x="16" y="${top + ph / 2}" transform="rotate(-90 16 ${top + ph / 2})" font-size="12" fill="${C.muted}" text-anchor="middle">${esc(D.directions[state.direction].ylabel)}</text>`;
    });
    return svg(w, h, body, "Thirty-one prompt strategies across tasks");
  }

  function conciseBaseline(D) {
    const rows = D.baseline,
      w = 1100,
      h = 355,
      ys = [105, 170, 235];
    let body =
      txt(0, 20, "200 paired items", 13, C.muted) +
      txt(520, 20, "Score (%)", 14, C.ink, "middle") +
      txt(1015, 20, "Mean output tokens", 14, C.ink, "middle");
    const maxT =
      Math.ceil(Math.max(...rows.map((r) => r.mean_tokens)) / 50) * 50;
    [
      ["score_pct", 0, 100, 80, 440],
      ["mean_tokens", 0, maxT, 640, 380],
    ].forEach(([key, min, max, left, width], panel) => {
      [0, 0.5, 1].forEach((t) => {
        const v = min + (max - min) * t,
          x = X(v, min, max, left, width);
        body +=
          line(x, 55, x, 260, C.grid) +
          txt(x, 286, String(Math.round(v)), 12, C.faint, "middle");
      });
      rows.forEach((r, i) => {
        const y = ys[i],
          x = X(r[key], min, max, left, width),
          color =
            r.prompt === "BeConcise"
              ? C.accent
              : r.prompt === "DefaultCoT"
                ? C.ink
                : C.faint;
        if (panel === 0) body += txt(0, y + 5, r.prompt, 15, C.ink);
        body +=
          line(left, y, left + width, y, C.grid) +
          line(left, y, x, y, color, 3) +
          circle(x, y, r.prompt === "NoCoT" ? 6 : 9, color) +
          txt(
            left + width + 12,
            y + 5,
            key === "score_pct" ? f(r[key]) + "%" : f(r[key]),
            14,
            color,
          );
      });
      const a = rows.find((r) => r.prompt === "DefaultCoT"),
        b = rows.find((r) => r.prompt === "BeConcise");
      body += path(
        `M${X(a[key], min, max, left, width)} ${ys[1]}L${X(b[key], min, max, left, width)} ${ys[2]}`,
        C.accent,
        1.2,
        'opacity=".35" stroke-dasharray="3 4"',
      );
    });
    body +=
      txt(
        80,
        318,
        "NoCoT is a reference; DefaultCoT → BeConcise is the paired comparison.",
        12,
        C.muted,
      ) + txt(1015, 318, "+0.5 pp score · −21.5% tokens", 15, C.accent, "end");
    return svg(w, h, body, "Paired score and token comparison");
  }
  function conciseCross(D) {
    const rows = D.concise,
      w = 1100,
      h = 390,
      left = 72,
      top = 54,
      pw = 990,
      ph = 265,
      maxX = Math.ceil(Math.max(...rows.map((r) => r.saving)) / 10) * 10,
      minY = Math.min(
        -2,
        Math.floor(Math.min(...rows.map((r) => r.delta)) - 1),
      ),
      maxY = Math.ceil(Math.max(...rows.map((r) => r.delta)) + 2);
    const dirs = [...new Set(rows.map((r) => r.direction))],
      colors = [C.accent, C.blue, C.gold, C.ink];
    let body =
      txt(left, 22, "Token saving →", 13, C.muted) +
      txt(left + pw, 22, "Score change ↑", 13, C.muted, "end");
    dirs.forEach((d, i) => {
      const x = left + i * 190;
      body += circle(x, 40, 5, colors[i]) + txt(x + 12, 44, d, 12, C.muted);
    });
    [minY, 0, Math.round(maxY / 2), maxY]
      .filter((v, i, a) => a.indexOf(v) === i)
      .forEach((v) => {
        const y = Y(v, minY, maxY, top, ph);
        body +=
          line(
            left,
            y,
            left + pw,
            y,
            v === 0 ? C.ink : C.grid,
            v === 0 ? 1.2 : 1,
          ) + txt(left - 12, y + 4, (v > 0 ? "+" : "") + v, 12, C.faint, "end");
      });
    [0, 0.25, 0.5, 0.75, 1].forEach((t) => {
      const v = maxX * t,
        x = X(v, 0, maxX, left, pw);
      body +=
        line(x, top, x, top + ph, C.grid) +
        txt(x, top + ph + 25, f(v, 0) + "%", 12, C.faint, "middle");
    });
    const maxDelta = Math.max(...rows.map((r) => r.delta)),
      minDelta = Math.min(...rows.map((r) => r.delta));
    rows.forEach((r) => {
      const x = X(r.saving, 0, maxX, left, pw),
        y = Y(r.delta, minY, maxY, top, ph),
        color = colors[dirs.indexOf(r.direction)];
      body += circle(
        x,
        y,
        7,
        color,
        `opacity=".86"><title>${esc(modelNames[r.model] || r.model)} · ${esc(r.task)} · ${f(r.saving)}% saved · ${r.delta >= 0 ? "+" : ""}${f(r.delta)} pp</title></circle>`,
      );
      if (r.delta === maxDelta || r.delta === minDelta)
        body += txt(
          x + 11,
          y - 9,
          `${modelNames[r.model] || r.model} / ${r.task}`,
          11,
          color,
        );
    });
    body +=
      txt(left, 374, "17 model–task groups", 14, C.ink) +
      txt(
        left + pw,
        374,
        "15 at or above zero score change",
        14,
        C.accent,
        "end",
      );
    return svg(w, h, body, "Seventeen replications of concise prompting");
  }
  function language(D, state) {
    const rows = D.chinese.filter((r) => r.task === state.task),
      w = 1100,
      h = 360,
      ys = [92, 154, 216, 278],
      scores = rows.flatMap((r) => [r.default_score_pct, r.chinese_score_pct]),
      min = Math.floor((Math.min(...scores) - 4) / 5) * 5,
      max = Math.ceil((Math.max(...scores) + 3) / 5) * 5,
      maxSave = Math.max(
        20,
        Math.ceil(Math.max(...rows.map((r) => r.token_saving_pct)) / 10) * 10,
      );
    let body =
      txt(70, 23, "Score: DefaultCoT → Chinese template", 14, C.ink) +
      txt(745, 23, "Output token reduction", 14, C.ink) +
      txt(520, 43, "Default", 11, C.faint, "middle") +
      txt(650, 43, "Chinese", 11, C.faint, "middle");
    [min, (min + max) / 2, max].forEach((v) => {
      const x = X(v, min, max, 120, 530);
      body +=
        line(x, 54, x, 302, C.grid) +
        txt(x, 325, f(v, 0), 11, C.faint, "middle");
    });
    rows.forEach((r, i) => {
      const y = ys[i],
        x1 = X(r.default_score_pct, min, max, 120, 530),
        x2 = X(r.chinese_score_pct, min, max, 120, 530),
        up = r.score_difference_pp >= 0;
      body +=
        txt(0, y + 5, modelNames[r.model] || r.model, 15, C.ink) +
        line(x1, y, x2, y, up ? C.accent : C.faint, 2) +
        circle(x1, y, 7, C.ink) +
        circle(x2, y, 8, C.accent, `fill-opacity="${up ? 1 : 0.45}"`) +
        txt(x1, y - 13, f(r.default_score_pct), 12, C.ink, "middle") +
        txt(x2, y + 22, f(r.chinese_score_pct), 12, C.accent, "middle");
      const bx = X(r.token_saving_pct, 0, maxSave, 770, 260);
      body +=
        line(770, y, 770 + 260, y, C.grid) +
        line(770, y, bx, y, C.accent, 3) +
        circle(bx, y, 7, C.accent) +
        txt(1042, y + 5, f(r.token_saving_pct) + "%", 13, C.accent);
      if (r.chinese_truncation_pct > 0)
        body += circle(
          x2,
          y,
          12,
          "none",
          `stroke="${C.gold}" stroke-width="1.5"><title>Chinese truncation ${f(r.chinese_truncation_pct)}%</title></circle>`,
        );
    });
    body +=
      txt(770, 325, "0", 11, C.faint) +
      txt(1030, 325, maxSave + "%", 11, C.faint, "end");
    return svg(
      w,
      h,
      body,
      "Default versus Chinese templates across four models",
    );
  }
  function position(D, state) {
    const positions = [1, 3, 5, 8, 10, 13, 15, 18, 20],
      w = 1100,
      h = 405,
      left = 66,
      top = 54,
      pw = 994,
      ph = 280,
      focus = positions[state.position];
    const series = [
      { key: "Qwen3", name: "Qwen3 8B", color: C.ink },
      { key: "Qwen2.5", name: "Qwen2.5 7B", color: C.accent },
    ];
    let body = "";
    [40, 50, 60, 70, 80].forEach((v) => {
      const y = Y(v, 40, 80, top, ph);
      body +=
        line(left, y, left + pw, y, C.grid) +
        txt(left - 12, y + 4, String(v), 12, C.faint, "end");
    });
    const focusX = X(focus, 1, 20, left, pw);
    body +=
      line(focusX, 38, focusX, top + ph, C.accent, 1, "3 4") +
      txt(focusX, 30, "Position " + focus, 12, C.accent, "middle");
    series.forEach((s) => {
      const rows = D.positions
          .filter((r) => r.model.includes(s.key))
          .sort((a, b) => a.position - b.position),
        pts = rows.map((r) => [
          X(r.position, 1, 20, left, pw),
          Y(r.rate * 100, 40, 80, top, ph),
        ]);
      if (state.ci) {
        const upper = rows.map((r) => [
            X(r.position, 1, 20, left, pw),
            Y(r.ci_high * 100, 40, 80, top, ph),
          ]),
          lower = [...rows]
            .reverse()
            .map((r) => [
              X(r.position, 1, 20, left, pw),
              Y(r.ci_low * 100, 40, 80, top, ph),
            ]);
        body += `<polygon points="${[...upper, ...lower].map((p) => p.join(",")).join(" ")}" fill="${s.color}" opacity=".09"/>`;
      }
      body += path(pointsPath(pts), s.color, 2.4);
      rows.forEach((r, i) => {
        body +=
          circle(pts[i][0], pts[i][1], r.position === focus ? 7 : 5, s.color) +
          `<title>${s.name} · position ${r.position} · ${f(r.rate * 100)}% [${f(r.ci_low * 100)}, ${f(r.ci_high * 100)}]</title>`;
      });
    });
    body += line(left, top + ph, left + pw, top + ph, C.ink);
    positions.forEach(
      (p) =>
        (body += txt(
          X(p, 1, 20, left, pw),
          top + ph + 25,
          String(p),
          12,
          C.muted,
          "middle",
        )),
    );
    body +=
      txt(
        left + pw / 2,
        top + ph + 53,
        "Evidence document position (out of 20)",
        13,
        C.muted,
        "middle",
      ) +
      `<text x="17" y="${top + ph / 2}" transform="rotate(-90 17 ${top + ph / 2})" font-size="13" fill="${C.muted}" text-anchor="middle">Final-answer hit rate (%)</text>`;
    body +=
      circle(left + 650, 20, 5, C.ink) +
      txt(left + 662, 24, "Qwen3 8B", 12) +
      circle(left + 780, 20, 5, C.accent) +
      txt(left + 792, 24, "Qwen2.5 7B", 12) +
      txt(left + pw, 24, "95% intervals", 12, C.muted, "end");
    return svg(w, h, body, "Model score by evidence position");
  }
  function repair(D, state) {
    const rows = D.repair[state.repairModel],
      w = 1100,
      h = 405,
      left = 70,
      top = 58,
      pw = 910,
      ph = 270,
      arms = [
        ["counterexample", "Counterexample", C.accent, ""],
        ["self_review", "Self-review", C.ink, ""],
        ["pass_fail", "Pass / fail", C.gold, ""],
        ["resample", "Independent resample", C.faint, "5 5"],
      ],
      vals = rows.flatMap((r) =>
        r.arm === "counterexample"
          ? [r.rate * 100, r.ci_low * 100, r.ci_high * 100]
          : [r.rate * 100],
      ),
      min = Math.floor((Math.min(...vals) - 2) / 5) * 5,
      max = Math.ceil((Math.max(...vals) + 2) / 5) * 5;
    let body = "";
    for (let v = min; v <= max; v += 5) {
      const y = Y(v, min, max, top, ph);
      body +=
        line(left, y, left + pw, y, C.grid) +
        txt(left - 12, y + 4, String(v), 12, C.faint, "end");
    }
    const focusX = X(state.round, 0, 4, left, pw);
    body +=
      `<rect x="${focusX - 34}" y="38" width="68" height="${ph + 20}" fill="${C.accent}" opacity=".045"/>` +
      txt(
        focusX,
        30,
        state.round === 0 ? "Shared draft" : "Revision " + state.round,
        12,
        C.accent,
        "middle",
      );
    const counter = rows
        .filter((r) => r.arm === "counterexample")
        .sort((a, b) => a.round - b.round),
      upper = counter.map((r) => [
        X(r.round, 0, 4, left, pw),
        Y(r.ci_high * 100, min, max, top, ph),
      ]),
      lower = [...counter]
        .reverse()
        .map((r) => [
          X(r.round, 0, 4, left, pw),
          Y(r.ci_low * 100, min, max, top, ph),
        ]);
    body += `<polygon points="${[...upper, ...lower].map((p) => p.join(",")).join(" ")}" fill="${C.accent}" opacity=".08"/>`;
    const endLabels = arms
      .map(([arm]) => {
        const r = rows.find((r) => r.arm === arm && r.round === state.round);
        return { arm, y: Y(r.rate * 100, min, max, top, ph) };
      })
      .sort((a, b) => a.y - b.y);
    let previous = -Infinity;
    endLabels.forEach((d) => {
      d.y = Math.max(d.y, previous + 18);
      previous = d.y;
    });
    arms.forEach(([arm, name, color, dash], i) => {
      const data = rows
          .filter((r) => r.arm === arm)
          .sort((a, b) => a.round - b.round),
        pts = data.map((r) => [
          X(r.round, 0, 4, left, pw),
          Y(r.rate * 100, min, max, top, ph),
        ]);
      body += path(
        pointsPath(pts),
        color,
        arm === "counterexample" ? 2.8 : 2,
        dash ? `stroke-dasharray="${dash}"` : "",
      );
      data.forEach(
        (r, j) =>
          (body +=
            circle(
              pts[j][0],
              pts[j][1],
              r.round === state.round ? 7 : 4.5,
              color,
            ) +
            `<title>${name} · version ${r.round + 1} · ${r.success}/${r.tasks}</title>`),
      );
      const current = data.find((r) => r.round === state.round),
        ly = endLabels.find((d) => d.arm === arm).y;
      body += txt(left + pw + 14, ly + 4, `${current.success}/164`, 12, color);
      body +=
        circle(left + i * 235, 20, 5, color) +
        txt(left + 12 + i * 235, 24, name, 12, C.muted);
    });
    ["Draft", "R1", "R2", "R3", "R4"].forEach(
      (v, i) =>
        (body += txt(
          X(i, 0, 4, left, pw),
          top + ph + 28,
          v,
          12,
          C.muted,
          "middle",
        )),
    );
    body +=
      txt(left + pw / 2, top + ph + 55, "Code version", 13, C.muted, "middle") +
      `<text x="18" y="${top + ph / 2}" transform="rotate(-90 18 ${top + ph / 2})" font-size="13" fill="${C.muted}" text-anchor="middle">Current full-test pass rate (%)</text>`;
    return svg(w, h, body, "Feedback strategy by code revision");
  }
  function limits(D, state) {
    const rows = D.limits[`${state.model}-${state.task}-${state.family}`],
      w = 1100,
      h = 390,
      left = 72,
      top = 58,
      ph = 245,
      pw = 570,
      maxT = Math.ceil(Math.max(...rows.map((r) => r.mean_tokens)) / 100) * 100;
    let body =
      txt(left, 22, "Actual output tokens", 14, C.ink) +
      txt(790, 22, "Score & truncation", 14, C.ink);
    [0, maxT / 2, maxT].forEach((v) => {
      const y = Y(v, 0, maxT, top, ph);
      body +=
        line(left, y, left + pw, y, C.grid) +
        txt(left - 12, y + 4, String(Math.round(v)), 12, C.faint, "end");
    });
    const pts = rows.map((r, i) => [
        left + i * (pw / (rows.length - 1)),
        Y(r.mean_tokens, 0, maxT, top, ph),
      ]),
      area =
        pointsPath(pts) +
        `L${pts.at(-1)[0]} ${top + ph}L${pts[0][0]} ${top + ph}Z`;
    body +=
      `<path d="${area}" fill="${C.accent}" opacity=".07"/>` +
      path(pointsPath(pts), C.accent, 2.6);
    rows.forEach((r, i) => {
      const x = pts[i][0],
        y = pts[i][1],
        tight = i === 0;
      body +=
        circle(x, y, tight ? 10 : 7, tight ? C.accent : C.ink) +
        txt(
          x,
          y - 18,
          f(r.mean_tokens, 0),
          13,
          tight ? C.accent : C.ink,
          "middle",
        ) +
        `<title>${esc(r.prompt)} · ${f(r.mean_tokens)} tokens · ${f(r.score_pct)}% score · ${f(r.truncated_pct)}% truncated</title>`;
    });
    const sx = (i) => 790 + i * (250 / (rows.length - 1));
    [0, 50, 100].forEach((v) => {
      const y = Y(v, 0, 100, top, ph);
      body +=
        line(790, y, 1040, y, C.grid) +
        txt(1050, y + 4, String(v), 11, C.faint);
    });
    const scorePts = rows.map((r, i) => [
      sx(i),
      Y(r.score_pct, 0, 100, top, ph),
    ]);
    body += path(pointsPath(scorePts), C.blue, 2.4);
    rows.forEach((r, i) => {
      const x = sx(i),
        sy = Y(r.score_pct, 0, 100, top, ph),
        ty = Y(r.truncated_pct, 0, 100, top, ph);
      body +=
        circle(x, sy, 7, C.blue) +
        txt(x, sy - 15, f(r.score_pct, 0) + "%", 11, C.blue, "middle");
      if (r.truncated_pct > 0) {
        body +=
          line(x, top + ph, x, ty, C.gold, 7, "") +
          circle(x, ty, 4, C.gold) +
          `<title>Truncated ${f(r.truncated_pct)}%</title>`;
      }
    });
    rows.forEach((r, i) => {
      const n = r.prompt.match(/\((\d+)\)/)?.[1] || r.prompt;
      body +=
        txt(pts[i][0], top + ph + 27, n, 12, C.muted, "middle") +
        txt(
          sx(i),
          top + ph + 48,
          f(r.truncated_pct, 0) + "% trunc.",
          10,
          C.faint,
          "middle",
        );
    });
    body +=
      txt(
        left + pw / 2,
        top + ph + 55,
        "Requested " +
          state.family.replace("Limit", "").toLowerCase() +
          " limit",
        13,
        C.muted,
        "middle",
      ) +
      txt(
        left,
        top + ph + 82,
        "Prompted limits, not API hard caps.",
        12,
        C.muted,
      ) +
      txt(1040, 22, "Score (%) · truncation below", 11, C.muted, "end");
    return svg(w, h, body, "Requested length limit versus actual output");
  }
  window.LENS_CHARTS = {
    landscape,
    conciseBaseline,
    conciseCross,
    language,
    position,
    repair,
    limits,
  };
})();

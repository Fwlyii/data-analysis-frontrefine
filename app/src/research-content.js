/* Generated content configuration from saved research snapshots. */
export const researchContent = {
  "schema": "lens-reconstruction-content-v1",
  "language": "zh-CN",
  "question": {
    "title": "同一个任务，怎样提示会更有效？",
    "lead": "从共同的提示词策略出发，研究回答质量与输出开销，再走向不同任务的专项问题。",
    "central": "提示词策略如何影响模型的任务表现？",
    "tasks": [
      {
        "id": "math",
        "name": "数学与选择题",
        "variable": "作答语言与回答组织",
        "question": "相同题目，换一种作答模板会怎样？",
        "exampleTitle": "把计算过程说清楚，也可以保持简洁",
        "example": "每小时处理15千克，每天工作10小时，共750千克，需要几天？",
        "answer": "15 × 10 = 150；750 ÷ 150 = 5天。",
        "metric": "沿用题库源评分，比较同题条件差异",
        "source": "GSM8K · 已保存匿名案例 Z006587 / Z006787",
        "linkTopic": "language",
        "footnote": "任务为公开基准案例的中文概述。"
      },
      {
        "id": "document",
        "name": "文档问答",
        "variable": "关键证据的位置",
        "question": "资料相同，只移动关键文档，答案会改变吗？",
        "exampleTitle": "从20份资料中找出问题的答案",
        "example": "哪位游击手获得的金手套奖最多？每组20篇资料中只有一篇包含关键证据。",
        "answer": "参考答案为 Ozzie Smith。案例C007中，证据在不同位置时模型回答曾发生变化。",
        "metric": "最终答案包含率，同时保留其他评分口径",
        "source": "NQ-Open · 匿名案例 C007 · 位置专项200题",
        "linkTopic": "position",
        "footnote": "九个位置均有实测，位置曲线连接真实观测点。"
      },
      {
        "id": "code",
        "name": "Python代码",
        "variable": "执行反馈与修改轮次",
        "question": "代码出错后，怎样反馈才能帮助修复？",
        "exampleTitle": "倒置区间应返回什么？",
        "example": "choose_num(x, y)返回闭区间中的最大偶数；没有有效结果时返回−1。",
        "answer": "输入 choose_num(13, 12)，期望 −1，初稿却交换端点并返回12。具体反例指出了错误假设。",
        "metric": "当前版本同时通过诊断与额外测试",
        "source": "HumanEval+ Mini · 已保存案例 HumanEval/102",
        "linkTopic": "feedback",
        "footnote": "独立采样与获得执行反馈后的多轮修复分别统计。"
      }
    ]
  },
  "dimensions": [
    {
      "id": "language",
      "name": "语言模板",
      "description": "默认指令与中文作答条件；带长度的中文策略同时属于两个维度。",
      "examples": [
        "默认指令",
        "中文作答"
      ]
    },
    {
      "id": "reasoning",
      "name": "回答组织",
      "description": "直接给答案、分步回答、简洁分步，以及步骤数量。",
      "examples": [
        "只给答案",
        "默认分步",
        "简洁分步"
      ]
    },
    {
      "id": "length",
      "name": "长度预算",
      "description": "词数、字母数、Token及中文字符上限；提示中的软限制与实际用量分开记录。",
      "examples": [
        "WordLimit",
        "CharLimit",
        "TokenLimit"
      ]
    },
    {
      "id": "format",
      "name": "表达格式",
      "description": "项目符号、缩写、语法、空格、数字与算式。",
      "examples": [
        "项目符号",
        "去空格",
        "数字与算式"
      ]
    }
  ],
  "prompts": [
    {
      "id": "AbbreviateWords",
      "label": "缩写单词",
      "instruction": "Abbreviate words as much as possible. Remove vowels. For example, you can replace 'concept' with 'cncpt'.",
      "dimensions": [
        "format"
      ]
    },
    {
      "id": "BeConcise",
      "label": "简洁分步",
      "instruction": "Think step by step before answering, but be concise.",
      "dimensions": [
        "reasoning"
      ]
    },
    {
      "id": "BulletPoints",
      "label": "项目符号",
      "instruction": "Only use bullet points. Do not use complete sentences.",
      "dimensions": [
        "format"
      ]
    },
    {
      "id": "CharLimit(10)",
      "label": "字母上限 10",
      "instruction": "Only use 10 letters for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "CharLimit(100)",
      "label": "字母上限 100",
      "instruction": "Only use 100 letters for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "CharLimit(50)",
      "label": "字母上限 50",
      "instruction": "Only use 50 letters for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "CharLimit(500)",
      "label": "字母上限 500",
      "instruction": "Only use 500 letters for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "ChineseCoT",
      "label": "中文作答",
      "instruction": "Respond in Chinese.",
      "dimensions": [
        "language"
      ]
    },
    {
      "id": "ChineseCoT(10)",
      "label": "中文字符上限 10",
      "instruction": "Respond in Chinese, but use at most 10 characters.",
      "dimensions": [
        "language",
        "length"
      ]
    },
    {
      "id": "ChineseCoT(100)",
      "label": "中文字符上限 100",
      "instruction": "Respond in Chinese, but use at most 100 characters.",
      "dimensions": [
        "language",
        "length"
      ]
    },
    {
      "id": "ChineseCoT(50)",
      "label": "中文字符上限 50",
      "instruction": "Respond in Chinese, but use at most 50 characters.",
      "dimensions": [
        "language",
        "length"
      ]
    },
    {
      "id": "ChineseCoT(500)",
      "label": "中文字符上限 500",
      "instruction": "Respond in Chinese, but use at most 500 characters.",
      "dimensions": [
        "language",
        "length"
      ]
    },
    {
      "id": "DefaultCoT",
      "label": "默认分步",
      "instruction": "Think step by step before answering.",
      "dimensions": [
        "reasoning"
      ]
    },
    {
      "id": "NoCoT",
      "label": "只给答案",
      "instruction": "Only give the final answer. Do not give any explanation.",
      "dimensions": [
        "reasoning"
      ]
    },
    {
      "id": "NoProperGrammar",
      "label": "简化语法",
      "instruction": "Do not use proper grammar. Avoid using connecting words like 'and', 'since', 'but', or 'then', etc.",
      "dimensions": [
        "format"
      ]
    },
    {
      "id": "NoSpaces",
      "label": "移除空格",
      "instruction": "Do not use any spaces or line breaks. For example, instead of 'since 20 + 4 = 24' respond with 'since20+4=24'.",
      "dimensions": [
        "format"
      ]
    },
    {
      "id": "OnlyNumbers",
      "label": "数字与算式",
      "instruction": "Only use numbers or equations in your steps. Use as few words as possible.",
      "dimensions": [
        "format"
      ]
    },
    {
      "id": "StepLimit(1)",
      "label": "步骤上限 1",
      "instruction": "List your steps (e.g. 'Step 1', 'Step 2', ...). Use at most 1 steps.",
      "dimensions": [
        "reasoning"
      ]
    },
    {
      "id": "StepLimit(2)",
      "label": "步骤上限 2",
      "instruction": "List your steps (e.g. 'Step 1', 'Step 2', ...). Use at most 2 steps.",
      "dimensions": [
        "reasoning"
      ]
    },
    {
      "id": "StepLimit(5)",
      "label": "步骤上限 5",
      "instruction": "List your steps (e.g. 'Step 1', 'Step 2', ...). Use at most 5 steps.",
      "dimensions": [
        "reasoning"
      ]
    },
    {
      "id": "TokenLimit(10)",
      "label": "Token上限 10",
      "instruction": "Only use 10 tokens for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "TokenLimit(100)",
      "label": "Token上限 100",
      "instruction": "Only use 100 tokens for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "TokenLimit(50)",
      "label": "Token上限 50",
      "instruction": "Only use 50 tokens for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "TokenLimit(500)",
      "label": "Token上限 500",
      "instruction": "Only use 500 tokens for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "WordLimit(1)",
      "label": "词数上限 1",
      "instruction": "Only use 1 words for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "WordLimit(10)",
      "label": "词数上限 10",
      "instruction": "Only use 10 words for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "WordLimit(100)",
      "label": "词数上限 100",
      "instruction": "Only use 100 words for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "WordLimit(15)",
      "label": "词数上限 15",
      "instruction": "Only use 15 words for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "WordLimit(25)",
      "label": "词数上限 25",
      "instruction": "Only use 25 words for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "WordLimit(5)",
      "label": "词数上限 5",
      "instruction": "Only use 5 words for your answer.",
      "dimensions": [
        "length"
      ]
    },
    {
      "id": "WordLimit(50)",
      "label": "词数上限 50",
      "instruction": "Only use 50 words for your answer.",
      "dimensions": [
        "length"
      ]
    }
  ],
  "experiments": [
    {
      "id": "reasoning",
      "name": "数学与选择题提示对照",
      "records": 74400,
      "questions": 600,
      "models": 4,
      "formula": "600题 × 4模型 × 31策略",
      "benchmarks": "GSM8K / MATH500 / MMLU-Pro",
      "modelsLabel": "DeepSeek Flash · HY4 preview · 两款Qwen"
    },
    {
      "id": "document_qa",
      "name": "文档问答提示对照",
      "records": 74800,
      "questions": 200,
      "models": 2,
      "formula": "200题 × 2模型 × 187条件",
      "benchmarks": "NQ-Open，10/20篇资料与无资料对照",
      "modelsLabel": "Qwen2.5 7B · Qwen3 8B"
    },
    {
      "id": "code_generation",
      "name": "代码独立生成",
      "records": 90210,
      "questions": 194,
      "models": 3,
      "formula": "194题 × 3模型 × 31策略 × 5次采样",
      "benchmarks": "CodePromptEval",
      "modelsLabel": "DeepSeek Flash · Qwen2.5 7B · Qwen3 8B"
    },
    {
      "id": "document_positions",
      "name": "文档位置专项",
      "records": 3600,
      "questions": 200,
      "models": 2,
      "formula": "200题 × 2模型 × 9位置",
      "benchmarks": "NQ-Open，固定20篇资料",
      "modelsLabel": "Qwen2.5 7B · Qwen3 8B"
    },
    {
      "id": "code_repair",
      "name": "代码反馈修复专项",
      "records": 5576,
      "questions": 164,
      "models": 2,
      "formula": "164题 × 2模型 ×（1份初稿 + 4组×4轮）",
      "benchmarks": "HumanEval+ Mini",
      "modelsLabel": "Qwen2.5 7B · Qwen3 8B"
    }
  ],
  "totalRecords": 248586,
  "excludedRecords": 465,
  "collectionNotes": [
    "31种是实际策略清单；四维是说明与标签，部分策略有多个标签。",
    "响应条数、独立题目、采样次数、修改轮次分别记录。",
    "代码生成465条环境排除记录保留为空评分，不记作模型失败。"
  ],
  "cleaning": {
    "title": "同样的含义，不同的字段名",
    "intro": "点选一个红色字段，跟随映射规则，查看它在清洗后统一保存的位置。",
    "legend": "红色表示同义异名字段，不表示数据错误。",
    "projectionNote": "来源字段视图根据实际清洗代码生成，仅显示映射所需字段；数值来自同条已保存记录，省略问答全文。",
    "savedFormat": "实际保存：CSV（gzip压缩）；JSON为同一记录的结构化阅读视图。",
    "headers": [
      "record_id",
      "experiment_id",
      "model_id",
      "benchmark",
      "question_key",
      "prompt_id",
      "timestamp",
      "input_tokens",
      "output_tokens",
      "latency_seconds",
      "finish_reason",
      "is_truncated",
      "metric_name",
      "metric_value",
      "environment_excluded",
      "document_count",
      "evidence_position",
      "independent_sample",
      "revision_round",
      "feedback_type",
      "parent_record_key"
    ],
    "records": {
      "reasoning": {
        "record_id": "ff06fa0216f19970e31b288b",
        "experiment_id": "reasoning",
        "model_id": "deepseek",
        "benchmark": "mmlu",
        "question_key": "8f53c60f78a25a18b86b2263",
        "prompt_id": "NoCoT",
        "timestamp": null,
        "input_tokens": 214,
        "output_tokens": 3,
        "latency_seconds": 1.261,
        "finish_reason": "stop",
        "is_truncated": false,
        "metric_name": "source_score",
        "metric_value": 1.0,
        "environment_excluded": false,
        "document_count": null,
        "evidence_position": null,
        "independent_sample": null,
        "revision_round": null,
        "feedback_type": null,
        "parent_record_key": null
      },
      "document_qa": {
        "record_id": "d78048df8d60560fb1ba8831",
        "experiment_id": "document_qa",
        "model_id": "qwen",
        "benchmark": "NaturalQuestions-Open",
        "question_key": "e976796b7f1f9c8b9b536f18",
        "prompt_id": "NoCoT",
        "timestamp": "2026-10-20T16:17:23+00:00",
        "input_tokens": 2980,
        "output_tokens": 7,
        "latency_seconds": 1.4602,
        "finish_reason": "stop",
        "is_truncated": false,
        "metric_name": "final_answer_contains",
        "metric_value": 1.0,
        "environment_excluded": false,
        "document_count": 20,
        "evidence_position": 10,
        "independent_sample": null,
        "revision_round": null,
        "feedback_type": null,
        "parent_record_key": null
      }
    },
    "fields": [
      {
        "id": "output_tokens",
        "name": "输出Token",
        "type": "integer / null",
        "reasoningKey": "输出词元数",
        "documentKey": "response.usage.completion_tokens",
        "rule": "读取各自来源的输出计数，转成整数；没有记录时保留null。",
        "code": "output_tokens = parse_int(row[\"输出词元数\"])\noutput_tokens = parse_int(response[\"usage\"][\"completion_tokens\"])"
      },
      {
        "id": "input_tokens",
        "name": "输入Token",
        "type": "integer / null",
        "reasoningKey": "输入词元数",
        "documentKey": "response.usage.prompt_tokens",
        "rule": "统一计数类型，保留输入与输出两个字段。",
        "code": "input_tokens = parse_int(row[\"输入词元数\"])\ninput_tokens = parse_int(response[\"usage\"][\"prompt_tokens\"])"
      },
      {
        "id": "finish_reason",
        "name": "结束原因",
        "type": "category / null",
        "reasoningKey": "结束原因",
        "documentKey": "response.choices[0].finish_reason",
        "rule": "读取原始结束原因；length与stop分别保留，空值不补成正常结束。",
        "code": "finish_reason = row[\"结束原因\"] or None\nfinish_reason = response[\"choices\"][0].get(\"finish_reason\")"
      },
      {
        "id": "model_id",
        "name": "模型标识",
        "type": "category",
        "reasoningKey": "模型标识",
        "documentKey": "model",
        "rule": "将不同来源的模型名称映射到可连接的规范标识。",
        "code": "model_id = MODEL_MAP[source_model]\n# Qwen/Qwen2.5-7B-Instruct → qwen"
      }
    ],
    "rules": [
      {
        "title": "统一字段与类型",
        "text": "模型、Token、结束原因、时间与布尔值按数据字典规范。"
      },
      {
        "title": "保留真实缺失",
        "text": "CSV空单元格表示null；缺失Token和耗时不补0。"
      },
      {
        "title": "区分评分含义",
        "text": "用metric_name保留源评分、答案包含、代码测试等口径。"
      },
      {
        "title": "保持物理计数",
        "text": "共享修复初稿只计一次；环境排除单列。"
      }
    ],
    "provenance": {
      "fieldMapping": "scripts/cleaning/clean_baseline_data.py: normalize_reasoning / clean_document_qa",
      "unifiedBuilder": "scripts/cleaning/build_unified_features.py",
      "sampleSource": "data/processed/all_records.csv.gz",
      "sampleSHA256": "f06493928672360c94131e550a3bebbf4ce11f3f64ef271d868d33a697c64552"
    }
  },
  "topics": [
    {
      "id": "budget",
      "group": "general",
      "title": "Token投入与边际收益",
      "question": "多用一些Token，能多解决多少问题？",
      "summary": "实测点与log拟合一起呈现，比较模型与任务内的边际收益变化。"
    },
    {
      "id": "scale",
      "group": "general",
      "title": "模型规模与任务表现",
      "question": "模型规模与成功率、输出开销有什么关系？",
      "summary": "使用已核实参数量和同条件结果考察规模效应，保留未知规模模型的表现对照。"
    },
    {
      "id": "concise",
      "group": "general",
      "title": "简洁思考的效率收益",
      "question": "保持分步要求，能否压缩冗余表达？",
      "summary": "17组跨任务对照全部缩短输出，15组得分点估计持平或提高。"
    },
    {
      "id": "limits",
      "group": "general",
      "title": "限制越紧，输出反而更长",
      "question": "极端限长为什么可能适得其反？",
      "summary": "词数上限10→1，12个模型×题库分组中9组实际输出增加。"
    },
    {
      "id": "language",
      "group": "specific",
      "title": "数学任务的语言模板",
      "question": "相同数学题，中文作答模板会改变什么？",
      "summary": "MATH500四模型全部缩短输出、三模型提分；其他题库可切换查看。"
    },
    {
      "id": "position",
      "group": "specific",
      "title": "关键证据放在哪里",
      "question": "移动唯一相关文档，模型表现会怎样变化？",
      "summary": "同题同资料，九个实测位置；模型优势随位置改变。"
    },
    {
      "id": "feedback",
      "group": "specific",
      "title": "让执行反馈指向错误",
      "question": "具体反例比“再检查一下”更有用吗？",
      "summary": "Qwen3第四轮修改后，具体反例141/164，自查129/164。"
    }
  ],
  "conclusion": {
    "title": "让每一条结论都能追到证据",
    "summary": "从提示策略出发，连接模型、任务、输出开销与反馈，把研究过程整理成可复算、可探索的证据链。",
    "principles": [
      {
        "title": "按任务选择表达",
        "text": "先比较质量与Token，再决定使用哪种模板。"
      },
      {
        "title": "给预算保留空间",
        "text": "简洁表达与极端限长分别测量，观察实际输出。"
      },
      {
        "title": "组织好资料与反馈",
        "text": "移动证据、给出执行反例，检查具体条件下的变化。"
      }
    ],
    "limits": [
      "当前研究覆盖有限模型、题库与固定采集设置。",
      "数学、问答和代码保留各自评分定义，部分自动评分还需人工抽查。",
      "测试通过表示通过当前测试集；结果解释与数据范围一并保留。"
    ]
  }
};

const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (value) => Number(value).toLocaleString('zh-CN');
const dimensionName = (id) => researchContent.dimensions.find(d => d.id === id)?.name || id;
const typeOf = (value) => value === null ? 'null' : typeof value === 'number' ? (Number.isInteger(value) ? 'integer' : 'number') : typeof value;

function taskDetail(id) {
  const task = researchContent.question.tasks.find(t => t.id === id) || researchContent.question.tasks[0];
  return `<article class="rc-task-example" data-rc-task-example="${esc(task.id)}"><header class="rc-task-heading"><h3>${esc(task.name)}</h3><p>${esc(task.variable)}</p></header><p class="rc-task-question">${esc(task.question)}</p><div class="rc-task-case"><h4>${esc(task.exampleTitle)}</h4><p class="rc-example-question">${esc(task.example)}</p><p class="rc-example-answer">${esc(task.answer)}</p></div><p class="rc-task-metric"><strong>评价</strong>${esc(task.metric)}</p><p class="rc-source-note">${esc(task.source.split(" · ")[0])}</p></article>`;
}

export function renderQuestion(selected = 'math') {
  const q = researchContent.question;
  return `<section class="rc-question" data-rc-question><p class="rc-lead">${esc(q.lead)}</p><div class="rc-central-question"><strong>${esc(q.central)}</strong></div><svg class="rc-branch-lines" viewBox="0 0 900 90" fill="none" aria-hidden="true"><path d="M450 0V30M150 90V50Q150 35 165 35H735Q750 35 750 50V90M450 35V90" stroke="currentColor" stroke-width="1.5"/><circle cx="450" cy="35" r="5" fill="currentColor" stroke="none"/></svg><div class="rc-task-grid">${q.tasks.map(t => taskDetail(t.id)).join('')}</div></section>`;
}

function promptItems(dimension = 'all') {
  const list = researchContent.prompts.filter(p => dimension === 'all' || p.dimensions.includes(dimension));
  return `<div class="rc-prompt-list">${list.map(p => `<article class="rc-prompt-item" title="${esc(p.instruction)}"><strong>${esc(p.label)}</strong><code>${esc(p.id)}</code><span class="rc-prompt-tags">${p.dimensions.map(d => esc(dimensionName(d))).join(' / ')}</span></article>`).join('')}</div>`;
}

export function renderCollection() {
  const data = researchContent;
  return `<section class="rc-collection" data-rc-collection><p class="rc-lead">同一道题保持不变，分别改变语言、回答组织、长度预算与表达格式。</p><div class="rc-dimension-grid">${data.dimensions.map(d => `<article class="rc-dimension"><h3>${esc(d.name)}</h3><p>${esc(d.description)}</p><div class="rc-dimension-examples">${d.examples.map(e => `<span>${esc(e)}</span>`).join('')}</div></article>`).join('')}</div><section class="rc-collection-ledger"><div class="rc-section-heading"><h3>五项实验，${number(data.totalRecords)}条物理响应</h3><p>题目 × 模型 × 条件 × 采样或修改协议</p></div><div class="rc-table-wrap" tabindex="0" role="region" aria-label="实验数据表，可横向滚动"><table class="rc-experiment-table"><thead><tr><th scope="col">实验与任务</th><th scope="col">计算关系</th><th scope="col">响应记录</th><th scope="col">题库与模型</th></tr></thead><tbody>${data.experiments.map(e => `<tr><th scope="row">${esc(e.name)}</th><td class="rc-formula">${esc(e.formula)}</td><td class="rc-numeric">${number(e.records)}</td><td><span>${esc(e.benchmarks)}</span><small>${esc(e.modelsLabel)}</small></td></tr>`).join('')}</tbody></table></div><ul class="rc-method-notes">${data.collectionNotes.map(n => `<li>${esc(n)}</li>`).join('')}</ul></section><section class="rc-prompt-catalog"><div class="rc-section-heading"><h3>实际采用的31种策略</h3><p>四个维度是考察标签，部分策略跨维度。</p></div>${promptItems()}</section></section>`;
}

function sourceValue(source, key) {
  const row = researchContent.cleaning.records[source];
  if (key === 'model_id' && source === 'document_qa') return 'Qwen/Qwen2.5-7B-Instruct';
  return row[key];
}
function sourceFieldTable(source) {
  const d=researchContent.cleaning;
  const fieldName=f=>{
    if(source==='reasoning')return `<mark class="rc-field-token">${esc(f.reasoningKey)}</mark>`;
    const path=f.documentKey.split('.'),leaf=path.pop(),prefix=path.length?path.join('.')+'.':'';
    return `${prefix?`<span class="rc-field-path">${esc(prefix)}</span>`:''}<mark class="rc-field-token">${esc(leaf)}</mark>`;
  };
  return `<table class="rc-origin-table"><thead><tr><th scope="col">来源字段</th><th scope="col">原始值</th></tr></thead><tbody>${d.fields.map(f=>`<tr><th scope="row">${fieldName(f)}</th><td>${esc(String(sourceValue(source,f.id)))}</td></tr>`).join('')}</tbody></table>`;
}
function unifiedRecordTable() {
  const d=researchContent.cleaning;
  const keys=['model_id','benchmark','input_tokens','output_tokens','finish_reason','metric_name','metric_value','document_count','evidence_position'];
  const mapped=new Set(d.fields.map(f=>f.id));
  const cell=value=>value===null?'<span class="rc-null">null</span>':esc(String(value));
  return `<table class="rc-saved-table rc-combined-records"><thead><tr><th scope="col">统一字段</th><th scope="col" data-rc-record="reasoning">推理记录</th><th scope="col" data-rc-record="document_qa">文档记录</th></tr></thead><tbody>${keys.map(key=>`<tr data-rc-saved-field="${esc(key)}"${mapped.has(key)?' class="is-mapped"':''}><th scope="row"><code>${esc(key)}</code></th><td data-source="reasoning">${cell(d.records.reasoning[key])}</td><td data-source="document_qa">${cell(d.records.document_qa[key])}</td></tr>`).join('')}</tbody></table>`;
}
const flowArrow = '<svg viewBox="0 0 40 24" aria-hidden="true"><path d="M2 12h32m-9-9 9 9-9 9" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>';
export function renderCleaning(field = 'output_tokens', source = 'reasoning', view = 'csv') {
  const d=researchContent.cleaning;
  return `<section class="rc-cleaning" data-rc-cleaning><figure class="rc-cleaning-figure" aria-labelledby="rc-cleaning-caption"><div class="rc-figure-legend"><span><i class="rc-legend-red" aria-hidden="true"></i>红色：同义异名字段</span><span><i class="rc-legend-blue" aria-hidden="true"></i>蓝色：统一字段与保存值</span><p>相同含义，不同名字；红色不表示数据错误。</p></div><div class="rc-cleaning-stage"><section class="rc-clean-panel rc-panel-a" aria-labelledby="rc-panel-a-title"><header><span class="rc-panel-letter" aria-hidden="true">A</span><h3 id="rc-panel-a-title">两种来源</h3></header><article class="rc-origin-block" data-rc-source="reasoning"><h4>推理实验 · 源表格</h4>${sourceFieldTable('reasoning')}</article><article class="rc-origin-block" data-rc-source="document_qa"><h4>文档问答 · API字段</h4>${sourceFieldTable('document_qa')}</article></section><div class="rc-stage-arrow" aria-hidden="true">${flowArrow}</div><section class="rc-clean-panel rc-panel-b" aria-labelledby="rc-panel-b-title"><header><span class="rc-panel-letter" aria-hidden="true">B</span><h3 id="rc-panel-b-title">统一字段与类型</h3></header><p class="rc-map-note">源表字段 / API末级字段</p><div class="rc-mapping-list">${d.fields.map(f=>`<article class="rc-mapping-row" data-rc-mapping="${esc(f.id)}"><div class="rc-map-origin"><mark class="rc-field-token">${esc(f.reasoningKey)}</mark><mark class="rc-field-token">${esc(f.documentKey.split('.').at(-1))}</mark></div><span class="rc-map-arrow" aria-hidden="true">${flowArrow}</span><div class="rc-map-target"><code>${esc(f.id)}</code><span>${esc(f.type)}</span></div><p>${esc(f.rule)}</p></article>`).join('')}</div></section><div class="rc-stage-arrow" aria-hidden="true">${flowArrow}</div><section class="rc-clean-panel rc-panel-c" aria-labelledby="rc-panel-c-title"><header><span class="rc-panel-letter" aria-hidden="true">C</span><h3 id="rc-panel-c-title">按同一结构保存</h3></header><p class="rc-map-note">两条已保存记录的9个关键字段</p>${unifiedRecordTable()}<p class="rc-record-note">模型名称归一，数值类型一致；不适用的位置字段保持null。</p></section></div><section class="rc-storage-summary" aria-label="统一格式与清洗原则"><div class="rc-storage-file"><span class="rc-panel-letter" aria-hidden="true">D</span><div><strong>统一落盘</strong><code>all_records.csv.gz</code><p>21个统一字段；每条物理响应保存一行。</p></div></div><div class="rc-cleaning-rules">${d.rules.map(r=>`<article><h4>${esc(r.title)}</h4><p>${esc(r.text)}</p></article>`).join('')}</div></section><figcaption id="rc-cleaning-caption"><strong>从不同来源，到同一份可分析的数据。</strong><span>${esc(d.projectionNote)} 实际保存格式为gzip压缩CSV。</span></figcaption></figure></section>`;
}

export function renderConclusion() {
  const d = researchContent.conclusion;
  return `<section class="rc-conclusion"><p class="rc-lead">${esc(d.summary)}</p><div class="rc-principles">${d.principles.map(p => `<article><h3>${esc(p.title)}</h3><p>${esc(p.text)}</p></article>`).join('')}</div><div class="rc-conclusion-scope"><h3>研究范围与后续核对</h3><ul>${d.limits.map(l => `<li>${esc(l)}</li>`).join('')}</ul></div><p class="rc-source-note">原始材料、清洗规则、统计与SVG图形分别保留；系统和报告使用同一组数据与结论。</p></section>`;
}

function csvCell(value) {
  const text = value === null || value === undefined ? '' : typeof value === 'boolean' ? String(value) : String(value);
  return /[",\r\n]/.test(text) ? '"'+text.replaceAll('"','""')+'"' : text;
}
export function cleaningSampleCSV() {
  const d=researchContent.cleaning;
  return [d.headers.join(','),...Object.values(d.records).map(row=>d.headers.map(key=>csvCell(row[key])).join(','))].join('\r\n')+'\r\n';
}
export function bindContent(container, options = {}) {
  // Research chapters are static presentation figures; no local controls to bind.
  return () => {};
}

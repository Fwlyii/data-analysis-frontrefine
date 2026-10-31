# Lost in the Middle: nine-position extension

## Frozen protocol

200 identical questions, 20 identical documents per question, nine measured positions, NoCoT; 2 analyzed model(s), 3,600 fresh responses. Historical anchors are compared separately, never pooled into the curve.

Primary metric: extracted final-answer containment; strict final exact match, first-line containment, and full-response containment are sensitivity analyses. None is a new human semantic adjudication.

## Position profile

| Position | Qwen2.5-7B-Instruct | Qwen3-8B |
| --- | ---: | ---: |
| 1 | 54.5% | 71.0% |
| 3 | 52.5% | 61.0% |
| 5 | 50.0% | 61.0% |
| 8 | 52.0% | 61.5% |
| 10 | 52.5% | 61.5% |
| 13 | 50.5% | 58.5% |
| 15 | 51.0% | 58.5% |
| 18 | 51.0% | 59.0% |
| 20 | 56.5% | 59.0% |

## Prespecified paired contrasts

| Model | Contrast | Difference (pp) | 95% interval (pp) |
| --- | --- | ---: | ---: |
| Qwen2.5-7B-Instruct | position1-position10 | +2.00 | [-4.00, 8.00] |
| Qwen2.5-7B-Instruct | position20-position10 | +4.00 | [-0.51, 9.00] |
| Qwen2.5-7B-Instruct | front_band-center_band | +0.67 | [-2.50, 3.83] |
| Qwen2.5-7B-Instruct | back_band-center_band | +1.17 | [-1.67, 4.17] |
| Qwen3-8B | position1-position10 | +9.50 | [4.50, 15.00] |
| Qwen3-8B | position20-position10 | -2.50 | [-7.00, 2.00] |
| Qwen3-8B | front_band-center_band | +3.83 | [0.67, 7.17] |
| Qwen3-8B | back_band-center_band | -1.67 | [-4.33, 0.83] |

## Exploratory model-by-position comparisons

Qwen3-8B minus Qwen2.5-7B-Instruct; resample the same question across both models and all positions. Models were collected on separate dates, with identical saved prompts and generation settings. Historical three-position results are not pooled into these contrasts.

| Comparison | Difference (pp) | 95% interval (pp) |
| --- | ---: | ---: |
| model_gain_at_position01 | +16.50 | [10.00, 23.50] |
| model_gain_at_position03 | +8.50 | [2.00, 15.00] |
| model_gain_at_position05 | +11.00 | [4.50, 17.50] |
| model_gain_at_position08 | +9.50 | [3.50, 16.00] |
| model_gain_at_position10 | +9.00 | [3.00, 15.00] |
| model_gain_at_position13 | +8.00 | [1.50, 14.50] |
| model_gain_at_position15 | +7.50 | [0.50, 14.00] |
| model_gain_at_position18 | +8.00 | [1.00, 15.00] |
| model_gain_at_position20 | +2.50 | [-4.50, 9.00] |
| model_gain_over_all_positions | +8.94 | [4.28, 13.78] |
| front_band_gain-minus-back_band_gain | +6.00 | [1.17, 11.17] |
| gain_position1-minus-position20 | +14.00 | [5.50, 23.00] |

## 中文结论与解释

### Qwen2.5-7B-Instruct

第 1、10、20 位的最终答案包含率分别为 54.5%、52.5%、56.5%。九点轮廓的起伏及预设配对区间见上表。

首位与第 10 位之间，38/200 道题的二元评分不同（19.0%）：21 道仅首位命中，17 道仅中位命中。两类变化的净平均差为 +2.00 个百分点。逐题统计同时记录了两个方向的变化。

文档位置全部命中的题目 63 道，全部未命中 59 道，至少发生一次评分变化 78 道（39.0%），反映位置变动下的成功集合更替。

新旧批次三个相同提示锚点的评分一致 596/600（99.33%）。

### Qwen3-8B

九点轮廓体现明确的首位优势：第 1 位相对第 10 位高 9.50 个百分点，95% 区间 [4.50, 15.00]；第 20 位相对第 10 位为 -2.50 个百分点。

首位与第 10 位之间，31/200 道题的二元评分不同（15.5%）：25 道仅首位命中，6 道仅中位命中。两类变化的净平均差为 +9.50 个百分点。逐题统计同时记录了两个方向的变化。

文档位置全部命中的题目 90 道，全部未命中 44 道，至少发生一次评分变化 66 道（33.0%），反映位置变动下的成功集合更替。

新旧批次三个相同提示锚点的评分一致 591/600（98.50%）。


## Interpretation limits

Confidence intervals resample the 200 questions as paired clusters, preserving all positions. Intervals are pointwise/exploratory and not adjusted for multiplicity. Nine positions improve horizontal resolution but do not increase independent question count. The same provider model ID does not guarantee unchanged weights across dates. U-shape claims require both front and back advantages over the center; a front advantage alone is insufficient.

See `historical-anchor-comparison.csv` for batch drift and `position-summary.csv` for all four scoring rules. SVG labels use Times New Roman when installed; lines only connect observed positions.

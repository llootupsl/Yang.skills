<!-- 作者: 阿洋 -->
# Parallel Sub-Agent Protocol（并行子 Agent 协议）

定义 yang-score v4 的三陪审并行评分机制，包括子 Agent 角色分工、输出 Schema、主 Agent 合成规则、争议仲裁与超时处理。

---

## §1 适用范围

**适合并行的 skill：**

| Skill | 并行策略 | 理由 |
|-------|---------|------|
| yang-score | 3-Judge 并行评分 | 三个陪审分别评估不同维度组，互不依赖，可完全并行 |
| yang-trends | 3-Source 并行抓取 | 三个趋势源（微博/知乎/AI热点）独立抓取，互不干扰 |
| yang-shoot | 3-Version 并行生成 | 三个拍摄版本独立生成，主 Agent 择最优 |
| yang-retro | 3-Perspective 并行复盘 | 三个复盘视角（数据/内容/策略）独立分析，主 Agent 合成 |

**不适合并行的 skill：**

| Skill | 原因 |
|-------|------|
| yang-bump | 严格顺序状态机——校准样本计数、bucket 重算、rubric 升版必须按序执行 |
| yang-predict | 顺序依赖链——必须等待 yang-score 输出完成后才能进行预测建模 |
| yang-publish | 原子 buffer 计数器——发布操作涉及 buffer 递减，必须串行保证一致性 |

---

## §2 三陪审角色定义

**Agent-A (judge-hook-emotion):**

"你的唯一任务是从钩子力和情绪力两个维度评估此脚本。你特别擅长识别黄金3秒钩子类型和情绪刺点的植入位置。对于你不擅长的结构力和文案力维度，给出保守估计分（≥2 ≤4）。"

**Agent-B (judge-structure-copy):**

"你的唯一任务是从结构力和文案力两个维度评估此脚本。你特别擅长分析叙事骨架（递进式/并列式/对比式/故事式/问题解决式）和文案的传播效率。对于你不擅长的钩子力和人设力维度，给出保守估计分（≥2 ≤4）。"

**Agent-C (judge-persona-virality):**

"你的唯一任务是从人设力、传播力和节奏力三个维度评估此脚本。你特别擅长识别人设戳（专业层/经历层/价值观层/性格层/审美层）和传播因子（共鸣力/冲突性/稀缺感/社交货币）。对于你不擅长的维度，给出保守估计分（≥2 ≤4）。"

---

## §3 子 Agent 输出 JSON Schema

```json
{
  "judge_role": "string: judge-hook-emotion | judge-structure-copy | judge-persona-virality",
  "script_id": "string, 被评脚本的唯一标识",
  "scores": {
    "hook": { "value": "integer 0-10", "justification": "string ≤50字" },
    "emotion": { "value": "integer 0-10", "justification": "string ≤50字" },
    "structure": { "value": "integer 0-10", "justification": "string ≤50字" },
    "copywriting": { "value": "integer 0-10", "justification": "string ≤50字" },
    "persona": { "value": "integer 0-10", "justification": "string ≤50字" },
    "virality": { "value": "integer 0-10", "justification": "string ≤50字" },
    "rhythm": { "value": "integer 0-10", "justification": "string ≤50字" }
  },
  "overall_comment": "string ≤80字",
  "knowledge_references": ["string array, 格式 '来源-模块'"]
}
```

---

## §4 主 Agent 合成规则

对每个维度 `d ∈ {hook, emotion, structure, copywriting, persona, virality, rhythm}`：

```
scores = [A.d.value, B.d.value, C.d.value]
median_d = median(scores)
range_d = max(scores) - min(scores)

If range_d > 3:
    mark disputed, enter arbitration
If range_d ≤ 3:
    final_d = median_d
```

**一致度计算**：

```
agreement_score = 1 - (disputed_dimensions_count / 7)
```

| agreement_score | 解释 |
|----------------|------|
| 1.0 | 完全一致——三个陪审在所有 7 个维度上极差 ≤3 |
| ≥ 0.71 | 高度一致——仅 1-2 个维度有分歧 |
| ≥ 0.43 | 中等一致——3-4 个维度有分歧，仲裁后可用 |
| < 0.43 | 低一致——5+ 维度有分歧，建议人工审核 |

---

## §5 争议仲裁流程

对每个被标记为 `disputed` 的维度：

1. 定位产生极端分的子 Agent（max 或 min 端）
2. 发起对立辩论：

   ```
   维度{d}：Agent-X给了{score_X}分（理由:{justification_X}），
   Agent-Y给了{score_Y}分（理由:{justification_Y}）。
   请各自审视对方的理由，重新打分。
   ```

3. 双方重新打分后，取两者的平均值作为最终分数：

   ```
   final_d = (rescored_X + rescored_Y) / 2
   ```

4. 在最终输出 JSON 中标记：

   ```json
   {
     "dimension_d_resolved_by_debate": true
   }
   ```

---

## §6 超时处理

- 子 Agent 单次评分超时阈值：**3 分钟**
- 超时子 Agent 标记为 `timed_out`
- 最终分数计算：取剩余未超时 Agent 的中位数

```
If 1 timed_out:
    final_d = median(remaining_2_scores)
If 2 timed_out:
    该维度标记为 single_source，仅用唯一存活 Agent 的分数
    并在最终输出中标注 low_confidence: true
If 3 timed_out:
    所有维度标记为 system_failure
    提示用户重试或手动评分
```
---
name: yang-init
version: "2.0"
description: Yang.skills 系统初始化与脚手架生成。创建项目目录结构、模板文件、状态文件。
trigger-words: [初始化, init, 首次使用, setup, 开始使用, 第一次用, 初始化系统, 设置项目]
tags: [初始化, 安装, 配置, 入口]
author: 阿洋
argument-hint: "[output-dir]"
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# yang-init · 系统初始化与脚手架

## ⚡ 紧凑核心规则

**初始化5步**：①环境检测(Python≥3.10+虚拟环境) → ②依赖安装(按tier:core/media/full) → ③数据湖初始化(project_data.db 11张表) → ④生成项目结构+核心文件(模板变量替换) → ⑤写入状态文件(.yang-state.json v2.1)。每步有检查点，失败触发对应编码不继续。

**首次运行指引3步**：①yang-persona(建立人设，必填5项) → ②yang-competitor-search+yang-benchmark(发现竞品+建立基线) → ③yang-trends→yang-score-blind→yang-publish→yang-retro(选题→打分→发布→复盘闭环)。最小可用路径：init→persona→trends→score-blind→publish→retro。

**渐进式加载**：初始化完成后，输出"→ 首次使用建议：说'找选题'开始你的第一条内容创作"。Agent只需加载主SKILL.md的紧凑核心规则段，按需加载子skill。

> **前置条件**：无（这是整个系统的入口）
>
> **产生**：rubric_notes.md、WORKFLOW.md、STATUS.md、.yang-state.json、candidates.md、benchmark.md、脚本/预测/视频/对标 目录
>
> **依赖**：starter-rubrics/、templates/

---

## 前置条件检查

> [前置条件] 无（这是整个系统的入口 skill，无需任何前置条件）

读取 `.yang-state.json`:
- 若 `.yang-state.json` 已存在 → 警告"项目已初始化，重复初始化可能覆盖现有配置"，询问用户是否继续
- 若不存在 → 正常进入初始化流程

---

## 工作流

### 安装层级 (--tier)

| tier | 安装内容 | 预计时间 | 解锁功能 |
|------|----------|----------|----------|
| `core`（默认） | requirements-core.txt | 30 秒 | 打分 + 预测 + 复盘 + 润色 + 人设管理 |
| `media` | core + requirements-media.txt | 3-5 分钟 | core + yang-benchmark 视频分析 |
| `full` | core + media + requirements-full.txt | 10-20 分钟 | media + GraphRAG 知识图谱增强 + 贝叶斯校准 |

若用户未指定 --tier → 默认安装 core
安装完成后提示："输入「升级到 media」安装视频分析功能 | 输入「升级到完整版」安装全部依赖"

### Step 1: 环境检测

检测 Python 版本 >= 3.10。若不满足，报错退出。

```bash
python --version
```

> **✅ 检查点 1**：确认 Python 版本 ≥ 3.10。若不满足，触发 `INIT_PYTHON_VERSION` 失败模式，不继续后续步骤。

### 虚拟环境检测

检测当前环境：
- 检查 `VIRTUAL_ENV` 环境变量
- 检查 `CONDA_PREFIX` 环境变量

若不在虚拟环境中：
  → 输出警告并询问：
    ```
    ⚠️ 未检测到虚拟环境。建议在虚拟环境中安装以避免污染系统 Python。
    输入 'y' 自动创建 .venv 并继续 / 输入 'n' 跳过（直接安装到系统 Python）
    ```
  → 用户选 'y'：执行 `python -m venv .venv` → 激活虚拟环境 → 继续安装
  → 用户选 'n'：记录警告日志 → 继续安装

若已在虚拟环境中 → 静默继续

> **✅ 检查点 2**：确认虚拟环境状态已明确（已激活 / 用户确认跳过 / 已自动创建）。不在虚拟环境中且用户未确认时，不得静默继续。

### Step 2: 依赖安装（按 tier）

- tier=core（默认）:
  ```bash
  pip install -r requirements-core.txt
  ```
- tier=media:
  ```bash
  pip install -r requirements-core.txt
  pip install -r requirements-media.txt
  ```
- tier=full:
  ```bash
  pip install -r requirements-full.txt
  ```

若对应的 requirements 文件不存在，打印错误并退出。

> **✅ 检查点 3**：确认对应 tier 的 requirements 文件存在且 pip install 成功。若安装失败，触发 `INIT_VENV_FAILED` 失败模式，不继续后续步骤。

🔍 检测跨模型审计通道...
  → mcp__llm-chat__chat 工具: <可用/不可用>
  → 若不可用: ⚠️ 跨模型审计 (Channel C) 不可用。
    yang-bump --strict 模式下将自动降级为自审模式。
    安装指引: 参见 skills/yang-score-blind/SKILL.md § Channel C 配置

### Step 2.5: 竞品系统依赖确认

确认以下竞品依赖已安装：

```bash
pip install jieba opencv-python-headless requests
```

若 `sherlock-project` 可通过 pip 安装（可选，用于跨平台账号反查）：
```bash
pip install sherlock-project  # 可选；若失败不影响核心功能
```

检查竞品搜索工具链：
- `adapters/competitor-search/search.py` 存在 → ✓ 多平台竞品搜索就绪
- `adapters/competitor-data/collector.py` 存在 → ✓ 多源数据采集就绪
- `adapters/competitor-monitor/monitor.py` 存在 → ✓ 竞品监控系统就绪
- `adapters/landscape/analyze.py` 存在 → ✓ 赛道格局分析就绪

若任一文件缺失，打印警告但不中断初始化：
```
⚠️ 缺失竞品工具文件: [文件名]
请检查 Yang.skills 包是否完整。
```

### Step 3: 浏览器驱动安装

```bash
if tier in [media, full]:
    playwright install chromium
else:
    # tier = core：跳过 Playwright，仅输出提示
    echo "💡 当前 tier=core，跳过 Playwright 安装。升级到 media/full 以启用浏览器驱动。"
```

若 playwright 尚未安装（pip 未包含），打印"playwright 将通过 pip 自动安装..."

### Step 4: 数据湖初始化

```python
from adapters.data_pipeline.db import init_db
init_db("project_data.db")
```

创建包含 11 张表（videos, frames, comments, emotions, predictions, trends, competitors, competitor_snapshots, competitor_strategy_changes, landscape_snapshots, competitor_monitors）的 SQLite 数据库。

> **✅ 检查点 4**：确认 `project_data.db` 已创建且可读写。若初始化失败，触发 `INIT_DB_FAILED` 失败模式，询问用户是否跳过（竞品功能将不可用但核心功能正常）。

🧪 **实验性 Web 看板**（可选）：
```bash
cd tools/dashboard
python data_bridge.py                    # 生成 data.json
# 然后在浏览器中打开 index.html
# macOS:     open index.html
# Windows:   start index.html
# Linux:     xdg-open index.html
```

### Step 5: GraphRAG 索引构建（可选）

询问用户："是否立即构建知识图谱索引？（约需 5-15 分钟，可稍后运行 python tools/graphrag_index.py --init）"

若用户同意 → 运行 `python tools/graphrag_index.py --init`

### Step 6: 确认用户身份和垂直领域

询问用户：
- 用什么内容平台？（抖音/小红书/B站/视频号/YouTube/TikTok）
- 做什么垂直领域？（职场/情感/知识/搞笑/美食/美妆/科技/财经/教育/其他）
- 当前粉丝数（大致即可，用于对标配置）

### Step 6.5: 建立创作人设档案（新增 · yang-persona）

询问用户：

"接下来帮你建立创作人设档案。
这会让你之后的文章更有「活人感」——读者会觉得是一个真人在说话，
而不是 AI 在输出信息。你也可以跳过，随时回来补充。

要现在建立吗？(y/n/稍后)"

若用户选"y" → 进入人设填写流程
若用户选"n"或"稍后" → 跳过，记录 persona_exists: false，继续 Step 7

#### 人设填写流程

**必填项（逐项引导）：**

1. **身份**
   引导："先来最简单的——你是谁？用一句话说清楚。比如：做了三年AI内容的创业者 / 在大厂做过五年产品的独立开发者"

2. **核心价值观**
   引导："你相信什么？一句话。比如：技术应该让人更有创造力，而不是更焦虑 / 好的产品不需要说明书"

3. **个人故事（至少 3 个）**
   引导："现在说说你的故事。不是你简历上的经历，是那种有场景、有情绪、有转折的真实故事。

   比如'创业失败的那一刻你在哪里、窗外是什么天气、你第一个想到谁'
   比如'第一次用AI做出你想要的东西时那种惊喜的感觉'

   先说第一个？"

   每个故事检查清晰度：
   - 是否包含时间地点？
   - 是否有情绪变化？
   - 是否有具体场景和细节？

   若不满足 → 触发知识库追问（见下方"追问机制"）
   追问最多 2 轮，2 轮后仍不够清晰 → 标注 `[待补充]` 继续

4. **口癖/习惯用语**
   引导："你平时说话一定会用的词有哪些？不是书面语，是真·口语。比如有些人永远说'讲真'，有些人开口就是'巨'，有些人的'绝对'永远挂在嘴边。你的是哪些？"

5. **情绪表达方式**
   引导："最后一项必填——你在不同情绪下会怎么说？
   - 震惊的时候：_______（比如：我靠 / 天哪 / 真的假的）
   - 无语的时候：_______（比如：算了 / 行吧 / 就离谱）
   - 兴奋的时候：_______（比如：太爽了 / 牛啊 / 起飞）
   - 难过的时候：_______（比如：唉 / 破防了 / 整个人都不好了）

**选填项（可选逐项询问）：**

"必填项搞定了。还有 7 个选填项，填了效果会更好。每项都可以跳过，要逐项看看吗？(y/n)"

若用户选"y" → 逐项引导：
- **自嘲方式**：我通常怎么调侃自己？
- **知识舒适区**：我能"聊着聊着随手掏"的知识领域有哪些？
- **文化参照系**：我经常引用/联想到的书、电影、历史事件、哲学观点？
- **幽默风格**：荒诞比喻？冷吐槽？自黑？
- **读者称呼**：你习惯怎么称呼读者？（"朋友们""各位"还是直接"你"）
- **结尾偏好**：你更喜欢哪种结尾？引用收尾 / 哲思留白 / 行动呼吁 / 回环呼应
- **文风对标**：你的文章给人感觉像谁？（帮AI校准方向感，不是抄袭）

若用户选"n" → 选填项留空，生成档案

#### 追问机制（知识库驱动）

当用户故事不清晰时，按以下逻辑追问：

知识库A（安先生-情绪刺点）→ 追问场景+感官+情绪触发点：
"当时你人在哪里？还记得周围的环境吗？那一刻心里是什么感觉？"

知识库B（旭辉-三有原则）→ 追问价值+共鸣+趣味：
"这段经历里最有意思/最有价值/最能引起共鸣的地方是什么？如果有人听到这个故事，他们会在哪个点点头？"

知识库C（社恐-起号36计）→ 追问转折+行动+成长：
"后来是怎么走出来的？有没有一个具体的人/一句话/一件事把你拉了出来？你做了什么？"

**降级补偿**：若知识库A为占位状态（文件 < 1KB），追问框架A跳过，但启用文字版情绪追问替代：
"这件事对你的情绪影响是什么？当时的身体感受呢——心跳、呼吸、有没有某个具体的身体感觉？如果能回到那一天，你最想对当时的自己说什么？"

追问不是公式套用，是用知识库的深层理解来设计引导性问题。目标是帮用户从他模糊的记忆里挖出本来就有的、有层次的故事。

#### 写入人设档案

生成 `.yang-persona.md`：
- 包含 YAML frontmatter（`created_at`, `updated_at`, `version: "1.0"`）
- 按"必填/选填"分区展示
- 用户故事以 `### 故事 N` 为标题逐段写入

更新 `.yang-state.json`：
- `persona_exists: true`
- `persona_version: "1.0"`
- `persona_name: "{用户身份/名称}"`
- `persona_history: []`

输出确认：
```
🧑 创作人设已建立
📝 必填 5/5 · 选填 X/7
📁 .yang-persona.md v1.0
💡 随时说"编辑人设"来修改
```

### Step 7: 生成项目结构

```bash
mkdir -p "$OUTPUT_DIR/scripts" "$OUTPUT_DIR/predictions" "$OUTPUT_DIR/videos" "$OUTPUT_DIR/samples" "$OUTPUT_DIR/videos/benchmark"
```

生成后的目录结构：
```
<user-content-project>/
├── scripts/
├── predictions/
├── videos/
│   └── benchmark/
├── samples/
├── .claude/
│   ├── settings.json
│   └── hooks/
│       ├── prediction-immutability.sh
│       ├── session-start.sh
│       ├── log-event.sh
│       └── bump-trigger-monitor.sh
├── rubric_notes.md
├── WORKFLOW.md
├── STATUS.md
├── .yang-state.json
├── .yang-cache/
├── benchmark.md
└── candidates.md
```

### Step 7.5: Hook 安装

1. 创建 `.claude/hooks/` 目录（如不存在）
2. 复制以下 hook 脚本到 `.claude/hooks/`：
   - `prediction-immutability.sh`
   - `session-start.sh`
   - `log-event.sh`
   - `bump-trigger-monitor.sh`
3. 将以下 hook 配置合并写入 `.claude/settings.json`：
   - `prediction-immutability.json` → PreToolUse hook
   - `session-start.json` → SessionStart hook
   - `meta-logging.json` → PostToolUse hook

> **✅ 检查点 6**：确认所有 hook 脚本已复制且 `.claude/settings.json` 中 hook 配置已写入。若任一 hook 安装失败，触发 `INIT_HOOK_INSTALL_FAILED` 失败模式，打印具体失败项但不中断初始化（hook 失败不阻塞核心功能）。

### Step 8: 从模板生成核心文件

为以下模板做变量替换（`$$PLATFORM$$`、`$$VERTICAL$$`、`$$FOLLOWER_COUNT$$`）后写入：

| 模板源 | 目标 |
|--------|------|
| `templates/rubric_notes.template.md` | `rubric_notes.md` |
| `templates/benchmark.template.md` | `benchmark.md` |
| `templates/candidates.template.md` | `candidates.md` |
| `templates/status.template.md` | `STATUS.md` |

根据用户选择的垂直领域，从 `starter-rubrics/` 中选择对应的启动评分表复制到 `rubric_notes.md`。

**规则**：
- 不会自定义 scoring 的新手 → 用 `*fusion-zero.md`（最极简版）
- 已经拍过 3+ 条的老人 → 用 `*fusion.md`（含初始校准）

> **✅ 检查点 5**：确认所有模板文件存在且变量替换成功。若任一模板缺失，触发 `INIT_TEMPLATE_MISSING` 失败模式，报告缺失路径并退出。

### Step 9: 写入 WORKFLOW.md

从本 SKILL.md 生成 WORKFLOW.md，包含完整的 5 阶段流程说明。

### Step 10: 写入状态文件

生成 `.yang-state.json` v4 模板（非 v3 模板）：

```json
{
  "schema_version": "v2.1",
  "skill_version": "2.1.0",
  "project_name": "<用户输入的项目名>",
  "created_at": "<now_ISO8601>",
  "initialized_at": "<now_ISO8601>",
  "in_progress_session": null,
  "rubric_version": "v0",
  "content_form": "opinion-video",
  "typical_duration_seconds": 240,
  "target_publish_cadence_days": 2,
  "rubric_form_mismatch": false,
  "benchmark_status": "none",
  "benchmark_name": null,
  "benchmark_sample_count": 0,
  "baseline_plays": null,
  "calibration_samples": 0,
  "calibration_samples_at_last_bump": 0,
  "data_collection": "manual",
  "pool_status": "none",
  "data_layer": "markdown",
  "hooks_installed": false,
  "enabled_trend_sources": ["manual-paste"],
  "enabled_perf_adapters": [],
  "last_bump_at": null,
  "last_bump_self_audited": false,
  "last_published_at": null,
  "last_published_file": null,
  "last_retro_at": null,
  "last_trends_run_at": null,
  "last_trends_added_count": 0,
  "last_prediction_self_scored": false,
  "last_self_scored_at": null,
  "consecutive_directional_errors": [],
  "pending_retros": [],
  "shoots": [],
  "calibration_records": [],
  "bucket_params": {
    "A": { "alpha": 1.0, "beta": 1.0 },
    "B": { "alpha": 1.0, "beta": 1.0 },
    "C": { "alpha": 1.0, "beta": 1.0 },
    "D": { "alpha": 1.0, "beta": 1.0 }
  },
  "persona_exists": false,
  "persona_version": null,
  "persona_name": null,
  "persona_history": [],
  "knowledge_index_version": null,
  "knowledge_index_exists": false,
  "error_log": [],
  "competitor_count": 0,
  "monitor_enabled_competitors": 0,
  "last_monitor_check": null,
  "total_strategy_changes_detected": 0,
  "last_landscape_snapshot": null
}
```

### Step 11: 输出确认

输出初始化完成的摘要：

```
✅ Yang.skills 已初始化
📁 项目目录: <path>
📏 Rubric: opinion-video-fusion-zero
🔖 垂直领域: <vertical>
📱 平台: <platform>
👥 粉丝数: ~<count>
🧑 创作人设：<已建立/未建立>
📚 知识依据：A-选题 | B-脚本 | C-起号

下一步:
  → "发现竞品" → 运行 yang-competitor-search 自动搜索对标账号
  → "找选题" → 进入四通道选题流程
  → "状态" → 查看当前系统状态

💡 升级提示：输入「升级到 media」安装视频分析 | 「升级到完整版」安装全部依赖
```

---

### 知识库A 状态检测

读取 `knowledge/ansir/SKILL.md`:
- 若文件大小 < 1KB → 判定为占位状态
  → 在知识来源标注中显示 "A-占位（内容降级）"
  → 降低知识库A 的权重依赖
- 若 ≥ 1KB → 正常加载

**降级行为（yang-init）**：追问框架A维度跳过
- 当A降级时：创作人设追问机制中A（安先生-情绪刺点）追问维度跳过
- 追问机制从A/B/C三库 → 降级为B/C两库（旭辉-三有原则 + 社恐-起号36计）
- 场景+感官+情绪触发点的追问 → 跳过，仅保留B和C的追问逻辑
- 账号定位四步法 → 降级为C（起号36计-赛道选择三标准）替代
- 初始rubric设计的框架 → 仅依赖B（四大脚本类型）+ C（起号策略）

---

## 知识库依赖

本 skill 在系统初始化过程中引用以下知识库内容：

- 知识库A：账号定位四步法与普世化选题思路—— 作为垂直领域引导与初始rubric设计的框架 `[来源：A-选题]`
- 知识库B：四大脚本类型（观点型/过程型/知识型/故事型）—— 用于初始评分表的维度结构设计 `[来源：B-脚本]`
- 知识库C：起号36计-赛道选择三标准、账号定位黄金圈—— 用于初始化阶段的项目方向锚定 `[来源：C-起号]`
- 知识库A/B/C：创作人设追问框架（情绪刺点/三有原则/起号策略 → 个性化追问）`[来源：A-情绪]` `[来源：B-三有]` `[来源：C-起号]`

在输出初始化完成摘要时，应追加：

```
📚 知识依据：A-选题 | B-脚本 | C-起号
🔧 能力：竞品搜索 | 数据采集 | 持续监控 | 赛道格局 | 注意力热力图 | 话术DNA
```

---

## 错误处理

| 场景 | 行为 |
|------|------|
| 目录已存在且非空 | 询问用户是覆盖、合并还是换目录 |
| 无法创建目录 | 报告权限问题并退出 |
| 模板文件缺失 | 报告缺失的模板文件路径并退出 |
| 竞品工具缺失 | 打印警告，不中断初始化。提示用户检查 Yang.skills 包完整性 |
| project_data.db 初始化失败 | 打印具体错误信息，询问是否跳过（竞品功能将不可用但核心功能正常） |

---

## 失败模式编码

| 编码 | 含义 | 触发条件 | 恢复策略 |
|------|------|----------|----------|
| `INIT_PYTHON_VERSION` | Python 版本不满足 | `python --version` 返回版本 < 3.10 | 报错退出，提示用户安装 Python 3.10+；不继续后续步骤 |
| `INIT_VENV_FAILED` | 虚拟环境或依赖安装失败 | `python -m venv` 失败或 `pip install` 返回非零退出码 | 打印具体错误信息；询问用户是否跳过依赖安装（部分功能将不可用）；记录到 `error_log` |
| `INIT_DB_FAILED` | 数据库初始化失败 | `init_db()` 抛出异常或 `project_data.db` 不可写 | 询问用户是否跳过（竞品功能将不可用但核心功能正常）；记录到 `error_log` |
| `INIT_TEMPLATE_MISSING` | 模板文件缺失 | `templates/` 下任一必需模板文件不存在 | 报告缺失的模板文件路径并退出；不生成不完整的文件 |
| `INIT_HOOK_INSTALL_FAILED` | Hook 安装失败 | hook 脚本复制失败或 `.claude/settings.json` 写入失败 | 打印具体失败项但不中断初始化（hook 失败不阻塞核心功能）；标记 `hooks_installed: false` |

---

## 反例黑名单

> 以下行为严格禁止，任何一条违反都应视为 bug：

1. **不要覆盖已有项目**：若 `.yang-state.json` 已存在，必须先警告用户并获得确认，不得静默覆盖现有配置和数据
2. **不要跳过环境检测**：Python 版本检测和虚拟环境检测是必经步骤，不得因"看起来没问题"而跳过
3. **不要在无虚拟环境时静默安装**：检测到不在虚拟环境中时，必须明确告知用户并让其选择，不得静默安装到系统 Python
4. **不要忽略依赖安装失败**：`pip install` 失败时必须报告，不得假设"可能装上了"而继续
5. **不要使用占位变量写入文件**：模板中的 `$$PLATFORM$$` 等变量必须替换为实际值，不得将占位符原样写入产出文件
6. **不要跳过数据库初始化**：`project_data.db` 是核心依赖，初始化失败时必须明确告知用户后果，不得静默跳过
7. **不要在模板缺失时生成空文件**：若模板文件不存在，不得创建空的目标文件冒充已生成
8. **不要遗漏 hook 配置**：`.claude/settings.json` 中的 hook 配置必须与实际安装的 hook 脚本一一对应，不得只复制脚本而不写配置

---

## 初始化自检清单

> init 完成后，自动执行以下验证项。任一项失败均需在输出中标注 ⚠️ 并提示修复方式：

| # | 验证项 | 验证方式 | 预期结果 |
|---|--------|----------|----------|
| 1 | Python 版本 | `python --version` | ≥ 3.10 |
| 2 | 虚拟环境状态 | `$VIRTUAL_ENV` 或 `$CONDA_PREFIX` | 非空（或用户已确认跳过） |
| 3 | 核心依赖已安装 | `pip show jieba opencv-python-headless requests` | 全部已安装 |
| 4 | 项目目录结构完整 | 检查 `scripts/`, `predictions/`, `videos/`, `samples/` 目录存在 | 全部存在 |
| 5 | 核心文件已生成 | 检查 `rubric_notes.md`, `WORKFLOW.md`, `STATUS.md`, `candidates.md`, `benchmark.md` | 全部存在且非空 |
| 6 | 状态文件有效 | 读取 `.yang-state.json`，验证 `schema_version` 字段 | `schema_version` = "v2.1" |
| 7 | 数据库可读写 | `sqlite3 project_data.db ".tables"` | 返回 11 张表名 |
| 8 | Hook 已安装 | 检查 `.claude/hooks/` 下 4 个脚本 + `.claude/settings.json` 中 hook 配置 | 全部存在且配置完整 |
| 9 | 模板变量已替换 | `grep -c '$$' rubric_notes.md` | 返回 0（无残留占位符） |
| 10 | 人设状态一致 | `.yang-state.json` 中 `persona_exists` 与 `.yang-persona.md` 存在性 | 两者一致 |

---

## 初始化后首次运行指引

> init 完成后，用户应按以下顺序使用各 skill，确保系统从零到闭环的最短路径。

**推荐首次运行路径**（按顺序执行）：

```
Step 1: yang-init ✅ （已完成）
  ↓
Step 2: yang-persona（建立创作人设）
  → 如果 init 时跳过了人设填写，现在补上
  → 人设会影响后续选题和脚本的风格一致性
  ↓
Step 3: yang-competitor-search（发现竞品）
  → 搜索对标账号，建立 benchmark 基准
  → 至少找到 3-5 个同领域对标账号
  ↓
Step 4: yang-benchmark（建立对标基线）
  → 分析对标账号的爆款内容，提取数据基线
  → 生成 baseline_plays 和各档次参考值
  ↓
Step 5: yang-trends（抓热点）或 yang-competitor-search（深挖竞品）
  → 两条路可选：
    A. 先抓热点 → 快速产出第一条内容（适合"先跑起来"策略）
    B. 先深挖竞品 → 更精准地定位差异化（适合"谋定后动"策略）
  ↓
Step 6: yang-score-blind（盲预测打分）
  → 对第一条内容做盲预测，建立校准起点
  → 这一步是闭环校准系统的起点
  ↓
Step 7: yang-publish（发布）
  → 发布内容，记录发布时间
  ↓
Step 8: yang-retro（复盘）
  → T+3d 做快速复盘，验证预测准确度
  → 积累校准样本
  ↓
Step 9: 循环迭代
  → 积累 10+ 校准样本后 → yang-bump（升级 rubric）
  → 持续选题 → 打分 → 发布 → 复盘 → 升级
```

**最小可用路径**（时间有限时）：
```
yang-init → yang-persona → yang-trends → yang-score-blind → yang-publish → yang-retro
```
只需 6 步即可完成从初始化到首次复盘的完整闭环。

**关键里程碑**：
| 里程碑 | 条件 | 意义 |
|--------|------|------|
| 🟢 闭环启动 | 完成首次 yang-retro | 系统开始积累校准数据 |
| 🟡 校准就绪 | `calibration_samples ≥ 10` | 可以执行首次 yang-bump |
| 🔵 模型进化 | 完成首次 yang-bump | rubric 从默认值进化为个性化模型 |
| 🟠 稳态运行 | 连续 3 次 bump 验证通过 | 预测模型趋于稳定，进入精细调优阶段 |

## 常见初始化问题 FAQ

> 初始化过程中最常遇到的问题和解决方案。

**Q1: Python 版本不满足 3.10 怎么办？**
- macOS: `brew install python@3.12` 或从 [python.org](https://python.org) 下载安装
- Ubuntu/Debian: `sudo apt install python3.12`
- Windows: 从 [python.org](https://python.org) 下载安装包，安装时勾选"Add to PATH"
- 使用 pyenv: `pyenv install 3.12 && pyenv global 3.12`
- 注意：不支持 Python 3.9 及以下版本，3.13 可能有兼容性问题，建议使用 3.10-3.12

**Q2: pip install 报错 "No module named '\_ctypes'" 怎么办？**
- 这是 Python 编译时缺少系统依赖导致的
- Ubuntu/Debian: `sudo apt install libffi-dev`，然后重新编译 Python
- CentOS/RHEL: `sudo yum install libffi-devel`
- macOS: 通常不会出现此问题，若出现请检查 Xcode Command Line Tools 是否安装

**Q3: 虚拟环境创建失败怎么办？**
- 尝试使用 conda 替代: `conda create -n yang python=3.12 && conda activate yang`
- 检查 Python 安装是否完整: `python -m ensurepip`
- 若 `venv` 模块缺失: Ubuntu/Debian 执行 `sudo apt install python3-venv`

**Q4: Playwright 安装失败（tier=media/full）怎么办？**
- 网络问题: 设置镜像 `PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium`
- 权限问题: 不要使用 `sudo` 安装，确保在用户权限下操作
- 依赖缺失: Ubuntu/Debian 执行 `sudo apt install libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2`
- 若仍失败: 先用 tier=core 完成初始化，后续手动安装 Playwright

**Q5: 数据库初始化失败怎么办？**
- 检查磁盘空间: `df -h`（至少需要 100MB 可用空间）
- 检查写入权限: `ls -la <project_dir>`
- 若 SQLite 版本过旧: `sqlite3 --version`（需要 ≥ 3.35.0）
- 可跳过数据库初始化继续使用核心功能，竞品相关功能将不可用

**Q6: 初始化后找不到某些 skill 怎么办？**
- 确认 Yang.skills 包完整性: 检查 `skills/` 目录下是否包含所有 skill 子目录
- 确认 `.claude/settings.json` 中 skill 路径配置正确
- 重新运行 `yang-init` 不会覆盖已有数据（会先询问确认）

**Q7: 知识库A显示"占位状态"影响大吗？**
- 不影响核心功能（打分/预测/复盘/发布）
- 影响范围: 人设追问少一个维度、bump 时权重调整参考降级为知识库B
- 解决方案: 补充知识库A内容后，运行 `yang-bump` 重新校准

**Q8: 如何在已有项目上重新初始化？**
- 运行 `yang-init` 会检测到已有 `.yang-state.json` 并警告
- 选择"覆盖"会重置状态文件但保留 `scripts/`、`predictions/` 等目录下的内容
- 选择"合并"会保留现有配置，仅补充缺失的文件和目录
- 建议先备份: `cp -r <project_dir> <project_dir>.backup`

## 环境兼容性矩阵

> 不同操作系统和 Python 版本的兼容情况，供用户参考。

**操作系统兼容性**：

| 操作系统 | 版本 | core | media | full | 已知问题 |
|---------|------|------|-------|------|---------|
| macOS | 13+ (Ventura+) | ✅ | ✅ | ✅ | M1/M2 芯片需确认 Python 为 arm64 版本 |
| macOS | 12 (Monterey) | ✅ | ✅ | ⚠️ | GraphRAG 部分依赖可能需手动编译 |
| macOS | 11 (Big Sur) | ✅ | ⚠️ | ❌ | Playwright chromium 可能无法启动 |
| Ubuntu | 22.04+ | ✅ | ✅ | ✅ | 推荐的 Linux 环境 |
| Ubuntu | 20.04 | ✅ | ✅ | ⚠️ | 需手动安装新版 SQLite (≥ 3.35) |
| Debian | 11+ | ✅ | ✅ | ✅ | 需手动安装部分系统依赖 |
| CentOS/RHEL | 8+ | ✅ | ⚠️ | ⚠️ | Playwright 依赖需手动安装 |
| Windows | 10/11 | ✅ | ✅ | ⚠️ | WSL2 推荐用于 full tier；原生 Windows 下 GraphRAG 可能有路径问题 |
| Windows | WSL2 | ✅ | ✅ | ✅ | 推荐的 Windows 使用方式 |

**Python 版本兼容性**：

| Python 版本 | core | media | full | 备注 |
|------------|------|-------|------|------|
| 3.10 | ✅ | ✅ | ✅ | 最低支持版本 |
| 3.11 | ✅ | ✅ | ✅ | 推荐版本 |
| 3.12 | ✅ | ✅ | ✅ | 推荐版本，性能最优 |
| 3.13 | ⚠️ | ⚠️ | ❌ | 部分依赖尚未适配，core/media 基本可用但可能遇到兼容问题 |
| 3.9 及以下 | ❌ | ❌ | ❌ | 不支持（使用了 3.10+ 的 match/case 等语法） |

**依赖版本关键约束**：

| 依赖 | 最低版本 | 推荐版本 | 用途 |
|------|---------|---------|------|
| SQLite | 3.35.0 | 3.39+ | 数据库（窗口函数支持） |
| pip | 22.0 | 24+ | 包管理 |
| Node.js | 18.0 | 20+ | Hook 脚本执行（可选） |
| Git | 2.30 | 2.40+ | 版本管理（可选） |

**特殊环境说明**：
- **Docker 容器**: 基于 Ubuntu 22.04 镜像构建，需预装 `python3 python3-pip python3-venv`
- **CI/CD 环境**: 建议使用 tier=core，跳过 Playwright 和 GraphRAG
- **低内存环境**（< 2GB RAM）: 建议使用 tier=core，GraphRAG 索引构建需要约 4GB RAM
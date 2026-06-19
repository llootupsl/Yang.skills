<!-- Author: 阿洋 (Ayang) -->
<sub>🌐 <a href="README.md">中文</a> · <b>English</b></sub>

<div align="center">

# Yang.skills · Content Creation & Operations System

> *"Your next piece of content is already rewriting you 3 months from now — patterns are objective, the only difference is whether you see them or not"*

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Yang.skills-blueviolet)](skills/yang-init/SKILL.md)
[![skills.sh](https://skills.sh/yang/Yang.skills)](https://skills.sh/yang/Yang.skills)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Turn content creation into a calibratable prediction loop — score, predict, publish, retro, evolve. Every round is more accurate than the last.**

[See Examples](#examples) · [Install](#quick-start) · [Triggers](#triggers) · [How It Differs](#how-it-differs) · [Safety Boundaries](#safety-boundaries) · [FAQ](#faq)

</div>

---

## What Problem Does It Solve

You've made 20 videos — can you explain exactly why one blew up and another flopped?

Most people can't. Not because they don't work hard, but because they move on after publishing without leaving any traceable judgment record. Three months later, you're still picking topics by gut, writing scripts by gut, choosing titles by gut — no different from day one.

The common approach is "check data after publishing, keep going if it feels good, pivot if it doesn't." The problem: gut feel isn't calibratable. You never know if your judgment is too high or too low, because there's no baseline — you never wrote down your expectations before publishing.

Yang.skills takes a different approach: **write predictions before you publish**. Turn "I think this will hit 50K views" into a written commitment. Three days later when real data comes back, the gap is crystal clear. Each predict-retro cycle corrects your judgment model, like a machine learning training loop — more samples, better predictions.

---

## Examples

### Blind Prediction → Retro Comparison

```markdown
## Prediction (written before publishing, immutable)
- Expected views: 30K-80K
- Traffic tier: B+ (stable recommendation pool)
- Confidence: medium (7 calibration samples)
- Core judgment: Strong hook impact, but flat emotion curve in the second half

## Retro (appended after T+3d real data)
- Actual views: 42K
- Deviation: +5%, within predicted range
- Deviation attribution: The "flat second half" judgment was correct — completion rate 38% vs benchmark avg 45%
- Calibration signal: The weight of emotion curve decay on completion rate may be underestimated
```

### Human-Polish (去AI味)

```markdown
# Before Polish (AI-sounding)
In today's society, short videos have become a very important way of information dissemination.
According to statistics, over hundreds of millions of users watch short video content on major platforms every day.

# After Polish (Human-feeling)
Every video you scroll past is fighting for your three seconds. It's not that the content isn't good enough — it's that the first three seconds didn't make you stop. I had to shoot 30 videos before I figured this out.
```

### Topic Scoring

```markdown
# yang-score output
| Dimension       | Score | Benchmark Comparison  |
|-----------------|-------|-----------------------|
| Hook Impact     | 7.2   | Above benchmark 6.5   |
| Emotion Curve   | 5.8   | Below benchmark 6.8 ⚠️ |
| Info Density    | 6.5   | On par with benchmark  |
| Copywriting     | 7.0   | Above benchmark 6.2   |
| Composite       | 6.6   | Suggest: boost emotion curve |
```

### 4. Search Intent Topic Discovery

**Input**: 「Help me find topics with high search volume but low competition」

**Output**:
```
🔍 Search Intent Topic Report · Seed: AI工具

📊 Signal Distribution:
  Search suggestions: 18 | Related searches: 12 | Question-type: 8 | Long-tail: 25 | Content gaps: 3

🅰 High Priority (Content Gap detected):
  1. "How to choose AI tools without getting burned" — Content gap score: 0.82
     Signal: content_gap · Search results 87% homogenized, no video content
     Opportunity: Create comparison review video, strong search intent but poor content

🅱 Medium Priority (Search suggestions + Question-type):
  2. "Free AI writing tool recommendations" — Baidu suggestion rank #3
  3. "Which AI tool is best Zhihu" — Zhihu question 2.3k followers/387 answers

📚 Knowledge basis: E-Search Intent | A-Topic Selection
```

### 5. Humanness Score Quantification

**Input**: 「Polish this script, then tell me how much it changed」

**Output**:
```
🧪 Humanness Score Change:
  Before: 32 🔴 → After: 78 🟢 (+46)

  Dimension Changes:
  H-OPEN:   15 → 85 (+70)  "In today's society" → Direct scene opening
  H-FLOW:   25 → 72 (+47)  Three-part formula → Natural transitions
  H-SPEC:   40 → 82 (+42)  "significantly" → "gained 200 followers in 3 days"
  H-STRUCT: 30 → 75 (+45)  Uniform parallelism → Varied sentence rhythm
  H-EMOT:   20 → 68 (+48)  "It's shocking" → "Honestly I didn't expect that"
  H-PERSONA: 10 → 82 (+72)  No personal trace → Persona naturally integrated
```

---

## Quick Start

```bash
npx skills add yang/Yang.skills
```

After installing, tell your Agent:

```text
/yang-init "my vertical niche"
```

This creates your persona profile, data lake, and scoring rubric. After initialization, run `/yang-learn-from` to import benchmark accounts, then use `/yang-seed` to generate topics.

<details>
<summary>Manual Installation (three tiers available)</summary>

```bash
pip install -r requirements-core.txt    # Minimal: topic/scoring/scoring loop
pip install -r requirements-media.txt   # Advanced: frame extraction/transcription/card rendering
pip install -r requirements-full.txt    # Full: knowledge graph/Bayesian/vector store
playwright install chromium             # Browser automation (optional)
```

Windows users:

```powershell
.\install.ps1 -Tier core     # Minimal inference environment
.\install.ps1 -Tier media    # Inference + video analysis
.\install.ps1 -Tier full     # Full operations workbench
```

</details>

---

## Triggers

- "帮我初始化" / "第一次用" / "setup"
- "打分这篇稿子" / "这稿子能打几分"
- "预测一下效果" / "盲预测"
- "润色一下" / "去 AI 味" / "改得像人写的"
- "复盘" / "数据回来了" / "T+3 数据来了"
- "找选题" / "不知道拍什么" / "下一篇做什么"
- "抓热点" / "现在什么火"
- "找对标" / "拆这个账号" / "学他的手法"

Full routing table in [SKILL.md](SKILL.md).

---

## What It Can Do

### Core Content Pipeline

| Stage | Skill | Deliverable |
|-------|-------|-------------|
| Init | `yang-init` | Persona profile + data lake + scoring rubric |
| Topic | `yang-seed` | 4-channel topic discovery (self-ignition + competitor-driven + trend injection + top-comment gems) |
| Score | `yang-score` | 7-dimension scoring + improvement suggestions + benchmark comparison |
| Polish | `yang-polish` | Human-feeling final draft (3-layer funnel + 4-layer self-check) |
| Predict | `yang-predict` | Immutable prediction log (expected views + traffic tier + confidence) |
| Publish | `yang-publish` | Publish timing suggestions + publish checklist |
| Retro | `yang-retro` | Deviation attribution + calibration sample + convergence curve |

### Competitor Analysis

| Skill | Deliverable |
|-------|-------------|
| `yang-competitor-search` | Multi-platform competitor account list (API → Playwright → search engine 3-tier fallback) |
| `yang-benchmark` | Full retrospective report (visual patterns + script DNA + top comments + strategy change detection) |
| `yang-learn-from` | Reusable patterns + rubric anchor signals |

### Auxiliary Skills

| Skill | Deliverable |
|-------|-------------|
| `yang-hook-factory` | Multi-prototype × style matrix hook variants |
| `yang-emotion-curve` | ER-Curve emotion analysis + benchmark comparison |
| `yang-trends` | Zero-config multi-source trend aggregation (Weibo/Zhihu/Bilibili/Baidu/Douyin/Toutiao, no token needed) |
| `yang-graphic` | Xiaohongshu card PNG / Zhihu semantic layout / WeChat inline-style HTML |
| `yang-persona` | Creator persona profile management |
| `yang-status` | System dashboard (buffer warning + feature unlock progress) |
| `yang-doctor` | Health diagnostics (8 indicators + `--fix` auto-repair) |
| `yang-bump` | Calibration-driven rubric upgrade (with cross-model audit) |

---

## How It Differs

| Dimension | Generic AI Writing Tools | Humanizers | Yang.skills |
|-----------|------------------------|------------|-------------|
| Judgment Calibration | None — starts from zero each time | N/A | Blind prediction → retro → evolve, correcting judgment each round |
| AI-Flavor Treatment | Template replacement or none | 29 English Before/After rules + second-pass audit | 25 Chinese Before/After + 3-layer funnel + 4-layer self-check + persona-driven |
| Scoring System | Generic quality score | N/A | 7-dimension scoring + benchmark anchors + evolvable rubric |
| Knowledge Source | Generic writing knowledge | Wikipedia AI writing traits | 3 operational knowledge bases (91 lessons + 262 cases + growth/opening methodology) |
| Competitor Analysis | None | N/A | Full retrospective (download → frame extraction → transcription → script DNA → comment mining) |
| Visual Content | Text only | Text only | Xiaohongshu cards / Zhihu layout / WeChat HTML, shared knowledge base |
| External Dependencies | API Key required | Zero-dependency single file | Zero Key out-of-box, Playwright optional with fallback |
| Search Intent Research | N/A | N/A | 6 search intent signals (suggestions/related/question/long-tail/rising/content gap) |
| Language | Primarily English | English only | Chinese-first, covering Chinese AI writing characteristics |

---

## Safety Boundaries

**What it won't do:**

- Won't download benchmark videos for you (guides you to use yt-dlp / BBDown to avoid TOS + anti-scraping risks)
- Won't fabricate retro data — calibration pool must be filled with real published data; if insufficient, wait
- Won't modify original predictions after results are known — prediction section is immutable, enforced by hooks
- Won't recommend topics by gut feel — every recommendation has scoring and benchmark comparison
- Won't copy competitor scripts verbatim — learn patterns, not text
- Won't retro before T+3d — data hasn't stabilized; early retros cause misjudgment

**When it will stop and ask you:**

- Buffer overflow (≥ 4 unpublished items) — reminds you to digest before producing more
- Insufficient calibration samples — labels "low confidence," suggests directional reference only
- Rubric upgrade requires cross-model audit to pass before execution — won't auto-change formulas
- Pipeline mode requires prerequisites (calibration pool > 30 + at least 1 successful bump)

**What data it doesn't touch:**

- Won't upload your content or data to any external service
- All data stored locally (SQLite + Markdown files)
- Trend fetching uses public endpoints, no cookies or tokens needed

---

## File Structure

```
Yang.skills/
├── SKILL.md                    # Master protocol + router (entry point for 26 sub-skills)
├── skills/                     # 26 sub-skills (yang-init, yang-score, yang-predict...)
├── knowledge/                  # 3 operational knowledge bases
│   ├── ansir/                  #   KB-A: Short video creation methodology + director-level audiovisual language
│   ├── xuehui/                 #   KB-B: Fan economy → business positioning → content positioning
│   └── shekong/                #   KB-C: 36 growth tactics + 36 opening tactics
├── adapters/                   # Data source adapters (zero-config out-of-box)
│   ├── trend-sources/          #   Trend fetching (Weibo/Zhihu/Bilibili/Baidu/Douyin/Toutiao)
│   ├── benchmark-analysis/     #   Benchmark analysis pipeline (download→frames→transcription→comment mining)
│   ├── competitor-search/      #   Multi-platform competitor search
│   ├── graphic-suite/          #   Visual rendering (Xiaohongshu cards/Zhihu/WeChat)
│   └── data_pipeline/          #   Data lake & competitor database
├── shared-protocols/           # Cross-skill shared protocols (blind prediction/bump validation/cadence protocol...)
├── hooks/                      # Harness enforcement layer (prediction-immutability/session-start)
├── evolution-bus/              # Evolution bus (pipeline mode 3-stage sync)
├── starter-rubrics/            # Prior rubrics for each content format
├── templates/                  # File skeletons written to user repos
├── migrations/                 # Schema evolution records
├── research/                   # Technical research (optional reference, not in routing)
└── tools/                      # Standalone CLI scripts (Bayesian/DSPy/GraphRAG/dashboard)
```

---

## Verification & Testing

After installing, tell your Agent:

```text
/yang-init "opinion short video"
```

Expected behavior: System creates `.yang-state.json`, `rubric_notes.md`, `candidates.md` and other scaffold files, outputs initialization summary, and suggests running `/yang-learn-from` next.

Deep verification (20 test prompts):

```text
/yang-doctor
```

Expected behavior: Outputs 8-item health indicator report; a newly initialized project should show "calibration samples: 0 (cold-start)" with all other items green.

Full test suite in [test-prompts.json](test-prompts.json), covering 15 core sub-skills + 5 edge scenarios.

---

## Core Loop

```
Search Intent Research → Topic → Score → Human-Polish → Blind Predict → Publish → Data Collection → Retro → Evolve Rubric → Back to Topic
```

**"Blind prediction"** is the heart of this system: before publishing content, write down how many views you think it'll get and which traffic tier it'll land in. 3 days later when real data comes back, compare the gap and correct your judgment model. Loop after loop, your judgment evolves like a machine learning model.

### Human-Polish Engine

Systematically removes AI flavor through a 3-layer funnel:

| Layer | Function | Core Mechanism |
|-------|----------|----------------|
| Persona Layer | Loads creator persona profile as personality baseline | 12-field persona: identity/values/personal stories/catchphrases/emotional expressions |
| Methodology Layer | Applies human-feeling writing techniques | Suspense progression / number anchoring / sentence fragmentation / character portrait method / cultural elevation / counter-argumentation |
| Rule Layer | 4-layer hardware self-check | L1 banned-word scan → L2 style consistency → L3 content quality → L4 human-feeling final review |

Polish intensity is auto-determined by scores: copywriting or emotion ≥ 6 → L1+L2 only; < 5 → add L3; < 4 → full L1-L4.

### Visual Content Creation

Beyond video, covers the visual content loop for Xiaohongshu, Zhihu, and WeChat Official Accounts:

| Platform | Output | Key Adaptation |
|----------|--------|----------------|
| Xiaohongshu | Cover image + content cards (PNG) | First image = crowd imprint + quick judgment; color = emotion; auto-pagination for long content |
| Zhihu | Paste-friendly semantic layout | Conclusion first, layered arguments, tables → lists |
| WeChat Official Account | Inline-style HTML (paste preserves formatting) | Hook within first 100 chars, left-bar subtitles, golden-quote blocks |

### Competitor Database

All competitor data persisted to SQLite:

| Table | Purpose |
|-------|---------|
| `competitors` | Competitor profiles: platform, account ID, follower count |
| `competitor_snapshots` | Data snapshots: periodic follower changes, video lists |
| `competitor_strategy_changes` | 8-dimension strategy change detection |
| `landscape_snapshots` | Market landscape snapshots |

---

## FAQ

### Q1: Which command should I start with?

Run `yang-init "your vertical niche"` to initialize. This creates your persona profile, data lake, and scoring rubric. After initialization, run `yang-learn-from` to import benchmark accounts, then use `yang-seed` to generate topics.

### Q2: Are predictions reliable when calibration samples = 0?

No. When `calibration_samples = 0`, all predictions are purely inferred from benchmark data. The system will label them `⚠️ speculative (low confidence)`. We recommend publishing at least 3-5 videos to build your own calibration pool before heavily relying on predictions. Until then, use predictions for directional reference only.

### Q3: Can I modify a blind prediction after writing it?

No. Once a prediction is written to the `## 预测` section in the `predictions/` directory, it's locked as immutable by hooks. This is the core principle of blind prediction — ensuring prediction-actual comparisons aren't contaminated by post-hoc edits. If you discover a factual error, record the deviation in the `## 复盘` section. Pure formatting fixes can bypass via `CHEAT_BYPASS_IMMUTABILITY=1`, but this is logged in stderr and git history.

### Q4: How do I improve prediction confidence?

Confidence is determined by `calibration_samples`. Ways to improve:
- Publish more videos and complete T+3 retros (each +1.0)
- Perform deep analysis of benchmark hits (each +0.5, max 3)
- Confirm historical videos as "representative works" (each +1.0)
- Note: benchmark data exceeding 50% of total triggers a downgrade, so your own published data is the most reliable path to higher confidence

### Q5: When does a Bump evaluation trigger?

Bump evaluation requires all of the following:
- ≥ 3 consecutive samples with same-direction deviation (persistent over- or under-estimation)
- `calibration_samples ≥ 5`
- Confidence at least medium

After triggering, it must pass 5-step validation (Re-Score → Cross-Validation → Anomaly Detection → Wall-Clock Stability → Cross-Agent Audit). All PASS required for rubric upgrade execution.

### Q6: What's the difference between Solo mode and full Pipeline mode?

In Solo mode, the Agent engine is not activated (C-001~C-007 all dormant), only the calibration loop runs independently. Suitable for single operations like script evaluation, retros, benchmark learning, status queries. Full Pipeline mode activates all Agents, executing the complete loop from topic → script → shoot → publish → retro.

### Q7: How long before benchmark data expires?

Benchmark data depreciates over time:
- ≤ 30 days: full contribution
- 31-60 days: ×0.7 depreciation
- 61-90 days: ×0.4 depreciation
- \> 90 days: zero contribution

We recommend updating benchmark analysis every 60 days via `yang-learn-from` or Stage1 Hook auto-benchmark discovery.

### Q8: Which platforms does the system support for content creation?

Video: Douyin (primary platform). Visual content: Xiaohongshu (`yang-graphic --platform xhs`), Zhihu (`--platform zhihu`), WeChat Official Account (`--platform wechat`). Competitor discovery supports Douyin and Bilibili.

### Q9: What if Playwright installation fails?

Playwright needs a Chromium browser for automated collection. If `playwright install chromium` fails:
1. Check network connection (Chromium download ~150MB)
2. Try setting a mirror: `PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium`
3. If you don't need browser-based collection, skip this step — the system will auto-downgrade to no-browser mode

### Q10: How do I check current system status?

Run `yang-status` to view: calibration sample count, confidence level, rubric version, candidate pool status, pending retro prediction queue, dead letter queue status, etc. Run `yang-doctor` for deeper health diagnostics, with `--fix` for auto-repair of common issues.

---

## Cross-Platform Compatibility

| Platform | Compatibility | Notes |
|----------|---------------|-------|
| **Claude Code** | ✅ Full support | Native platform. All hooks run completely |
| **Codex CLI** | ⚠️ Functional compatibility | Core routing compatible, hooks need manual configuration |
| **Other Agent Platforms** | ⚠️ Adaptation needed | Skill files loadable, hooks/adapter layers need adaptation |

---

## Changelog

### v5.1 Key Improvements

**Evolution Feedback Bus**
- New tri-synergy architecture (Agent Engine + Calibration Loop + Evolution Feedback Bus)
- New bus message format specification (3-layer structure: header/body/trailer)
- New message priority definitions (URGENT/NORMAL/LOW) and dynamic escalation rules
- New message retry and dead letter queue mechanism
- New signal translation precision standard (EXACT/APPROXIMATE/LOST)

**Calibration Loop Enhancements**
- New benchmark data time depreciation rules (30/60/90-day decay coefficients)
- New zero-calibration warning and downgrade strategy
- New C-006 deviation audit and Bump signal linkage mechanism

**Hook System**
- New prediction-immutability hook degradation scheme (Level 0-3)
- New immutable section range customization guide

---

## Contributing

### Contribution Types

| Type | Description | Example |
|------|-------------|---------|
| **New Sub-Skill** | Add independent functional module | Add `yang-subtitle` subtitle generation skill |
| **Knowledge Base Extension** | Add or improve knowledge base content | Add industry terminology, supplement hook templates |
| **Adapter** | Add adapter for external tools | Add new ASR engine adapter |
| **Bug Fix** | Fix existing functionality defects | Fix scoring calculation error |
| **Documentation Improvement** | Improve docs and comments | Supplement FAQ, improve API descriptions |

### Contributing a New Sub-Skill

1. Create `yang-{name}/` directory under `skills/`
2. Write `SKILL.md` (with YAML frontmatter: name/description/author)
3. Follow core principles: don't modify other skills' internal logic, share state via `.yang-state.json`
4. Ensure new skill can run independently in Solo mode
5. Submit PR: include SKILL.md + implementation code + usage example

### Code Style

- Python: Follow PEP 8, type annotations recommended but not required
- Shell: Follow Google Shell Style Guide, MUST include `set -uo pipefail`
- Markdown: YAML frontmatter MUST include name/description/author

### Commit Convention

Format: `{type}({scope}): {description}`

- type: feat / fix / docs / refactor / test / chore
- scope: skill name / bus / hook / knowledge / adapter
- Example: `feat(yang-trends): add multi-platform trend aggregation`

---

## Acknowledgments

- [ansir knowledge base](knowledge/ansir/SKILL.md) — Short video creation methodology (91 lessons + 262 cases + director-level audiovisual language)
- [xuehui knowledge base](knowledge/xuehui/SKILL.md) — Short video operations teaching system (fan economy → business positioning → content positioning)
- [shekong knowledge base](knowledge/shekong/SKILL.md) — Growth and opening methodology (36 growth tactics + 36 opening tactics)
- Blind prediction methodology inspired by training-validation loops in machine learning and prediction market mechanisms
- Human-polish technique system references core frameworks from narrative psychology and rhetoric

---

## License

[MIT](LICENSE)

---

<div align="center">

*Topic → Predict → Publish → Retro → Evolve. Every round is more accurate than the last.*

</div>

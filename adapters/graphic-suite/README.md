<!-- 作者: 阿洋 -->
# 图文套件 graphic-suite

被 `yang-graphic` 调用，覆盖小红书 / 知乎 / 公众号三类图文落地。三个工具均可独立运行。

## 工具

| 脚本 | 平台 | 输入 → 输出 | 依赖 |
|---|---|---|---|
| `render_card.py` | 小红书 | 卡片 JSON / 命令行 → 封面+内容卡 **PNG**（+HTML 兜底） | Playwright(Chromium)，无则降级出 HTML |
| `wechat_md.py` | 微信公众号 | Markdown → **内联样式 HTML**（粘贴保留排版） | 纯标准库 |
| `zhihu_format.py` | 知乎 | Markdown → **语义 HTML**（粘贴保留结构） | 纯标准库 |

> 公众号编辑器剥离 `<style>` 与外部 CSS，只认元素 `style=""` → 故 `wechat_md.py` 逐元素内联。
> 知乎保留语义结构但丢内联样式 → 故 `zhihu_format.py` 产出干净语义标签，并把表格转列表、保留 LaTeX。

## 小红书图卡 render_card.py

```bash
python render_card.py --in card.json --out out/xhs/
python render_card.py --title "标题" --subtitle "钩子" --body "第一步...\n第二步..." \
  --theme cream --badge 干货 --footer "@账号 关注不迷路" --out out/xhs/
```

卡片 JSON：
```json
{
  "title": "封面大标题（含人群印记，≤22字）",
  "subtitle": "封面钩子（可选）",
  "theme": "cream",
  "size": "3:4",
  "badge": "干货",
  "cards": [ {"heading": "小标题(可选)", "body": "正文，可用\\n分段"} ],
  "footer": "@账号名 · 关注不迷路"
}
```
- 尺寸：`3:4`(1080×1440，默认) / `1:1`(1080×1080)。
- 正文超长自动按字数分页成多张内容卡。
- 输出 `01_cover.png`、`NN_card.png`、`manifest.json`；同时落每页 HTML 作兜底/二次编辑。
- 无 Chromium 时：只出 HTML + 提示 `pip install playwright && playwright install chromium`。

## 主题（配色=情绪，呼应安先生·附录P 视听语言）

| 主题 | 气质 | 适用选题 |
|---|---|---|
| `cream` | 米色暖调 | 生活/治愈/存钱/家居 |
| `sunset` | 橘暖 | 情感/温暖/节日 |
| `mono` | 极简黑白 | 干货/职场/理性 |
| `fresh` | 清新绿 | 健康/成长/自然 |
| `dark` | 夜感深色 | 高级感/情绪/夜话 |

公众号主题：`default` / `warm` / `dark` / `green`（与上表主色呼应）。

## 各平台输出质量检查清单

### 小红书 render_card.py
- [ ] 封面图 `01_cover.png` 标题文字清晰可读，无截断/溢出
- [ ] 内容卡 `NN_card.png` 正文无超框，分段合理（单卡正文 ≤ 200 字）
- [ ] 主题配色与选题气质一致（见下方主题适配规则）
- [ ] 尺寸正确：3:4 → 1080×1440，1:1 → 1080×1080
- [ ] 中文字体正常渲染（无方块/乱码），字体栈兜底生效
- [ ] `manifest.json` 条目数与实际输出图片数一致
- [ ] HTML 兜底文件存在且可在浏览器中正常打开

### 微信公众号 wechat_md.py
- [ ] 所有样式均为内联 `style=""`，无 `<style>` 标签或外部 CSS
- [ ] 粘贴到公众号编辑器后排版保留（标题/正文/引用/列表结构完整）
- [ ] 图片使用 `max-width:100%` 自适应，无溢出
- [ ] 主题配色在公众号编辑器中显示正确

### 知乎 zhihu_format.py
- [ ] 语义 HTML 标签正确（`<h2>`/`<p>`/`<ul>`/`<ol>`/`<blockquote>`）
- [ ] 表格已转为列表形式（知乎不支持复杂表格）
- [ ] LaTeX 公式保留且语法正确
- [ ] 粘贴到知乎编辑器后结构完整，无丢失段落

## 主题适配推荐规则

选择主题时应匹配内容气质，以下是详细适配指引：

| 主题 | 最佳适配内容 | 不适配内容 | 配色要点 |
|---|---|---|---|
| `cream` | 生活技巧、存钱攻略、家居整理、治愈系、亲子、美食 | 硬核技术、严肃财经 | 米色底+深棕文字，暖而不腻 |
| `sunset` | 情感故事、温暖治愈、节日祝福、恋爱、闺蜜 | 冷数据、理性分析 | 橘暖渐变，情绪感强 |
| `mono` | 职场干货、技术教程、数据分析、方法论、工具推荐 | 生活分享、情感倾诉 | 黑白灰，信息密度优先 |
| `fresh` | 健康养生、个人成长、自然户外、运动、习惯养成 | 夜间话题、重口味 | 浅绿底+深绿文字，清新感 |
| `dark` | 深度思考、情绪夜话、高级感、品牌故事、小众文化 | 活泼日常、轻松搞笑 | 深色底+亮色文字，对比度 ≥ 4.5:1 |

**选择原则**：
1. 内容有明确情绪倾向时，优先匹配情绪（如情感→sunset）。
2. 信息密度高的干货内容，优先选 `mono` 或 `fresh`，避免花哨配色干扰阅读。
3. 不确定时选 `cream`（最通用，接受度最高）。
4. 同一系列内容保持主题一致，不要跨主题混搭。

## 浏览器不可用时的降级输出规范

当 Playwright/Chromium 不可用时，`render_card.py` 自动降级为纯 HTML 输出：

1. **输出内容**：每页生成独立 HTML 文件（`01_cover.html`、`NN_card.html`），包含完整内联样式，可直接在浏览器打开。
2. **不输出 PNG**：降级模式下不生成截图，`manifest.json` 中 `type` 字段标记为 `"html-fallback"` 而非 `"png"`。
3. **提示信息**：`stderr` 输出安装指引 `pip install playwright && playwright install chromium`。
4. **HTML 兜底质量要求**：
   - 内联样式必须完整，不依赖外部 CSS/字体文件。
   - 布局使用 Flexbox，保证在 Chrome/Firefox/Safari 中渲染一致。
   - 图片占位使用纯色背景 + 文字替代，不依赖外部图片资源。
5. **调用方处理**：下游流程应检查 `manifest.json` 中的 `type` 字段，若为 `html-fallback`，提示用户手动截图或安装浏览器依赖后重新渲染。

## 维护

排版规则全部写在脚本内（HTML/CSS 由 Python 生成，零外部模板路径依赖），改样式直接改对应脚本的主题字典或 HTML 模板函数即可。中文渲染依赖渲染机的系统中文字体，脚本已用 PingFang/思源/雅黑 字体栈兜底。

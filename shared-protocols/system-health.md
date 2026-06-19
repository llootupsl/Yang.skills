<!-- 作者: 阿洋 -->
# 系统健康指标

以下指标定义了 Yang.skills 系统的整体健康状态，yang-doctor 诊断时逐项检查并输出报告。

| # | 指标名称 | 定义 | 健康标准 | 不健康阈值 | 检查方式 |
|---|----------|------|----------|-----------|----------|
| 1 | **校准样本数** | predictions/ 下含完整复盘段且填了真实数据的文件数 | ≥ 10（可触发 bump） | < 3（无法进入 calibration 模式） | `ls predictions/*.md` + grep `## 复盘` |
| 2 | **预测准确率趋势** | 最近5次复盘的预测偏差移动平均值 | 偏差 < 30% 且呈下降趋势 | 连续3次偏差 > 30% | 读取 predictions/*.md 的预测值与实际值 |
| 3 | **rubric 版本** | 当前 rubric_notes.md 的版本号与 .yang-state.json 记录是否一致 | 版本号一致 | 版本号不一致 | 对比 `rubric_notes.md` 头部版本与 state 中 `rubric_version` |
| 4 | **buffer 天数** | 当前 shoot buffer 中的未发布内容数量 | 0-2 条（健康节奏） | ≥ 4 条（积压风险） | 读取 `.yang-state.json` 的 `shoot_buffer` |
| 5 | **预测完整性** | 已打分但未写预测的脚本数量 | 0（所有打分脚本都有对应预测） | ≥ 2（预测遗漏） | 对比 scripts/ 和 predictions/ 文件列表 |
| 6 | **校准池新鲜度** | 校准池最近一条复盘数据距今的天数 | ≤ 14 天 | > 30 天（校准数据过期） | 读取最近复盘文件的 `published_at` |
| 7 | **知识库索引版本** | Knowledge-Index.md 版本与 .yang-state.json 记录是否一致 | 版本号一致 | 版本号不一致 | 对比索引文件头部版本与 state 中 `knowledge_index_version` |
| 8 | **钩子完整性** | .claude/hooks/ 下必需钩子文件是否齐全 | 全部存在 | 任一缺失 | 检查 `prediction-immutability.sh`、`session-start.sh`、`log-event.sh`、`bump-trigger-monitor.sh` |

### 健康等级

| 等级 | 条件 | 建议动作 |
|------|------|----------|
| 🟢 **健康** | 8项全部达标 | 正常运行 |
| 🟡 **注意** | 1-2项不达标 | 尽快处理不达标项 |
| 🔴 **异常** | 3+项不达标 | 暂停新内容生产，优先修复异常项 |

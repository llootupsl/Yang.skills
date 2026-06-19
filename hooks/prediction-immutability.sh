#!/usr/bin/env bash
# 作者: 阿洋
#
# Yang.skills / prediction-immutability hook
#
# ============================================================================
# 【Hook 触发条件与工作原理】
#
# 本 hook 挂载在 Claude Code 的 PreToolUse 事件上，拦截所有对 Edit 和 Write
# 工具的调用。当检测到编辑操作的目标文件位于 predictions/ 目录下，且编辑
# 内容涉及 '## 预测' / '## Prediction' 段落时，自动阻止该操作。
#
# 触发流程：
#   1. Claude Code 在执行 Edit/Write 前将工具调用参数以 JSON 格式传入 stdin
#   2. 本 hook 解析 tool_name 和 file_path
#   3. 若文件路径匹配 */predictions/*.md，进入不可变性检查
#   4. 对 Edit 操作：提取 old_string，检查是否落在预测段落内
#   5. 对 Write 操作：若目标文件已存在，直接阻止（Write 是全量覆盖）
#   6. 返回 exit 0（放行）或 exit 1（阻止，stderr 内容会展示给模型）
#
# 设计哲学：
#   盲预测的核心原则是"预测一旦写下，不可修改"。这确保了预测-实际的对标
#   不会被事后修正所污染。只有 '## 复盘' 段落允许追加内容。
#
# ============================================================================
# 【如何自定义 immutable 段的范围】
#
# 默认情况下，本 hook 保护 '## 预测' / '## Prediction' 及其版本后缀
# （如 '## 预测 v1'、'## 预测 v2'）到下一个 H2 标题之间的所有内容。
#
# 自定义方式：
#
#   1. 修改 awk 匹配规则（第 89-98 行附近）：
#      当前规则：/^## (预测|Prediction)([^a-zA-Z]|$)/
#      若需保护更多段落，可扩展正则，例如同时保护 '## 假设' 段：
#        /^## (预测|Prediction|假设|Hypothesis)([^a-zA-Z]|$)/
#
#   2. 修改文件路径匹配规则（第 57-64 行附近）：
#      当前规则：*/predictions/*.md 或 predictions/*.md
#      若需保护其他目录下的文件，扩展 case 分支：
#        */hypotheses/*.md|hypotheses/*.md)
#
#   3. 修改段落结束标记（第 88-98 行的 awk 脚本）：
#      当前逻辑：遇到第一个非预测的 H2 标题即结束保护范围
#      若需保护到文件末尾，修改 awk 的 exit 逻辑
#
# ============================================================================
# 【Hook 失效时的降级方案】
#
# 当本 hook 因环境问题无法正常工作时（如 jq 不可用、bash 版本过低、
# stdin 格式异常），系统应遵循以下降级策略：
#
#   Level 0（hook 正常运行）：
#     · 所有对预测段落的编辑被自动阻止
#     · 完整的不可变性保护
#
#   Level 1（hook 部分失效——jq 不可用）：
#     · tool_name/file_path 解析失败时，hook 退出码为 0（放行）
#     · 降级为"信任模型自觉"模式
#     · 建议在 system prompt 中追加提示：
#       "预测段落不可修改。如需修正，请在复盘段记录偏差。"
#     · 安装 jq 后恢复：brew install jq (macOS) / apt install jq (Linux)
#
#   Level 2（hook 完全失效——bash 环境异常）：
#     · hook 无法执行，Claude Code 会跳过 hook 直接执行工具调用
#     · 降级为"人工审计"模式
#     · 建议在 git pre-commit hook 中增加二次检查：
#       git diff --cached 可检测对 predictions/ 目录的修改
#     · 修复 bash 环境后恢复
#
#   Level 3（hook 被绕过——CHEAT_BYPASS_IMMUTABILITY=1）：
#     · 仅用于纯格式修正（如多余空行、Markdown 语法错误）
#     · 绕过操作会记录到 stderr，在 git 历史中可见
#     · 严禁用于任何语义层面的修改
#
# ============================================================================
#
# Wires PreToolUse(Edit|Write) → blocks any edit that touches the
# '## 预测' / '## Prediction' section of a file under predictions/.
#
# Allows:
#   - Writing brand-new prediction files
#   - Editing the file's metadata header (above first ##)
#   - Appending to the '## 复盘' / '## Retrospective' section
#   - Touching files outside predictions/
#
# Blocks:
#   - Any change to lines between '## 预测' (or '## Prediction') and the next H2
#
# Bypass (rare, for true formatting-only fixes):
#   CHEAT_BYPASS_IMMUTABILITY=1 — single-shot bypass; logs a warning to stderr
#
# Requirements: bash 3+, jq, diff. Mac default install has all of these.
#
# Exit codes:
#   0 = allow tool call to proceed
#   1 = block tool call (Claude Code will surface stderr to the model)
# ============================================================================

set -uo pipefail

# Single-shot bypass — opt-in, logs prominently
if [[ "${CHEAT_BYPASS_IMMUTABILITY:-0}" == "1" ]]; then
  echo "[Yang.skills] ⚠️  IMMUTABILITY BYPASS active (CHEAT_BYPASS_IMMUTABILITY=1)" >&2
  echo "[Yang.skills] ⚠️  This should only be used for pure markdown-formatting fixes." >&2
  echo "[Yang.skills] ⚠️  Bypass will be visible in git history." >&2
  exit 0
fi

# Read tool call payload from stdin (Claude Code passes JSON)
input=$(cat)
if [[ -z "$input" ]]; then
  # No input — let it through (defensive default; nothing to check)
  exit 0
fi

# Extract tool name and file path
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")

# Only intercept Edit and Write
if [[ "$tool_name" != "Edit" && "$tool_name" != "Write" ]]; then
  exit 0
fi

# Only intercept files under predictions/
if [[ -z "$file_path" ]]; then
  exit 0
fi

case "$file_path" in
  */predictions/*.md|predictions/*.md)
    : # match — continue checking
    ;;
  *)
    exit 0
    ;;
esac

# Allow Write if the file does not yet exist (creating new prediction)
if [[ "$tool_name" == "Write" && ! -f "$file_path" ]]; then
  exit 0
fi

# For Edit — extract the old_string and new_string and check whether either touches
# the prediction section.
#
# Strategy: compute the byte range of the '## 预测' (or '## Prediction') section
# in the file BEFORE the edit, then check whether the old_string lies inside that
# range. If yes — block.

if [[ "$tool_name" == "Edit" ]]; then
  old_string=$(printf '%s' "$input" | jq -r '.tool_input.old_string // empty' 2>/dev/null || echo "")
  if [[ -z "$old_string" ]]; then
    exit 0
  fi

  # Find prediction section bounds. Match '## 预测' / '## Prediction' / '## 预测 v1'
  # / '## 预测 v2' / etc. — all version-suffixed prediction headings count as prediction
  # sections and are locked together.
  #
  # Section ends at the first NON-prediction '## ' heading (typically '## 复盘').
  prediction_section=$(awk '
    /^## / {
      if ($0 ~ /^## (预测|Prediction)([^a-zA-Z]|$)/) {
        in_pred=1; print; next
      } else if (in_pred) {
        exit
      }
    }
    in_pred { print }
  ' "$file_path" 2>/dev/null || echo "")

  if [[ -z "$prediction_section" ]]; then
    # File has no prediction section — let the edit through.
    # (Could be a non-conforming prediction file or an edge case.)
    exit 0
  fi

  # Check whether old_string appears inside the prediction section.
  # We use grep -F (literal) on a temporary file because old_string may contain regex chars.
  pred_tmp=$(mktemp)
  printf '%s' "$prediction_section" > "$pred_tmp"

  if grep -qF -- "$old_string" "$pred_tmp" 2>/dev/null; then
    rm -f "$pred_tmp"
    cat >&2 <<EOF

[Yang.skills] 🚫 BLOCKED: edit targets the '## 预测' / '## Prediction' section of:
  $file_path

This violates principle #1 of Yang.skills: predictions are immutable.
Once written, the prediction section can never be modified — only the
'## 复盘' / '## Retrospective' section can be appended to.

What to do instead:
  • If you want to redo the prediction with new info, create a NEW file:
      ${file_path%.md}_redo.md
    The original must be preserved.
  • If you noticed a factual mistake AFTER seeing data, document it in the
    '## 复盘' section: "Correction: original probability X% should have been Y%".
  • If this is a pure markdown-formatting fix (no semantic change), you can
    bypass once with: CHEAT_BYPASS_IMMUTABILITY=1 (logs to stderr, visible in git).

See: shared-protocols/blind-prediction-protocol.md
EOF
    exit 1
  fi

  rm -f "$pred_tmp"
  exit 0
fi

# Write tool on an existing file — that's a full overwrite, definitely touches prediction section.
if [[ "$tool_name" == "Write" && -f "$file_path" ]]; then
  cat >&2 <<EOF

[Yang.skills] 🚫 BLOCKED: Write would overwrite an existing prediction file:
  $file_path

Use Edit on the '## 复盘' section to append retrospective content.
Use a new '_redo.md' file path to create a redo prediction.
The original prediction file must be preserved verbatim.

See: shared-protocols/blind-prediction-protocol.md
EOF
  exit 1
fi

exit 0

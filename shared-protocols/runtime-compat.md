<!-- 作者: 阿洋 -->
# 跨 Runtime 兼容性协议

> 本文档定义 Yang.skills 在不同 Agent runtime 下的兼容性矩阵、适配指南和测试清单。
> 遵循 luban-skill "默认面向跨Agent生态"原则，确保 skill 核心功能在主流 runtime 上可用。

---

## 1. 兼容性矩阵

| 功能域 | Claude Code | Codex CLI | OpenCode | OpenClaw | Cursor | GitHub Copilot |
|--------|-------------|-----------|----------|----------|--------|----------------|
| **SKILL.md 解析与路由** | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ⚠️ 部分 | ⚠️ 部分 |
| **子 skill 调用链** | ✅ 完整 | ✅ 功能可用 | ✅ 功能可用 | ✅ 功能可用 | ⚠️ 手动触发 | ⚠️ 手动触发 |
| **Hooks（生命周期钩子）** | ✅ 完整 | ⚠️ 需适配 | ⚠️ 需适配 | ⚠️ 需适配 | ❌ 不支持 | ❌ 不支持 |
| **allowed-tools 声明** | ✅ 原生 | ⚠️ 需映射 | ⚠️ 需映射 | ⚠️ 需映射 | ⚠️ 部分映射 | ⚠️ 部分映射 |
| **知识库引用** | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| **Python 适配器脚本** | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| **共享协议（shared-protocols）** | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| **状态文件读写** | ✅ 完整 | ✅ 功能可用 | ✅ 功能可用 | ✅ 功能可用 | ⚠️ 需手动 | ⚠️ 需手动 |
| **多 Agent 协作（进化总线）** | ✅ 完整 | ⚠️ 需适配 | ⚠️ 需适配 | ⚠️ 需适配 | ❌ 不支持 | ❌ 不支持 |

### 兼容性等级说明

| 等级 | 含义 |
|------|------|
| **full** | 所有功能原生可用，无需额外适配 |
| **functional** | 核心功能可用，hooks/工具映射等需按本指南适配 |
| **partial** | 部分功能受限（如无 hooks 支持、无自动 skill 路由），需手动操作补偿 |

---

## 2. Claude Code 专属功能清单

以下功能为 Claude Code 原生支持，其他 runtime 需要适配替代方案：

### 2.1 Hooks 系统（`.claude/hooks/` 目录）

| Hook | 触发时机 | 作用 | 文件 |
|------|----------|------|------|
| `prediction-immutability` | `on_prediction_write` | 预测写入时计算 hash，后续检测非法修改 | `prediction-immutability.sh` + `.json` |
| `session-start` | `on_session_start` | 会话启动时检查环境状态、更新看板 | `session-start.sh` + `.json` |
| `bump-trigger-monitor` | `on_retro_complete` | 复盘后检查是否达到 Bump 阈值并提示 | `bump-trigger-monitor.sh` |
| `meta-logging` | 被动记录 | 使用日志被动记录 | `log-event.sh` + `meta-logging.json` |

### 2.2 `.claude/` 目录结构

```
.claude/
├── settings.json          # 项目级 Claude Code 设置
└── hooks/
    ├── prediction-immutability.sh
    ├── prediction-immutability.json
    ├── session-start.sh
    ├── session-start.json
    ├── log-event.sh
    ├── meta-logging.json
    └── bump-trigger-monitor.sh
```

### 2.3 `allowed-tools` 原生映射

Claude Code 直接识别 `SKILL.md` 中的 `allowed-tools` 字段：
- `Bash(*)` → 允许执行任意 shell 命令
- `Read` / `Write` / `Edit` → 文件读写编辑
- `Grep` / `Glob` → 搜索工具
- `Skill` → 子 skill 调用

---

## 3. 非 Claude Code Runtime 适配指南

### 3.1 Codex CLI 适配

#### Hooks 迁移

Codex CLI 不支持 `.claude/hooks/` 目录格式，需通过以下方式实现等价功能：

| Claude Code Hook | Codex CLI 等价方案 | 实现方式 |
|------------------|-------------------|----------|
| `on_prediction_write` | Codex CLI `post_tool_call` hook | 在 `codex.yaml` 中配置 `post_tool_call` 回调，匹配 `Write` 工具调用且路径含 `predictions/`，执行 hash 计算脚本 |
| `on_session_start` | Codex CLI `on_start` hook | 在 `codex.yaml` 中配置 `on_start` 回调，调用 `session-start.sh` |
| `on_retro_complete` | Codex CLI `post_tool_call` hook | 在 `codex.yaml` 中配置 `post_tool_call` 回调，匹配 `yang-retro` skill 调用完成后检查 bump 条件 |
| 被动日志 | Codex CLI `post_tool_call` hook | 在 `codex.yaml` 中配置通用 `post_tool_call` 回调记录使用日志 |

Codex CLI hook 配置示例（`codex.yaml`）：

```yaml
hooks:
  on_start:
    - command: "bash /path/to/Yang.skills/hooks/session-start.sh"
  post_tool_call:
    - match:
        tool: "Write"
        path_pattern: "predictions/.*"
      command: "bash /path/to/Yang.skills/hooks/prediction-immutability.sh"
    - match:
        tool: "Skill"
        name: "yang-retro"
      command: "bash /path/to/Yang.skills/hooks/bump-trigger-monitor.sh"
```

#### allowed-tools 映射

| Claude Code 工具 | Codex CLI 映射 | 说明 |
|-----------------|---------------|------|
| `Bash(*)` | `shell` | Codex CLI 的 shell 执行权限 |
| `Read` | `read_file` | 文件读取 |
| `Write` | `write_file` | 文件写入 |
| `Edit` | `edit_file` | 文件编辑 |
| `Grep` / `Glob` | `search` | 搜索工具 |
| `Skill` | `task` / `subagent` | 子 skill 通过 task 调用 |

### 3.2 OpenCode 适配

#### Hooks 迁移

OpenCode 使用 skill tool 调用模式，无独立 hooks 目录：

| Claude Code Hook | OpenCode 等价方案 | 实现方式 |
|------------------|-----------------|----------|
| `on_prediction_write` | OpenCode `after_action` 回调 | 在 skill 配置中注册 `after_action`，当 action 为 `write_file` 且路径匹配 `predictions/` 时触发 hash 校验 |
| `on_session_start` | OpenCode `on_load` 回调 | 在 skill 配置中注册 `on_load` 回调，执行环境检查 |
| `on_retro_complete` | OpenCode `after_action` 回调 | 在 skill 配置中注册 `after_action`，当 action 为 `yang-retro` 完成后触发 bump 检查 |
| 被动日志 | OpenCode `after_action` 通用回调 | 在 skill 配置中注册通用 `after_action` 记录使用日志 |

OpenCode skill 配置示例：

```yaml
callbacks:
  on_load:
    - run: "bash /path/to/Yang.skills/hooks/session-start.sh"
  after_action:
    - match:
        action: "write"
        path: "predictions/**"
      run: "bash /path/to/Yang.skills/hooks/prediction-immutability.sh"
    - match:
        action: "skill_call"
        skill: "yang-retro"
      run: "bash /path/to/Yang.skills/hooks/bump-trigger-monitor.sh"
```

#### allowed-tools 映射

| Claude Code 工具 | OpenCode 映射 | 说明 |
|-----------------|-------------|------|
| `Bash(*)` | `execute` | 命令执行 |
| `Read` | `read` | 文件读取 |
| `Write` | `write` | 文件写入 |
| `Edit` | `edit` | 文件编辑 |
| `Grep` / `Glob` | `search` / `glob` | 搜索工具 |
| `Skill` | `invoke` | 子 skill 调用 |

### 3.3 OpenClaw 适配

#### Hooks 迁移

OpenClaw 使用事件驱动架构：

| Claude Code Hook | OpenClaw 等价方案 | 实现方式 |
|------------------|-----------------|----------|
| `on_prediction_write` | OpenClaw `on_file_written` 事件 | 在 claw 配置中订阅 `on_file_written` 事件，路径匹配 `predictions/` 时触发校验 |
| `on_session_start` | OpenClaw `on_session_init` 事件 | 在 claw 配置中订阅 `on_session_init` 事件 |
| `on_retro_complete` | OpenClaw `on_skill_complete` 事件 | 在 claw 配置中订阅 `on_skill_complete` 事件，skill 名匹配 `yang-retro` |
| 被动日志 | OpenClaw `on_any_action` 事件 | 订阅通用事件记录日志 |

#### allowed-tools 映射

| Claude Code 工具 | OpenClaw 映射 | 说明 |
|-----------------|-------------|------|
| `Bash(*)` | `run` | 命令执行 |
| `Read` / `Write` / `Edit` | `file_ops` | 文件操作集合 |
| `Grep` / `Glob` | `find` | 搜索工具 |
| `Skill` | `call` | 子 skill 调用 |

### 3.4 Cursor 适配

Cursor 不支持 hooks 和自动 skill 路由，需手动补偿：

| 受限功能 | 补偿方案 |
|----------|----------|
| Hooks | 用户需手动在终端执行对应 `.sh` 脚本（如每次写预测后手动运行 `prediction-immutability.sh`） |
| 自动 skill 路由 | 用户需手动在聊天中输入完整 skill 命令（如 `/yang-score`） |
| allowed-tools | Cursor 自动管理工具权限，无需显式声明 |
| 进化总线 | 不支持多 Agent 协作，仅可使用 Solo 模式 |

### 3.5 GitHub Copilot 适配

GitHub Copilot 限制与 Cursor 类似，额外注意：

| 受限功能 | 补偿方案 |
|----------|----------|
| Hooks | 不支持。用户需在 VS Code 终端手动执行 hook 脚本 |
| Skill 路由 | 通过 Copilot Chat 的 `@workspace` 代理手动触发 |
| allowed-tools | Copilot 自动管理，无需声明 |
| 进化总线 | 不支持，仅 Solo 模式 |

---

## 4. 跨 Runtime 测试清单

以下清单用于验证 Yang.skills 在目标 runtime 上的功能完整性。每个 runtime 上线前必须通过所有 **P0** 项，**P1** 项建议通过。

### P0：核心功能（必须通过）

- [ ] **SKILL.md 解析**：runtime 能正确读取并解析 SKILL.md 的 frontmatter（name、version、description、compatibility、trigger-words、tags）
- [ ] **子 skill 路由**：用户输入触发词后，runtime 能正确路由到对应子 skill
- [ ] **知识库引用**：子 skill 能正确引用 `knowledge/` 下的知识库文件
- [ ] **共享协议加载**：子 skill 能正确引用 `shared-protocols/` 下的协议文件
- [ ] **状态文件读写**：能正确读写 `.yang-state.json`，schema 版本校验通过
- [ ] **文件操作**：能创建/读取/编辑项目目录下的所有必要文件（scripts/、predictions/、videos/ 等）
- [ ] **Python 适配器执行**：能调用 `adapters/` 下的 Python 脚本（需 Python 环境可用）
- [ ] **盲预测不可变**：预测写入后，immutability 保护机制生效（hook 或手动等价方案）

### P1：增强功能（建议通过）

- [ ] **Session 启动报告**：会话启动时自动报告 buffer 状态和待复盘项
- [ ] **Bump 触发监控**：复盘完成后自动检查 bump 条件
- [ ] **使用日志记录**：skill 调用被被动记录到 `.yang-cache/usage.jsonl`
- [ ] **allowed-tools 映射**：SKILL.md 中声明的工具权限在目标 runtime 上正确映射
- [ ] **多 Agent 协作**：进化总线在支持多 Agent 的 runtime 上正常运行（仅 Claude Code / Codex CLI / OpenCode / OpenClaw）
- [ ] **竞品数据库写入**：竞品数据正确写入 `project_data.db`（非纯 markdown）

### P2：体验优化（可选）

- [ ] **Hot reload**：修改 SKILL.md 或子 skill 后无需重启即可生效
- [ ] **缓存机制**：知识库引用缓存、热点缓存等在目标 runtime 上正常工作
- [ ] **错误恢复**：hook 执行失败不阻断主流程，降级为警告
- [ ] **跨平台路径**：Windows/macOS/Linux 路径分隔符正确处理

### 测试执行方式

```bash
# 1. 在目标 runtime 中加载 Yang.skills
# 2. 依次执行 P0 清单项
# 3. 记录每项结果（通过/失败/不适用）
# 4. P0 全部通过 → runtime 兼容性等级为 functional
# 5. P0 + P1 全部通过 → runtime 兼容性等级为 full
# 6. P0 有失败项 → runtime 兼容性等级为 partial，需补充适配
```

---

## 5. 适配贡献指南

如需为新的 Agent runtime 提交适配方案：

1. 在本文件兼容性矩阵中新增列，标注各功能域的兼容状态
2. 在第 3 节中新增子节，提供 hooks 迁移方案和 allowed-tools 映射
3. 在第 4 节测试清单中针对新 runtime 补充特有测试项
4. 提交 PR 并附上测试清单执行结果

适配方案设计原则：
- **不修改核心逻辑**：适配层应仅涉及 hooks 配置和工具映射，不修改 skill 内部工作流
- **等价行为**：适配后的行为必须与 Claude Code 原生行为等价，尤其是盲预测不可变保护
- **降级透明**：如某功能无法等价实现，必须在适配指南中明确标注限制和补偿方案

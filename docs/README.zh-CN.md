# PowerShell 可靠性框架（PRF）

> 让 AI Agent 可靠地生成 PowerShell —— AI Agent Infrastructure / Windows Automation Reliability Layer
>
> v0.1.0 Skill Package（规划报告 Part I：Skill-based Reliability Layer）

[English](../README.md)

PRF 不是教程、不是代码生成器、也不是 Copilot 提示词。它是一个面向 AI Coding Agent 的
**可靠性层**：任何支持 Agent Skills 的 Agent 在生成 / 审查 / 执行 PowerShell 之前默认加载，
把流程从「LLM → 脚本 → 祈祷」变成：

```text
Probe → Classify(R/W/D/N/C) → Draft → Rule Check → Propose(-WhatIf) → Confirm → Execute → Verify → Report
```

## 仓库结构

```text
PowerShell-Reliability-Framework/
├── SKILL.md                        # 技能入口：Generation Protocol + 硬性门禁
├── README.md                       # 英文主说明
├── knowledge/                      # 知识库（6 篇）
│   ├── powershell-model.md         #   对象管道 / 流 / 错误语义
│   ├── compatibility.md            #   5.1 ↔ 7.x 差异矩阵、模块可用性现实
│   ├── security-rules.md           #   攻击面与防御性生成姿态
│   ├── enterprise-patterns.md      #   ShouldProcess、日志、远程、批量操作礼仪
│   ├── anti-patterns.md            #   AP-01..AP-24 反模式目录（bad→good）
│   └── here-strings-and-heredocs.md #   定界符语法、bash heredoc 冲突、写入器差异
├── rules/
│   └── reliability-rules.yaml      # 机器可读规则语料（v0.1：109 条）
├── examples/
│   ├── bad/                        # 12 个负样本（禁止执行）
│   ├── good/                       # 12 个对应正样本
│   └── EXAMPLES.md                 # 配对索引
├── benchmark/
│   └── cases.json                  # 可靠性 Benchmark（v0.1：110 个用例）
├── tools/
│   ├── probe-environment.ps1       # 目标机规范探测脚本
│   ├── validate.py                 # 包完整性门禁（L0）
│   └── rule-selftest.py            # 检测器一致性门禁（L1）
├── .github/workflows/ci.yml        # CI 门禁（macOS 优先通道）
└── docs/
    ├── README.zh-CN.md             # 本文件
    └── testing-plan.md             # 测试与评测方案（A/B 协议，英文）
```

## 快速开始

1. **接入你的 Agent**：把本目录交给 Agent 的 skill 加载机制（入口是 `SKILL.md`）。
   - Claude Code / Cursor 风格的 Agent：放入其 skills 目录即可。
   - DeepSeek Harness (DSH)：复制到 `${DSH_HOME:-$HOME/.dsh}/.agent-presets/<preset>/skills/`
     或在 preset composition 中引用。
2. 指示 Agent：*"Load the powershell-reliability-framework skill before any PowerShell work."*
3. 随时校验包完整性：

   ```bash
   python3 tools/validate.py        # L0 门禁
   python3 tools/rule-selftest.py   # L1 门禁
   ```

4. 对目标机做任何生成动作前先跑规范探测：

   ```powershell
   pwsh -File tools/probe-environment.ps1 -AsJson   # 或 powershell.exe
   ```

## 规则 Schema

`rules/reliability-rules.yaml` 中每条规则包含：`id · category · severity · title ·
description · bad · good · rationale · applies_to · tags · detection{pattern,
psscriptanalyzer}`。当前 109 条中 45 条带检测提示（见 YAML 头部 `detection_rule_count`），
覆盖率随 v0.2 静态分析集成继续提升。

## 路线图

| 版本 | 目标 | 状态 |
|---|---|---|
| v0.1.0 | Skill-based Reliability Layer | ✅ 本仓库（alpha） |
| v0.2.0 | 静态分析集成（PSScriptAnalyzer + PRF 自定义规则） | 已预留 `detection.psscriptanalyzer` 字段 |
| v0.3.0 | 沙箱执行（Windows Sandbox / Hyper-V runner） | — |
| v0.4.0 | 企业策略引擎（Admission-Controller 式 deny/audit/approve） | — |
| v0.5.0 | 多 Agent 架构（Planner/Engineer/Reviewer/Executor） | — |
| v1.0 | PowerShell Agent Runtime | Vision |

## 成功指标

| 指标 | 目标 | 当前 |
|---|---:|---:|
| Benchmark 用例数 | 100 | 110 ✅ |
| 规则条数 | 100+ | 109 |
| 知识文档 | 5 | 6 |
| 示例配对 | — | 12 |
| Agent 支持 | 3+ | 任意支持 Skills 的 Agent（格式通用） |

有效性目标（A/B 协议见 `docs/testing-plan.md`）正在建立；首轮双盲评测完成前不对外宣称任何有效性数字。

## 安全声明

`examples/bad/` 与安全规则片段展示的是*攻击形态*的 PowerShell（下载执行 cradle、
持久化模式等），**仅作为负样本教学用途**。会关闭安全控制的片段（Defender 偏好、
审计日志、内联原生代码、脚本 URL 加载器）以文字描述代替可运行命令；其余片段是真实的
PowerShell，需要 URL 处使用示例主机。绝不执行 `examples/bad/*.ps1` 或规则中的 `bad`
片段。PRF 仅用于防御性与可靠性工程目的。

## 许可证

按内容类型双许可：

| 内容 | 许可证 | 范围 |
|---|---|---|
| 代码 —— `tools/`、CI workflow | [MIT](../LICENSE) | 脚本与自动化 |
| 数据集 —— `knowledge/`、`rules/`、`benchmark/`、`examples/` | [CC-BY-4.0](../LICENSE-DATA) | 知识库、规则语料、Benchmark 用例、示例对 |

数据集复用的建议署名：*PowerShell Reliability Framework (PRF) dataset, CC-BY-4.0.*

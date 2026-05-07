# phdtaketaketake

> **以人脉关系网络为先**的 PhD 导师匹配工具，打包成 **Claude Code skill**（也兼容 Codex CLI / Cursor / 任何能读 SKILL.md 的 LLM agent）。
> 不靠 h-index，靠 connection 找对的导师。

中文 · [English](README.md)

## 安装

```bash
git clone https://github.com/powerofjinbo/phdtaketaketake.git \
  ~/.claude/skills/phdtaketaketake

cd ~/.claude/skills/phdtaketaketake
pip install -e .
```

下次开 Claude Code session 时自动加载。其他 agent 见下方[与其他 agent 配合](#与其他-agent-配合)。

> 没装 Claude Code？在 [claude.com/code](https://claude.com/code) 安装。

## 怎么用

在任何 Claude Code session 里，自然语言（中英文都行）描述你的情况：

> *"我今年秋季申请 Physics PhD，这是我的 CV [粘贴]，帮我找匹配的导师。"*

> *"我是 SJTU 材料系本科，研究方向 2D 材料 photodetector，GPA 88/100，求美国 PhD 申请定位。"*

Agent 会：

1. 拼装 profile（缺关键信息会主动问）
2. 在你的目标学校 web-search 匹配你研究方向的候选 PI
3. 查证每个候选与你现导师的 connection（合著 paper、学术家谱、共同 collaboration）
4. 调 `scripts/match.py` 跑确定性 4.0 制打分
5. 返回 ranked 候选 + 各维度分项 + 引用来源的解释

### 每个候选的输出

- **Match score**（0–4.0）+ **application_strength**（0–4.0，**不是概率**），带置信区间 ±
- **risk_adjusted_strength** = `application_strength − band/2` —— **这是默认排序键**，evidence 充分的候选能压过证据稀薄但 nominal strength 更高的对手
- **lower_bound** = `application_strength − band` —— 不确定性宽边的保守读数
- **5 档定性标签**：Reach · Target · Match · Safe · Far Reach
- **分项分**：Connection / Publication / Experience / GPA
- **Evidence 分项**：`total_signals` / `verified` / `missing` / `unsourced`（带具体哪些 signal 落在每档）
- **匹配原因** —— 引用真实搜索来源：例如 *"与 Prof. Wang 2022–2024 合著 4 篇 small-team 论文 (Google Scholar) · 同属 ATLAS H→cc̄ working group (ATLAS Glance)"*

## 架构：无静态缓存，只用真实数据

**没有打包候选导师缓存**。PhD 导师信息变化太快、覆盖太广，静态数据集不实用。改成：

| 组件 | 职责 |
|------|------|
| Agent（Claude / Codex / Cursor / …）| 深度检索：找候选、查证 connection、估计 signal —— **全部从真实网络来源，严禁编造** |
| `scripts/match.py` | 纯 Python 确定性打分 —— 把 agent 的发现喂入 4.0 制公式 |
| `data/journals/<field>.yaml`、`references/*.md`、`docs/scoring.md` | 项目对 tier / 公式 / schema 的权威定义 |

### Cardinal rule：只用真实数据

每条 connection edge、每个候选 PI 的事实，都必须可追溯到 agent 实际访问过的真实源（Google Scholar / OpenAlex / INSPIRE-HEP / PubMed / Math Genealogy / faculty page 等）。**严禁编造** —— 学生会根据 ranking 做真实人生决定，假数据比无数据更糟。缺失信号是诚实的，matcher 会自动加宽置信区间。

完整的允许来源列表和禁止行为列在 [`references/data_integrity.md`](references/data_integrity.md)。

## 设计 Charter

完整设计目标 / 非目标 / roadmap 在 [`docs/DESIGN.md`](docs/DESIGN.md)。一句话使命：

> **为 STEM 申请者生成"可审计、学科校准、connection-first"的美国 PhD advisor/program 排名，用来辅助选校选导师，但不伪装成录取概率预测器。**

## 覆盖范围

打分引擎本身领域无关；但**校准**对设计时考虑的领域更准：

| | 覆盖度 |
|--|--------|
| 🟢 **Best-supported** | 物理 / HEP、材料 (MSE) —— `data/journals/<field>.yaml` 有 bundled tier 表；打分系统最初就是针对这些子领域校准的 |
| 🟡 **可扩展** | 化学、生物、CS、数学、EE、化工、地学 —— agent 用 [`references/journal_tiers.md`](references/journal_tiers.md) 跨领域指引 + 训练知识；置信区间更宽 |
| ⚠️ **领域特殊性** | CS 顶会优先（venue 分布不同）、生物有 co-first authorship 惯例、数学论文节奏慢、医学走 multi-center RCT 体系 —— 详见 `references/journal_tiers.md` |

agent 检索质量决定结果质量 —— 数据永远新鲜（没有缓存）。

为新领域加 tier YAML：见 [CONTRIBUTING.md](CONTRIBUTING.md)。欢迎 PR。

## 跟其他工具对比

|                    | CSrankings   | h-index 排名 | **phdtaketaketake**          |
| ------------------ | ------------ | ------------ | ---------------------------- |
| 数据新鲜度          | 静态         | 静态         | ✅ agent 实时检索            |
| 个性化             | ❌           | ❌           | ✅ 学生 profile → 候选导师   |
| Connection 优先    | ❌           | ❌           | ✅ #1 排序信号               |
| 大组论文处理       | ❌           | ❌           | ✅ ATLAS/CMS 式 5+ 作者规则  |
| 多领域             | ❌ 仅 CS     | 部分         | ✅ 通用（任意领域）          |

## 打分哲学

4 维度 4.0 制（对齐 GPA），按学校档位自适应加权：

- **Connection (C)** —— 候选导师 ↔ 你现导师 的合著 + 家谱 + 共同 collab + 委员会同台
- **Publication (P)** —— 期刊 tier × 作者位次衰减；5+ 作者大组论文特殊化
- **Experience (E)** —— 实验室声誉 × 时长 × 产出，产出主导（50%）
- **GPA (G)** —— 直接 4.0 制；百分制 / 4.3 / 4.5 / 英制 honours 自动转换

`application_strength = match_score + tier_adjustment + pi_recruiting_signal`，clip 到 [0, 4.0]。

完整公式：[docs/scoring.md](docs/scoring.md) · Skill 指令：[SKILL.md](SKILL.md) · Profile + CandidateAdvisor schema：[references/profile_schema.md](references/profile_schema.md)。

## 与其他 agent 配合

Skill 是 Claude Code native 设计，但底层 matcher 是纯 Python，SKILL.md 工作流指令也是 framework-agnostic。其他 agent 用法：

- **Codex CLI / OpenCode**：在 repo 根加 symlink `ln -s SKILL.md AGENTS.md`。Codex 自动读 `AGENTS.md`。
- **Cursor**：把 `SKILL.md` 内容放到 `.cursorrules` 里。
- **其他**：直接说"follow the workflow in `SKILL.md`"，主流 coding agent 都能读懂并跑完整 deep-research + `scripts/match.py` 流。

## 示例对话

见 [`docs/example_session.md`](docs/example_session.md) 完整 walk-through。

## License

MIT —— 见 [LICENSE](LICENSE)。

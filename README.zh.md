# phdtaketaketake

> **以人脉关系网络为先**的 PhD 导师匹配工具，打包成 **Claude Code skill**（也兼容 Codex CLI / Cursor / 任何能读 SKILL.md 的 LLM agent）。
> 不靠 h-index，靠 connection 找对的导师。

中文 · [English](README.md)

> ⚠️ **校准声明**：phdtaketaketake 是**专家设计的启发式决策辅助系统**，**不是**经过实证校准的录取概率预测器。所有阈值（CAPEG 权重、recency 衰减、program difficulty 各 component、strategy bucket 切分等）都是 v1/v2 默认值，需要在真实 portfolio 上慢慢校准。输出是 4.0 制的**相对匹配度 / 申请强度指数**，**不是录取概率**。设计边界见 [`docs/DESIGN.md`](docs/DESIGN.md) §11。

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

在任何 Claude Code / QClaw / Codex session 里，自然语言（中英文都行）描述你的情况 —— **不需要自己写 JSON**：

> *"我是 2027 fall 申请 Physics PhD，方向 ATLAS Higgs / detector ML，UCI 本科 GPA 3.85/4.0，两篇 ATLAS big-collab paper，导师 Prof. X。请帮我找美国 top 10–30 的匹配 PI 并按 phdtaketaketake 的 evidence-first 规则排序。"*

> *"我是 SJTU 材料系本科，研究方向 2D 材料 photodetector，GPA 88/100，导师是 Prof. Y，求美国 top-30 PhD 申请定位。"*

Agent 会：

1. 拼装 profile（缺关键信息会主动问）
2. 在你的目标学校 web-search 匹配你研究方向的候选 PI
3. 查证每个候选与你现导师的 connection（合著 paper、学术家谱、共同 collaboration）
4. 调 `scripts/match.py` 跑确定性 4.0 制打分
5. 返回 ranked 候选 + 各维度分项 + 引用来源的解释

### 你需要给 agent 提供的信息

**必需（缺了 agent 会主动问）**：

- **学科 / 子方向** —— 例如 `physics / HEP`、`cs / NLP`、`bio / immunology`
- **本科学校 + GPA**（带 scale：`4.0` / `4.3` / `4.5` / `100` / UK honours）
- **研究方向** —— 1–2 句话即可
- **现导师** —— 姓名 + 学校。**没有这个，connection-first 匹配会失去 anchor**，matcher 会向 stderr 打 warning 且 C 维落地。
- **目标学校 tier 或 列表** —— `top_10` / `top_11_30` / `top_31_60` / `top_60_plus` 或具体校名

**可选（提供后输出更准）**：论文（题目 / 期刊 / 状态 / 作者位置 / 总作者数）、本科科研经历、已经看好的具体候选 PI、theory ↔ experiment 偏好、签证 / funding 限制。

Matcher 是 **evidence-first**：缺了可选字段 *只会让 confidence band 变宽*，**不会崩、也不会瞎填**。

### 每个候选的输出

- **`match_score`**（0–4.0）—— CAPEG 综合
- **`application_strength`**（0–4.0，**不是录取概率**）= `match + opportunity_adj`
- **`risk_adjusted_strength`** = `application_strength − band/2`
- **`difficulty_adjusted_strength`** = `max(0, risk_adjusted − program_penalty)` —— **主排序键（post-#5）**
- **`lower_bound`** = `application_strength − band` —— 不确定性宽边的保守读数
- **5 档定性标签**（应用在 `difficulty_adjusted_strength`）：Far Reach · Reach · Target · Match · Safe
- **5 维 pillar**：`c_score` / `a_score` / `p_score` / `e_score` / `g_score`
- **辅助 feature**：`o_score`（opportunity）· `program_difficulty_penalty` + `difficulty_reasons` · `research_fit_score` + 各 axis
- **Evidence 分项**：`total_signals` / `verified` / `missing` / `unsourced`（带具体哪些 signal 落在每档）
- **Strategy（post-#7）**：`apply_bucket`（priority / target / reach / only_if_space / drop）+ `recommended_action`（apply / contact_first / investigate_evidence / deprioritize / skip）+ `outreach_angle`（仅在有 sourced 材料时）+ `evidence_to_fix` 修复队列
- **匹配原因** —— 引用真实搜索来源：例如 *"与 Prof. Wang 2022–2024 合著 4 篇 small-team 论文 (Google Scholar) · 同属 ATLAS H→cc̄ working group (ATLAS Glance)"*

CLI 输出还有顶层 **`strategy_summary`**：portfolio 级别的 priority/target/reach/only_if_space/drop 候选 ID 列表 + evidence_fix_queue + portfolio_notes。

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

整套打分是**5 层 deterministic Python pipeline**，每个分数都能 trace 回引用过的 evidence：

```
match_score          = w_C·C + w_A·A + w_P·P + w_E·E + w_G·G        # CAPEG，按学校档位自适应权重
application_strength = clip(match_score + opportunity_adj, 0, 4.0)   # 加上招生周期可用性
risk_adjusted        = application_strength − band/2                 # band 越宽排序越靠后
difficulty_adjusted  = max(0, risk_adjusted − program_penalty)       # ← 主排序键
strategy             = bucket(difficulty_adjusted, evidence, …)      # → priority/target/reach/only_if_space/drop
```

5 个 **CAPEG** pillar，4.0 制，按学校档位 tier-adaptive 加权：

- **Connection (C)** —— 候选导师 ↔ 你现导师/推荐人之间的真实人脉路径：合著（区分 small-team vs big-collab）、学术家谱、共同 grant、co-mentored student、working group / analysis contact 重叠、committee/exam、同 institute、prior institution overlap、conference session 重叠。v2 聚合公式：`strongest + 0.10·second_strongest`，cap 到 1.0，再乘 recency 衰减。
- **Advisor influence (A)** —— **纯声誉**（post-#6a 重构）：h-index proxy + elite status + grad placement quality。Funding 和 recruiting 已拆到 **Opportunity (O)**。
- **Publication (P)** —— field-aware：venue tier × author role × status × recency × contribution-bonus，含 big-collab 和 consortium guardrail。Top-3 加权聚合。
- **Experience (E)** —— `0.20·lab_prestige + 0.30·duration + 0.50·output`，取最强单段。
- **GPA (G)** —— 4.0 直接对齐；4.3 / 4.5 / 100 / UK honours 全部归一化。

3 个**非 CAPEG** 维度：

- **Opportunity (O)** —— 招生周期可用性：recruiting health + active funding + lab capacity + accessibility。派生 `opportunity_adj`（替代 v1 `pi_adj`）。`not_recruiting` 强制 `application_strength=0`。
- **Program difficulty (D)** —— per-program penalty 0–0.8：school tier admit-rate factor + cohort size + admission model + funding structure + faculty count + international friendliness。从 `risk_adjusted_strength` 减掉得到 `difficulty_adjusted_strength`（**主排序键**）。
- **Research fit (R)** —— 结构化 6 轴 tie-breaker：`0.30·topic + 0.20·method + 0.15·system + 0.15·temporal + 0.10·grant + 0.10·background`。永远不当 6th pillar，仅作排序 tie-break。

5 档定性标签（应用在 `difficulty_adjusted_strength` 上）：**Far Reach · Reach · Target · Match · Safe**。

完整公式：[docs/scoring.md](docs/scoring.md) · 流水线图：[docs/scoring_pipeline.md](docs/scoring_pipeline.md) · Skill 指令：[SKILL.md](SKILL.md) · Profile + CandidateAdvisor schema：[references/profile_schema.md](references/profile_schema.md)。

## 与其他 agent 配合

Skill 是 Claude Code native 设计，但底层 matcher 是纯 Python，SKILL.md 工作流指令也是 framework-agnostic。其他 agent 用法：

- **Codex CLI / OpenCode**：在 repo 根加 symlink `ln -s SKILL.md AGENTS.md`。Codex 自动读 `AGENTS.md`。
- **Cursor**：把 `SKILL.md` 内容放到 `.cursorrules` 里。
- **其他**：直接说"follow the workflow in `SKILL.md`"，主流 coding agent 都能读懂并跑完整 deep-research + `scripts/match.py` 流。

## 示例对话

见 [`docs/example_session.md`](docs/example_session.md) 完整 walk-through。

## License

MIT —— 见 [LICENSE](LICENSE)。

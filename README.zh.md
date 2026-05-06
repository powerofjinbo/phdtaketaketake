# phdtaketaketake

> **以人脉关系网络为先**的 PhD 导师匹配工具 —— 不靠 h-index，靠 connection。
>
> 打包成 **Claude Code skill** 形式，自然语言（中英文都行）就能用。

中文 · [English](README.md)

![demo](docs/demo.png)

---

## 安装（作为 Claude Code skill）

```bash
git clone https://github.com/powerofjinbo/phdtaketaketake.git \
  ~/.claude/skills/phdtaketaketake

cd ~/.claude/skills/phdtaketaketake
pip install -e .
```

下次开 Claude Code session 时自动加载这个 skill。

> **没装 Claude Code？** 在 [claude.com/code](https://claude.com/code) 安装。
> 也支持纯 CLI / Streamlit / Python API 用法，见下方[其他用法](#其他用法)。

## 怎么用

在任何 Claude Code session 里，直接说你要什么：

> *"我今年秋季申请 Physics PhD，这是我的 CV [粘贴]，帮我找匹配的导师。"*

> *"我是 SJTU 材料系本科，研究方向 2D 材料的 photodetector，GPA 88/100，求美国 PhD 申请定位。"*

> *"帮我评估一下我这 3 篇 paper 在申研里值多少分：[列表]"*

Claude 会读你的 CV，build profile，跑匹配脚本（`scripts/match.py`），
返回 ranked 候选导师 + 各维度分项 + connection 路径解释。

## 输出内容

每个候选导师卡片：

- **Match score**（0–4.0）—— 4 维加权
- **录取可能性**（0–4.0），带置信区间 ±0.3 / 0.5 / 0.7
- **5 档定性标签**：Reach · Target · Match · Safe · Far Reach
- **分项分**：Connection / Publication / Experience / GPA
- **匹配原因**：connection 路径解释
  （例："与你导师近 5 年合著 4 篇；学术家谱同一师门"）

## 跟其他工具对比

|                    | CSrankings   | h-index 排名 | **phdtaketaketake**          |
| ------------------ | ------------ | ------------ | ---------------------------- |
| 数据               | 顶会 paper 数| 引用数       | 合著图 + 家谱 + 多维度       |
| 个性化             | ❌           | ❌           | ✅ 学生 profile → 候选导师   |
| Connection 优先    | ❌           | ❌           | ✅ #1 排序信号               |
| 多领域             | ❌ 仅 CS     | 部分         | ✅（v0.1 含 HEP/物理 + MSE） |
| 大组论文处理       | ❌           | ❌           | ✅ ATLAS/CMS 式 5+ 作者规则  |
| 自然语言交互       | ❌           | ❌           | ✅ via Claude Code           |

## 打分哲学

4 维度 4.0 制：

- **Connection (C)** —— 候选导师 ↔ 你现导师 的合著 + 家谱 + 共同 collaboration + 委员会同台
- **Publication (P)** —— 期刊 tier × 作者位次衰减；5+ 作者大组论文特殊化
- **Experience (E)** —— 实验室声誉 × 时长 × 产出，产出主导（50%）
- **GPA (G)** —— 直接 4.0 制；百分制 / 4.3 / 4.5 / 英制 honours 自动转换

权重 **按学校档位自适应**：Top 10 偏 Connection（0.45），Top 60+ 偏 GPA（0.30）。

`admit_likelihood = match_score + tier_adjustment + pi_recruiting_signal`，
clip 到 [0, 4.0]。

完整公式见 [docs/scoring.md](docs/scoring.md)。
Skill 给 Claude 的指令在 [SKILL.md](SKILL.md)。
Profile schema 在 [references/profile_schema.md](references/profile_schema.md)。

## 覆盖范围（v0.1）

- 🔭 **高能物理 / 物理 (HEP/Physics)**
- 🧱 **材料科学与工程 (MSE)**

每个领域 Top 30 美国 PhD program。

加新领域 = 一个 YAML + 一个 cache build 脚本。见
[`scripts/build_advisors_cache.py`](scripts/build_advisors_cache.py)（WIP）。欢迎 PR。

## 其他用法

不用 Claude Code 也能跑（独立 Python 包）：

```bash
# CLI
phd-matcher match --profile data/samples/sample_student_physics.json \
  --field physics --top-k 10

# Streamlit demo
streamlit run phd_matcher/app.py

# Python API
python -c "from phd_matcher import rank_advisors; ..."

# 直接调脚本（skill 内部调的就是这个）
python scripts/match.py --profile-file profile.json --field physics --top-k 10
```

## Mock 数据声明

打包的 `data/advisors/mock_advisors.json` 是**合成 mock 数据**，不是真实教授信息。
这样 skill / CLI / demo 不用任何数据抓取就能跑起来。
真实 OpenAlex 缓存 pipeline 在 `scripts/build_advisors_cache.py`（WIP）。

## Roadmap

- [ ] 真实 OpenAlex 导师缓存（替换 mock）
- [ ] embedding 研究方向匹配（sentence-transformers / Voyage AI）
- [ ] LLM 生成解释（目前模板）
- [ ] 化学、生物、CS 等领域（欢迎社区 PR）
- [ ] 上 plugin marketplace

## License

MIT —— 见 [LICENSE](LICENSE)。

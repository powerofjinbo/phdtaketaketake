# phdtaketaketake

> **以人脉关系网络为先**的 PhD 导师匹配工具 —— 不靠 h-index，靠 connection。

中文 · [English](README.md)

![demo](docs/demo.png)

---

## 为什么做这个

主流 PhD 选导师工具按 h-index、引用数、论文数排序。这个工具按一个对实际录取机制更诚实的信号排序：

- **候选导师 ↔ 你现导师**之间的网络强度 —— 合著图、学术家谱、共同 collaboration、委员会同台。这是录取背后真正起作用的机制。
- **4 维度量化**，全部 4.0 制（对齐 GPA），按学校档位自适应加权。

## 它做什么

**输入**：本科 / 硕士院校、GPA、研究方向、当前研究导师（如有）、发表论文。

**输出**：候选 PhD 导师 ranked list，每个含：

- match score（0–4.0）
- 录取可能性（0–4.0，带置信区间）
- 4 维分项 breakdown（Connection / Publication / Experience / GPA）
- connection 路径解释（例："你导师与该 PI 近 5 年合著 4 篇论文"）

## 快速开始

```bash
git clone https://github.com/powerofjinbo/phdtaketaketake.git
cd phdtaketaketake
pip install -e .
streamlit run phd_matcher/app.py
```

预置示例 profile，clone 完直接看结果。换成自己的 profile JSON 即可匹配。

CLI 也能跑：

```bash
phd-matcher match --profile data/samples/sample_student_physics.json --field physics --top-k 10
```

## 跟其他工具的区别

|                     | CSrankings     | h-index 排名 | **phdtaketaketake**                |
| ------------------- | -------------- | ------------ | ---------------------------------- |
| 数据                | 顶会 paper 数 | 引用数       | 合著图 + 家谱 + 多维度             |
| 个性化              | ❌             | ❌            | ✅ 学生 profile → 候选导师         |
| Connection 优先     | ❌             | ❌            | ✅ #1 排序信号                     |
| 多领域              | ❌ 仅 CS       | 部分         | ✅（v0.1 含 HEP/物理 + MSE）       |
| 大组论文处理        | ❌             | ❌            | ✅ ATLAS/CMS 式 5+ 作者规则         |

## 打分哲学

4 维度 4.0 制：

- **Connection (C)** —— 候选导师 ↔ 你现导师 的合著 + 家谱 + 共同 collaboration
- **Publication (P)** —— 期刊 tier × 作者位次衰减；5+ 作者大组论文特殊化处理
- **Experience (E)** —— 实验室声誉 × 时长 × 产出，产出主导（50%）
- **GPA (G)** —— 直接 4.0 制；百分制 / 4.3 / 4.5 / 英制 honours 自动转换

权重 **按学校档位自适应**：Top 10 偏 Connection（0.45），Top 60+ 偏 GPA（0.30）。

`admit_likelihood = match_score + tier_adjustment + pi_recruiting_signal`，截到 [0, 4.0]，并给 5 档定性（`Reach` / `Target` / `Match` / `Safe` / `Far Reach`）。

完整公式见 [docs/scoring.md](docs/scoring.md)。

## 覆盖范围（v0.1）

- 🔭 **高能物理 / 物理 (HEP/Physics)**
- 🧱 **材料科学与工程 (MSE)**

每个领域覆盖 Top 30 美国 PhD program。

加新领域只需要：一个 YAML + 一个 cache build 脚本。欢迎 PR —— 见 `docs/contributing.md`。

## Roadmap

- [ ] 真实 OpenAlex 导师缓存（目前是 mock 数据 —— 让 demo 开箱即用，不是真的 PI 列表）
- [ ] embedding 研究方向匹配（sentence-transformers / Voyage AI）
- [ ] LLM 生成解释（可选，需 Anthropic / OpenAI key）
- [ ] HF Spaces live demo
- [ ] 化学、生物、CS 等领域（欢迎社区 PR）

## Mock 数据声明

打包的 `data/advisors/mock_advisors.json` 是**合成 mock 数据**，不是真实教授信息。这样 demo 不用 OpenAlex API key 就能跑起来。真实导师缓存 pipeline 在 `scripts/build_advisors_cache.py`（WIP）。

## License

MIT —— 见 [LICENSE](LICENSE)。

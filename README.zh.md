# phdtaketaketake

> **以人脉关系网络为先**的 PhD 导师匹配工具，打包成 **Claude Code skill**。
> 不靠 h-index，靠 connection 找对的导师。

中文 · [English](README.md)

## 安装

```bash
git clone https://github.com/powerofjinbo/phdtaketaketake.git \
  ~/.claude/skills/phdtaketaketake

cd ~/.claude/skills/phdtaketaketake
pip install -e .
```

下次开 Claude Code session 时自动加载这个 skill。

> 没装 Claude Code？在 [claude.com/code](https://claude.com/code) 安装。

## 怎么用

在任何 Claude Code session 里，自然语言（中英文都行）描述你的情况：

> *"我今年秋季申请 Physics PhD，这是我的 CV [粘贴]，帮我找匹配的导师。"*

> *"我是 SJTU 材料系本科，研究方向 2D 材料 photodetector，GPA 88/100，求美国 PhD 申请定位。"*

Claude 会：

1. 读你的 CV（信息不全时主动问关键字段）
2. 拼装 profile JSON
3. 跑 `scripts/match.py` 算分
4. 返回 ranked 候选导师 + 各维度分项 + connection 路径解释

### 每个候选的输出

- **Match score**（0–4.0）+ **录取可能性**（0–4.0），带置信区间 ±
- **5 档定性标签**：Reach · Target · Match · Safe · Far Reach
- **分项分**：Connection / Publication / Experience / GPA
- **匹配原因** —— 例："与你导师近 5 年合著 4 篇；学术家谱同一师门"

## 跟其他工具对比

|                    | CSrankings   | h-index 排名 | **phdtaketaketake**          |
| ------------------ | ------------ | ------------ | ---------------------------- |
| 数据               | 顶会 paper 数| 引用数       | 合著图 + 家谱 + 多维度       |
| 个性化             | ❌           | ❌           | ✅ 学生 profile → 候选导师   |
| Connection 优先    | ❌           | ❌           | ✅ #1 排序信号               |
| 大组论文处理       | ❌           | ❌           | ✅ ATLAS/CMS 式 5+ 作者规则  |
| 多领域             | ❌ 仅 CS     | 部分         | ✅ HEP/物理 + MSE            |

## 打分哲学

4 维度 4.0 制（对齐 GPA），按学校档位自适应加权：

- **Connection (C)** —— 候选导师 ↔ 你现导师 的合著 + 家谱 + 共同 collab + 委员会同台
- **Publication (P)** —— 期刊 tier × 作者位次衰减；5+ 作者大组论文特殊化
- **Experience (E)** —— 实验室声誉 × 时长 × 产出，产出主导（50%）
- **GPA (G)** —— 直接 4.0 制；百分制 / 4.3 / 4.5 / 英制 honours 自动转换

`admit_likelihood = match_score + tier_adjustment + pi_recruiting_signal`，clip 到 [0, 4.0]。

完整公式：[docs/scoring.md](docs/scoring.md) · Skill 指令：[SKILL.md](SKILL.md) · Profile schema：[references/profile_schema.md](references/profile_schema.md)。

## 覆盖范围 —— 支持任意 STEM 领域

确定性打分引擎（Connection / Publication / Experience / GPA，4.0 制）**与领域无关** —— 任何 STEM 学科都跑同一套数学。

根据是否有 bundled 候选导师缓存分两条路径：

| 路径 | 领域 | 怎么跑 |
|------|------|-------|
| 🟢 **Bundled 缓存**（置信度高） | `physics`、`mse` | `scripts/match.py` 从 `data/advisors/` 加载候选 |
| 🟡 **Claude 生成候选**（置信度稍低） | 其他所有 STEM（化学 · 生物 · CS · 数学 · EE · 化工 · 地学 · …） | Claude 用训练知识针对用户的研究方向生成合理候选导师，再喂给同一套打分引擎 |

添加新领域的 verified cache：见 [CONTRIBUTING.md](CONTRIBUTING.md)。欢迎 PR。

## Mock 数据声明

打包的 `data/advisors/mock_advisors.json` 是**合成 mock 数据**，不是真实教授信息。这样 skill 不用任何数据抓取就能跑起来。真实 OpenAlex 缓存 pipeline 还在 roadmap 上。

## License

MIT —— 见 [LICENSE](LICENSE)。

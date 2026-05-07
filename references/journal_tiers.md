# Journal tier reference

The tier scale (S / 1–5 / 0) is universal across STEM. The journals are
field-specific. This page is a cross-field digest. Bundled YAMLs at
`data/journals/<field>.yaml` cover **physics + MSE** in detail; for other fields,
use this page + your domain knowledge.

⚠️ **Field-specific caveats** (the scoring system was originally calibrated
for physics + MSE; treat other fields with appropriate skepticism):

- **CS** is **conference-first**, not journal-first. Treat top conferences
  as journal-equivalent. Different tier balance (most CS PhDs apply with
  conference papers, not journals).
- **Biology** has **co-first authorship** and **co-corresponding** conventions.
  When the user says "shared first author" or there's an asterisk on the
  byline, treat as 1st-author position. Co-corresponding for senior author —
  not relevant for grad applicants.
- **Math** has a longer publication pipeline (1–3y is normal); preprints on
  arXiv often count more like papers. Top venues (Annals, Inventiones, JAMS)
  publish far fewer papers / yr than physics flagships.
- **Clinical / medical** uses RCT-driven prestige hierarchies (NEJM, Lancet,
  JAMA). The 5+ author rule applies to large multi-center trials similarly
  to HEP big-collab papers.

## Tier baselines

| Tier | Baseline | Meaning |
|------|----------|---------|
| `"S"` | 4.0 | Cross-disciplinary top |
| `1` | 4.0 | Field flagship |
| `2` | 3.7 | Upper specialty |
| `3` | 3.3 | Mid specialty |
| `4` | 2.8 | General SCI |
| `5` | 2.3 | Weak / workshop |
| `0` | 0 | Retracted / predatory |

## Cross-disciplinary (Tier S, all fields)

Nature · Science · Cell · Nature Methods · Nature Biotechnology · Nature Medicine · PNAS *(field-specific tier 2 in some bio circles, but treat as Tier S for broad cross-disciplinary work)*

## Physics

**Tier 1 (4.0)**: PRL · Nature Physics · Science Advances (physics scope)
**Tier 2 (3.7)**: PRX · JHEP · PRA / B / C / D / E · ApJL · Nature Astronomy · Nature Photonics · Reviews of Modern Physics
**Tier 3 (3.3)**: ApJ · MNRAS · PLB · EPJC · NJP · A&A · JCAP
**Tier 4 (2.8)**: PR Applied / Materials / Fluids · J Phys G · AJP

## Chemistry

**Tier 1 (4.0)**: JACS · Angewandte Chemie Int. Ed. · Nature Chemistry · Chem
**Tier 2 (3.7)**: Chemical Science · ACS Catalysis · Nature Catalysis · J. Phys. Chem. Lett. (selectively) · Accounts of Chemical Research
**Tier 3 (3.3)**: Org. Lett. · Inorg. Chem. · J. Phys. Chem. A / B / C · Chem. Mater. · Macromolecules · ACS Catal. (B-list) · Green Chem.
**Tier 4 (2.8)**: Most other ACS / RSC / Wiley SCI specialty journals

## Biology / Life sciences

**Tier 1 (4.0)**: Nature subjournals (Genetics, Methods, Biotechnology, Cell Biology, Immunology, Neuroscience, Microbiology, Structural & Mol. Biology) · Cell subjournals (Mol Cell, Cancer Cell, Cell Stem Cell, Immunity, Neuron)
**Tier 2 (3.7)**: eLife · PNAS · Nature Communications · EMBO Journal · Genome Research · Genes & Development
**Tier 3 (3.3)**: PLOS Biology · J. Cell Biology · Bioinformatics · Nucleic Acids Research · Cancer Research · Blood · Circulation · Plant Cell
**Tier 4 (2.8)**: BMC series · PLOS ONE · Sci. Reports · most field-general SCI

## Materials Science & Engineering

**Tier 1 (4.0)**: Nature Materials · Advanced Materials · Nature Nanotechnology · Acta Materialia · JACS
**Tier 2 (3.7)**: Adv Funct Mater · Nano Letters · ACS Nano · Materials Today · Materials Horizons · Angew Chem Int Ed · Energy & Environmental Science · Nature Energy
**Tier 3 (3.3)**: Chem Mater · J Mater Chem A / B / C · Nanoscale · Adv Energy Mater · Carbon · Acta Cryst B · Macromolecules · J Phys Chem C · Small
**Tier 4 (2.8)**: J Appl Phys · Surf Sci · J Mater Sci · Mater Lett · Thin Solid Films

## Computer Science

**CS is conference-driven.** Treat top conferences as journal-equivalent:

**Tier 1 (4.0)**: NeurIPS · ICML · ICLR · CVPR · ACL · SOSP · OSDI · SIGGRAPH · STOC · FOCS · JMLR · CACM (research articles)
**Tier 2 (3.7)**: EMNLP · NAACL · KDD · WWW · ICCV · ECCV · UIST · CHI · POPL · PLDI · USENIX Security · IEEE S&P · CCS · NDSS · ICSE · Communications of the ACM
**Tier 3 (3.3)**: AAAI · IJCAI · COLING · ACMMM · ACML · ICDE · MICRO · ASPLOS · HPCA · ICSE workshops · TPAMI · TIT · TC
**Tier 4 (2.8)**: Mid-tier IEEE / ACM transactions · domain workshops with proceedings
**Tier 5 (2.3)**: Workshop posters without rigorous review

## Mathematics

**Tier 1 (4.0)**: Annals of Mathematics · Inventiones Mathematicae · J. American Mathematical Society (JAMS) · Acta Mathematica · Publications mathématiques de l'IHÉS
**Tier 2 (3.7)**: Duke Math J · Geometry & Topology · Math. Annalen · J. Reine und Angew. Math. (Crelle) · Compositio Math · J. Topology
**Tier 3 (3.3)**: Trans. AMS · Proc. AMS · Math. Z. · Pacific J. Math · J. Functional Analysis · J. Differential Equations
**Tier 4 (2.8)**: Most JCR Q1–Q2 specialty math journals not above

## Electrical & Computer Engineering

**Tier 1 (4.0)**: Nature Electronics · Nature Photonics · IEEE TPAMI (selectively) · Journal of Solid-State Circuits (top venues)
**Tier 2 (3.7)**: IEEE Trans. Circuits & Systems · Optica · IEEE TIT · Proc. IEEE
**Tier 3 (3.3)**: Most IEEE Transactions — Signal Processing, Communications, Power Electronics, etc.
**Tier 4 (2.8)**: IEEE Access · IET journals · domain mid-tier

## Chemical Engineering

**Tier 1 (4.0)**: Nature Catalysis · ACS Catalysis · Joule
**Tier 2 (3.7)**: Chem. Eng. Sci. (selectively) · AIChE Journal · Energy & Environmental Science (cross with MSE) · ACS Energy Letters
**Tier 3 (3.3)**: Ind. Eng. Chem. Res. · Chem. Eng. J. · J. Membrane Sci. · Energy & Fuels
**Tier 4 (2.8)**: Most other ChemE specialty journals

## Earth / atmospheric / planetary science

**Tier 1 (4.0)**: Nature Geoscience · Nature Climate Change · Reviews of Geophysics
**Tier 2 (3.7)**: J. Geophysical Research (subjournals) · Geophysical Research Letters · Earth & Planetary Sci. Letters · Atmospheric Chemistry & Physics
**Tier 3 (3.3)**: Geochim. Cosmochim. Acta · J. Climate · Tectonics · Quaternary Science Reviews
**Tier 4 (2.8)**: Most JCR Q1–Q2 domain journals not above

## When you don't recognize a journal

1. Check if it's a sister journal of one above (e.g., *Nature Communications*
   → tier 2; *Phys. Rev. Research* → tier 3 typically; *Communications Chemistry*
   → tier 2/3 boundary).
2. Look up SCI quartile / impact factor as a rough proxy. **Q1 with high IF
   ≠ tier 1** automatically — flagship status requires editorial reputation
   in the field, not just IF.
3. Default to **tier `4` (general SCI)** when truly uncertain. Conservative.
4. **Never guess tier `1`** for an unfamiliar journal. That demands strong
   evidence of flagship status.

## Author position decay (within a paper)

| Position | Decrement |
|----------|-----------|
| 1 | 0 |
| 2 | −0.10 |
| 3 | −0.25 |
| 4 | −0.45 |
| 5+ | special: `min(3.5, baseline − 0.45)` |

The 5+ rule keeps top-tier big-collab papers (e.g., ATLAS / CMS PRL with 3000
authors, big multi-institution biology consortium papers) at 3.5, while
lower-tier 5+ papers don't get a reverse boost.

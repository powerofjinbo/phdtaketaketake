# Journal tier reference

Full tier table for both currently covered fields. Source: bundled YAML at
`data/journals/<field>.yaml`. This page is the human-readable digest.

## Tier baselines (4.0 scale)

| Tier | Baseline | Meaning |
|------|----------|---------|
| `"S"` | 4.0 | Cross-disciplinary top |
| `1` | 4.0 | Field flagship |
| `2` | 3.7 | Upper specialty |
| `3` | 3.3 | Mid specialty |
| `4` | 2.8 | General SCI |
| `5` | 2.3 | Weak / workshop |
| `0` | 0 | Retracted / predatory |

## Cross-disciplinary (Tier S, both fields)

Nature · Science · Cell · Nature Methods · Nature Biotechnology · Nature Medicine

## Physics

**Tier 1 (4.0)**
- Physical Review Letters (PRL)
- Nature Physics
- Science Advances (physics scope)

**Tier 2 (3.7)**
- Physical Review X (PRX)
- Journal of High Energy Physics (JHEP)
- Astrophysical Journal Letters (ApJL)
- Nature Astronomy
- Nature Photonics
- Reviews of Modern Physics (RMP)

**Tier 3 (3.3)**
- Physical Review A / B / C / D / E
- Astrophysical Journal (ApJ)
- Monthly Notices of the Royal Astronomical Society (MNRAS)
- Physics Letters B (PLB)
- European Physical Journal C (EPJC)
- New Journal of Physics (NJP)
- Astronomy & Astrophysics (A&A)
- Journal of Cosmology and Astroparticle Physics (JCAP)

**Tier 4 (2.8)**
- Physical Review Applied / Materials / Fluids
- Journal of Physics G
- American Journal of Physics (AJP)

## Materials Science & Engineering

**Tier 1 (4.0)**
- Nature Materials
- Advanced Materials
- Nature Nanotechnology
- Acta Materialia
- Journal of the American Chemical Society (JACS)

**Tier 2 (3.7)**
- Advanced Functional Materials
- Nano Letters
- ACS Nano
- Materials Today
- Materials Horizons
- Angewandte Chemie International Edition
- Energy & Environmental Science
- Nature Energy

**Tier 3 (3.3)**
- Chemistry of Materials
- Journal of Materials Chemistry A / B / C
- Nanoscale
- Advanced Energy Materials
- Carbon
- Acta Crystallographica B
- Macromolecules
- Journal of Physical Chemistry C
- Small

**Tier 4 (2.8)**
- Journal of Applied Physics
- Surface Science
- Journal of Materials Science
- Materials Letters
- Thin Solid Films

## When unsure

If a journal isn't on this list:

1. Check if it's a sister journal of one above (e.g. *Nature Communications* —
   tier 2; *PRR / Phys. Rev. Research* — tier 3).
2. Look up SCI quartile / impact factor as a rough proxy.
3. Default to tier `4` (general SCI) when truly uncertain — conservative.
4. **Never guess tier `1`** for an unfamiliar journal — that demands strong
   evidence (flagship status in the field).

## Author position decay (within a paper)

| Position | Decrement |
|----------|-----------|
| 1 | 0 |
| 2 | −0.10 |
| 3 | −0.25 |
| 4 | −0.45 |
| 5+ | special: `min(3.5, baseline − 0.45)` |

The 5+ rule keeps top-tier big-collab papers (e.g., ATLAS / CMS PRL with 3000
authors) at 3.5, while lower-tier 5+ papers don't get a reverse boost.

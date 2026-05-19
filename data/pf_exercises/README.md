# PF Exercises Dataset
# Extracted from papers for training/evaluating PF exercise generation

## Summary

| Source | Domain | Topic | Level | # Exercises | Types |
|--------|--------|-------|-------|-------------|-------|
| Kapur & Bielaczyc (2012) | Math | Average Speed | Grade 7 | 5 | complex, well-structured, posttest |
| Kerrigan, Weber & Chinn (2021) | Math | Fair Division | Undergraduate | 4 | complex, posttest, in-class |
| Loibl & Rummel (2014) | Math | Variance/Consistency | Grade 10 | 4 | complex, conceptual, contrasting cases |
| Puech, Macina et al. (2025) | Math | Variance + Apportionment | Grade 9 | 2 | invention, ill-structured |

## Dataset Statistics
- Total exercises: 15
- Complex PF problems (generation phase): 7
- Well-structured problems: 3
- Posttest/transfer problems: 4
- Contrasting cases: 1

## Design Principles (common across all papers)

### Problem Design (Phase 1: Generation)
1. **Challenge but don't frustrate** — problems use elementary operations but solutions aren't obvious
2. **Activate prior knowledge** — require resources students already have (but are insufficient)
3. **Admit multiple RSMs** — multiple representations/solution methods possible
4. **Affective engagement** — real-world narrative contexts
5. **Sweet spot calibration** — complexity × prior resources × affective draw

### Instruction Design (Phase 2: Consolidation)
1. Compare/contrast student solutions to canonical solution
2. Highlight WHY student solutions fail (specify knowledge gaps)
3. Identify critical conceptual features
4. Assemble canonical concepts from failed attempts

## Key Observations for LLM Generation

### What makes a good PF problem:
- The problem LOOKS solvable with prior knowledge
- Common approaches (ratios, simple division, range) produce reasonable-looking but WRONG answers
- The "trap" is a specific conceptual feature that prior methods miss
- Multiple students will produce DIFFERENT incorrect solutions (RSM diversity)
- The narrative context motivates engagement and makes assumptions explicit

### Topics that work well for PF:
- **Average speed**: ratio trap (non-additive property)
- **Variance/consistency**: range and mean are equal → must invent deviation measure
- **Fair division**: standoff situations requiring new resolution methods
- All share: canonical solution requires a NEW operation not in prior repertoire

### Structural patterns:
1. Data with controlled features (same mean/range forces deeper thinking)
2. Multi-party scenarios with constraints that create "standoffs"
3. Narrative problems where intuitive approaches give wrong answers
4. Problems where the QUESTION is clear but the METHOD is unknown

## Files
- `kapur_bielaczyc_2012.yaml` — Average speed problems (Singapore, Grade 7)
- `kerrigan_weber_chinn_2021.yaml` — Fair division problems (USA, undergraduate)
- `loibl_rummel_2014.yaml` — Variance/consistency problems (Germany, Grade 10)
- `puech_macina_2025_stratl.yaml` — Consistency + Apportionment (Singapore, Grade 9)

## TODO: Additional datasets to acquire
- [ ] StratL full dataset (15 problems, CC-BY-4.0) — check GitHub supplementary material
- [ ] Eedi dataset (Kaggle) — math misconception diagnostic questions
- [ ] Schwartz & Martin (2004) — original "inventing to prepare for learning" (variance)
- [ ] Kapur (2012) — extended study with more average speed variants
- [ ] Roll et al. (2009, 2011) — invention tasks with contrasting cases

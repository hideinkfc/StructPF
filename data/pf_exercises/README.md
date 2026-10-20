# PF Exercises Dataset

This folder holds two overlapping collections: paper-derived curated records
with research annotations, and a separate import of the StratL source dataset.
They support design inspection and comparisons; they are not a uniform set of
original, fully specified PF generation tasks.

## Local inventory

| File | Topic/context | Records | Provenance |
|---|---|---:|---|
| [kapur_bielaczyc_2012.yaml](kapur_bielaczyc_2012.yaml) | Average speed; Grade 7, Singapore | 6 | Curated transcription/normalization from the paper |
| [kerrigan_weber_chinn_2021.yaml](kerrigan_weber_chinn_2021.yaml) | Fair division; US undergraduate | 4 | Curated task text, solutions and behavioral annotations |
| [loibl_rummel_2014.yaml](loibl_rummel_2014.yaml) | Consistency/spread; Grade 10, Germany | 4 | Curated task structure; several data/item placeholders |
| [puech_macina_2025_stratl.yaml](puech_macina_2025_stratl.yaml) | Consistency and apportionment | 2 | Earlier annotated subset; retain separately from the source import |
| [puech_macina_2025_stratl_full.yaml](puech_macina_2025_stratl_full.yaml) | Mathematics/physics; Grades 5, 7, 9, 11 and non-STEM undergraduate | 15 | Imported exercise/solution text from StratL `PFdataset.csv` |

The first four files contain **16 records**, including six with
`phase: generation`, six posttest records, three practice records and one
instruction/contrasting-cases record. The full import adds **15 records**, but
overlaps the curated tasks: **31 stored records does not mean 31 unique PF
exercises**. Its source types include invention, ill-structured, well-structured
and mixed labels; the import assigns `phase: generation` to every row, even
well-structured comparison tasks. Filter by source, type and actual content,
not that field alone.

## Provenance and limitations

- The curated YAMLs mix transcribed text, abbreviated or reconstructed task
  descriptions, normalized prior resources, solutions and interpretive design
  notes. Do not call all fields verbatim author-provided data or observed
  student behavior. Loibl's `[Data table ...]` and `[Given dataset ...]` entries
  are placeholders, not runnable numerical originals.
- The full StratL import preserves source exercise/solution text, source
  references and grades. It does **not** supply `prior_knowledge_required`,
  `expected_student_rsms` or `critical_conceptual_features`; those lists are
  deliberately empty. Empty means unavailable, not that no prior knowledge
  or student methods exist.
- Preserve original imported text, including inherited typos and numerical
  inconsistencies. For example, the consistency task has conflicting year
  labels and the source solution says `12/5 = 3.2` after giving a squared
  deviation sum of 16. Its players' means and ranges are not all equal, despite
  the earlier annotated subset's generic design claim. Report a source issue
  rather than silently rewriting the original into a verified task.
- Grades/context in the earlier Puech subset are not authoritative for every
  imported task; the full file identifies country/apportionment as
  non-STEM undergraduate, for example.
- Kapur's prior resources and nine student representation/solution categories
  have a separate [source verification note](../../docs/pf-generation/KAPUR_BIELACZYC_2012_EVIDENCE.md).
  Their YAML wording is normalized, not a verbatim checklist, and the observed
  methods are specific to that study.
- The full StratL import declares CC BY 4.0 and attributes Puech, Macina,
  Chatain, Sachan and Kapur (2025), arXiv:2410.03781, and
  [eth-lre/Productive-Failure-Problems](https://github.com/eth-lre/Productive-Failure-Problems).
  That license does not automatically apply to every paper-derived file here.

## Current use

The current PF route uses prior-resource recommendations, design selection,
bounded numerical checking/repair and task writing. Expert-resource lists are
comparison evidence held out of the grounded recommender's prompt; they are
not automatically copied into generation. See the
[PF pipeline](../../docs/pf-generation/PF_PIPELINE.md) and
[curriculum-grounding inventory](../curriculum_grounding/README.md).

Recent expert-direction comparisons use researcher-prepared generation inputs,
not original expert worksheets. Their generated tasks and model ratings are
separate from the source-text reference panels. In the saved comparison, the
Loibl-direction panel uses the related StratL consistency task attributed to
Kapur (2015), not the exact Loibl task. The pilot's
[provenance note](../../experiments/results/pf_expert_direction_pilot_20260929/postrun_provenance_note.json)
also records that its fixed V2 hypotheses were curator-authored, not observed
student errors or a blind held-out treatment.

Expert PF design can elicit correct-but-insufficient approaches as well as
mistakes. Familiar methods may fail to distinguish alternatives, become
incomplete or work only under a special assumption. Multiple wrong answers
alone do not establish multiple meaningful representations or productive
failure; instruction/consolidation and student behavior matter too.

## Maintenance

Run from the repository root. These scripts operate on local files, not models:

```bash
# Re-import from an existing local source CSV; overwrites the full-import YAML
./.venv/bin/python scripts/prior_methods/integrate_stratl.py data/stratl/PFdataset.csv

# Rebuild the descriptive method inventory; overwrites expert_anticipated.json
./.venv/bin/python scripts/prior_methods/build_expert_anticipated.py
```

Supply the actual CSV path to the importer; `data/stratl/PFdataset.csv` above
is an example input location, not a bundled file. Do not omit the argument.
Preserve historical artifacts before either rebuild. The inventory script
normalizes annotation fields heuristically and skips rows with no supplied
methods; its categories are not new human-validated student evidence.

The full StratL import is already present. Remaining work is source verification
of placeholders, inherited inconsistencies and unsupported annotation claims,
not acquisition of that same fifteen-task collection. Eedi has a separate role
and input contract documented in the
[MCQ overview](../../docs/mcq/MCQ_GENERATION_OVERVIEW.md).

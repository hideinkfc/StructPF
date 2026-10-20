# Learning Commons for PF tasks (2026-09-25; updated 2026-10-10)

**Status:** optional Learning Commons mathematical context is wired through recommendation,
task design and writing behind `--learning-commons`; baseline behavior stays unchanged.
A small paired pilot found no clear consistent quality gain. Keep the saved benchmark unchanged and the
[expert tasks](../../data/pf_exercises/) as evaluation holdouts.
The downstream default now uses a selected design brief, bounded data/check/repair,
and writing; the October 9 paired pilot below used the earlier route and was not
rerun under this default. See [PF_PIPELINE.md](PF_PIPELINE.md) for current status.

## Why investigate?

| Evidence | Result |
|---|---|
| [Saved Grade 7 benchmark](PF_PIPELINE.md#paper-setting-method-benchmark-protocol-and-results-september-23) | Pipeline 22/30 ready vs 30/30 for each direct version; frozen model-judge means 11.82/15 vs 14.40, 14.03, 14.20/15 on different ready subsets. In 21/22 pipeline tasks, "steady change" also rejects the data. |
| [Two-topic pilot](../../experiments/results/pf_prompt_proposal_feasibility_20260925/) | Checked contrast: Grade 7 1/1 ready, variance 0/1 ready. The [one ready task](../../experiments/results/pf_paper_benchmark/20260925_grade7_pipeline_feasibility_standalone_table1/) received 10/15 from the frozen model judge (difficulty and openness: 1/3 each). |

The [earlier Grade 7 design](../../experiments/results/pf_prompt_scope_pilot_20260925/grade7_pipeline/attempts/PIPELINE/001/result.json)
froze incompatible conditions for its intended contrast. Equal steps can
still have unequal rates: `[10,20,30] -> [4,10,16]`. This is a design
constraint, not an arithmetic failure. Neither run measured student learning.

**Hypothesis:** A sourced student first move plus checked mathematical contrast
may help PF tasks; not every task needs a wrong first move.

## What the graph offers

```text
Graph link -> candidate earlier skill -> check against the PF task
                              (not proof a class learned it)
```

[`buildsTowards`](https://docs.learningcommons.org/knowledge-graph/datasets/learning-progressions/math-coherence-map)
suggests progression, not a strict prerequisite;
[`supports`](https://docs.learningcommons.org/knowledge-graph/datasets/learning-components/math-learning-components)
links a fine-grained skill to a standard; `relatesTo` is not sequential.
[Eedi `hinders`](https://docs.learningcommons.org/knowledge-graph/datasets/learning-components/eedi-misconceptions-graph)
links misconceptions to Eedi constructs, **not** to standards. No Eedi
misconception was mapped here. [MCQ pathways](../mcq/MCQ_EVALUATION_OVERVIEW.md)
suggest errors, not observed student behavior.

| Expert target | Local match | Missing match |
|---|---|---|
| Singapore G7 average speed | Texas science; US unit rates | Singapore math |
| NRW G10 consistency | US spread measures | NRW curriculum |
| US undergraduate fair division | US high-school methods | Undergraduate Lone Divider task |

[Selected records, licenses, and offline helper](../../data/learning_commons/README.md)
are in the local v1.14.0 snapshot; the [curriculum corpus](../../data/curriculum_grounding/README.md)
holds jurisdiction-specific sources. Check row-level licenses and attribution.
`certifi` fixes the local TLS certificate error. Later HTTP 451 attempts failed;
the 2026-10-04 retry succeeded. The cause of HTTP 451 remains unknown.

## Official semantic search (2026-09-29)

User-run query via the [API helper](../../scripts/learning_commons_api.py):
`average speed`, Mathematics, default limit 5; no grade filter. Results are
ranked by the server's vector-similarity score, not a probability.

| Rank | Standard | What matched | Score |
|---:|---|---|---:|
| 1 | `6.RP.A.3.b` | Unit rates including constant speed | 0.6673 |
| 2 | `HSF-IF.B.6` | Average rate of change; related wording, different context | 0.6655 |
| 3 | `HSN-VM.A.3` | Velocity vectors; weak fit to this task | 0.6517 |
| 4 | `8.EE.B.5` | Distance-time graphs and speed comparison | 0.6506 |
| 5 | `7.RP.A.1` | Grade 7 unit rates, including a distance/time example | 0.6488 |

The top result is a useful constant-speed proxy; `7.RP.A.1` is the clearest
grade-aligned proxy. Neither establishes Singapore curriculum placement or
average speed over changing speeds. The narrow score range also cautions
against treating rank as a quality judgment.

**Follow-up API run (2026-10-04):** 7/7 queries completed, 10 returned matches
per query; completion does not mean relevance.
Mathematics throughout; Grade 7 only for speed; no jurisdiction filter.
[Raw results](../../experiments/results/learning_commons_queries/guided_search_20261004T154519022423Z.json).

| Query | First-ranked standard | Reading of the matches |
|---|---|---|
| `total distance divided by total time` | `7.RP.A.1` | Useful unit-rate background; not changing-speed reasoning. |
| `compare the spread of two data sets` | `HSS-ID.A.2` | Relevant comparison of spread, including standard deviation. |
| `measure variability using mean absolute deviation` | `7.SP.B.3` | Relevant; rank 2, `6.SP.B.5.c`, explicitly covers the measure. |
| `standard deviation as a measure of spread` | `7.SP.B.3` | First result uses mean absolute deviation; rank 3, `HSS-ID.A.2`, is more direct. |
| `fair division and envy-free allocation` | `3.G.A.2` | Mostly elementary equal shares; no target method in the returned ten. |
| `divide resources fairly among several people` | `2.G.A.3` | Equal shares and random fair decisions, not the target method. |
| `Lone Divider method` | `3.OA.C` | Arithmetic division, not the fair-division method. |

**Takeaway:** Useful candidate standards for speed/spread; fair division remains
unresolved by these searches, not absent from the graph. No prerequisite links
or PF improvement were tested.

[One real record -> proposed pipeline steps](LEARNING_COMMONS_DATA_FLOW.md).

**Other-topic searches (2026-10-09):** eight queries returned 80 entries
(51 distinct records). An [assistant review of every entry](../../experiments/results/learning_commons_queries/exploratory_search_20261009T130649982938Z_review.md)
found 35 specific supporting, 33 weak/broad, and 12 off-topic occurrences.
None fully states the queried relationship under the review's strict criterion;
this is not an independently validated benchmark. Exact-grade filters were used;
their effect on missing earlier foundations and search completeness is unknown.

## Implemented optional retrieval flow (2026-10-09)

One plain-language case-topic query retrieves up to ten standard descriptions on
a cache miss. The existing
recommendation call filters relevance, merges overlapping ideas, and selects
up to three distinct useful references, or none. No separate ranking call or
automatic linked-skill lookup is added. Initially omit the exact-grade filter;
give the recommender the target and class context instead. The flag is opt-in;
reference selection is not a prior-curriculum confirmation step.

Keep target explanations and related mathematical references separate from
prior-skill recommendations. The current prior-resource rules remain unchanged;
references are not turned into claims of classroom teaching.

Save the query, filters, retrieval time and complete API response once, then
save the selected short source labels and their mapping to original records.
Keep full identifiers, licenses and attribution in the saved evidence, not in
the main prompt. Reuse saved responses for fixed-input experiments without
presenting them as fresh searches. This is automatic logging, not another
model call or a manual evidence-review stage.
Code validates selected labels and forwards only the selected original text.
Offline production-gate tests pass. Small live selection trials exist, but broad
headings still sometimes survive selection, so relevance filtering is not yet
validated. A small paired generation pilot is recorded below; no learning
benefit or consistent PF quality improvement is established.
See the [implemented flow, commands and saved live traces](LEARNING_COMMONS_DATA_FLOW.md).
Reference text also reaches the current `design_brief` data/check loop; it
does not establish a taught prerequisite, a verified condition, or a student
response. The data stage preserves unsupported claims as warnings rather than
silently asserting them or treating them as demonstrated failures.

## Paired task generation (2026-10-09; gpt-5.6-luna)

[Exact side-by-side tasks and assistant inspection](../../experiments/results/learning_commons_pf_comparison_luna_20261009T151453Z/REVIEW.md):
baseline and context each produced 2/3 exercises, with the same cases, local
curriculum evidence, source code and requested caps. Actual calls were 28 versus
29. All four emitted tasks have valid checked arithmetic.

Speed shows the same numerical learning opportunity in both arms. Baseline
fractions are a very easy `1/2 = 2/4` task; context fractions stop on an ambiguous
instance-versus-family requirement. Context spread gives a same-mean/same-range
comparison, but reveals those summaries' insufficiency and can already be solved
by the assumed quartile method. Baseline spread was rejected for a range tie;
the inspection's numeric diagnostic shows that rejection is too strict.

No clear consistent improvement is demonstrated by these one-attempt pairs.
The review is by the assistant, not an independent human evaluator, and no
student responses were measured. Stopped cases and the earlier, separately
retained mini-model failures are not replaced or hidden.
These 28-versus-29 actual-call totals describe the saved legacy paired run,
not the current three-call D2b budget or a matched-cost quality experiment.

## Full-export phrase search (2026-09-29)

Case-insensitive literal search of names and descriptions across 301,294 v1.14.0
nodes; standards usually store their wording in descriptions. This was an
exploratory fallback; the official method is
`GET /academic-standards/search?query=<plain language>` (semantic, ranked) or
`statementCode=` (exact), used by the official tutorials in the
[knowledge-graph repo](https://github.com/learning-commons-org/knowledge-graph).

```mermaid
flowchart LR
  A["Three PF targets"] --> B["Plain-language terms"]
  B --> C["Search names + descriptions"]
```

| Target / term | Name / description matches | What appeared |
|---|---|---|
| Average speed: `average speed` | 0 / 5 | Texas Grade 7 science standard; also US high-school science and one Eedi misconception. No Singapore math standard. |
| Average speed: `distance and time` | 2 / 32 | Two activity titles; descriptions include 30 standards and two constructs, mostly broad quantity relationships. |
| Consistency: `consistency` | 0 / 195 | Only three math records: two Eedi misconception texts about data consistency and one probability standard. |
| Consistency: `spread` | 26 / 714 | 389 are Mathematics nodes; many concern statistical spread, but the phrase is broad and name hits include spreadsheets. |
| Fair division: `fair division` | 0 / 12 | All are math standards, mainly US high-school methods; no undergraduate match. |
| Fair division: `fair share` | 1 / 6 | One Grade 2 activity; standards mainly concern elementary sharing or mean as a fair share. |

`average speed` and `fair division` found clear US standards; `spread` found
useful but broad statistics matches. `consistency` found possible Eedi error
pathways, not a matching curriculum standard. No search filled the Singapore,
NRW, or undergraduate-context gaps.

## Next test (proposed)

1. Fix held-out targets; record source, gaps, and proposed first moves.
   Leave unsupported claims `unknown`.
2. Compare direct V1/V2/V3, existing pipeline, checked-contrast pipeline,
   and **checked-contrast plus graph** with frozen prompts, selection, and
   judge. Match both attempts and model-call budgets.
3. Check solutions and first moves; report ready/attempted, failures,
   validity, and distinct approaches. Blind-rate all ready tasks; seek
   independent and, where possible, simulated-then-real student evidence.

Success requires a pre-specified gain over the strongest tested direct
baseline without lower validity or hidden failures. Model ratings alone
cannot establish student learning.

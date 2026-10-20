# Curriculum Grounding for Expert PF Tasks

This folder contains curated prior-resource records and a separate retrieval
corpus for PF task design. A curriculum page proposes what students might have
learned; it does not establish what a particular class was taught or mastered.

The current grounded recommender sees curriculum/textbook excerpts, **not the
curated expert-resource lists**. Those lists are held out for comparison. Older
runs that supplied curated records to the model are historical conditions, not
evidence of independent recovery. See the canonical
[PF pipeline record](../../docs/pf-generation/PF_PIPELINE.md).

## Cells (grade × topic × country)

| File | Grade / Country | Target concept | Grounds | Strongest source |
|---|---|---|---|---|
| [moe_sg_grade7_average_speed.yaml](moe_sg_grade7_average_speed.yaml) | 7, Singapore | Average speed | Kapur avg-speed, StratL biking/hummingbird | MOE 2020 syllabus (local PDF) + paper-verified list |
| [moe_sg_grade9_variance.yaml](moe_sg_grade9_variance.yaml) | 9, Singapore | Variance/consistency | StratL consistency (Premier League) | MOE 2020 syllabus (local PDF) |
| [nrw_grade10_variance.yaml](nrw_grade10_variance.yaml) | 10, NRW Germany | Variance/consistency | Loibl & Rummel (2014) | NRW Kernlehrplan (local PDF) |
| [nrw_grade5_fraction_equivalence.yaml](nrw_grade5_fraction_equivalence.yaml) | 5, NRW Germany | Fraction equivalence | Mazziotti pizza, Pia/Ole | NRW Kernlehrplan (local PDF) + Mazziotti (2016) verified |
| [cbse_grade11_kinematics.yaml](cbse_grade11_kinematics.yaml) | 11, India CBSE | Kinematics (braking) | Kapur (2008) lawyer tasks | CBSE Physics curriculum (local PDF) |
| [usa_undergrad_fair_division.yaml](usa_undergrad_fair_division.yaml) | undergrad, USA | Fair division / apportionment | Kerrigan tasks, StratL country/store/land/furniture | Kerrigan (2018) + Lippman OER chapters |
| [usa_grade9_consistency.yaml](usa_grade9_consistency.yaml) | 9, USA (KY) | Consistency (tea growers) | StratL consistency_tea | CCSS official standards proxy; KAS PDF still blocked |

## Files

- Seven YAML cells record `prior_resources_taught_before_target`,
  `target_concept_first_appearance`, source/page references and caveats.
- `documents/` contains six local PDFs: MOE 2020 secondary mathematics, CBSE
  Physics 2025-26, NRW G9 mathematics and three Lippman *Math in Society* v2.6
  chapters (fair division, apportionment, voting theory). The textbook chapters
  are CC BY-SA 4.0; retain their source attribution and license.
- `documents/ccss_statistics_supplement.json` contains ten selected CCSS
  statistics records with standard IDs and source URLs, not Kentucky page citations.
- `corpus_chunks.json` currently contains 224 chunks: 174 original PDF page
  excerpts, 40 English translation chunks and ten CCSS records. PDF excerpts
  are capped at 2,000 characters; pages with little extractable text are skipped.
  This is not a full-text or section-complete corpus.
- `corpus_translations.json` records 40 NRW page translations made with
  `gpt-4.1-mini`. Original and translated chunks coexist with source hashes.
  Translations are model artifacts, not official English curriculum text.

## Commands

Run from the repository root. Curated lookup is offline:

```bash
# Curated cells (the expert-task grounding cells)
./.venv/bin/python scripts/lookup_curriculum_grounding.py --list
./.venv/bin/python scripts/lookup_curriculum_grounding.py --exercise kapur2012_complex_1
./.venv/bin/python scripts/lookup_curriculum_grounding.py --grade 10 --topic variance
```

Retrieval uses Azure embeddings, including a query-embedding call even when
document vectors are cached. It requires `AZURE_OPENAI_BASE_URL` and
`AZURE_OPENAI_API_KEY` in `.env.local` or the environment, and the
`text-embedding-3-small-EU` deployment:

```bash
./.venv/bin/python scripts/retrieve_prior_knowledge.py "average speed distance over time" --k 4
./.venv/bin/python scripts/retrieve_prior_knowledge.py "kinematics braking motion" --grade 11 --jurisdiction India
./.venv/bin/python scripts/retrieve_prior_knowledge.py "Hamilton method standard divisor quota" --jurisdiction USA
./.venv/bin/python scripts/retrieve_prior_knowledge.py "mean variability standard deviation" --grade 9 --jurisdiction USA
```

The retrieval CLI accepts `query`, `--k`, `--grade`, `--jurisdiction` and
`--min-score`. Subject filtering exists in the Python `retrieve_chunks` API,
used by the recommender, but there is no `--subject` retrieval CLI flag.

Recommendation inspection is offline; generation makes Azure model calls:

```bash
./.venv/bin/python scripts/run_prior_recommendations.py --list-cases
./.venv/bin/python scripts/run_prior_recommendations.py --compare-expert --model gpt41mini
./.venv/bin/python scripts/run_prior_recommendations.py \
  --case kapur_average_speed_g7_singapore --condition grounded --max-resources 5
```

Saved outputs go to timestamped files in
`experiments/results/prior_recommendations/` unless `--output` is supplied.
Use a new destination rather than overwriting an earlier condition.

To maintain the corpus:

```bash
# Offline rebuild from the registered local PDFs and existing translation artifact
./.venv/bin/python scripts/build_curriculum_corpus.py

# Model calls: create/update German-page translations, then rebuild
./.venv/bin/python scripts/translate_curriculum_pages.py --limit 1 --model gpt41mini
./.venv/bin/python scripts/build_curriculum_corpus.py
```

The builder needs `pypdf`, which is not currently declared in
`pyproject.toml`; ordinary retrieval can use the existing corpus without
rebuilding. Rebuilds overwrite `corpus_chunks.json`; translations are
incrementally saved to `corpus_translations.json`. Preserve old artifacts when
their content defines a historical experiment. The builder rejects a
translation whose hash no longer matches its source excerpt.

## Learning Commons is a separate evidence source

The [local snapshot](../learning_commons/README.md) covers three bounded
lookup targets: Kapur average speed (Grade 7, Singapore), Loibl consistency
(Grade 10, NRW) and Kerrigan fair division (US undergraduate). Its US K-12
records are concept/progression candidates, not exact local curriculum or
course-sequence matches.

Offline inspection needs neither an API key nor model calls:

```bash
./.venv/bin/python scripts/learning_commons_local.py targets
./.venv/bin/python scripts/learning_commons_local.py target kapur_average_speed_g7_singapore
./.venv/bin/python scripts/learning_commons_local.py search "mean absolute deviation"
```

The recommender and diagnostic runner's optional `--learning-commons` context
uses a separate API-response cache, not this curated offline snapshot. Selected
standard descriptions are mathematical reference context, kept separate from
assumed prior knowledge. See the
[data flow and validation limits](../../docs/pf-generation/LEARNING_COMMONS_DATA_FLOW.md).

## Corpus retrieval: what it does and its limits

Pipeline: local PDF excerpts/CCSS records -> original and translated chunks ->
cached Azure document embeddings -> cosine-similarity search -> metadata filters.
Cosine similarity measures text-vector closeness, not prerequisite validity.

Filters use a document's grade range and jurisdiction metadata, not the grade
at which each excerpt was taught. They are applied after retrieving a finite
candidate pool, so fewer than `k` results do not establish absence from the corpus.
The recommender deduplicates document/page pairs, prefers an English translation
when both variants are retrieved, and presents up to `--evidence-k` excerpts
(default six).

## Coverage audit: does the corpus cover every topic we care about?

The table records available source coverage, not independently validated
recommender accuracy or proof of each class's prior learning. The original
coverage inspection was recorded on 2026-08-24; no fresh semantic retrieval
experiment is implied by this documentation refresh.

| Topic | Grade / Jurisdiction | Curated cell | Available corpus source | Limitation |
|---|---|---|---|---|
| Average speed / rates | 7, Singapore | Paper-verified resources + MOE cell | MOE secondary math | Primary PDF reference remains missing |
| Variance / consistency | 10, NRW | NRW cell | NRW original + English translations | Curriculum boundary, not class-level observation |
| Variance / consistency | 9, Singapore | MOE cell | MOE secondary math | Exact instruction timing is school-dependent |
| Fraction equivalence | 5, NRW | NRW cell | NRW original + English translations | Mazziotti paper supplies the instruction boundary |
| Kinematics / braking | 11, India CBSE | CBSE cell | CBSE Physics 2025-26 | Current curriculum, not the 2008 study document |
| Fair division / apportionment | undergrad, USA | Course-sequence cell | Lippman OER chapters | General textbook proxy, not the original course textbook |
| Consistency (tea growers) | 9, USA (KY) | CCSS-proxy cell | Selected CCSS standards | Kentucky-specific page verification pending |

**Remaining provenance gaps:**

1. **Kerrigan's original textbook attribution:** Tannenbaum (2013) is still not downloaded,
   but the open Lippman chapters now provide a general liberal-arts mathematics source.
2. **Kentucky specificity:** the CCSS snapshot is an official standards-level proxy. The
   Kentucky KAS PDF remains blocked (403), so do not describe the CCSS text as a
   Kentucky-specific page citation.

**Retrieval-quality caveat:** earlier NRW inspections found that the top-scoring
page was not always the exact statistics/fraction section. Page-level chunks
mix topics; treat them as candidates to filter, not precise section cuts.

Known limits:
- **Translation layer:** NRW pages now have English translation chunks. Translation is
  a model-generated artifact and should be spot-checked before making thesis claims.
- Page-level chunks coarsen section boundaries (a page mixes topics); the trade-off is zero
  format assumptions per document.
- Missing source documents are skipped during corpus rebuilding, not reconstructed.
- Similarity, model-generated resource labels and model confidence do not prove
  that a skill came before the target concept or was learned by these students.

## Evidence discipline

- **Author-reported** (Kapur 2012 prior-resource list, Kerrigan 2018 course schedule) >
  **official curriculum section titles** > **curator inference**.
- Cells with `status: needs_page_reference` or `placeholder` caveats must not be cited
  as verified in the thesis.
- Known open items: MOE primary PDF link is stale (404); Kentucky KAS PDF blocks
  non-browser download (403); Tannenbaum (2013) textbook not yet obtained.

## Grounded vs ungrounded recommendations

`scripts/run_prior_recommendations.py` emits the same recommendation contract
for both conditions (`prior-method-recommendations/v1`, or `v2` with optional
Learning Commons reference context):

- **ungrounded:** the model lists resources from the target/context; provenance
  is explicitly `model`.
- **grounded:** the model maps retrieved curriculum/textbook excerpts to
  taught-skill labels with valid evidence IDs. Curated expert lists remain held out.

Both conditions deduplicate and cap resources (default five), then expand each
into a first student move and a specific shortcoming. The code allows fewer
resources or a grounded `no_evidence` result; it does not invent a verified
resource list when retrieval is empty.

This build emits `[builds_on]` recommendations only. Eedi
`[tempting_mistake]` evidence is intentionally deferred. The comparison runner
uses three topic-diverse cells (average speed, variance, fair division); expected
expert resources are shown beside each output. Lexical matches are inspection
hints, not validated quality scores. Recommendation quality and downstream PF
benefits still need separate evaluation; recovering resource labels does not
establish distinct student approaches.

See also: [KAPUR_BIELACZYC_2012_EVIDENCE.md](../../docs/pf-generation/KAPUR_BIELACZYC_2012_EVIDENCE.md)

# Learning Commons local snapshot

This folder contains a small, curated extract from the Learning Commons
Knowledge Graph v1.14.0 JSONL exports. The complete `nodes.jsonl` and
`relationships.jsonl` exports were read from an external cache, not copied into
the Git repository. The builder's default source location is
`~/Library/Caches/learning-commons/knowledge-graph/v1.14.0/`; no repository was
cloned or nested here.

## Contents and provenance

- [`target_selection.json`](./target_selection.json) records the three expert
  PF targets, selected graph-node identifiers, match limitations, source
  release, and allowed licenses.
- [`v1.14.0/nodes.jsonl`](./v1.14.0/nodes.jsonl) contains 84 graph entities;
  [`v1.14.0/relationships.jsonl`](./v1.14.0/relationships.jsonl) contains 85
  graph edges selected for those targets and their immediate context.
- [`v1.14.0/manifest.json`](./v1.14.0/manifest.json) records the source URLs,
  raw-export sizes, extracted record counts, relationship types, and licenses.

The saved manifest dates this extract to 2026-09-29. These counts describe the
local artifact, not the current size or coverage of the remote graph.

Every row in this snapshot identifies CC BY 4.0 and retains its own
`attributionStatement`. Preserve those row-level attributions when using or
publishing records; the full Knowledge Graph mixes datasets with different
licenses. The snapshot builder rejects selected rows without an explicitly
allowed license or required CC BY attribution.

Included links are `supports` (a Learning Component supports a standard),
`buildsTowards` (a directional candidate progression, not a strict
prerequisite), `relatesTo` (a non-sequential link), and `hasChild` (framework
hierarchy). The snapshot does not include the Eedi misconception graph.

## What the records say

- **Average speed:** the graph includes a Texas Grade 7 science standard that
  names average speed, plus US mathematics unit-rate standards and components.
  These are not Singapore mathematics curriculum records.
- **Consistency/spread:** US standards and components cover mean absolute
  deviation and standard deviation. There is no NRW curriculum record here.
- **Fair division:** Texas, Florida, and Alabama high-school standards cover
  fair division methods, including Divider-Chooser and Knaster. They are not
  undergraduate course records or an exact match for the Lone Divider
  standoff-resolution task.

These are candidate mappings, not evidence that a class was taught or that
students mastered a skill. A search miss applies only to this curated extract,
not to the full Learning Commons graph.

## Offline helpers

Run from the repository root. No API key, API connection or model call is needed:

```bash
./.venv/bin/python scripts/learning_commons_local.py targets
./.venv/bin/python scripts/learning_commons_local.py target kapur_average_speed_g7_singapore
./.venv/bin/python scripts/learning_commons_local.py search "mean absolute deviation"
./.venv/bin/python scripts/learning_commons_local.py show c3126032-2984-5b67-9ed5-2f2f0821e99f
```

Search is literal text matching, not semantic search. `show` accepts either a
graph `identifier` or a standard's `caseIdentifierUUID`.

## Optional remote API searches

These commands make network requests. The standalone API and guided-search
helpers require `LEARNING_COMMONS_API_KEY` exported in the environment; they
do not load dotenv files themselves. Do not paste credentials into saved output.

```bash
./.venv/bin/python scripts/learning_commons_api.py standards \
  --query "average speed as total distance over total time" --subject Mathematics --limit 10
./.venv/bin/python scripts/learning_commons_api.py standards --code "HSS-ID.A.2"
./.venv/bin/python scripts/learning_commons_api.py search-components \
  --query "measure spread around the arithmetic mean" --subject Mathematics
./.venv/bin/python scripts/learning_commons_api.py frameworks \
  --jurisdiction "Multi-State" --subject Mathematics
./.venv/bin/python scripts/learning_commons_api.py standards-in-framework FRAMEWORK_UUID \
  --grade-level 6 --subject Mathematics --statement-type Standard
./.venv/bin/python scripts/learning_commons_api.py get-standard CASE_UUID
./.venv/bin/python scripts/learning_commons_api.py components-for-standard CASE_UUID
```

Replace `FRAMEWORK_UUID` and `CASE_UUID` with identifiers returned by the API.
`standards` requires either semantic text (`--query`) or an exact code
(`--code`). The client sends no jurisdiction filter unless supplied; do not
assume an omitted filter establishes local curriculum coverage. Search returns
candidates, while `components-for-standard` retrieves linked components.
Paginated commands return one page; pass the response cursor with `--cursor`.
Framework browsing has an optional `--include-non-current` flag.

The guided helper lists the three PF targets, asks for natural-language search
phrases and optional grade/jurisdiction filters, and accepts additional tasks.
It uses the authenticated REST API and saves each run as timestamped JSON under
`experiments/results/learning_commons_queries/`. The API key is not written to
the results file. Leave jurisdiction unfiltered unless you specifically want
to restrict frameworks; non-US standards coverage is limited.

```bash
./.venv/bin/python -m scripts.learning_commons_guided_search --limit 10
```

The API client uses the installed `certifi` CA bundle by default; set
`SSL_CERT_FILE` only when using a different trusted CA bundle. Authentication,
HTTP and malformed-response failures are errors, not empty search results.
An earlier attempt from this environment returned HTTP 451; this documentation
refresh does not verify current API availability. The local snapshot remains
usable without remote access.

## Optional pipeline context

The recommendation and PF diagnostic runners accept `--learning-commons`.
One case-topic query fetches up to ten standards on a cache miss, without grade
or jurisdiction filtering; physics uses the API's Science subject category.
The existing inventory/mapping call selects up to three source labels, or none.
Code forwards the corresponding unchanged descriptions as mathematical context,
separately from assumed prior knowledge. No linked-skill or extra ranking call
is added.

Full responses, IDs, licenses and attribution are retained in immutable snapshots
under `experiments/results/learning_commons_queries/cache/` and in the saved D1
result. Short labels are used in prompts. Both runners support
`--learning-commons-cache-dir` and `--refresh-learning-commons`; refresh keeps
older snapshots. API failures, malformed responses/caches and invalid source
selections are surfaced instead of treated as empty results.

This API-response cache is separate from `data/learning_commons/v1.14.0/`.
The runners do not fall back to the curated snapshot on API failure. Unlike the
standalone helpers, context retrieval loads `.env` on a cache miss. Reusing a
diagnostic run's D1 results freezes its reference context; do not combine
`--reuse-d1-root` with a new Learning Commons retrieval or refresh.

For example, this runs the current default PF `design_brief` route with
optional references and **makes model calls**, plus an API request on a cache miss:

```bash
./.venv/bin/python scripts/run_pf_diagnostic.py \
  --cases kapur_average_speed_g7_singapore --model luna --max-workers 1 \
  --learning-commons
```

See [the flow, run command and validation limits](../../docs/pf-generation/LEARNING_COMMONS_DATA_FLOW.md).
Learning Commons remains opt-in; selection quality and downstream PF benefits
remain unvalidated. The default PF route's numerical acceptance is not proof of
reference correctness, student prior learning or productive failure.

Regenerate the snapshot from the full exports with:

```bash
./.venv/bin/python scripts/build_learning_commons_snapshot.py
```

The default source directory is the user cache path above. The builder includes
only the configured records, selected relationships, and their direct endpoint
nodes; it does not copy the full exports into the repository or download missing
exports. To use a different existing local export directory, pass `--source-dir`.
Regeneration overwrites the snapshot files and manifest at the output path; use
`--output-dir` for a separate artifact when preserving historical evidence.

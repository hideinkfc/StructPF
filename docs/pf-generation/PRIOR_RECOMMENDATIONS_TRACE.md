# Grounded vs Ungrounded Prior-Resource Generation

> **Historical trace (2026-08-24), not the current D1 protocol.** The saved run
> supplied and preserved curated expert-resource records. Current grounded D1
> retrieves curriculum/textbook excerpts only and holds those expert lists out
> of generation. See [PF_PIPELINE.md](PF_PIPELINE.md) for current behavior and
> evidence limits.

## Purpose

This is a small trace of the real run stored in
[expert_comparison_gpt41mini_final.json](../../experiments/results/prior_recommendations/expert_comparison_gpt41mini_final.json).
It shows the intermediate records rather than only the final recommendation.

- Model: `gpt-4.1-mini`
- Run timestamp in the artifact: `2026-08-24T11:29:22Z`
- Example case: Grade 7 average speed, Singapore
- Conditions: ungrounded and grounded

The JSON artifact stores the intermediate model outputs and retrieval metadata,
but not the complete rendered prompts or raw API responses. The current
[prior_recommendations.yaml](../../src/generation/prompts/prior_recommendations.yaml)
has changed since this run; it is not a frozen snapshot of the historical prompts.

## 1. Common input

Both conditions receive the same target:

```text
TARGET CONCEPT:
Average speed as total distance divided by total time; students have not yet learned the new concept.

TOPIC:
average speed and rates

GRADE:
7

JURISDICTION:
Singapore

SUBJECT:
mathematics

TEACHER-SUPPLIED RECENTLY TAUGHT SKILLS:
(none supplied in this case)
```

The expert reference held outside the generation prompt was:

```text
Speed = distance / time
Ratio and proportion
LCM and HCF
Trial and error / guess-and-check
```

The comparison list was outside the prompt, but the historical grounded arm
supplied corresponding curated resource records and preserved them in output.
This was therefore not an expert-list holdout, even though the comparison field
itself was hidden.

## 2. Condition 1: ungrounded

### 2.1 Inventory call

The model receives only the common input. It is asked to free-list 3-6
previously taught resources.

Actual resources returned in the run:

| Resource | Taught as |
|---|---|
| Calculate total distance | Add distances covered in different parts of a trip |
| Calculate total time | Add times spent in different parts of a trip |
| Division of whole by part | Divide a whole quantity by a part quantity to find a rate |
| Calculate speed as distance divided by time for single segments | Compute speed for one part of a trip |
| Add fractions with like denominators | Add fractions with the same denominator |

Every candidate had:

```json
{
  "provenance": {
    "type": "model",
    "source": "gpt-4.1-mini ungrounded inventory"
  },
  "evidence_ids": []
}
```

This means the model generated plausible labels, but the run has no curriculum
page or paper that verifies them.

### 2.2 Expansion call

The runner then makes one separate expansion call for each inventory item. It
passes one resource at a time and asks for the student's **first move** and the
specific way that resource falls short.

Actual expansion for the first resource:

```json
{
  "resource": "Calculate total distance",
  "kind": "builds_on",
  "taught_as": "Add distances covered in different parts of a trip to find the total distance",
  "student_move": "The student sums the distances from each segment of the trip to find a total distance value",
  "falls_short_because": "The task requires understanding average speed, which depends on both total distance and total time, but the student has not yet linked total time or the ratio concept to the total distance",
  "condition": "ungrounded"
}
```

The expansion is structurally valid, but the underlying resource remains
model-suggested. The final artifact contains five such expansions.

## 3. Condition 2: grounded

The grounded route has one extra evidence stage before the model generates
resource labels.

### 3.1 Evidence retrieval and merge

The historical runner combined:

1. the matching curated grounding cell; and
2. the top curriculum pages retrieved with the topic, grade, jurisdiction, and
   subject filters.

Actual retrieval metadata:

```json
{
  "status": "mapped",
  "curated_records": 4,
  "curriculum_pages": 5,
  "preserved_curated_records": 4
}
```

The four curated records were:

```text
curated:moe_sg_grade7_average_speed:0
curated:moe_sg_grade7_average_speed:1
curated:moe_sg_grade7_average_speed:2
curated:moe_sg_grade7_average_speed:3
```

The retrieved curriculum pages included MOE pages 27, 10, 26, 17, and 16.
The important point is that each page keeps its document and page provenance;
retrieval is not an unsupported model memory claim.

### 3.2 Evidence-to-resource mapping call

The model sees the common input plus:

- the four paper/curriculum records from the curated cell;
- five retrieved MOE page chunks;
- an ID for every evidence item.

It must return resource labels and cite the supplied evidence IDs. The runner
rejects a grounded item that cites an unknown ID.

Actual resources returned after mapping:

| Resource | Evidence used |
|---|---|
| Speed (distance per unit time) | `curated:moe_sg_grade7_average_speed:0` |
| Ratio and proportion | `curated:moe_sg_grade7_average_speed:1` |
| Lowest common multiple (LCM) and highest common factor (HCF) | `curated:moe_sg_grade7_average_speed:2` |
| Trial and error / guess-and-check heuristic | `curated:moe_sg_grade7_average_speed:3` |

The historical runner also preserved task-applicable curated records directly. This was
made explicit after an earlier calibration allowed the model to omit an
authoritative resource or expose a later method as prior knowledge.
Consequently, recovery of these labels is not independent retrieval accuracy.
The current runner records `curated_records_held_out` and preserves zero curated
records in generation.

### 3.3 Expansion calls

As in the ungrounded condition, the runner makes one expansion call per
resource. The expansion model sees the confirmed resource but not a competing
error list. It must describe only the first application, not a chain of
several procedures.

Actual expansion for `Speed (distance per unit time)`:

```json
{
  "resource": "Speed (distance per unit time)",
  "kind": "builds_on",
  "taught_as": "Speed (distance per unit time)",
  "student_move": "The student calculates the speed for each segment of a journey separately by dividing the distance traveled in that segment by the time taken for that segment.",
  "falls_short_because": "This approach does not address the overall average speed of the entire journey, which requires combining total distance and total time before dividing, rather than averaging individual segment speeds.",
  "provenance": {
    "type": "curriculum",
    "source": "MOE Secondary syllabus",
    "page": 17
  },
  "condition": "grounded"
}
```

Actual expansion for `Ratio and proportion`:

```json
{
  "resource": "Ratio and proportion",
  "kind": "builds_on",
  "student_move": "The student attempts to find average speed by setting up a ratio comparing distance to time for one part of the journey and then tries to apply the same ratio directly to the entire trip without combining total distance and total time.",
  "falls_short_because": "The student does not yet understand that average speed requires combining total distance and total time before forming the ratio; simply applying ratios from parts of the journey independently does not account for varying speeds or times across segments.",
  "provenance": {
    "type": "curriculum",
    "source": "MOE Secondary syllabus",
    "page": 19
  },
  "condition": "grounded"
}
```

## 4. What the two paths produced

| Stage | Ungrounded | Grounded |
|---|---|---|
| Inventory/mapping | Model free-lists resources | Retrieves evidence, then maps evidence to resources |
| Resources in this case | Total distance, total time, division, segment speed, fraction addition | Speed, ratio/proportion, LCM/HCF, trial-and-error |
| Evidence IDs | None | Curated and curriculum IDs |
| Provenance | `model` | `curriculum` for this case |
| Expansion | First move + shortcoming | First move + shortcoming |
| Output category | `[builds_on]` | `[builds_on]` |

The grounded output contained all four expected Kapur resources in this run,
after the historical runner supplied and preserved the curated records.
The ungrounded output recovered only a speed-like resource and did not recover
ratio/proportion, LCM/HCF, and trial-and-error as labels.

This is a functional comparison, not a validated accuracy score. The
`possible_lexical_matches` field in the JSON is an inspection aid; it is not an
independent human judgment.

## 5. Insight: the student-move layer is procedurally narrow

We compared the grounded moves with Kapur and Bielaczyc's nine observed
representation and solution methods (RSMs) for this task. Three generated
resource moves overlap with the observed procedural core:

- ratio reasoning;
- LCM/HCF; and
- trial and error.

However, this saved expansion trace does not recover three kinds of observed student
approach:

1. **Qualitative insights**, such as "the faster person should walk more."
2. **Diagrammatic approaches**, such as drawing the two journeys and marking
   the partition point.
3. **Algebraic attempts**, including both multiple-variable and single-variable
   formulations.

The saved speed recommendation describes separate segment-rate calculations;
its shortcoming mentions averaging segment speeds, but its `student_move` does
not explicitly execute that arithmetic mean. Neither wording establishes an
observed student method. Current expansion instead adds an **activation note**,
the objects a taught tool needs to start, and the extra demand of the target.
It does not generate a full solution or simulate student behavior.

This limitation matters for PF design: the historical grounded list can support
a resource inventory and some data-design candidates, but it does not guarantee
representation diversity. The source comparison and the nine observed RSMs
are documented in
[KAPUR_BIELACZYC_2012_EVIDENCE.md](KAPUR_BIELACZYC_2012_EVIDENCE.md).

## 6. The historical generation pattern in one diagram

```text
same target input
       |
       +--> ungrounded inventory call
       |        |
       |        +--> one expansion call per model-suggested resource
       |
       +--> grounded retrieval
                |
                +--> curated paper/curriculum records
                +--> curriculum page chunks
                         |
                         +--> evidence-to-resource mapping call
                                  |
                                  +--> one expansion call per confirmed resource
```

The recommendation category remains `builds_on`; Eedi-based
`tempting_mistake` recommendations are deferred. Optional Learning Commons
references are selected separately and do not establish prior teaching. For
the current `design_brief` -> checked data -> writing route, use
[PF_PIPELINE.md](PF_PIPELINE.md), not this historical trace as a run protocol.

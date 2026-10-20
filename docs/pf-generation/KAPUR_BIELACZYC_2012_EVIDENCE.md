# Kapur & Bielaczyc (2012): Source Evidence Notes

> Verified from the user-supplied PDF:  
> `/Users/xuouyu/Downloads/Designing for Productive Failure (1).pdf`
> This is the recorded source-verification provenance, not a portable repository
> PDF link or a fresh re-verification. Current implementation and experiment
> status are in [PF_PIPELINE.md](PF_PIPELINE.md).

## Citation

Kapur, M., & Bielaczyc, K. (2012). *Designing for Productive Failure*. **The
Journal of the Learning Sciences, 21**(1), 45-83.

DOI: [10.1080/10508406.2011.591717](https://doi.org/10.1080/10508406.2011.591717)

## Why this paper matters here

This is the source for the average-speed PF exercise in
[kapur_bielaczyc_2012.yaml](../../data/pf_exercises/kapur_bielaczyc_2012.yaml). It verifies that the exercise was
designed around resources students had already learned and that the listed
solution methods were observed and coded from student work, not invented by our
LLM pipeline.

## Prior knowledge: verified provenance

The paper states that the Grade 7 students had not received formal instruction
on the target concept of average speed. In primary school (Grades 1-6), they had
been taught:

- speed;
- ratio and proportion;
- lowest common multiple (LCM);
- highest common factor (HCF); and
- trial and error, also called guess and check.

**Location:** journal pp. 50-51 (PDF pages 7-8).

The authors report that pilot tests showed students could use these prior
resources. They then deliberately changed the problem parameters so that those
resources were insufficient. For example, the walking-speed ratio and
biking-speed ratio were made different, so a simple ratio method could not solve
the task.

### Mapping to the repository YAML

The repository field is therefore paper-grounded, but its wording is a compact
normalization rather than a verbatim quotation:

| YAML entry | Status |
|---|---|
| `speed = distance / time` | Operational form of the paper's prior resource "speed"; not quoted as a prerequisite formula in the paper |
| `ratio and proportion` | Directly supported |
| `LCM and HCF` | Directly supported |
| `trial and error heuristic` | Directly supported; the paper also says "guess and check" |

Safe thesis wording: **"The prior resources were transcribed and normalized
from Kapur and Bielaczyc's description of what Grade 7 students had learned in
Grades 1-6."** Do not call the YAML wording a verbatim author-provided
checklist.

## Student-generated methods: verified provenance

The paper analyzed PF group artifacts and discussion transcripts. Two raters
independently segmented discussions into episodes and coded the representation
and solution methods (RSMs). Interrater reliability was reported as:

- Krippendorff's alpha = .94 for episode chunking;
- Krippendorff's alpha = .97 for RSM coding.

The paper identifies nine RSM categories for the average-speed task:

1. Hady should walk more (a qualitative insight);
2. Jasmine's walking distance must equal Hady's biking distance, and vice versa;
3. diagrams;
4. LCM/HCF;
5. ratios;
6. trial and error A (brute force);
7. trial and error B (ratio-informed);
8. letter-symbolic algebra A (multiple variables);
9. letter-symbolic algebra B (single variable).

**Location:** journal pp. 58-61 (PDF pages 15-18).

These are observed, coded student RSMs. They are stronger evidence for a prior
method pool than a model's generic list, but they are still local to this
average-speed task, these Grade 7 students, and the Singapore school context.

## Design facts useful for PF generation

Drawing on earlier research and their own PF studies, the authors develop a
design theory (journal p. 48). They propose four interdependent mechanisms
(journal p. 49):

1. activation and differentiation of prior knowledge;
2. attention to critical conceptual features;
3. explanation and elaboration of those features; and
4. organization and assembly into the target concept.

These mechanisms describe learning processes, not a task-rating checklist.
The authors then state three design principles intended to embody them:

1. Create complex problem-solving contexts that challenge without frustrating,
   rely on prior mathematical resources, and admit multiple representations and
   solution methods.
2. Provide opportunities for explanation and elaboration.
3. Compare the affordances and constraints of failed or suboptimal RSMs and
   assemble canonical RSMs.

The paper explicitly maps principle 1 to mechanisms (a) and (b), principle 2
to (b) and (c), and principle 3 to (b)-(d). These mappings do not assign each
mechanism exclusively to one learning phase.

**Location:** journal pp. 48-49 (PDF pages 5-6). Presentation slide 17 quotes the
mechanism descriptions. Slide 18 uses concise paraphrases of the principles
and reproduces the authors' principle-to-mechanism mapping.

For the average-speed problem, the task parameters were deliberately calibrated
so that students could start with familiar resources but could not finish with
the simple ratio method. The canonical answer was not the only useful output:
the study treated unsuccessful but diverse RSMs as important PF evidence.

## Interpretation for our pipeline

- `prior_knowledge_required` is an appropriate reference for the **taught-resource**
  inventory (D1), provided it is described as a normalized transcription. It is
  not a Table 1 model-rating score or proof of teaching in a new classroom.
- `expected_student_rsms` is appropriate ground truth for methods students
  actually produced in this specific task.
- The nine RSMs should not be treated as a universal list for every topic. They
  are a task-specific anchor and a test of whether a generator can recover
  expert- and student-grounded methods.
- The paper supports separating **prior resources** from the later errors or
  failed applications those resources produce.
- It does not justify claiming that an LLM-generated list is complete. It gives
  an anchor for coverage and provenance, not a universal curriculum graph.

### Current task comparison (October 10)

The [final speed replay](../../experiments/results/d2b_claim_policy_replays_20261010/final_live/speed/result.json)
asks students to compare fixed journeys, including waiting, whereas Kapur's task
requires finding an unknown bike-handover point so both people arrive together.
Checked journey-rate calculations do not establish the same construction
opportunity or the nine observed methods. This is an assistant comparison of task
texts, not a human rating or student study.

The paper motivates accessible starts and comparison of partial, failed and
successful approaches; it does not require banning valid methods or making all
methods fail. In the current pipeline, prior-resource generation, calculator
acceptance and observed student methods remain different evidence sources.

## Study limitations to retain

### October 11 source-normalized simulator check

The [bounded reference protocol](../../experiments/configs/pf_kapur_reference_20261011.json)
uses an original concise paraphrase of Appendix A, not the published worksheet.
It starts at the remaining 5 km, changes names, treats rates as constant, explicitly
rules out waiting, and normalizes Jasmine's 450 m in 13--15 minutes to 30 m/min
(the 15-minute endpoint). Mira/Leon riding rates are 150/200 m/min, walking
rates 30/50 m/min. The normalization gives an exact feasible handover of 3,400 m
and 76 minutes per person. Solutions, method names and these check results are
withheld from the learner/predictor requests.

The paper was rechecked locally at Appendix A (PDF pp. 38--39) and method analysis
(PDF pp. 15--18). The nine categories contain conceptual insights, a representation
and algorithms; they must not all be counted as independent solution strategies.
This source-normalized single-response check does not reproduce group exploration,
original task ambiguity or real student frequencies. Its results and limitations
are recorded in the [canonical pipeline record](PF_PIPELINE.md#october-11-source-normalized-kapur-pathway-reference-check).

- The evidence comes from three Singapore public schools and Grade 7 students.
- RSM diversity was coded at the group level; it is not a per-student frequency
  table for every method.
- The paper reports associations between RSM diversity and later outcomes, not
  a clean causal estimate for each individual design component.
- The repository YAML is a curated transcription. The paper now verifies its
  substantive source, but the YAML should retain its normalized/transcribed
  status rather than being presented as a verbatim data table.

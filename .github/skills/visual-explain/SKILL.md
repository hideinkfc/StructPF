---
name: visual-explain
description: Explain concepts, bugs, research findings, pipeline status, brainstorming, and decisions in fluent plain English with focused supporting visuals. Use when the user asks what something means, why it failed, what works, what to do next, or requests diagrams, plots, or clearer explanations.
---

# Clear Explanations with Supporting Visuals

Help the user understand the situation before introducing the implementation.
Follow the communication and evidence rules in the
[project instructions](../../copilot-instructions.md).

## Procedure

1. Identify the user's actual questions and requested scope. Use the existing
   conversation and project records; do not ask them to repeat known context.
   When there are several questions, answer them in the requested order.
2. Give a direct answer in complete, natural sentences. Start with what happens
   in the user's situation, not internal stage names or schema fields. Explain
   the connection between ideas instead of presenting disconnected labels.
3. Choose a compact visual when it clarifies the answer or the user requests one.
   Use the shape guide below. A visual should support the explanation, not replace
   missing reasoning; a simple factual answer may need no visual.
4. Keep diagram labels short and meaningful. For workflows and data movement,
   prefer a rendered flow diagram to a wide table. Move lengthy identifiers,
   payloads, and code hooks into optional details unless they are the question.
5. Put a concrete example inside the visual when useful. Use supplied data when
   available; otherwise label it as a teaching example, not an experimental result.
   Do not repeat the whole example in a separate prose walkthrough.
6. State essential evidence and uncertainty clearly in a short caption or
   paragraph. Add a source link for repository findings. Separate a proposal
   from an implemented or tested change without repeating the same caveat in
   every sentence.
7. End with a useful conclusion or next step when needed. If a decision is
   genuinely needed, explain the trade-offs and ask one focused question.
   Do not turn every answer into a new plan.

These steps are not mandatory headings or a fixed response template. Use enough
connected prose to answer the question; do not cut an explanation into fragments
to fit a word quota.

## Learnings

The user wants a compact, scannable layout: 2–3 labeled sections (for example,
**Verdict**, **Evidence**, **Limitations**), with only 1–2 fluent sentences per
section (~120–180 words total). Avoid both long paragraphs and fragmented bullet
lists.

Keep diagram boxes to a few words, never repeat in text what the diagram already
shows, and state caveats in a single sentence inside **Limitations**.

## Choose the Shape

| User needs | Useful shape |
|---|---|
| Understand a concept | Annotated example or relationship diagram showing why it works |
| Understand a misconception or proposed change | Before/after diagram or brief comparison |
| See where a pipeline stopped | Short stage sequence with the actual stop marked |
| Choose an approach | Brief options with benefit, cost/risk, and a recommendation |
| Understand a bug | Expected versus observed behavior, then cause and evidence |
| Understand research status | Implemented / observed in runs / not yet tested |
| Compare measured outcomes over time | Plot with units, denominators, and evidence limitations |

Use diagrams for relationships or control flow, not as decoration. Avoid status
colors or progress bars without explaining what they measure.

## Worked Wording Example

This is an illustrative wording example, not an experiment result.

**Avoid:** "3 records; not a skill budget. Teaching unknown; keep candidates."

**Use:** "The API returned three skill records linked to the standard we selected.
That does not limit us to three, because other relevant standards may provide
additional skills. These records describe a possible background skill, but they
do not establish what the class was taught."

The second version stays concise while explaining the connections in complete
sentences. Keep fragments for diagram labels, not the main explanation.

## Worked Teaching Example: Conflicting Requirements

**Avoid leading with:** "The selected design violates its semantic contract."

**Lead with:** "We asked the model to make the same two fractions both equal and
unequal. No choice of numbers can satisfy that."

For example, `3/5 = 6/10 = 0.6`.

```text
One fraction pair
  +-- Requirement A: equal
  +-- Requirement B: unequal
              |
       Cannot both hold
```

The smallest fix is to choose one condition. Keeping both requires two separate
pairs, which changes the task design and must be recorded rather than silently
treated as a repaired calculation.

This explains the design problem first. Only then, if useful, identify the
responsible pipeline stage or field.

## Evidence Discipline for This Thesis

- Check the current [pipeline record](../../../docs/pf-generation/PF_PIPELINE.md)
  and relevant artifacts before reporting status. Do not store changing test
  counts or experiment outcomes in this skill.
- Distinguish **observed** (what the artifact or run shows), **suspected** (a
  possible explanation), and **verified** (confirmed by a specific check).
  Use only the labels needed for the answer.
- Report completion separately from quality. State the number of tasks attempted
  and produced; do not score only successful outputs and hide blocked cases.
- Distinguish an automatic run, a retry, a manually redesigned continuation, and
  a fixed-input test. Passing software tests is not evidence of productive
  failure, student approach diversity, or learning.
- An LLM review is a model judgment, not a human rating. Anticipated student
  approaches are hypotheses, not observed behavior.
- A failed gate is not automatically a correct rejection. Explain whether the
  evidence points to the task, its mathematical representation, or the checker.
- Keep mock data visibly marked as illustrative, including inside exported
  figures. A sidecar file alone does not protect a standalone figure's meaning.

## Final Check

- Can the opening sentence be understood without pipeline jargon?
- Does the prose sound like natural speech, with complete sentences and clear
  connections between ideas?
- Have all requested questions been answered in the user's order and scope?
- Does the example actually demonstrate the claim?
- If a visual is used, does it make the answer easier to understand?
- Are labels short, with technical detail kept separate when it would clutter
  the picture?
- Are the evidence, uncertainty, and practical consequence clear?
- Does the ending give a useful conclusion without forcing an unnecessary plan?

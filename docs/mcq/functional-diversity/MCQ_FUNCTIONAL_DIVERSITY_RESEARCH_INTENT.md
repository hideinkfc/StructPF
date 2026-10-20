# Functional Diversity: Research Intent and Direction

> Companion to [MCQ_FUNCTIONAL_DIVERSITY_MEASUREMENT.md](MCQ_FUNCTIONAL_DIVERSITY_MEASUREMENT.md), which holds
> the protocol and run results. This file holds the *why*: the research question, the decisions that
> are settled, the ideas that were considered and rejected, and the reason each rejection was made.
> Read this first when resuming work on functional diversity.

> Current status: functional diversity is inactive in the current MCQ evaluation. Historical
> rule-level calibrations (Tests 1--5) and a 30-call non-independent Test 6 demonstration exist.
> The intended misconception-level instrument with an independently frozen profile pool has not
> been validated. Only the archived Test 6 runner enforces `--enable-functional-diversity`; other
> calibration scripts can still make model calls without that flag.

## 1. What this work is

**Research question:** can LLM-simulated students serve as a valid instrument for measuring whether a
set of MCQ distractors is *behaviorally* diverse?

The contribution is the **instrument**, not a verdict on any particular distractor set. A verdict on
the pilot distractors is a demonstration of the instrument, and it inherits its meaning from the
instrument's validity.

**Definition of diversity used here:** a distractor set is diverse when *different kinds of struggling
students pick different distractors*. "Kind of student" must be something a student can plausibly
**be** (a held belief, a missing skill), not a procedure the experimenter dictates.

**Why this definition and not the alternatives:**

| Level | Definition | Status |
|---|---|---|
| Surface | distractor texts are dissimilar (embedding cosine) | Rejected as the primary construct: similar-looking time answers can arise from different errors; no particular cosine value is asserted here |
| Pathway | a judge compares supplied faulty steps and reasoning, with labels/rationales as context | Implemented in the active MCQ evaluator, but insufficient for a behavioral claim |
| Behavioral | distinct student states reach distinct options | **Proposed target construct**, not yet validated |

## 2. Literature grounding

- **PF side.** Kapur defines diversity as RSMs (representations and solution methods) that *learners
  produce*. It is behavioral and measured over people.
  Rahimi's rubric splits it into Multiple Representations and Open-Endedness.
- **MCQ side.** Feng et al. (NAACL 2024 Findings) measure Proportional Match against human
  distractors, which is reference alignment, not diversity. They have no misconception labels, so
  they cannot measure error-level distinctness.
- **Consequence.** This project's proposed behavioral-diversity construct is
  assembled from components (Tatsuoka Q-matrix validation, Brown & Burton buggy procedures, Vinh et
  al. chance-corrected MI, Lu & Wang 2024 KC-based simulated student profiles) and the composite is
  ours. Do not present it as an inherited validated method or claim an exhaustive literature
  novelty search. Bibliographic starting points are in
  [thesis/references.bib](../../../thesis/references.bib) and
  [phase1_mcq_design.md](../../../notebooks/phase1_mcq_design.md); exact paper-level claims need
  source verification before thesis use. The October 11
  [LLM-student review](../../pf-generation/PF_PIPELINE.md#october-11-starting-research-on-llm-student-attempts)
  verified Lu and Wang's actual paper: Xinyi Lu and Xu Wang, *Generative Students:
  Using LLM-Simulated Student Profiles to Support Question Item Evaluation*,
  Learning @ Scale 2024. It evaluates usability MCQs, not mathematical PF reasoning.

**Logical chain from profiles to a diversity claim:**

1. PF's criterion is behavioral: a good exercise elicits multiple distinct approaches.
2. At generation time there are no students, so the criterion cannot be applied directly.
3. Simulated students stand in for real ones; each profile is one documented student state.
4. Profiles must be built **independently** of the distractors. This is what makes "diverse" refer to
   an external error space instead of the generator's own story.
5. If k independently specified student states reach k different options, the distractor set
   functionally separates student kinds.

## 3. Settled decisions

| Decision | Choice | Reason |
|---|---|---|
| Profile specification | **Misconception-level** (belief / missing skill; wrong behavior must emerge) | If the profile carries an explicit procedure, the pick is arithmetic we authored and the definition collapses to "we computed different answers" |
| Rule-level profiles | Retained as a **calibration arm** with explicitly instructed errors | Test 1 followed assigned rules in 170/180 GPT-4.1 calls (94.4%); later option-setting checks differ. The misconception-level comparison has not run |
| Intended readout per attempt | **Reasoning trace** + intermediate answer + option pick | Proposed for the independent experiment; archived procedural outputs primarily contain intermediate answers and choices, not a mandatory full trace |
| Primary claim | **Instrument validity** | "Different students pick different distractors" only means something if the simulated students deserve the word *students* |
| External anchor | **Proposed**, per-profile fidelity checked against suitable student evidence | Scraped per-option rates are aggregate selection shares, not labeled per-profile conditional responses; the stronger anchor is not established |
| Scoring | Coverage/verdict **counts** should lead; any NMI is secondary | NMI, normalized mutual information, measures association between profile identity and option choice; it can be high without any generated distractor being selected |

### Profile schema

The intended independent profile is a **mastery map over the topic's skill list**: which prerequisite skills the student has,
which they lack, and at most one wrong belief. One varied absence per profile, so an observed behavior
is attributable to one cause.

`kc_mastery` in [student_profiles.py](../../../src/simulation/student_profiles.py) supplies an existing
mastery-map representation. The current `active_errors` and `to_prompt_block()` explicitly inject
`ErrorBehavior.rule` for unmastered skills, however: this is rule-level behavior, not the proposed
belief-only profile. Lu & Wang is a bibliographic starting point, not proof that this local
representation or simulator has been validated.

Proposed local choices include phrasing the missing concept as a **negative constraint** in the prompt
(to fight correctness pull), the one-varied-absence identifiability rule, and reading *which* present
skill gets recruited as the diversity readout.

### Sources for profile content, ranked

| Source | Gives | Trust |
|---|---|---|
| [data/eedi_scraped/_skill_bank.json](../../../data/eedi_scraped/_skill_bank.json) (88 skill records) | Scraped teacher explanations and recorded per-option selection percentages | Source-grounded, but scraping, image dependence and skill assignment need review |
| Eedi misconception mapping + `same_error_in_questions` siblings | Which errors recur across questions of the same skill | High |
| Bug-catalog papers (Brown & Burton, VanLehn) | Precedent and structure for buggy-procedure wording | High, older domains |
| LLM generation | Phrasing a terse label in student voice | Drafting aid only |

Rule for the proposed independent experiment: the LLM may **phrase** a profile, never **invent**
the error. `ErrorBehavior.source` (`"eedi"` vs `"llm"`) records provenance, but the current profile
module supports both sources; merely recording a source does not enforce this research restriction.

Pool size: 6-9 profiles for 3 distractors. Do not force one-to-one profile-to-distractor ownership.
Freeze the pool before seeing the generated distractors.

## 4. Rejected ideas, and why

Recorded so they are not re-proposed.

| Idea | Verdict | Reason |
|---|---|---|
| Match the simulated option distribution to the real student distribution | **Dropped as the primary diversity test** | Aggregate shares cannot identify which student states produced each choice. Tests 3 and 4 check controls and prescribed-error recovery, not real-student fidelity |
| Replace simulation with deterministic rule execution | **Rejected for this chapter** | Valid only against *rule-level* profiles, where the answer is arithmetic we authored. At misconception level the behavior is genuinely stochastic and non-derivable. Deterministic execution remains useful as a cheap refinement-feedback side channel, not as the instrument |
| Build profiles from the distractors' own `error_rationale` | **Never** | Every set becomes diverse by construction |
| Inject the error procedure into the student prompt for the real experiment | **No** | Obedience is not behavior. Error rules move to the *scoring* side, as classifiers that name an observed attempt |
| Four-field profile (toolkit / gap / belief / disposition) | **Collapsed** | Toolkit and gap are the same skill list with different role labels. `disposition` has no literature grounding and was not shown to move behavior |
| Embedding-cosine diversity | **Replaced** | Topic-level clustering inflates similarity for mathematically distinct errors |

## 5. Known failure modes of the measurement

1. **NMI can be high with zero coverage.** In the saved pilot, Q1437 scored NMI 0.918 while all three
   generated distractors were picked by nobody. The split was between the *correct* option and
   `OTHER`. Proposed fix: compute any NMI over **distractor columns only** (exclude the correct option and
   `OTHER`), and condition rows on rule-following. The archived Test 6 scorer still includes all
   selected categories; this restriction has not been implemented there.
2. **`OTHER` is a coverage signal, not student behavior.** It means a documented error produces an
   answer the option set does not offer. Report separately.
3. **Uncovered is `unknown`, never "low diversity."** No picks means no evidence.
4. **Correctness pull.** Visible options drag the simulator back to the correct answer. Measured:
   94.4% rule-following without options, 68.3% intended-option recovery under the original prompt,
   and 82.8% answer-rule following / 81.1% intended-option recovery under the revised GPT-4.1
   prompt. These are different readouts. Lower belief-only controllability is a hypothesis,
   not a measured result.
5. **Circularity.** Any profile that saw the distractors is disqualified.
6. **Comparability.** Column distances only mean something if every distractor faced the same profile
   pool.

## 6. Where the work stands

**Saved historical rule-level calibration (GPT-4.1 and GPT-4.1-mini where stated):**

| Test | Result |
|---|---|
| 1 rule-following, no options | 170/180 = 94.4% (GPT-4.1) |
| 2 with options, original prompt | 123/180 = 68.3%, 26.1 pp drop, failed gate |
| 2 revised procedural prompt | GPT-4.1 146/180 = 81.1%; mini 170/180 = 94.4% |
| 3 controls | expert 60/60 = 100% both models; no dominant floor option |
| 4 known-good | GPT-4.1 82.4%, NMI 0.958; mini 95.7%, NMI 0.981 |
| 5 negative controls | GPT-4.1 same-error NMI 0.011; nonsense unavailable and stored `negative_control_pass=false`. Mini same-error 0.034; nonsense 0.027 |
| worked-example ablation | no improvement |

The values are model-response calibration, not observed student behavior. The GPT-4.1-mini full
12-question no-options baseline is absent; its visible-options result is not a matched model comparison.

**Saved 30-call pilot on generated distractors** (rule-level profiles, not independent, so a
procedure demonstration only):
[functional_diversity_test6_saved_pilot_gpt41.json](../../../experiments/results/functional_diversity_test6_saved_pilot_gpt41.json).
One of six generated options was selected and five were uncovered in the saved matrices. This is
not a validated "discriminating" verdict. `selected_option_matches_answer` was 0/30. Source inspection
shows this field compares selected-option text with the profile's predeclared expected answers,
**not** with the actual simulated answer; `selected_option_matches_expected` also refers to the old
Eedi target letter after options have been replaced. Thus those inherited flags do not establish
answer-to-generated-option consistency. Review/fix the readout before quoting functional verdicts.

**Not started:**

- Misconception-level profile rewrite and its controllability pilot
- Independent frozen 6-9 profile pool built from `same_error_in_questions` siblings
- Per-profile fidelity check with suitable student-state evidence (aggregate Eedi shares alone are insufficient)
- Jensen-Shannon column distance + split-half noise threshold + permutation null
- GPT-4.1-mini full 12-question Test 1 baseline (`scripts/run_test1_rule_following.py` hardcodes
  `models["gpt41"]`; needs a `--model` selector and a distinct `--output`)

## 7. Proposed Next Step If This Direction Is Reactivated

**Gate A, misconception-level controllability, ~45 calls.** Rewrite 3 existing Test 1 profiles at
misconception level (belief only, no procedure, e.g. *"you believe operations are always done left to
right"* instead of *"compute left to right"*), same questions, 5 repeats, full reasoning traces.
Compare wrong-answer production with the 94.4% rule-level calibration on matched questions and
readouts; that calibration is not an empirical upper bound.

Both outcomes are reportable. If misconception-level profiles cannot hold their state, that is a
finding about the limits of LLM student simulation, not a reason to fall back to injected rules and
call the result behavioral.

Then, in order: independent frozen pool -> suitable student-fidelity anchor -> corrected full Test 6 with
verdict counts read against the Test 4 and Test 5 reference points.

## 8. Working conventions

- Interpreter `./.venv/bin/python`; `ruff check` and `py_compile` before any live API call
- Azure config via `scripts/run_azure_mcq_plausibility.load_azure_config()`; `.env.local` at repo root
- Common procedural parameters are `temperature=0.7`, `max_tokens=256`, `timeout=60.0`;
  saved Tests 3--5 used 20 workers and Test 3 used 128 tokens. Use each artifact's parameters,
  not a single assumed configuration for every historical run.
- Read results from the saved JSON artifact, not terminal scrollback
- Never overwrite historical result files; use a distinct `--output`
- Pre-register go/stop thresholds before each test
- Report `unknown`, `uncovered`, and `not measurable` honestly; never silently convert them to zero

Offline checks from the repository root:

```bash
./.venv/bin/python scripts/run_test1_rule_following.py --help
./.venv/bin/python scripts/run_test6_saved_distractors_pilot.py --help
```

The Test 1 script hardcodes GPT-4.1 and has no `--model` selector. Test 6 defaults to GPT-4.1-mini
and a mini-named output, while the saved artifact above is GPT-4.1. Its
`--enable-functional-diversity` flag is a guard against accidental reactivation, not evidence of
validation. Do not run the calibration scripts as an offline inspection step.

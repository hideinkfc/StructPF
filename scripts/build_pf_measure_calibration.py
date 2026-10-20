"""Freeze a local, no-model PF-measure development and reserved-transfer pack.

Run ``python -m scripts.build_pf_measure_calibration`` once, then use ``--verify``.
References are assistant-provisional diagnostic hypotheses, never human ratings.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("experiments/results/pf_measure_campaign_20261014/calibration_pack.json")
EXPERT = "data/pf_exercises/puech_macina_2025_stratl_full.yaml"
KAPUR = "data/pf_exercises/kapur_bielaczyc_2012.yaml"
KERRIGAN = "data/pf_exercises/kerrigan_weber_chinn_2021.yaml"
SETTING = "experiments/configs/pf_rahimi_multi_theme_setting.json"
MAIN = "experiments/results/pf_rahimi_multi_theme_20261013/main_30"
GROUNDING = "experiments/results/pf_grounding_study_20261013"
SETTING_SHA256 = "1c30203dd9e127992ccd24930d574a1ee5402f795605f0436095063b01a4f4a8"
METRIC_VALUES = {
    "target_alignment": ["yes", "partly", "no", "unclear"],
    "mathematical_validity": ["yes", "no", "unclear", "not_assessed"],
    "prior_knowledge_accessibility": ["yes", "no", "unclear"],
    "familiar_approach_limits": ["yes", "no", "unclear", "not_assessed"],
    "room_for_invention": ["yes", "partly", "no", "unclear"],
}
ATTEMPT_STATUSES = [
    "not_supported",
    "start_unresolved",
    "target_limit",
    "meets_demands",
    "unrelated_shortfall",
    "unresolved",
]
INPUT_KEYS = ("student_task", "learning_target", "learner_context")


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def file_digest(path: str | Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def read_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def exercise(path: str, identifier: str) -> dict[str, Any]:
    data = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    return next(item for item in data["exercises"] if item["id"] == identifier)


def source(path: str, selector: str, fields: list[str]) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": file_digest(path),
        "selector": selector,
        "student_fields": fields,
    }


def new_case(
    identifier: str,
    family: str,
    split: str,
    text: str,
    target: str | None,
    priors: list[Any],
    sources: list[dict[str, Any]],
    prior_provenance: dict[str, Any],
    target_provenance: str,
    **extra: Any,
) -> dict[str, Any]:
    context = {"assumed_prior_knowledge": copy.deepcopy(priors)}
    return {
        "id": identifier,
        "case_id": identifier,
        "family": family,
        "split": split,
        "student_task": text,
        "learning_target": target,
        "learner_context": context,
        "solver_input": {
            "student_task": text,
            "learner_context": copy.deepcopy(context),
        },
        "sources": sources,
        "prerequisite_provenance": {
            **prior_provenance,
            "independent_of_desired_errors": True,
        },
        "target_provenance": target_provenance,
        **extra,
    }


def expert_case(
    identifier: str,
    source_id: str,
    family: str,
    split: str,
    target: str,
    priors: list[str] | None = None,
    prior_source: tuple[str, str] | None = None,
    path: str = EXPERT,
) -> dict[str, Any]:
    item = exercise(path, source_id)
    sources = [source(path, f"exercises[id={source_id}]", ["problem"])]
    if prior_source is not None:
        prior_path, prior_id = prior_source
        priors = exercise(prior_path, prior_id)["prior_knowledge_required"]
        sources.append(
            source(
                prior_path,
                f"exercises[id={prior_id}].prior_knowledge_required",
                [],
            )
        )
        provenance = {
            "kind": "existing_curated_expert_history",
            "path": prior_path,
            "exercise_id": prior_id,
            "note": (
                "Existing repository curation, not new verification against the "
                "original paper. This is history evidence, not desired errors."
            ),
        }
    else:
        provenance = {
            "kind": "assistant_specified_history",
            "note": (
                "Import provides no prerequisites for this item. The list is an "
                "explicit assistant-specified educational-history assumption, "
                "not an expert-verified learner profile or observed student knowledge."
            ),
        }
    return new_case(
        identifier,
        family,
        split,
        item["problem"],
        target,
        priors or [],
        sources,
        provenance,
        "Assistant-specified operational target from source topic/demand; not a source rating.",
        origin="expert_task",
        source_exercise_id=source_id,
        source_phase=item.get("phase"),
        expert_exposure=(
            "Previously read expert example, reserved from new prompt tuning. "
            "Not an untouched-topic validation case."
        ),
        source_solution_policy="Only problem is extracted; solution fields are excluded.",
    )


def main_case(identifier: str) -> dict[str, Any]:
    config = read_json(SETTING)
    manifest_path = f"{MAIN}/manifest.json"
    manifest = read_json(manifest_path)
    if file_digest(SETTING) != SETTING_SHA256:
        raise ValueError("The original multi-theme setting hash changed")
    if manifest["config_sha256"] != SETTING_SHA256:
        raise ValueError("The setting does not match the saved run manifest")
    path = f"{MAIN}/attempts/{identifier}.json"
    record = read_json(path)
    cell = next(x for x in config["cells"] if x["cell_id"] == record["cell_id"])
    task = record["task"]
    if record["status"] != "ready":
        raise ValueError(f"No usable task: {identifier}")
    return new_case(
        identifier,
        f"main30_{record['cell_id']}",
        "development",
        "\n\n".join(task[key] for key in ("title", "body", "question")),
        cell["case"]["target_concept"],
        cell["learner_context"]["assumed_prior_knowledge"],
        [
            source(path, "$.task", ["title", "body", "question"]),
            source(SETTING, f"$.cells[cell_id={record['cell_id']}]", []),
            source(manifest_path, "$.config_sha256", []),
        ],
        {
            "kind": "saved_generation_history",
            "path": SETTING,
            "note": (
                "Exact assumed_prior_knowledge from the original setting; its "
                "bytes match config_sha256 in the frozen main_30 manifest."
            ),
        },
        "Original setting $.cells[].case.target_concept, verified by saved config hash.",
        origin="saved_generated_task",
        source_exercise_id=identifier,
        source_solution_policy="Only task title/body/question; no raw response or ratings.",
    )


def grounding_case(name: str) -> dict[str, Any]:
    base = f"{GROUNDING}/attempts/main/{name}/r01/A"
    result_path = f"{base}/result.json"
    input_path = f"{base}/input.json"
    context_path = f"{GROUNDING}/inputs/{name}/context_A.json"
    result = read_json(result_path)
    saved_input = read_json(input_path)
    context = read_json(context_path)["learner_context"]
    task = result["stages"]["D2_D3"]["task"]
    return new_case(
        f"grounding_{name}_r01_A",
        f"grounding_{name}",
        "transfer",
        "\n\n".join(task[key] for key in ("title", "body", "question")),
        saved_input["target_concept"],
        context["recently_taught"],
        [
            source(result_path, "$.stages.D2_D3.task", ["title", "body", "question"]),
            source(input_path, "$.target_concept", []),
            source(context_path, "$.learner_context.recently_taught", []),
        ],
        {
            "kind": "saved_generation_history",
            "path": context_path,
            "note": (
                "Exact saved recently_taught list translated without additions "
                "to assumed_prior_knowledge. target_not_taught, reference inventory "
                "and internal D1/solutions are excluded from solver inputs."
            ),
        },
        "Original per-attempt input.json $.target_concept.",
        origin="saved_generated_task",
        source_exercise_id=name,
        source_solution_policy="Only student-facing task fields; no internal examples.",
    )


ARITHMETIC = [
    "Addition, subtraction, multiplication and division of whole numbers and decimals",
    "Reading tables and comparing numerical quantities",
]
CONSISTENCY_PRIORS = ARITHMETIC + [
    "Arithmetic mean and range of a numerical data set",
]
RATE_PRIORS = ARITHMETIC + [
    "Speed equals distance divided by time",
    "Converting minutes and hours and comparing simple ratios",
]
FAIR_PRIORS = ARITHMETIC + [
    "Fractions of a total and an equal fair share",
]
PHYSICS_PRIORS = ARITHMETIC + [
    "Speed as distance divided by time and conversion between m/s and km/h",
    "Acceleration as change in speed per second",
    "Reading a distance-time sketch; no constant-acceleration distance law yet",
]


def freeze_inputs() -> dict[str, list[dict[str, Any]]]:
    """Construct every input before attaching any reference interpretation."""
    development = [
        expert_case(
            "expert_bicycle",
            "puech2025_stratl_biking",
            "expert_bicycle",
            "development",
            "Coordinate segment travel times for simultaneous arrival.",
            prior_source=(KAPUR, "kapur2012_complex_1"),
        ),
        expert_case(
            "expert_consistency",
            "puech2025_stratl_consistency",
            "expert_consistency",
            "development",
            "Construct and justify a numerical measure of variation using all data.",
            CONSISTENCY_PRIORS,
        ),
        expert_case(
            "expert_country",
            "puech2025_stratl_country",
            "expert_country",
            "development",
            "Construct a population-sensitive integer apportionment with a fixed seat total.",
            ARITHMETIC + ["Fractions, proportions and rounding decimal quantities"],
        ),
        expert_case(
            "expert_land",
            "puech2025_stratl_land_sharing",
            "expert_land",
            "development",
            "Construct a fair land allocation, resolving conflicting acceptable pieces.",
            prior_source=(KERRIGAN, "kerrigan2021_invention_1"),
        ),
        expert_case(
            "expert_time_sharing",
            "puech2025_stratl_fair_distrubution_time",
            "expert_time_sharing",
            "development",
            "Construct a contiguous two-person fair division using personal valuations.",
            FAIR_PRIORS,
        ),
        expert_case(
            "expert_ship",
            "kapur2012_well_structured_1",
            "expert_ship_practice",
            "development",
            "Calculate average speed for a whole journey from total distance and total time.",
            RATE_PRIORS,
            path=KAPUR,
        ),
        expert_case(
            "expert_walkcycle",
            "kapur2012_well_structured_2",
            "expert_walkcycle_practice",
            "development",
            "Calculate average speed for a whole journey from total distance and total time.",
            RATE_PRIORS,
            path=KAPUR,
        ),
    ]
    development.extend(
        main_case(identifier)
        for identifier in (
            "music_compare_distributions__gpt41__016",
            "garden_composite_area__gpt5mini__028",
            "garden_composite_area__gpt41__019",
            "sports_basketball_ratio__gpt41__021",
            "sports_basketball_ratio__gpt5mini__002",
        )
    )
    consistency = development[1]
    prescribed = copy.deepcopy(consistency)
    prescribed.update(
        id="synthetic_consistency_formula",
        case_id="synthetic_consistency_formula",
        family="expert_consistency",
        origin="synthetic_contrast",
        synthetic=True,
        synthetic_note=(
            "Clearly synthetic edit of development consistency; formula and route "
            "are deliberately supplied. Not an expert or generated task."
        ),
    )
    prescribed["student_task"] = (
        consistency["student_task"]
        + "\n\nSYNTHETIC CONTRAST: For this version use exactly this rule: compute "
        "each player's mean, subtract that mean from every score, square each "
        "difference, add the squares and divide by five. Choose the smallest "
        "result. Do not design alternative measures; only apply this supplied rule."
    )
    prescribed["solver_input"]["student_task"] = prescribed["student_task"]
    development.append(prescribed)
    transfer = [
        expert_case(
            "expert_hummingbird",
            "puech2025_stratl_hummingbird",
            "expert_hummingbird",
            "transfer",
            "Compare effective journey rates accounting for flight and rest.",
            RATE_PRIORS,
        ),
        expert_case(
            "expert_tea",
            "puech2025_stratl_consistency_tea",
            "expert_tea",
            "transfer",
            "Construct and justify a consistency measure from observed tea measurements.",
            CONSISTENCY_PRIORS,
        ),
        expert_case(
            "expert_goals",
            "puech2025_stratl_fraction_comparison",
            "expert_goals",
            "transfer",
            "Compare fractions with different denominators using a common whole.",
            ARITHMETIC + ["Equal sharing, fractions as parts of a whole and drawing fraction bars"],
        ),
        expert_case(
            "expert_pizza",
            "puech2025_stratl_fraction_comparison_2",
            "expert_pizza",
            "transfer",
            "Compare equal shares represented by equivalent fractions.",
            ARITHMETIC + ["Equal sharing and fractions as division; drawing equal-size wholes"],
        ),
        expert_case(
            "expert_furniture",
            "puech2025_stratl_fair_distribution",
            "expert_furniture",
            "transfer",
            "Construct a fair allocation of indivisible goods using cash compensation.",
            prior_source=(KERRIGAN, "kerrigan2021_invention_2"),
        ),
        expert_case(
            "expert_braking_collision",
            "puech2025_stratl_lawer",
            "expert_braking_collision",
            "transfer",
            "Infer pre-braking speeds from distances and deceleration under explicit physical "
            "assumptions.",
            PHYSICS_PRIORS,
        ),
        expert_case(
            "expert_braking_lawyer",
            "puech2025_stratl_lawer_2",
            "expert_braking_lawyer",
            "transfer",
            "Infer a braking speed range from skid distance and friction under explicit "
            "physical assumptions.",
            PHYSICS_PRIORS
            + ["Frictional deceleration magnitude is coefficient of friction times g"],
        ),
        grounding_case("scientific_scale_comparison"),
        grounding_case("signed_product_ledger"),
    ]
    controls = []
    specifications = [
        (
            "control_partial_alignment",
            "For the numbers 3, 5 and 10, calculate only their arithmetic mean.",
            "Calculate and interpret both the mean and median of a data set.",
            CONSISTENCY_PRIORS,
        ),
        (
            "control_off_target",
            "A rectangle is 5 cm by 3 cm. Use area = length times width to find its area.",
            "Compare fractions using a common denominator.",
            ARITHMETIC,
        ),
        (
            "control_inaccessible",
            "Apply the supplied rule d(x^n)/dx = n*x^(n-1) to find the derivative of x^3 at x=2.",
            "Compute a derivative using the power rule.",
            [
                "Recognize written numerals zero through nine",
                "No arithmetic operations, symbolic substitution, variables or powers have "
                "been learned",
            ],
        ),
        (
            "control_mathematical_contradiction",
            "A rectangle has length exactly 3 cm, width exactly 2 cm and area exactly 5 square cm. "
            "Use area = length times width and exhibit a rectangle satisfying all three exact "
            "conditions.",
            "Relate the area of a rectangle to its side lengths.",
            ARITHMETIC,
        ),
        (
            "control_unproved_universal_claim",
            "Prove that every even integer greater than 2 is the sum of two primes. "
            "Checking examples is not a proof of the universal claim.",
            "Construct a proof or counterexample for a universally quantified statement about "
            "prime sums.",
            ARITHMETIC
            + ["Definition of prime and even integers; checking an integer for primality"],
        ),
        (
            "control_missing_task_context",
            "Use the diagram on the previous page to invent and justify a rule for its marked "
            "lengths.",
            None,
            ARITHMETIC,
        ),
        (
            "control_missing_history",
            "Use the supplied rule total = 6 + 7 to calculate the total.",
            "Add two whole numbers.",
            [],
        ),
    ]
    for identifier, text, target, priors in specifications:
        controls.append(
            new_case(
                identifier,
                identifier,
                "control",
                text,
                target,
                priors,
                [],
                {
                    "kind": "assistant_specified_history",
                    "note": (
                        "Clearly synthetic instrument control, not an observed learner history."
                    ),
                },
                "Assistant-specified synthetic control; absence is deliberate where null.",
                origin="synthetic_control",
                synthetic=True,
                source_solution_policy=(
                    "Self-contained synthetic statement; no source solution exists."
                ),
            )
        )
    return {"development": development, "transfer": transfer, "controls": controls}


def reference(
    value: str,
    evidence: str,
    confidence: str = "high",
    alternatives: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "value": value,
        "acceptable_values": [value, *alternatives],
        "evidence": evidence,
        "label_confidence": confidence,
        "provenance": "assistant_provisional",
        "human_reviewed": False,
        "validated_gold": False,
    }


def annotations() -> dict[str, dict[str, Any]]:
    """Prewritten hypotheses; none is inferred from new model outputs or ratings."""
    result: dict[str, dict[str, Any]] = {}

    def add(
        identifier: str,
        values: tuple[str, str, str, str, str],
        evidence: tuple[str, str, str, str, str],
        approaches: list[tuple[str, str]],
        *,
        confidence: str = "medium",
        alternatives: dict[str, tuple[str, ...]] | None = None,
        limitations: tuple[str, ...] = (),
    ) -> None:
        alternatives = alternatives or {}
        result[identifier] = {
            "references": {
                metric: reference(value, reason, confidence, alternatives.get(metric, ()))
                for metric, value, reason in zip(METRIC_VALUES, values, evidence)
            },
            "expected_familiar_approaches": [
                {"idea": idea, "checkable_action": action} for idea, action in approaches
            ],
            "reference_scope": (
                "Task-text reading and explicitly described possible approaches. "
                "Attempt-based labels are conditional on these witnesses, not "
                "predictions of a solver, student frequencies or actual student work."
            ),
            "limitations": list(limitations),
        }

    add(
        "expert_bicycle",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "'arrive ... at the same time' requires coordinating both segment times.",
            "Remaining route is 8.75-3.75=5 km; equality x/.15+(5-x)/.03=x/.05+(5-x)/.2 gives "
            "x=17/5 km and both times76min.",
            "Listed distance/time and unit conversions give 5 km remaining before any new idea.",
            "Using only the biking-speed ratio 4:3 gives 20/7 km; times are 1900/21 and 475/7 "
            "min, not equal. Trial/refinement can still succeed.",
            "A ride-then-walk plan is supplied, but the central handover distance and "
            "combined-time construction remain open.",
        ),
        [
            ("Convert distances and rates", "75*7/60=8.75 km; .15*25=3.75 km; 5 km remain."),
            (
                "Biking-ratio partition",
                "Test x=20/7 km by calculating each person's full journey time.",
            ),
            (
                "Trial and refinement",
                "Tabulate both times for candidate handover distances and refine toward17/5 km.",
            ),
            (
                "Distance-time sketch",
                "Mark shared handover, opposing walking/biking segments and simultaneous arrival.",
            ),
        ],
        limitations=(
            "Approximate walking speeds are modeled as constant; the text says approximately.",
        ),
    )
    add(
        "expert_consistency",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "'Design as many different measures' and 'all data points' directly require "
            "constructing a variation measure.",
            "Means are 14,14,15; squared-deviation totals 16,10,44. Many justified consistency "
            "measures are feasible.",
            "The listed arithmetic mean/range history supports computing means or plotting the "
            "five observations.",
            "Range 5,4,8 ignores intermediate observations despite the all-data demand; signed "
            "deviations all sum to zero. Absolute deviations retain spread.",
            "The measure, reference point, treatment of differences and aggregation are not "
            "prescribed.",
        ),
        [
            ("Mean comparison", "Compute 14,14,15 and explain that level is not variation."),
            ("Range", "Compute 5,4,8 and check the explicit requirement to use all observations."),
            (
                "Signed deviations",
                "Compute deviations about each mean and show their sums all vanish.",
            ),
            (
                "Construct absolute differences",
                "MAD values are 8/5,6/5,12/5; this is a possible construction, not assumed taught.",
            ),
        ],
        limitations=(
            "Year labels conflict (2019-2023 versus 2007-2011); no numerical consistency "
            "comparison depends on that label.",
            "The curated assertion that means and ranges all match is false for this table and "
            "is not a reference.",
        ),
    )
    add(
        "expert_country",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "'250 seats' and 'fair representation' require a population-sensitive integer "
            "allocation.",
            "Population totals 12,500,000; quotas 32.92,138.72,3.08,41.82,13.70,19.76. "
            "Allocation 33,139,3,42,13,20 totals 250.",
            "Proportion and division give 50,000 people per seat and numerical quotas.",
            "Nearest-integer rounding gives 33+139+3+42+14+20=251 seats. Reconciling integer "
            "seats with a fixed total addresses the target.",
            "No apportionment rule is given; fairness and rounding choices require "
            "justification, not a unique canonical method.",
        ),
        [
            (
                "Quota and ordinary rounding",
                "Calculate quota decimals and verify nearest-integer total 251.",
            ),
            (
                "Equal seats",
                "Check unequal populations against a one-person/one-weight representation "
                "criterion.",
            ),
            (
                "Adjust remainder seats",
                "Start with floors totaling 246 and justify allocation of four remaining seats.",
            ),
        ],
    )
    add(
        "expert_land",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "'fairly divide the land' and conflicting personal valuations address fair allocation.",
            "With divisible additive valuations, give David piece 3, Andrea piece 4; Beatrice "
            "and Cleo value pieces 1+2 at 550 and 650, so divider-chooser guarantees each "
            ">=275 or >=325 respectively.",
            "The curated history explicitly includes divider-chooser and a fair share >=1/n; "
            "all totals are 1000 and thresholds 250.",
            "Andrea and Beatrice each accept only 2 or 4 at >=250; Cleo only 2. Three people "
            "cannot receive distinct acceptable whole pieces. Recombination addresses that "
            "conflict.",
            "The task does not supply an allocation, recombination step or new multi-person rule.",
        ),
        [
            (
                "Acceptable-piece table",
                "Threshold 250: Andrea {2,4}; Beatrice {2,4}; Cleo {2}; David all.",
            ),
            (
                "Greedy whole-piece allocation",
                "Expose the three-person/two-piece conflict rather than assert every approach "
                "fails.",
            ),
            (
                "Recombine and divide",
                "Use the already taught two-person divider-chooser on pieces 1+2 after "
                "allocating 3 and 4.",
            ),
        ],
        limitations=(
            "Fairness evidence assumes additive divisible land valuation; the text does not "
            "specify value density within pieces.",
        ),
    )
    add(
        "expert_time_sharing",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "'each receive a fair share' with one switch date requires valuation-sensitive "
            "division.",
            "Ann values the year at 140000 and Bob at 108000. Ann can cut after July: either "
            "side is 70000 to her; Bob chooses Aug-Dec worth 60000>=54000.",
            "Monthly addition and halves compute individual full-year values and fair-share "
            "thresholds.",
            "Equal calendar halves leave Ann Jan-Jun worth 60000<70000, though Bob Jul-Dec "
            "gets 72000>=54000. Value-sensitive cuts address the shortfall.",
            "The switch date and choice procedure are open; 'Ann ... first move' does not "
            "prescribe the fair cut.",
        ),
        [
            ("Equal calendar halves", "Compute Ann's Jan-Jun 60000 against her half-value 70000."),
            (
                "Value-balanced split",
                "Ann cuts after July into two equal-value 70000 intervals and Bob selects the "
                "later interval.",
            ),
        ],
        limitations=(
            "The imported mid-July canonical answer is wrong: Bob Jan-mid-July is 42000, not "
            "54000. Source solutions are excluded and this is not a task-invalid label.",
            "A month-boundary solution avoids assuming prorated within-month revenue or cash "
            "settlement.",
        ),
    )
    for identifier, calculation in (
        ("expert_ship", "(32*1+41*2)/(1+2)=38 km/h"),
        ("expert_walkcycle", "(4+6)/(1+6/12)=20/3 km/h"),
    ):
        add(
            identifier,
            ("yes", "yes", "yes", "no", "no"),
            (
                "'average speed for the whole journey' directly addresses the stated "
                "whole-journey rate.",
                calculation + "; all required distances/times are recoverable.",
                "The frozen history already includes speed=distance/time, rate arithmetic and "
                "unit conversion.",
                "For the checked distance/time aggregation, "
                + calculation
                + ". No target-related limitation is demonstrated; this is not an all-method "
                "claim.",
                "One fixed overall speed is requested; computing total distance and time "
                "leaves routine execution, not a central construction.",
            ),
            [("Total distance divided by total time", calculation)],
        )
    add(
        "music_compare_distributions__gpt41__016",
        ("partly", "not_assessed", "yes", "no", "yes"),
        (
            "Target explicitly includes random samples and inference about two populations; "
            "the task compares two complete submitted playlists, addressing center/variability "
            "but not sampling-based population inference.",
            "Skipped because alignment is Partly; descriptive arithmetic is not substituted "
            "for the conditional validity measure.",
            "The actual saved history already includes mean/median and IQR/MAD plus decimal "
            "operations.",
            "Checked mean-and-spread comparison meets the actual playlist demands using saved "
            "prerequisites; absence of population inference is alignment evidence, not an "
            "invented attempt limitation.",
            "Naming 'center and variability' is not a formula; the comparison criterion and "
            "evidential argument remain open.",
        ),
        [
            (
                "Mean and variability",
                "Playlist sums 37.2 and 39.7; means 4.65 and 4.9625; compare ranges 4.6 and 2.7.",
            ),
            (
                "Ordered displays",
                "Sort and plot both eight-song lists; compare longer center versus larger "
                "spread without assuming samples.",
            ),
        ],
    )
    add(
        "garden_composite_area__gpt5mini__028",
        ("yes", "no", "yes", "no", "partly"),
        (
            "The planted area of attached polygons is central, despite added plant-budget tasks.",
            "The plan places T on a 10-ft side and P on the 'opposite 12-ft side' of a "
            "12-by-10 rectangle; opposite sides cannot have unequal lengths.",
            "Compute rectangle area 120 and right-triangle area 30 with the saved "
            "decomposition/arithmetic history.",
            "The checked formal sum 120+30+40-24-3.5=162.5 can be computed by prior "
            "decomposition. The impossible attachment is a statement contradiction, not a "
            "target-related method limit.",
            "The task supplies the planted-area add/subtract route and example decompositions, "
            "but still leaves decomposition details and consequential plant-allocation choices.",
        ),
        [
            (
                "Separate polygon arithmetic",
                "R=120,T=30,P=40,patio=24,pond=3.5; formal total162.5 despite incompatible "
                "opposite-side statement.",
            ),
            (
                "Budget table",
                "10 shrubs+22 packs cover168 square ft, cost194.50; extra pack costs201.75, "
                "over budget. This does not repair geometry.",
            ),
        ],
    )
    add(
        "garden_composite_area__gpt41__019",
        ("yes", "yes", "yes", "no", "yes"),
        (
            "Students design a composite polygon patio and calculate its union area, exactly "
            "the area target.",
            "A nonoverlapping edge-connected layout is feasible. "
            "Triangle6+rectangle18+regular-hexagon6*sqrt(3) gives24+6*sqrt(3); regularity "
            "determines the missing altitude.",
            "Triangle area6 and rectangle18 are meaningful supported starts before the "
            "regular-hexagon challenge.",
            "A stopped exact-hexagon calculation may reflect an unlisted square-root/altitude "
            "skill, not a failure resolved by the target composite-area concept. Record "
            "unrelated_shortfall for that witness.",
            "Layout and overlap are genuine mathematical choices changing union area; a single "
            "fixed drawing or route is not supplied.",
        ),
        [
            (
                "Known component areas",
                "Compute triangle6 and rectangle18, then examine the exact regular-hexagon height.",
            ),
            (
                "Nonoverlapping layout",
                "Describe an edge-connected union and sum areas; mark any unlisted "
                "altitude/square-root import.",
            ),
            (
                "Overlap subtraction",
                "Choose a specified overlap and compute the resulting union rather than assume "
                "all arrangements equal.",
            ),
        ],
        limitations=(
            "The frozen polygon prior permits decomposition, but does not explicitly teach "
            "Pythagoras or square roots; no exact-hexagon prerequisite is silently added.",
        ),
    )
    add(
        "sports_basketball_ratio__gpt41__021",
        ("no", "not_assessed", "yes", "no", "yes"),
        (
            "Target is recognizing/representing proportional relationships between quantities; "
            "the actual demand is pooling shot outcomes and deciding 'most consistent' across "
            "shot types. Ratios alone are only topic overlap.",
            "Skipped because alignment is No, not marked mathematically invalid for being "
            "off-target.",
            "Saved unit-rate history supports 18/24=3/4 and the corresponding shot rates.",
            "The checked pooled-rate proposal 40/52,29/50,23/41 meets the task's open "
            "performance criterion when explicitly defined; no target-related limitation is "
            "established for that approach.",
            "A central definition of overall performance/consistency and how to combine two "
            "shot types remains open.",
        ),
        [
            (
                "Pooled success rate",
                "Curry40/52, Maya29/50, Alex23/41; state that the chosen meaning is overall "
                "accuracy.",
            ),
            (
                "Across-type consistency",
                "Compare each player's two success fractions; distinguish consistency from "
                "accuracy.",
            ),
        ],
        limitations=(
            "Different legitimate definitions of 'consistent' may rank players differently; "
            "this alone is not a contradiction.",
        ),
    )
    add(
        "sports_basketball_ratio__gpt5mini__002",
        ("yes", "yes", "yes", "no", "yes"),
        (
            "'decide whether ... proportional' and predictions/representations directly "
            "address the stated relationship target.",
            "3PT rates9/15=6/10=15/25=.6; MR rates2/3,.7,.625 and FT rates.9,.8,13/15 are not "
            "constant. Model assumptions can support an explicitly conditional plan.",
            "Unit rates are explicitly in the saved history: compute9/15=.6 using no new "
            "target rule.",
            "Checked unit-rate comparisons and a 40-minute3PT prediction24 meet the "
            "relationship demands; a plan can use that stable model. No target-related "
            "limitation is demonstrated in these checked approaches.",
            "The word 'proportional' and suggested representations do not supply the "
            "decisions; a prediction model and 40-minute allocation still require construction.",
        ),
        [
            (
                "Unit-rate table",
                "Compute all nine rates; identify 3PT's constant.6 and distinguish nonconstant "
                "MR/FT.",
            ),
            (
                "Scale a stable session",
                "40/10 copies of6 made shots predicts24; explain the constant-rate assumption.",
            ),
            (
                "Plan and justify",
                "Give an explicit40-minute allocation and justify any extrapolation of "
                "nonconstant data.",
            ),
        ],
        limitations=(
            "No unique future result follows from noisy MR/FT observations; conditional "
            "modeling is legitimate, not automatic invalidity.",
        ),
    )
    add(
        "synthetic_consistency_formula",
        ("yes", "yes", "yes", "no", "no"),
        (
            "The same variation data are used; the supplied formula still addresses consistency.",
            "Applying the supplied rule gives16/5,10/5,44/5, with Dave smallest.",
            "The rule is supplied in student text; listed arithmetic and means support its "
            "execution without importing an untaught formula.",
            "The checked supplied-rule calculation solves the prescribed demand; no "
            "target-related limitation remains in that route.",
            "'use exactly this rule' and 'Do not design alternative measures' remove the "
            "central construction.",
        ),
        [("Apply the supplied rule", "Means14,14,15; squared totals16,10,44; divide each by5.")],
    )
    add(
        "expert_hummingbird",
        ("yes", "unclear", "yes", "yes", "yes"),
        (
            "Arrival comparison depends on flapping rates and rest, so effective journey speed "
            "is central.",
            "Long-run wall-clock flap rates overlap: Giant[52.5,60], Broad[50,62.5] per "
            "minute. No guaranteed single winner is entailed without assumptions; an explicit "
            "conditional comparison may be valid.",
            "The stated rate history supports converting wing flaps to kilometres and "
            "flight/rest fractions.",
            "Comparing flying rates alone always favours Broad(100-125>70-80), but at70 "
            "versus100 including rest gives52.5>50 and Giant can win. Effective rate resolves "
            "that omission.",
            "Rest modeling, endpoint assumptions and a justified conditional comparison remain "
            "for students.",
        ),
        [
            (
                "Flying-rate comparison",
                "Compare70-80 to100-125 without rest and test why it does not settle "
                "whole-journey arrival.",
            ),
            (
                "Wall-clock rate",
                "Multiply by18/24 or12/24, then divide by550; preserve overlapping ranges.",
            ),
        ],
        alternatives={"mathematical_validity": ("yes",)},
        limitations=(
            "Yes validity is acceptable only with explicit assumptions/conditional conclusion; "
            "approximation and endpoint schedules must be stated, not silently fixed.",
        ),
    )
    add(
        "expert_tea",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "'Come up with a formula for consistency' is a construction demand, not routine "
            "named-formula recall.",
            "Five Thourbo observations and six each for the others allow explicitly stated "
            "missing-value treatment; ranges10,10,10 do not distinguish them.",
            "Compute observed means15,15,15 and ranges10,10,10 with the frozen history.",
            "Mean and range both tie despite different spread: mean squared "
            "deviations56/5,31/3,12. A richer all-observation measure can distinguish.",
            "The formula and justification, including how to handle the '--' entry, are open.",
        ),
        [
            (
                "Observed means and ranges",
                "Ignore unavailable Thourbo2010 only with an explicit missing-value "
                "assumption; means15 and ranges10.",
            ),
            (
                "Construct deviation aggregation",
                "Observed squared-deviation sums56,62,72 with counts5,6,6; normalize counts "
                "explicitly.",
            ),
        ],
        limitations=(
            "The '--' entry is unknown, not zero; no invented observation is added to the "
            "student input.",
        ),
    )
    add(
        "expert_goals",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "The task requests fractional graphical comparison of3/5 versus5/10.",
            "Each player has one attempt, so equal-whole normalization compares6/10>5/10; "
            "girls win on rate.",
            "Frozen fraction/diagram history supports drawing five and ten equal-share attempts.",
            "Raw totals5>3 favour boys but compare unequal team sizes; common-denominator "
            "fractions reverse that answer.",
            "A graphical construction and common reference whole must be chosen; examples of "
            "boxes/bars do not give the comparison.",
        ),
        [
            ("Raw goal totals", "Count3 and5; test fairness when attempts are5 and10."),
            ("Common denominator", "Represent3/5 as6/10 beside5/10 using equal-sized wholes."),
        ],
    )
    add(
        "expert_pizza",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "'greater proportion' and 'as many solution paths' address equivalent fair shares.",
            "Four/six and two/three both equal2/3 of an equal-sized pizza. If pizza sizes "
            "differ, the proportional claim remains equal, not equal physical area.",
            "Equal-sharing diagrams can divide four pizzas among six and two among three.",
            "Comparing only total pizzas4>2 predicts boys get more; grouping each into pairs "
            "of pizzas shared by three resolves the denominator mismatch.",
            "The equality conclusion and common-share construction are not supplied; multiple "
            "mathematical routes remain.",
        ),
        [
            ("Compare total pizzas", "Check why4 versus2 ignores recipients6 versus3."),
            (
                "Group or simplify shares",
                "Two groups of3 boys each share2 pizzas, exactly the girls' sharing situation.",
            ),
        ],
        limitations=(
            "Physical pizza sizes are unstated; reference compares the requested proportion of "
            "a pizza, not grams or area.",
        ),
    )
    add(
        "expert_furniture",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "'fair share' in dollar amounts with indivisible goods calls for allocation and "
            "compensation.",
            "Under permitted transfers: Ashley chair+125, Bill table/dresser/couch-400, "
            "Cliff275; cash sums0 and personal net values300,350,275 exceed250,300,225 "
            "thresholds.",
            "Curated prior includes fair division and arithmetic; personal fair shares "
            "are750/3=250,900/3=300,675/3=225.",
            "Highest-valued-item assignment gives Cliff no item/value, below225; compensated "
            "division addresses that specific shortfall.",
            "Neither cash transfers nor their calculation is supplied; students must propose "
            "and justify a settlement.",
        ),
        [
            (
                "Personal fair-share totals",
                "Compute750/3,900/3,675/3 rather than divide by four items.",
            ),
            (
                "Allocate by valuation",
                "Ashley gets chair175, Bill goods750, Cliff none; inspect cash compensation need.",
            ),
            (
                "Balance compensation",
                "Check transfers+125,-400,+275 sum0 and each own-valued net exceeds threshold.",
            ),
        ],
        limitations=(
            "The feasible reference assumes cash compensation is permitted, additive values "
            "and no external subsidy; no universal goods-only guarantee is asserted.",
        ),
    )
    add(
        "expert_braking_collision",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "The police decision requires reconstructing initial speeds from deceleration and "
            "skid distances.",
            "Under constant deceleration and coupled post-impact motion: shared speed "
            "sqrt(108), truck pre-impact1.5*sqrt(108), truck initial sqrt(315)=63.89km/h, car "
            "initial12m/s=43.2km/h, both>40.",
            "Prior speed conversion yields40km/h=100/9m/s; a distance-time sketch is "
            "meaningful without the new braking law.",
            "Distance/time at24km/h treats a varying speed as constant and cannot justify "
            "pre-braking speed; integrating constant deceleration or constructing a velocity "
            "triangle addresses it.",
            "Students choose a physical model and evidential argument rather than apply a "
            "supplied braking equation.",
        ),
        [
            (
                "Sketch and units",
                "Convert40km/h and distinguish pre-impact, post-impact and pre-braking phases.",
            ),
            (
                "Constant-speed shortcut",
                "Check why the stuck speedometer24km/h is not the pre-braking speed.",
            ),
            (
                "Construct acceleration reasoning",
                "Work from uniform deceleration to v^2=2as and the supplied1.5 collision "
                "factor; name any imported law.",
            ),
        ],
        limitations=(
            "The verdict is conditional on physical modeling assumptions; legal fault for the "
            "accident is not determined by speed arithmetic alone.",
        ),
    )
    add(
        "expert_braking_lawyer",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "The client file requests reconstructing speeding evidence from15m skid and "
            "friction0.6-0.7.",
            "With g=9.8 and a=mu*g constant, v=sqrt(2*mu*9.8*15)*3.6 spans47.81-51.65km/h, "
            "below55. Reaction distance is not added to a braking-only skid.",
            "Convert55km/h to275/18m/s and inspect the15m braking segment using listed "
            "speed/acceleration knowledge.",
            "Using15/0.8=18.75m/s assumes reaction time equals braking time, which the file "
            "does not say; a braking-distance relation addresses that missing relationship.",
            "The student must construct a justified model and case, not receive a supplied "
            "stopping-speed formula.",
        ),
        [
            (
                "Identify phases",
                "Distinguish reaction0.8s from braking time, and15m skid from total stopping "
                "distance.",
            ),
            (
                "Friction and deceleration",
                "Compute a interval5.88-6.86m/s^2 using the explicitly frozen prerequisite.",
            ),
            (
                "Braking reconstruction",
                "Construct or explicitly flag import of v^2=2as; obtain below55km/h under "
                "stated assumptions.",
            ),
        ],
        limitations=(
            "This is a physical-model argument, not proof of actual vehicle speed or legal "
            "innocence; friction and skid estimates have uncertainty.",
        ),
    )
    add(
        "grounding_scientific_scale_comparison_r01_A",
        ("yes", "yes", "yes", "no", "yes"),
        (
            "The compact exact comparison record requires a scale/coefficient convention and "
            "recoverable ordering.",
            "Using units of10^-10m gives integer "
            "coefficients4.2,7200000,21000000,75000000,34000000000; alternatively normalize "
            "coefficients and state exponent rules.",
            "Saved decimal comparison and powers-of-ten arithmetic supports ordering the "
            "supplied values.",
            "For the checked common-scale construction, existing decimal shifts preserve every "
            "value and ordering; no target-related limit is demonstrated. Reading4.2e-10 may "
            "need explicitly explained notation.",
            "The task leaves the convention and decoding/checking argument open, despite one "
            "datum already using e-notation.",
        ),
        [
            (
                "Decimal ordering",
                "4.2e-10<.00072<.0021<.0075<3.4 after interpreting the supplied e notation.",
            ),
            (
                "Common scale",
                "Choose10^-10m and construct exact coefficients without silently importing "
                "normalized-notation rules.",
            ),
        ],
        limitations=(
            "The source already contains4.2e-10, an interpretation risk for untaught notation. "
            "A missing decoding witness should stay start_unresolved, not be fabricated.",
        ),
    )
    add(
        "grounding_signed_product_ledger_r01_A",
        ("yes", "yes", "yes", "yes", "yes"),
        (
            "'every combination' including negative counts requires a coherent "
            "signed-multiplication convention.",
            "Interpreting a negative count as undoing positive applications makes(-3)*(-2)=6, "
            "agrees with addition/subtraction, and covers zero without contradiction.",
            "Saved signed addition and nonnegative repeated groups support3 applications of "
            "debt-2 as-6.",
            "Repeated addition directly handles positive counts but does not alone define "
            "'negative repetitions'; inverse/undo construction connects that limitation to the "
            "signed-product target.",
            "No sign table is supplied; the convention and its consistency argument are "
            "central constructions.",
        ),
        [
            (
                "Repeated signed addition",
                "Three debts of-2 total-6; explicitly identify why a negative count is not "
                "literal repeated addition.",
            ),
            (
                "Undo operations",
                "Construct negative count as removal/undoing and test all sign/zero combinations.",
            ),
        ],
    )
    add(
        "control_partial_alignment",
        ("partly", "not_assessed", "yes", "no", "no"),
        (
            "Target explicitly requires mean and median; task explicitly requests only mean.",
            "Not assessed after Partly alignment.",
            "(3+5+10)/3=6 is a meaningful supported calculation.",
            "Mean6 meets the actual task demand; the missing median is not an attempt error.",
            "Only a supplied familiar mean operation is requested.",
        ),
        [("Calculate mean", "(3+5+10)/3=6.")],
        confidence="high",
    )
    add(
        "control_off_target",
        ("no", "not_assessed", "yes", "no", "no"),
        (
            "Area multiplication is a different concept from comparing fractions.",
            "Not assessed after No alignment, even though15square cm is arithmetically correct.",
            "5*3=15 is supported by arithmetic.",
            "The supplied-route calculation completes the task; there is no target-related "
            "witness.",
            "The central formula is supplied and only routine multiplication remains.",
        ),
        [("Apply supplied formula", "5*3=15 square cm.")],
        confidence="high",
    )
    add(
        "control_inaccessible",
        ("yes", "yes", "no", "not_assessed", "no"),
        (
            "The task explicitly requests power-rule differentiation at a point.",
            "The supplied rule gives3*2^2=12; the mathematical task is consistent.",
            "Only numeral recognition is in the frozen pool; even meaningful substitution or "
            "multiplication is explicitly unavailable. Copying3 is not a start.",
            "Not assessed because no meaningful supported start is possible under this "
            "deliberately tiny prior pool.",
            "The differentiation rule is supplied; students are asked only to execute it.",
        ),
        [],
        confidence="high",
    )
    add(
        "control_mathematical_contradiction",
        ("yes", "no", "yes", "no", "no"),
        (
            "Area versus side length is central and matches the stated target.",
            "3*2=6, contradicting exact area5; no rectangle can satisfy all exact givens.",
            "3*2=6 is a meaningful prerequisite-supported start.",
            "The impossibility comes from inconsistent givens, not a target-resolvable "
            "familiar-method limitation: unrelated_shortfall.",
            "The formula and conclusion test are supplied; there is no central invention left "
            "open.",
        ),
        [("Check exact constraints", "3*2=6 !=5.")],
        confidence="high",
    )
    add(
        "control_unproved_universal_claim",
        ("yes", "unclear", "yes", "unclear", "yes"),
        (
            "The task explicitly asks for a universal prime-sum proof.",
            "This is the strong Goldbach conjecture, an open universal claim; small exact "
            "examples do not supply the missing general proof or establish a contradiction.",
            "4=2+2,6=3+3 and8=3+5 are meaningful starts using the stipulated prime/arithmetic "
            "pool.",
            "Finitely many examples and an unsupported generalization do not demonstrate a "
            "target-resolvable limit or a completed proof; outcome unresolved, not automatic "
            "failure.",
            "The central proof/counterexample is not provided.",
        ),
        [
            (
                "Test small cases",
                "Check4,6,8,10; explicitly avoid presenting finite checks as a universal proof.",
            )
        ],
        confidence="high",
        limitations=(
            "This is a deliberately unsuitable classroom task and instrument control, not a "
            "recommended PF exercise or a claim that a solvable school problem is inherently "
            "Unclear.",
        ),
    )
    add(
        "control_missing_task_context",
        ("unclear", "not_assessed", "unclear", "not_assessed", "unclear"),
        (
            "No target or actual diagram is available; alignment cannot be established.",
            "Skipped because alignment is Unclear, not an automatic mathematics failure.",
            "The missing diagram prevents verifying the proposed numerical start; that is "
            "start_unresolved, not evidence of unavailable knowledge.",
            "Skipped after Unclear accessibility.",
            "Without marked lengths/demands the significance of any remaining choice cannot be "
            "established.",
        ),
        [],
        confidence="high",
    )
    add(
        "control_missing_history",
        ("yes", "yes", "unclear", "not_assessed", "no"),
        (
            "The addition demand matches the declared addition target.",
            "6+7=13 exactly.",
            "Frozen prerequisite history is empty: skip the solver and record Unclear, never "
            "infer that no learner can start.",
            "Skipped because accessibility is Unclear.",
            "The task supplies the entire addition route and leaves routine execution.",
        ),
        [],
        confidence="high",
    )
    return result


def attempt_fixtures() -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []

    def add(
        identifier: str,
        case_id: str,
        rows: list[tuple[str, str, str, str]],
        accessibility: str,
        limits: str,
        no_start_argument: str | None = None,
    ) -> None:
        groups.append(
            {
                "id": identifier,
                "case_id": case_id,
                "provenance": "constructed_diagnostic_attempts",
                "not_actual_student_work": True,
                "not_model_solver_output": True,
                "attempts": [{"idea": idea, "work": work} for idea, work, _, _ in rows],
                "expected_reviews": [
                    {"attempt_index": index, "status": status, "reason": reason}
                    for index, (_, _, status, reason) in enumerate(rows)
                ],
                "no_start_argument": no_start_argument,
                "expected_verdicts": {
                    "prior_knowledge_accessibility": accessibility,
                    "familiar_approach_limits": limits,
                },
                "label_confidence": "high",
            }
        )

    add(
        "imported_formula_only",
        "expert_consistency",
        [
            (
                "Recall an untaught formula",
                "I already know population variance is sum((x-mean)^2)/n. "
                "I use that recalled formula directly: Mike3.2, Dave2, Ivan8.8; Dave wins.",
                "not_supported",
                "Explicit recall of a formula absent from frozen arithmetic/mean/range "
                "history; no independent supported start is shown.",
            )
        ],
        "unclear",
        "not_assessed",
    )
    add(
        "trivial_restatement",
        "expert_consistency",
        [
            (
                "Restate request",
                "There are three players. I need to find the most consistent one.",
                "not_supported",
                "Restates givens and goal but performs no meaningful mathematical action.",
            )
        ],
        "unclear",
        "not_assessed",
    )
    add(
        "misread_data",
        "expert_goals",
        [
            (
                "Misread team size",
                "There are3 girls with5 goals and10 boys with5 goals, so girls win5/3 versus5/10.",
                "not_supported",
                "The text has5 girls and3 goals, not3 girls and5 goals; this is a demonstrable "
                "misread.",
            )
        ],
        "unclear",
        "not_assessed",
    )
    add(
        "unverifiable_start",
        "control_missing_task_context",
        [
            (
                "Use unseen diagram",
                "The diagram's marked side looks like3, so I begin3*3=9.",
                "start_unresolved",
                "The diagram is absent. The premise of the action cannot be checked; do not "
                "call it a verified misread or unavailable skill.",
            )
        ],
        "unclear",
        "not_assessed",
    )
    add(
        "supported_start_then_giving_up",
        "expert_bicycle",
        [
            (
                "Convert route lengths",
                "The route is75*7/60=8.75km and we have ridden.15*25=3.75km, so5km remain. I "
                "stop because the rest looks hard.",
                "unresolved",
                "Supported meaningful arithmetic start, but merely stopping demonstrates no "
                "mathematical approach limit.",
            )
        ],
        "yes",
        "unclear",
    )
    add(
        "target_limit_with_successful_alternative",
        "expert_consistency",
        [
            (
                "Signed deviations",
                "The means are14,14,15. I add signed differences from each own mean. "
                "Mike:-1-2+1+3-1=0; Dave:-2+0+2+1-1=0; Ivan:-1-5+3+3+0=0. "
                "My proposed measure ties everyone and loses the spread I wanted to compare.",
                "target_limit",
                "Every observation is used, but cancellation erases variation; magnitude-based "
                "aggregation addresses this target-related limitation.",
            ),
            (
                "Construct absolute deviations",
                "To count distance from the mean I take each difference's positive magnitude "
                "and average them. "
                "Mike:(1+2+1+3+1)/5=1.6; Dave:(2+0+2+1+1)/5=1.2; "
                "Ivan:(1+5+3+3+0)/5=2.4. Dave varies least by my rule. "
                "I define this rule from differences, not recall a supplied formula.",
                "meets_demands",
                "A justified constructed all-data variation measure; building an idea from "
                "familiar arithmetic is allowed. Its success does not erase the other "
                "limitation.",
            ),
        ],
        "yes",
        "yes",
    )
    add(
        "routine_meets_demands",
        "expert_ship",
        [
            (
                "Whole journey rate",
                "Distance=32*1+41*2=114km; time=3h; average speed=114/3=38km/h.",
                "meets_demands",
                "All actions follow the listed speed/arithmetic history and complete the "
                "actual task.",
            )
        ],
        "yes",
        "no",
    )
    add(
        "unrelated_missing_skill",
        "garden_composite_area__gpt41__019",
        [
            (
                "Add component areas",
                "I choose no overlaps. The triangle area is4*3/2=6 and rectangle6*3=18. "
                "I split the regular hexagon into six equilateral triangles of side2, "
                "but cannot determine their exact height with my listed skills. I have not "
                "learned square roots or Pythagoras.",
                "unrelated_shortfall",
                "The supported start is clear; an unlisted altitude/root skill stops this "
                "exact calculation. The missing skill is not the composite-area target.",
            )
        ],
        "yes",
        "no",
    )
    add(
        "inconsistent_givens_not_target_limit",
        "control_mathematical_contradiction",
        [
            (
                "Check exact area",
                "3*2=6, but the task insists area5. I cannot exhibit such a rectangle.",
                "unrelated_shortfall",
                "The impossibility is the task's exact contradictory givens, not a failure "
                "fixed by learning rectangle area.",
            )
        ],
        "yes",
        "no",
    )
    add(
        "unsupported_universal_proof",
        "control_unproved_universal_claim",
        [
            (
                "Examples then universal claim",
                "4=2+2,6=3+3,8=3+5,10=3+7. I think every even integer works, so this proves it.",
                "unresolved",
                "The examples are meaningful supported starts but do not justify a universal "
                "conclusion; no general proof or counterexample is supplied.",
            )
        ],
        "yes",
        "unclear",
    )
    add(
        "concrete_no_start",
        "control_inaccessible",
        [
            (
                "Copy numerals",
                "I can copy the numerals3 and2 from the question.",
                "not_supported",
                "Numeral copying is not a mathematical start on substitution, powers or "
                "differentiation.",
            )
        ],
        "no",
        "not_assessed",
        "The only listed knowledge is numeral recognition; substitution, arithmetic and powers "
        "are explicitly absent. Even the first meaningful application of the supplied rule "
        "needs those unavailable resources.",
    )
    add(
        "success_and_unresolved_remain_unclear",
        "expert_ship",
        [
            (
                "Whole journey rate",
                "32+82=114km,1+2=3h,114/3=38km/h.",
                "meets_demands",
                "This checked approach completes the task.",
            ),
            (
                "Incomplete distance sketch",
                "I draw a first segment of32km. I have not worked out how the second segment "
                "affects my representation.",
                "unresolved",
                "A supported partial representation has no established outcome; another "
                "success does not settle this approach.",
            ),
        ],
        "yes",
        "unclear",
    )
    return groups


def all_cases(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return [case for key in ("development", "transfer", "controls") for case in pack[key]]


def fixture_verdicts(group: dict[str, Any]) -> dict[str, str]:
    """Expected aggregation only; this is not a text judge or student simulator."""
    statuses = {review["status"] for review in group["expected_reviews"]}
    supported = statuses & {"target_limit", "meets_demands", "unrelated_shortfall", "unresolved"}
    if supported:
        accessibility = "yes"
    elif group["no_start_argument"] and "start_unresolved" not in statuses:
        accessibility = "no"
    else:
        accessibility = "unclear"
    if accessibility != "yes":
        limits = "not_assessed"
    elif "target_limit" in statuses:
        limits = "yes"
    elif statuses & {"unresolved", "start_unresolved"}:
        limits = "unclear"
    else:
        limits = "no"
    return {
        "prior_knowledge_accessibility": accessibility,
        "familiar_approach_limits": limits,
    }


def mathematical_checks() -> list[dict[str, Any]]:
    """Run exact narrow checks, not a substitute for whole-task verification."""
    checks = []

    def check(label: str, actual: Any, expected: Any) -> None:
        holds = actual == expected
        checks.append(
            {
                "claim": label,
                "computed": str(actual),
                "expected": str(expected),
                "holds": holds,
                "evidence_level": "deterministic_arithmetic_only",
            }
        )
        if not holds:
            raise ValueError(f"Provisional-reference arithmetic failed: {label}")

    x = Fraction(17, 5)
    jasmine = x / Fraction("0.15") + (5 - x) / Fraction("0.03")
    hady = x / Fraction("0.05") + (5 - x) / Fraction("0.2")
    check("Bicycle proposed handover: Jasmine total minutes", jasmine, 76)
    check("Bicycle proposed handover: equal arrival times", jasmine, hady)
    check(
        "Bicycle biking-ratio shortcut: Jasmine minutes",
        Fraction(20, 7) / Fraction(".15") + Fraction(15, 7) / Fraction(".03"),
        Fraction(1900, 21),
    )
    check(
        "Bicycle biking-ratio shortcut: Hady minutes",
        Fraction(20, 7) / Fraction(".05") + Fraction(15, 7) / Fraction(".2"),
        Fraction(475, 7),
    )
    for source_id, expected_sums in (
        ("puech2025_stratl_consistency", [16, 10, 44]),
        ("puech2025_stratl_consistency_tea", [56, 62, 72]),
    ):
        columns: list[list[Fraction]] = [[], [], []]
        for line in exercise(EXPERT, source_id)["problem"].splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 4 and cells[0].isdigit():
                for index, value in enumerate(cells[1:]):
                    if value != "--":
                        columns[index].append(Fraction(value))
        for index, values in enumerate(columns):
            mean = sum(values) / len(values)
            total = sum((value - mean) ** 2 for value in values)
            check(
                f"{source_id} column{index + 1}: squared-deviation total",
                total,
                expected_sums[index],
            )
    population = [1646000, 6936000, 154000, 2091000, 685000, 988000]
    check("Country total population", sum(population), 12500000)
    check(
        "Country nearest-integer total is251, not250",
        sum(round(Fraction(p, 50000)) for p in population),
        251,
    )
    check("Country feasible integer allocation total", sum([33, 139, 3, 42, 13, 20]), 250)
    check("Time-sharing Ann whole-year valuation", 7 * 10000 + 5 * 14000, 140000)
    check("Time-sharing Bob chosen Aug-Dec valuation", 5 * 12000, 60000)
    check(
        "Rejected source answer: Bob Jan-mid-July valuation",
        6 * 6000 + Fraction(1, 2) * 12000,
        42000,
    )
    check("Ship whole-journey speed", Fraction(32 + 2 * 41, 3), 38)
    check("Walk-cycle whole-journey speed", Fraction(10) / Fraction(3, 2), Fraction(20, 3))
    check(
        "Garden028 formal areas do not repair geometric contradiction",
        120 + 30 + 40 - 24 - Fraction(7, 2),
        Fraction(325, 2),
    )
    check("Furniture proposed transfers conserve cash", 125 - 400 + 275, 0)
    check("Furniture Ashley personal net value", 175 + 125, 300)
    check("Furniture Bill personal net value", 250 + 200 + 300 - 400, 350)
    check("Furniture Cliff personal net value", 275, 275)
    check(
        "Braking collision: truck initial squared m/s", Fraction(3, 2) ** 2 * 108 + 2 * 6 * 6, 315
    )
    check(
        "Braking lawyer maximum speed squared is below speed limit squared",
        2 * Fraction("0.7") * Fraction("9.8") * 15 < (Fraction(55) / Fraction("3.6")) ** 2,
        True,
    )
    return checks


def build_pack() -> dict[str, Any]:
    inputs = freeze_inputs()
    frozen_records = [
        {"id": case["id"], **{key: case[key] for key in INPUT_KEYS}}
        for cases in inputs.values()
        for case in cases
    ]
    frozen_hash = digest(frozen_records)
    notes = annotations()
    for cases in inputs.values():
        for case in cases:
            case["input_sha256"] = digest({key: case[key] for key in INPUT_KEYS})
            case["student_task_sha256"] = hashlib.sha256(
                case["student_task"].encode("utf-8")
            ).hexdigest()
            case.update(notes[case["id"]])
    pack = {
        "schema_version": "pf-measure-calibration/v1",
        "created_at": "2026-10-14",
        "status": "inputs_and_provisional_references_saved_no_model_judgments",
        "model_calls": 0,
        "human_review_available": False,
        "reference_policy": {
            "provenance": "assistant_provisional",
            "not_human_ratings": True,
            "not_validated_gold": True,
            "authorization": (
                "The current request authorizes autonomous preparation of machine/"
                "researcher-provisional references while human review is unavailable. "
                "This explicitly differs from the earlier human-written-reference plan."
            ),
            "confidence_definition": (
                "Confidence concerns the provisional label/evidence, not a measured "
                "judge accuracy or educational validation probability."
            ),
            "alternatives_policy": (
                "Only genuinely ambiguous interpretations have acceptable alternatives, "
                "with the reason recorded; Partly is never a substitute for uncertainty."
            ),
            "prior_expert_exposure": (
                "All expert examples were previously read. Reserved means excluded from "
                "new prompt tuning, not untouched-topic or independent human validation. "
                "Development expert cases may calibrate evidence coding, not serve as "
                "new prompt examples; transfer cases are not used for new prompt tuning."
            ),
            "reserved_transfer": (
                "Transfer inputs and provisional references are prepared now for a "
                "later frozen-instrument check, not run or retuned on here."
            ),
        },
        "metric_values": METRIC_VALUES,
        "attempt_statuses": ATTEMPT_STATUSES,
        "dependencies": {
            "mathematical_validity": "target_alignment == yes",
            "familiar_approach_limits": "prior_knowledge_accessibility == yes",
        },
        "freeze": {
            "order": ["task_inputs", "input_hashes", "provisional_references", "verification"],
            "inputs_sha256": frozen_hash,
            "no_new_judgments_before_freeze": True,
            "model_judgments_executed": False,
        },
        "split_policy": {
            "disjoint_case_ids": True,
            "disjoint_source_task_instances": True,
            "no_curated_import_versions_across_splits": True,
            "topic_overlap": (
                "Average speed, variation and fair division recur in the expert pool. "
                "They are distinct task instances, not claims of disjoint topics. "
                "The synthetic formula contrast stays with development consistency."
            ),
            "generated_transfer": (
                "The scientific-scale and signed-ledger r01/A tasks were unused for "
                "this instrument's development; they are historical generated outputs, "
                "not never-inspected data or a new generation run."
            ),
            "controls_excluded_from_case_denominators": True,
        },
        **inputs,
        "attempt_fixture_groups": attempt_fixtures(),
        "deterministic_checks": mathematical_checks(),
        "limitations": [
            "This execution builds and verifies a pack; it does not run a solver or either judge.",
            "No human, teacher or independent expert reviewed these provisional labels.",
            "Constructed diagnostic attempts are neither actual student work nor sampled model "
            "behavior.",
            "A successful familiar approach does not erase a target-related limitation witness.",
            "Math validity is conditional on alignment Yes; limits are conditional on "
            "demonstrated accessibility Yes.",
            "References and targets are never included in solver_input; task wording may "
            "legitimately name its topic.",
            "Some targets/history are assistant-specified, and physical/additive-value "
            "modeling assumptions remain explicit.",
            "Prior-to-target import and coverage judgments require subsequent inspection of "
            "actual frozen solver output.",
        ],
    }
    pack["verification"] = validate_pack(pack, check_sources=True)
    return pack


def validate_pack(pack: dict[str, Any], *, check_sources: bool = True) -> dict[str, Any]:
    cases = all_cases(pack)
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case id")
    seen_instances: dict[tuple[str, str], str] = {}
    seen_texts: dict[str, str] = {}
    coverage = {metric: set() for metric in METRIC_VALUES}
    source_count: set[tuple[str, str]] = set()
    for case in cases:
        if case["case_id"] != case["id"]:
            raise ValueError("Core case_id and local id differ")
        payload = {key: case[key] for key in INPUT_KEYS}
        if case["input_sha256"] != digest(payload):
            raise ValueError(f"Frozen input changed: {case['id']}")
        text_hash = hashlib.sha256(case["student_task"].encode("utf-8")).hexdigest()
        if text_hash != case["student_task_sha256"]:
            raise ValueError("Student text hash mismatch")
        solver = case["solver_input"]
        expected_solver = {
            "student_task": case["student_task"],
            "learner_context": case["learner_context"],
        }
        if solver != expected_solver:
            raise ValueError("Solver input is not the strict task/history projection")
        if set(solver["learner_context"]) != {"assumed_prior_knowledge"}:
            raise ValueError("Solver context contains non-history fields")
        if not case["prerequisite_provenance"]["independent_of_desired_errors"]:
            raise ValueError("History must be independent of desired attempts")
        if case["student_task_sha256"] in seen_texts:
            raise ValueError("Duplicate student task across cases")
        seen_texts[text_hash] = case["id"]
        for item in case["sources"]:
            source_count.add((item["path"], item["sha256"]))
            if check_sources and file_digest(item["path"]) != item["sha256"]:
                raise ValueError(f"Source changed: {item['path']}")
            if item["student_fields"]:
                instance = (item["path"], item["selector"])
                prior_split = seen_instances.setdefault(instance, case["split"])
                if prior_split != case["split"]:
                    raise ValueError("A source task version crosses splits")
        refs = case["references"]
        if set(refs) != set(METRIC_VALUES):
            raise ValueError("Missing measure reference")
        for metric, ref in refs.items():
            if ref["value"] not in METRIC_VALUES[metric]:
                raise ValueError(f"Invalid value for {metric}")
            if ref["value"] not in ref["acceptable_values"]:
                raise ValueError("Primary label missing from acceptable values")
            if not set(ref["acceptable_values"]) <= set(METRIC_VALUES[metric]):
                raise ValueError("Invalid acceptable reference value")
            if ref["label_confidence"] not in {"high", "medium", "low"}:
                raise ValueError("Missing label confidence")
            if not ref["evidence"] or ref["human_reviewed"] or ref["validated_gold"]:
                raise ValueError("Reference provenance/evidence is invalid")
            coverage[metric].add(ref["value"])
        aligned = refs["target_alignment"]["value"] == "yes"
        mathematical = refs["mathematical_validity"]["value"]
        if (mathematical != "not_assessed") != aligned:
            raise ValueError("Mathematical-validity dependency violated")
        accessible = refs["prior_knowledge_accessibility"]["value"] == "yes"
        limits = refs["familiar_approach_limits"]["value"]
        if (limits != "not_assessed") != accessible:
            raise ValueError("Familiar-limit dependency violated")
    frozen_records = [
        {"id": case["id"], **{key: case[key] for key in INPUT_KEYS}} for case in cases
    ]
    if digest(frozen_records) != pack["freeze"]["inputs_sha256"]:
        raise ValueError("Frozen pack input hash mismatch")
    status_coverage: set[str] = set()
    for group in pack["attempt_fixture_groups"]:
        if group["case_id"] not in ids:
            raise ValueError("Fixture references missing case")
        if len(group["attempts"]) != len(group["expected_reviews"]):
            raise ValueError("Fixture attempt/review mismatch")
        for index, review in enumerate(group["expected_reviews"]):
            if review["attempt_index"] != index or review["status"] not in ATTEMPT_STATUSES:
                raise ValueError("Invalid fixture classification")
            status_coverage.add(review["status"])
        if fixture_verdicts(group) != group["expected_verdicts"]:
            raise ValueError("Inconsistent fixture-derived verdicts")
    if status_coverage != set(ATTEMPT_STATUSES):
        raise ValueError("Missing attempt-state control")
    for metric, values in METRIC_VALUES.items():
        if coverage[metric] != set(values):
            raise ValueError(f"Missing categorical-state control for {metric}")
    if not all(check["holds"] for check in pack["deterministic_checks"]):
        raise ValueError("A deterministic check failed")
    return {
        "passed": True,
        "counts": {
            **{key: len(pack[key]) for key in ("development", "transfer", "controls")},
            "attempt_fixture_groups": len(pack["attempt_fixture_groups"]),
            "constructed_attempts": sum(len(x["attempts"]) for x in pack["attempt_fixture_groups"]),
            "distinct_source_files": len(source_count),
            "deterministic_arithmetic_checks": len(pack["deterministic_checks"]),
        },
        "categorical_state_coverage": {
            metric: sorted(values) for metric, values in coverage.items()
        },
        "attempt_status_coverage": sorted(status_coverage),
        "origins": dict(Counter(case["origin"] for case in cases)),
        "source_hashes_checked": check_sources,
        "solver_projection_checked": True,
        "dependencies_checked": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--verify", action="store_true", help="Verify the saved artifact without rewriting it."
    )
    args = parser.parse_args(argv)
    path = args.output if args.output.is_absolute() else ROOT / args.output
    pack = build_pack()
    if args.verify:
        saved = json.loads(path.read_text(encoding="utf-8"))
        validate_pack(saved, check_sources=True)
        if saved != pack:
            raise ValueError(
                "Saved pack differs from reproducible build; do not silently overwrite"
            )
    elif path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != pack:
            raise FileExistsError("Refusing to overwrite a different frozen calibration pack")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(path.relative_to(ROOT)), **pack["verification"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

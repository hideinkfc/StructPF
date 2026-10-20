"""Build and verify the PF Solver Approach-Recall & Objectivity Benchmark dataset.

Combines six provenance-preserved cohorts where reference approaches exist prior to
and independently of the v3.0 evaluator solver:
  1. expert_pf (12 published PF exercises from Kapur & Bielaczyc 2012, Loibl & Rummel 2014,
     Kerrigan et al. 2021, and Puech et al. 2025 StratL)
  2. routine_and_control (12 routine textbook, prescribed-formula, and diagnostic control
     tasks from calibration_pack.json where familiar methods solve the task or hit a
     known control condition)
  3. pipeline_r1_audited (9 Pipeline R1 tasks from pf_method_comparison_draft_first_20261011
     with frozen selected_brief paths and baseline_coverage.json audited definitions)
  4. pipeline_r2_lc_impasse (9 Learning-Commons-grounded Pipeline R2 tasks from
     pf_pipeline_lc_impasse_v3_20261015 with pre-generation selected_brief approaches)
  5. pipeline_topic_sweep (19 curriculum-sweep PF tasks across 19 distinct maths topics from
     pf_topic_sweep_20261011/final_20 with pre-generation selected_brief approaches)
  6. pipeline_grounding_study (15 curriculum-grounded PF tasks across 5 topics x 3 arms from
     pf_grounding_study_20261013/attempts/main/*/r01/* with pre-generation selected_brief
     approaches)

Usage:
  ./.venv/bin/python scripts/build_pf_solver_recall_benchmark.py
  ./.venv/bin/python scripts/build_pf_solver_recall_benchmark.py --verify
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/configs/pf_solver_recall_benchmark_20261016.json"
CALIBRATION_PACK = ROOT / "experiments/results/pf_measure_campaign_20261014/calibration_pack.json"
CATALOG = ROOT / "experiments/results/pf_measure_campaign_20261014/catalog.json"
BASELINE_COVERAGE = (
    ROOT / "experiments/results/pf_path_coverage_final_20261012/baseline_coverage.json"
)
V30_CALIB_DIR = ROOT / "experiments/results/pf_v30_calibration_20261015"

KAPUR_YAML = "data/pf_exercises/kapur_bielaczyc_2012.yaml"
LOIBL_YAML = "data/pf_exercises/loibl_rummel_2014.yaml"
KERRIGAN_YAML = "data/pf_exercises/kerrigan_weber_chinn_2021.yaml"
STRATL_SUB_YAML = "data/pf_exercises/puech_macina_2025_stratl.yaml"

SCHEMA_VERSION = "pf-solver-recall-benchmark/v1"
VALID_ROLES = (
    "baseline_trap",
    "resolving_route",
    "routine_solution",
    "diagnostic_control_check",
    "shared_setup_or_representation",
)
PRIMARY_COMPLETE_ROLES = (
    "baseline_trap",
    "resolving_route",
    "routine_solution",
    "diagnostic_control_check",
)


def file_sha256(rel_path: str | Path) -> str:
    p = ROOT / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
    return hashlib.sha256(p.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def make_source(rel_path: str, selector: str) -> dict[str, str]:
    return {
        "path": rel_path,
        "sha256": file_sha256(rel_path),
        "selector": selector,
    }


def sanitize_learner_context(ctx: dict[str, Any]) -> dict[str, Any]:
    """Ensure learner_context contains only student-history fields and never desired errors."""
    clean: dict[str, Any] = {}
    for k in ("grade", "subject", "jurisdiction", "country", "age_range", "topic"):
        if k in ctx and ctx[k] is not None:
            clean[k] = ctx[k]
    raw_priors = ctx.get("assumed_prior_knowledge") or []
    priors = []
    for item in raw_priors:
        if isinstance(item, str):
            r = item.strip()
            priors.append({"resource": r, "taught_as": r})
        elif isinstance(item, dict) and isinstance(item.get("resource"), str):
            # Explicitly strip student_move, falls_short_because, relevance, etc.
            r = item["resource"].strip()
            ta = item.get("taught_as")
            ta_str = ta.strip() if isinstance(ta, str) and ta.strip() else r
            priors.append(
                {
                    "resource": r,
                    "taught_as": ta_str,
                }
            )
    if not priors:
        raise ValueError(f"Empty assumed_prior_knowledge in {ctx}")
    clean["assumed_prior_knowledge"] = priors
    return clean


# Explicit role classification and literature RSM enrichments for calibration_pack cases.
EXPERT_PF_APPROACH_SPECS: dict[str, list[dict[str, Any]]] = {
    "expert_bicycle": [
        {
            "approach_id": "equal_or_speed_ratio_partition",
            "name": "Single speed-ratio or equal-distance partition (50/50 or 4:3 / 5:3)",
            "role": "baseline_trap",
            "action_definition": (
                "Divide the 5 km remaining distance equally (2.5 km each) or by a single biking "
                "(4:3, x=20/7 km) or walking (5:3) speed ratio, compute both full travel times, "
                "and show that Hady and Jasmine do not arrive at the same time."
            ),
            "expected_limitation": (
                "Walking speed ratio (5:3) differs from biking speed ratio (4:3), so a single-ratio "
                "or equal split leaves unequal total arrival times."
            ),
            "resources_used": ["speed = distance / time", "ratio and proportion"],
            "provenance_kind": "paper_coded_rsm",
            "source_file": KAPUR_YAML,
            "selector": "exercises[id=kapur2012_complex_1].expected_student_rsms[Ratios method]",
        },
        {
            "approach_id": "lcm_hcf_distance_scaling",
            "name": "LCM/HCF common-distance or time-block scaling",
            "role": "baseline_trap",
            "action_definition": (
                "Use the LCM of speeds (such as 600 m blocks) to step through distances/times and "
                "check whether whole blocks partition the 5,000 m remaining distance with equal times."
            ),
            "expected_limitation": (
                "LCM of biking speeds (600 m) does not evenly partition the 5,000 m remaining "
                "distance into an exact simultaneous arrival without fractional adjustment."
            ),
            "resources_used": ["LCM and HCF", "speed = distance / time"],
            "provenance_kind": "paper_coded_rsm",
            "source_file": KAPUR_YAML,
            "selector": "exercises[id=kapur2012_complex_1].expected_student_rsms[LCM/HCF method]",
        },
        {
            "approach_id": "checked_trial_or_equal_time_coordination",
            "name": "Systematic trial-and-check or equal-travel-time coordination (x = 17/5 or 85/26 km)",
            "role": "resolving_route",
            "action_definition": (
                "Test candidate handover distances x or equate Jasmine's bike+walk time with Hady's "
                "walk+bike time under an explicit shared-bike speed assumption (reaching x = 17/5 = "
                "3.4 km at 0.15 km/min, or x = 85/26 ≈ 3.27 km if Hady's bike runs at 0.20 km/min)."
            ),
            "expected_limitation": None,
            "resources_used": ["speed = distance / time", "trial and error heuristic"],
            "provenance_kind": "paper_coded_rsm",
            "source_file": KAPUR_YAML,
            "selector": "exercises[id=kapur2012_complex_1].expected_student_rsms[Trial and Error A/B]",
        },
        {
            "approach_id": "remaining_distance_and_sketch_setup",
            "name": "Initial segment subtraction (8.75 - 3.75 = 5 km) and distance-time representation",
            "role": "shared_setup_or_representation",
            "action_definition": (
                "Compute total distance 75*7/60 = 8.75 km, distance already biked 0.15*25 = 3.75 km, "
                "remaining distance 5 km, and represent Jasmine's bike-then-walk versus Hady's walk-then-bike."
            ),
            "expected_limitation": None,
            "resources_used": ["speed = distance / time"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "development[case_id=expert_bicycle].expected_familiar_approaches[0,3]",
        },
    ],
    "expert_consistency": [
        {
            "approach_id": "mean_comparison_baseline",
            "name": "Arithmetic mean comparison across players",
            "role": "baseline_trap",
            "action_definition": (
                "Compute the 5-year arithmetic mean for Mike (14), Dave (14), and Ivan (15) and note "
                "that Mike and Dave tie at 14 (and mean measures central level rather than spread)."
            ),
            "expected_limitation": (
                "Mike and Dave tie with mean 14, and arithmetic mean measures average scoring level "
                "rather than year-to-year consistency."
            ),
            "resources_used": ["Arithmetic mean and range of a numerical data set"],
            "provenance_kind": "paper_coded_rsm",
            "source_file": LOIBL_YAML,
            "selector": "exercises[id=loibl2014_invention_1].expected_student_solutions[Mean comparison]",
        },
        {
            "approach_id": "range_max_minus_min_baseline",
            "name": "Range (max - min) comparison",
            "role": "baseline_trap",
            "action_definition": (
                "Compute each player's range (Mike 17-12=5, Dave 16-12=4, Ivan 18-10=8) and identify "
                "that max - min uses only two extreme years, violating condition (2) to use all data points."
            ),
            "expected_limitation": (
                "Range uses only the maximum and minimum values, violating the explicit task "
                "requirement to make use of all 5 data points."
            ),
            "resources_used": ["Arithmetic mean and range of a numerical data set"],
            "provenance_kind": "paper_coded_rsm",
            "source_file": STRATL_SUB_YAML,
            "selector": "exercises[id=puech2025_consistency].expected_student_rsms[Range (max - min)]",
        },
        {
            "approach_id": "signed_deviations_from_mean",
            "name": "Signed deviations from the mean summing to zero",
            "role": "baseline_trap",
            "action_definition": (
                "Subtract each player's mean from all 5 yearly scores and sum the signed differences, "
                "showing they cancel out to 0 for every player."
            ),
            "expected_limitation": (
                "Positive and negative deviations from the arithmetic mean cancel to 0 for every player."
            ),
            "resources_used": [
                "Addition, subtraction, multiplication and division of whole numbers and decimals",
                "Arithmetic mean and range of a numerical data set",
            ],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "development[case_id=expert_consistency].expected_familiar_approaches[2]",
        },
        {
            "approach_id": "all_data_unsigned_or_consecutive_deviation_measure",
            "name": "Constructed all-data unsigned deviation measure (MAD / squared deviations / year-to-year changes)",
            "role": "resolving_route",
            "action_definition": (
                "Aggregate unsigned deviations across all 5 years—either absolute deviations from the "
                "mean (totals 8, 6, 12 or MAD 1.6, 1.2, 2.4), squared deviations from the mean "
                "(16, 10, 44; variances 3.2, 2.0, 8.8), or consecutive year-to-year absolute changes "
                "(10, 8, 15)—identifying Dave as most consistent."
            ),
            "expected_limitation": None,
            "resources_used": [
                "Addition, subtraction, multiplication and division of whole numbers and decimals",
                "Arithmetic mean and range of a numerical data set",
            ],
            "provenance_kind": "paper_coded_rsm",
            "source_file": STRATL_SUB_YAML,
            "selector": "exercises[id=puech2025_consistency].expected_student_rsms[Mean absolute/squared/year-to-year]",
        },
    ],
    "expert_country": [
        {
            "approach_id": "exact_quota_ordinary_rounding",
            "name": "Proportional quota with standard nearest-integer rounding (sums to 251 != 250)",
            "role": "baseline_trap",
            "action_definition": (
                "Compute total population 12,500,000, standard divisor 50,000 people/seat, exact quotas "
                "(32.92, 138.72, 3.08, 41.82, 13.70, 19.76), and apply standard nearest-integer rounding "
                "(33, 139, 3, 42, 14, 20), showing the rounded total is 251 seats instead of 250."
            ),
            "expected_limitation": (
                "Standard nearest-integer rounding of the six proportional quotas sums to 251 seats, "
                "violating the fixed 250-seat legislature constraint."
            ),
            "resources_used": ["Fractions, proportions and rounding decimal quantities"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "development[case_id=expert_country].expected_familiar_approaches[0]",
        },
        {
            "approach_id": "equal_seat_split_or_floor_truncation",
            "name": "Unweighted equal division across states (250/6) or unadjusted integer floors (246 seats)",
            "role": "baseline_trap",
            "action_definition": (
                "Test dividing 250 seats equally among the 6 states (41.67 seats each, ignoring "
                "populations from 154,000 to 6,936,000) or taking integer floors (32+138+3+41+13+19 = 246 "
                "seats, leaving 4 seats unassigned)."
            ),
            "expected_limitation": (
                "Equal division ignores the 45-to-1 population disparity, and integer truncation alone "
                "allocates only 246 of the 250 seats."
            ),
            "resources_used": ["Fractions, proportions and rounding decimal quantities"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "development[case_id=expert_country].expected_familiar_approaches[1]",
        },
        {
            "approach_id": "largest_remainder_or_modified_divisor",
            "name": "Largest-remainder (Hamilton) or adjusted-threshold allocation totaling 250 seats",
            "role": "resolving_route",
            "action_definition": (
                "Assign integer floors totaling 246 seats and award the 4 surplus seats to the states "
                "with the largest decimal remainders (.92, .82, .76, .72 -> A, D, F, B), yielding "
                "33, 139, 3, 42, 13, 20 = 250 seats."
            ),
            "expected_limitation": None,
            "resources_used": ["Fractions, proportions and rounding decimal quantities"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "development[case_id=expert_country].expected_familiar_approaches[2]",
        },
    ],
    "expert_land": [
        {
            "approach_id": "greedy_whole_piece_standoff",
            "name": "Greedy whole-piece assignment at the $250 fair-share threshold",
            "role": "baseline_trap",
            "action_definition": (
                "Identify each player's fair share ($1,000 / 4 = $250) and acceptable pieces "
                "(Andrea {2,4}, Beatrice {2,4}, Cleo {2}, David {1,2,3,4}), assign David piece 3 and "
                "Andrea/Beatrice piece 4, and show the standoff where both remaining players require "
                "piece 2 while nobody except David accepts piece 1."
            ),
            "expected_limitation": (
                "Three players (Andrea, Beatrice, Cleo) accept only pieces from {2, 4}, so whole-piece "
                "assignment cannot give all four players a piece worth >= $250."
            ),
            "resources_used": ["Concept of fairness (>= 1/n of total value)", "Basic division"],
            "provenance_kind": "paper_coded_rsm",
            "source_file": KERRIGAN_YAML,
            "selector": "exercises[id=kerrigan2021_invention_1].expected_student_behaviors[0..3]",
        },
        {
            "approach_id": "recombine_and_divider_chooser",
            "name": "Recombine pieces 1 and 2 (or fractional piece split) with Divider-Chooser",
            "role": "resolving_route",
            "action_definition": (
                "Give David piece 3 ($250) and Andrea piece 4 ($350), then combine unclaimed piece 1 "
                "and contested piece 2 (worth $550 to Beatrice and $650 to Cleo) and apply the taught "
                "two-person Divider-Chooser method (or proportional split) so every player receives >= $250."
            ),
            "expected_limitation": None,
            "resources_used": [
                "Divider-Chooser method (learned previously)",
                "Concept of fairness (>= 1/n of total value)",
            ],
            "provenance_kind": "paper_coded_rsm",
            "source_file": KERRIGAN_YAML,
            "selector": "exercises[id=kerrigan2021_invention_1].solution",
        },
    ],
    "expert_time_sharing": [
        {
            "approach_id": "equal_calendar_half_split",
            "name": "Equal 6-month calendar split (Jan-Jun vs Jul-Dec)",
            "role": "baseline_trap",
            "action_definition": (
                "Compute full-year values (Ann $140,000, fair share $70,000; Bob $108,000, fair share "
                "$54,000) and test a 6-month calendar split (Jan-Jun vs Jul-Dec), showing Ann values "
                "Jan-Jun at only $60,000 < $70,000."
            ),
            "expected_limitation": (
                "An equal 6-month calendar split leaves Ann with $60,000 in Jan-Jun, which is below "
                "her $70,000 fair-share threshold."
            ),
            "resources_used": ["Fractions of a total and an equal fair share"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "development[case_id=expert_time_sharing].expected_familiar_approaches[0]",
        },
        {
            "approach_id": "valuation_balanced_switch_cut",
            "name": "Valuation-balanced switch date (cut after July: Ann $70k/$70k, Bob picks Aug-Dec $60k)",
            "role": "resolving_route",
            "action_definition": (
                "Have Ann propose a switch after July so Jan-Jul ($70,000) and Aug-Dec ($70,000) are "
                "both worth exactly half of her $140,000 total; Bob then selects Aug-Dec (worth $60,000 "
                ">= $54,000 to him) and Ann takes Jan-Jul ($70,000)."
            ),
            "expected_limitation": None,
            "resources_used": ["Fractions of a total and an equal fair share"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "development[case_id=expert_time_sharing].expected_familiar_approaches[1]",
        },
    ],
    "expert_hummingbird": [
        {
            "approach_id": "flying_speed_only_without_rest",
            "name": "Compare active flying speeds/flap rates without rest cycles",
            "role": "baseline_trap",
            "action_definition": (
                "Compare Giant Hummingbird's active flapping rate (70-80 flaps/min) directly against "
                "Broad-tailed Hummingbird's active rate (100-125 flaps/min) while ignoring their "
                "different rest schedules (18h flight / 6h rest vs 12h flight / 12h rest)."
            ),
            "expected_limitation": (
                "Active flying speed ignores that Giant flies 18/24 (75%) of each day while Broad-tailed "
                "flies only 12/24 (50%) of each day, reversing who covers more distance per day at "
                "several rates in the given ranges."
            ),
            "resources_used": ["Speed equals distance divided by time"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_hummingbird].expected_familiar_approaches[0]",
        },
        {
            "approach_id": "effective_wall_clock_journey_rate",
            "name": "Effective daily/wall-clock distance rate accounting for flight-to-rest duty cycle",
            "role": "resolving_route",
            "action_definition": (
                "Scale active flap/distance rates by the active fraction of a 24-hour cycle "
                "(18/24 = 0.75 for Giant -> 52.5 to 60 flaps/min effective; 12/24 = 0.50 for Broad-tailed "
                "-> 50 to 62.5 flaps/min effective), convert via 550 flaps/km over 9,000 km, and "
                "compare the resulting arrival times/ranges."
            ),
            "expected_limitation": None,
            "resources_used": [
                "Speed equals distance divided by time",
                "Converting minutes and hours and comparing simple ratios",
            ],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_hummingbird].expected_familiar_approaches[1]",
        },
    ],
    "expert_tea": [
        {
            "approach_id": "observed_mean_and_range_tie",
            "name": "Observed arithmetic mean (15) and range (10) across tea brands",
            "role": "baseline_trap",
            "action_definition": (
                "Compute the arithmetic mean (15, 15, 15) and range max - min (20-10 = 10 for all three "
                "brands) over the available observations, showing that both mean and range tie completely."
            ),
            "expected_limitation": (
                "All three tea varieties have the exact same observed mean (15) and range (10), so "
                "neither baseline can distinguish their consistency."
            ),
            "resources_used": ["Arithmetic mean and range of a numerical data set"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_tea].expected_familiar_approaches[0]",
        },
        {
            "approach_id": "sample_size_normalized_deviation_measure",
            "name": "All-observation deviation measure normalized by observation count (n=5 vs n=6)",
            "role": "resolving_route",
            "action_definition": (
                "Compute absolute or squared deviations from the mean (56, 62, 72 squared or 14, 18, 20 "
                "absolute) and divide by the number of available observations (5 for Thourbo, 6 for "
                "Darjeeling and Lapsang) so the missing 2010 entry does not artificially reward Thourbo."
            ),
            "expected_limitation": None,
            "resources_used": [
                "Addition, subtraction, multiplication and division of whole numbers and decimals",
                "Arithmetic mean and range of a numerical data set",
            ],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_tea].expected_familiar_approaches[1]",
        },
    ],
    "expert_goals": [
        {
            "approach_id": "raw_goal_count_comparison",
            "name": "Compare raw goal totals (5 boys' goals > 3 girls' goals) ignoring team size",
            "role": "baseline_trap",
            "action_definition": (
                "Compare the raw number of goals scored (5 goals by boys versus 3 goals by girls) "
                "without normalizing for the unequal group sizes (10 boys vs 5 girls)."
            ),
            "expected_limitation": (
                "Comparing raw totals (5 > 3) ignores that twice as many boys (10) took shots as girls (5)."
            ),
            "resources_used": ["Reading tables and comparing numerical quantities"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_goals].expected_familiar_approaches[0]",
        },
        {
            "approach_id": "common_whole_fraction_bar_comparison",
            "name": "Common-whole fraction comparison (3/5 = 6/10 > 5/10) with graphical bars",
            "role": "resolving_route",
            "action_definition": (
                "Represent girls' success as 3/5 (or 6/10 by doubling/subdividing equal-length fraction "
                "bars) and boys' success as 5/10 = 1/2, showing girls had the better rate (6/10 > 5/10)."
            ),
            "expected_limitation": None,
            "resources_used": [
                "Equal sharing, fractions as parts of a whole and drawing fraction bars"
            ],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_goals].expected_familiar_approaches[1]",
        },
    ],
    "expert_pizza": [
        {
            "approach_id": "raw_pizza_total_comparison",
            "name": "Compare total pizzas (4 pizzas > 2 pizzas) ignoring group size",
            "role": "baseline_trap",
            "action_definition": (
                "Compare the total number of pizzas given to each group (4 pizzas for boys versus 2 "
                "pizzas for girls) without dividing by the 6 boys and 3 girls."
            ),
            "expected_limitation": (
                "Comparing raw pizza counts (4 > 2) ignores that 6 boys share the 4 pizzas while 3 "
                "girls share the 2 pizzas."
            ),
            "resources_used": ["Reading tables and comparing numerical quantities"],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_pizza].expected_familiar_approaches[0]",
        },
        {
            "approach_id": "per_person_share_and_grouping_equivalence",
            "name": "Equal-share fraction division and sub-group partitioning (4/6 = 2/3)",
            "role": "resolving_route",
            "action_definition": (
                "Divide pizzas by people (4/6 for each boy, 2/3 for each girl) and/or split the 6 boys "
                "with 4 pizzas into two groups of 3 boys with 2 pizzas each, proving both shares are "
                "exactly 2/3 of a pizza."
            ),
            "expected_limitation": None,
            "resources_used": [
                "Equal sharing and fractions as division; drawing equal-size wholes"
            ],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_pizza].expected_familiar_approaches[1]",
        },
    ],
    "expert_furniture": [
        {
            "approach_id": "goods_only_highest_bidder_allocation",
            "name": "Goods-only highest-bidder or one-item-each assignment without cash transfers",
            "role": "baseline_trap",
            "action_definition": (
                "Compute each roommate's 1/3 fair-share threshold (Ashley $750/3=$250, Bill $900/3=$300, "
                "Cliff $675/3=$225) and assign indivisible items to highest bidders (Ashley chair $175, "
                "Bill table+dresser+couch $750, Cliff $0), showing goods alone leave Ashley ($175 < $250) "
                "and Cliff ($0 < $225) below their fair shares."
            ),
            "expected_limitation": (
                "Because the four furniture items are indivisible and Bill values three of them highest, "
                "assigning items without cash leaves Cliff with $0 and Ashley below $250."
            ),
            "resources_used": ["Basic division and arithmetic", "Concept of fairness"],
            "provenance_kind": "paper_coded_rsm",
            "source_file": KERRIGAN_YAML,
            "selector": "exercises[id=kerrigan2021_invention_2].solution[Step 1..2]",
        },
        {
            "approach_id": "sealed_bids_cash_compensation_with_surplus",
            "name": "Cash-compensated allocation with equal division of the $150 surplus",
            "role": "resolving_route",
            "action_definition": (
                "Assign each item to its highest bidder (Ashley chair $175, Bill table+dresser+couch "
                "$750, Cliff none), have Bill pay his $450 excess into a pool, pay Ashley $75 and Cliff "
                "$225 to reach their 1/3 fair shares, and split the remaining $150 surplus ($50 each) "
                "so net cash is Ashley +$125, Bill -$400, Cliff +$275."
            ),
            "expected_limitation": None,
            "resources_used": ["Basic division and arithmetic", "Concept of fairness"],
            "provenance_kind": "paper_coded_rsm",
            "source_file": KERRIGAN_YAML,
            "selector": "exercises[id=kerrigan2021_invention_2].solution[Step 3..5]",
        },
    ],
    "expert_braking_collision": [
        {
            "approach_id": "constant_speed_or_stuck_speedometer_baseline",
            "name": "Constant-speed d = v*t or taking the 24 km/h impact reading as initial speed",
            "role": "baseline_trap",
            "action_definition": (
                "Apply constant-speed d = v*t (or treat the truck's 24 km/h speedometer reading at "
                "collision as its pre-braking speed) and explain why constant speed mismodels a "
                "decelerating braking phase."
            ),
            "expected_limitation": (
                "The 24 km/h reading is the speed at impact after 2 seconds of braking, not the initial "
                "pre-braking speed, and d = v*t with constant speed ignores deceleration."
            ),
            "resources_used": [
                "Speed as distance divided by time and conversion between m/s and km/h"
            ],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_braking_collision].expected_familiar_approaches[1]",
        },
        {
            "approach_id": "deceleration_and_average_velocity_reconstruction",
            "name": "Reconstruct pre-braking speeds from deceleration changes and velocity-time area",
            "role": "resolving_route",
            "action_definition": (
                "Use acceleration as change in speed per second and average speed during uniform "
                "deceleration (or velocity-time sketch) to reconstruct initial pre-braking speeds "
                "and compare them against the 40 km/h (11.11 m/s) limit."
            ),
            "expected_limitation": None,
            "resources_used": [
                "Speed as distance divided by time and conversion between m/s and km/h",
                "Acceleration as change in speed per second",
                "Reading a distance-time sketch; no constant-acceleration distance law yet",
            ],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_braking_collision].expected_familiar_approaches[2]",
        },
    ],
    "expert_braking_lawyer": [
        {
            "approach_id": "skid_divided_by_reaction_time_baseline",
            "name": "Divide 15 m skid distance by 0.8 s reaction time (15 / 0.8 = 18.75 m/s = 67.5 km/h)",
            "role": "baseline_trap",
            "action_definition": (
                "Apply speed = distance / time directly to the 15 m skid mark and the 0.8 s reaction "
                "time (15 / 0.8 = 18.75 m/s = 67.5 km/h > 55 km/h) and note that 15 m occurred during "
                "braking, not during the 0.8 s reaction phase, and braking speed is not constant."
            ),
            "expected_limitation": (
                "The 0.8 s is reaction time before the brakes lock, whereas the 15 m skid happens "
                "during decelerating braking after reaction."
            ),
            "resources_used": [
                "Speed as distance divided by time and conversion between m/s and km/h"
            ],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_braking_lawyer].expected_familiar_approaches[0]",
        },
        {
            "approach_id": "frictional_deceleration_speed_bound",
            "name": "Reconstruct pre-skid speed from frictional deceleration a = mu*g (5.88 to 6.86 m/s^2)",
            "role": "resolving_route",
            "action_definition": (
                "Compute deceleration a = mu*g for mu in [0.6, 0.7] (5.88 to 6.86 m/s^2) and relate "
                "change in speed to the 15 m braking distance (yielding ~13.3 to 14.3 m/s = 47.8 to "
                "51.6 km/h < 55 km/h)."
            ),
            "expected_limitation": None,
            "resources_used": [
                "Speed as distance divided by time and conversion between m/s and km/h",
                "Acceleration as change in speed per second",
                "Frictional deceleration magnitude is coefficient of friction times g",
            ],
            "provenance_kind": "calibration_pack_witness",
            "source_file": "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
            "selector": "transfer[case_id=expert_braking_lawyer].expected_familiar_approaches[1,2]",
        },
    ],
}


def build_cohort_1_and_2() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pack = json.loads(CALIBRATION_PACK.read_text(encoding="utf-8"))
    expert_pf_cases: list[dict[str, Any]] = []
    routine_control_cases: list[dict[str, Any]] = []

    all_pack_cases = pack["development"] + pack["transfer"] + pack["controls"]
    for c in all_pack_cases:
        cid = c["case_id"]
        # Skip the 3 unassessable controls where the solver is intentionally not run or has 0 approaches
        if cid in (
            "control_inaccessible",
            "control_missing_task_context",
            "control_missing_history",
        ):
            continue
        # Skip the 2 grounding_r01 cases here so they sit cleanly in Cohort 6 without duplication
        if cid in (
            "grounding_scientific_scale_comparison_r01_A",
            "grounding_signed_product_ledger_r01_A",
        ):
            continue

        clean_ctx = sanitize_learner_context(c["learner_context"])
        lim_ref = c["references"]["familiar_approach_limits"]["value"]
        inv_ref = c["references"]["room_for_invention"]["value"]

        # Check if cached v3.0 evaluation job exists
        cached_sub = (
            "full_dev_jobs" if c["split"] in ("development", "control") else "transfer_jobs"
        )
        cached_path = V30_CALIB_DIR / cached_sub / f"{cid}.json"
        cached_rel = cached_path.relative_to(ROOT).as_posix() if cached_path.exists() else None

        if cid in EXPERT_PF_APPROACH_SPECS:
            ref_approaches = []
            for spec in EXPERT_PF_APPROACH_SPECS[cid]:
                ref_approaches.append(
                    {
                        "approach_id": spec["approach_id"],
                        "name": spec["name"],
                        "role": spec["role"],
                        "action_definition": spec["action_definition"],
                        "expected_limitation": spec["expected_limitation"],
                        "resources_used": spec["resources_used"],
                        "provenance_kind": spec["provenance_kind"],
                        "source": make_source(spec["source_file"], spec["selector"]),
                    }
                )
            expert_pf_cases.append(
                {
                    "case_id": cid,
                    "cohort": "expert_pf",
                    "split": c["split"],
                    "family": c["family"],
                    "topic": c["family"],
                    "student_task": c["student_task"],
                    "learning_target": c["learning_target"],
                    "learner_context": clean_ctx,
                    "solver_input": {
                        "student_task": c["student_task"],
                        "learner_context": copy.deepcopy(clean_ctx),
                    },
                    "expected_limits_verdict": lim_ref,
                    "expected_invention_verdict": inv_ref,
                    "cached_v30_eval_path": cached_rel,
                    "reference_approaches": ref_approaches,
                }
            )
        else:
            # Routine textbook, prescribed formula, or diagnostic control task
            ref_approaches = []
            for idx, a in enumerate(c.get("expected_familiar_approaches", [])):
                role = (
                    "diagnostic_control_check"
                    if cid
                    in (
                        "garden_composite_area__gpt5mini__028",
                        "garden_composite_area__gpt41__019",
                        "control_mathematical_contradiction",
                        "control_unproved_universal_claim",
                    )
                    else "routine_solution"
                )
                ref_approaches.append(
                    {
                        "approach_id": f"{cid}__ref_{idx + 1}",
                        "name": a["idea"],
                        "role": role,
                        "action_definition": a["checkable_action"],
                        "expected_limitation": (
                            "Task contains a geometric contradiction, unlisted hexagon-root skill, "
                            "or open universal conjecture."
                            if role == "diagnostic_control_check"
                            else None
                        ),
                        "resources_used": [
                            r["resource"] for r in clean_ctx["assumed_prior_knowledge"]
                        ],
                        "provenance_kind": "calibration_pack_witness",
                        "source": make_source(
                            "experiments/results/pf_measure_campaign_20261014/calibration_pack.json",
                            f"{c['split']}[case_id={cid}].expected_familiar_approaches[{idx}]",
                        ),
                    }
                )
            routine_control_cases.append(
                {
                    "case_id": cid,
                    "cohort": "routine_and_control",
                    "split": c["split"],
                    "family": c["family"],
                    "topic": c["family"],
                    "student_task": c["student_task"],
                    "learning_target": c["learning_target"],
                    "learner_context": clean_ctx,
                    "solver_input": {
                        "student_task": c["student_task"],
                        "learner_context": copy.deepcopy(clean_ctx),
                    },
                    "expected_limits_verdict": lim_ref,
                    "expected_invention_verdict": inv_ref,
                    "cached_v30_eval_path": cached_rel,
                    "reference_approaches": ref_approaches,
                }
            )

    return expert_pf_cases, routine_control_cases


def _catalog_lookup() -> dict[str, dict[str, Any]]:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    by_path: dict[str, dict[str, Any]] = {}
    for c in cat["cases"]:
        for occ in c.get("occurrences", []):
            p = occ.get("source", {}).get("path", "")
            if p.endswith("result.json"):
                by_path[p] = c
    return by_path


def _brief_approaches_from_result(
    rel_result_path: str,
    selected_brief: dict[str, Any],
    extra_audited_paths: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    approaches: list[dict[str, Any]] = []
    for idx, app in enumerate(selected_brief.get("approaches") or []):
        first_action = str(app.get("first_action", "")).strip()
        establishes = str(app.get("what_it_establishes", "")).strip()
        limitation = str(app.get("limitation", "")).strip()
        resources = [str(r).strip() for r in (app.get("resources") or []) if str(r).strip()]
        approaches.append(
            {
                "approach_id": f"brief_baseline_{idx + 1}",
                "name": first_action[:90] + ("..." if len(first_action) > 90 else ""),
                "role": "baseline_trap",
                "action_definition": f"{first_action} (Establishes: {establishes})",
                "expected_limitation": limitation or None,
                "resources_used": resources,
                "provenance_kind": "pre_generation_design_brief",
                "source": make_source(
                    rel_result_path,
                    f"$.stages.D2_D3.brief_selection.selected_brief.approaches[{idx}]",
                ),
            }
        )
    succ = str(selected_brief.get("successful_route") or "").strip()
    if succ:
        approaches.append(
            {
                "approach_id": "brief_resolving_route",
                "name": "Coordinated resolving route from design brief",
                "role": "resolving_route",
                "action_definition": succ,
                "expected_limitation": None,
                "resources_used": [],
                "provenance_kind": "pre_generation_design_brief",
                "source": make_source(
                    rel_result_path,
                    "$.stages.D2_D3.brief_selection.selected_brief.successful_route",
                ),
            }
        )
    if extra_audited_paths:
        for p in extra_audited_paths:
            if p.get("kind") == "representation":
                role = "shared_setup_or_representation"
            elif p["id"] == "successful_route_reference":
                continue  # already captured by brief_resolving_route
            else:
                continue
            approaches.append(
                {
                    "approach_id": f"audited_{p['id']}",
                    "name": p["id"],
                    "role": role,
                    "action_definition": p["operational_definition"],
                    "expected_limitation": None,
                    "resources_used": [],
                    "provenance_kind": "audited_path_codebook",
                    "source": make_source(
                        "experiments/results/pf_path_coverage_final_20261012/baseline_coverage.json",
                        f"$.tasks..paths[id={p['id']}]",
                    ),
                }
            )
    return approaches


def build_cohort_3_pipeline_r1(by_path: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    bc = json.loads(BASELINE_COVERAGE.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for task_id, task_info in sorted(bc["tasks"].items()):
        rel_path = task_info["source"]
        cat_case = by_path[rel_path]
        res_data = json.loads((ROOT / rel_path).read_text(encoding="utf-8"))
        sb = res_data["stages"]["D2_D3"]["brief_selection"]["selected_brief"]
        clean_ctx = sanitize_learner_context(cat_case["learner_context"])
        cat_cid = cat_case["case_id"]
        cached_path = V30_CALIB_DIR / "generated_jobs" / f"{cat_cid}.json"
        cached_rel = cached_path.relative_to(ROOT).as_posix() if cached_path.exists() else None

        family = Path(rel_path).parts[-4]
        ref_approaches = _brief_approaches_from_result(rel_path, sb, task_info.get("paths"))
        cases.append(
            {
                "case_id": f"r1_{task_id}",
                "catalog_case_id": cat_cid,
                "cohort": "pipeline_r1_audited",
                "split": "generated_r1",
                "family": family,
                "topic": family,
                "student_task": cat_case["student_task"],
                "learning_target": cat_case["learning_target"],
                "learner_context": clean_ctx,
                "solver_input": {
                    "student_task": cat_case["student_task"],
                    "learner_context": copy.deepcopy(clean_ctx),
                },
                "expected_limits_verdict": "design_intended_pf",
                "expected_invention_verdict": "yes",
                "cached_v30_eval_path": cached_rel,
                "reference_approaches": ref_approaches,
            }
        )
    return cases


def build_cohort_4_pipeline_r2() -> list[dict[str, Any]]:
    eval_dir = ROOT / "experiments/results/pf_pipeline_lc_impasse_v3_20261015/evaluations"
    gen_dir = ROOT / "experiments/results/pf_pipeline_lc_impasse_v3_20261015/generation"
    cases: list[dict[str, Any]] = []
    for eval_path in sorted(eval_dir.glob("*.json")):
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
        key = ev["key"]  # e.g. kapur_average_speed__001
        family, num = key.split("__")
        gen_res_path = gen_dir / family / num / "result.json"
        rel_gen_path = gen_res_path.relative_to(ROOT).as_posix()
        gen_data = json.loads(gen_res_path.read_text(encoding="utf-8"))
        sb = gen_data["stages"]["D2_D3"]["brief_selection"]["selected_brief"]

        inp = ev["v29"]["task_judge"]["input"]
        clean_ctx = sanitize_learner_context(inp["learner_context"])
        cached_path = V30_CALIB_DIR / "lc_pipeline_jobs" / f"{key}.json"
        cached_rel = cached_path.relative_to(ROOT).as_posix() if cached_path.exists() else None

        ref_approaches = _brief_approaches_from_result(rel_gen_path, sb)
        cases.append(
            {
                "case_id": f"r2_lc_{key}",
                "cohort": "pipeline_r2_lc_impasse",
                "split": "generated_r2",
                "family": family,
                "topic": family,
                "student_task": inp["student_task"],
                "learning_target": inp["learning_target"],
                "learner_context": clean_ctx,
                "solver_input": {
                    "student_task": inp["student_task"],
                    "learner_context": copy.deepcopy(clean_ctx),
                },
                "expected_limits_verdict": "design_intended_pf",
                "expected_invention_verdict": "yes",
                "cached_v30_eval_path": cached_rel,
                "reference_approaches": ref_approaches,
            }
        )
    return cases


def build_cohort_5_topic_sweep(by_path: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    sweep_dir = ROOT / "experiments/results/pf_topic_sweep_20261011/final_20"
    cases: list[dict[str, Any]] = []
    for res_path in sorted(sweep_dir.glob("*/result.json")):
        rel_path = res_path.relative_to(ROOT).as_posix()
        if rel_path not in by_path:
            continue
        cat_case = by_path[rel_path]
        res_data = json.loads(res_path.read_text(encoding="utf-8"))
        sb = res_data["stages"]["D2_D3"]["brief_selection"]["selected_brief"]
        case_inp = res_data.get("case_input") or {}
        topic_id = case_inp.get("id") or res_path.parent.name
        clean_ctx = sanitize_learner_context(cat_case["learner_context"])

        ref_approaches = _brief_approaches_from_result(rel_path, sb)
        cases.append(
            {
                "case_id": f"sweep_{topic_id}",
                "catalog_case_id": cat_case["case_id"],
                "cohort": "pipeline_topic_sweep",
                "split": "topic_sweep_final20",
                "family": topic_id,
                "topic": case_inp.get("topic") or topic_id,
                "student_task": cat_case["student_task"],
                "learning_target": cat_case["learning_target"],
                "learner_context": clean_ctx,
                "solver_input": {
                    "student_task": cat_case["student_task"],
                    "learner_context": copy.deepcopy(clean_ctx),
                },
                "expected_limits_verdict": "design_intended_pf",
                "expected_invention_verdict": "yes",
                "cached_v30_eval_path": None,
                "reference_approaches": ref_approaches,
            }
        )
    return cases


def build_cohort_6_grounding_study(by_path: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    grounding_dir = ROOT / "experiments/results/pf_grounding_study_20261013/attempts/main"
    cases: list[dict[str, Any]] = []
    for res_path in sorted(grounding_dir.glob("*/r01/*/result.json")):
        rel_path = res_path.relative_to(ROOT).as_posix()
        cat_case = by_path[rel_path]
        res_data = json.loads(res_path.read_text(encoding="utf-8"))
        sb = res_data["stages"]["D2_D3"]["brief_selection"]["selected_brief"]
        parts = res_path.parts
        topic_id = parts[-4]
        rep = parts[-3]
        arm = parts[-2]
        clean_ctx = sanitize_learner_context(cat_case["learner_context"])

        cid = f"grounding_{topic_id}_{rep}_{arm}"
        cached_path = V30_CALIB_DIR / "transfer_jobs" / f"{cid}.json"
        cached_rel = cached_path.relative_to(ROOT).as_posix() if cached_path.exists() else None

        ref_approaches = _brief_approaches_from_result(rel_path, sb)
        cases.append(
            {
                "case_id": cid,
                "catalog_case_id": cat_case["case_id"],
                "cohort": "pipeline_grounding_study",
                "split": f"grounding_{arm}",
                "family": topic_id,
                "topic": topic_id,
                "student_task": cat_case["student_task"],
                "learning_target": cat_case["learning_target"],
                "learner_context": clean_ctx,
                "solver_input": {
                    "student_task": cat_case["student_task"],
                    "learner_context": copy.deepcopy(clean_ctx),
                },
                "expected_limits_verdict": (
                    "no"
                    if cid == "grounding_scientific_scale_comparison_r01_A"
                    else (
                        "yes"
                        if cid == "grounding_signed_product_ledger_r01_A"
                        else "design_intended_pf"
                    )
                ),
                "expected_invention_verdict": "yes",
                "cached_v30_eval_path": cached_rel,
                "reference_approaches": ref_approaches,
            }
        )
    return cases


def build_dataset() -> dict[str, Any]:
    by_path = _catalog_lookup()
    c1, c2 = build_cohort_1_and_2()
    c3 = build_cohort_3_pipeline_r1(by_path)
    c4 = build_cohort_4_pipeline_r2()
    c5 = build_cohort_5_topic_sweep(by_path)
    c6 = build_cohort_6_grounding_study(by_path)

    all_cases = c1 + c2 + c3 + c4 + c5 + c6

    cohort_counts = Counter(c["cohort"] for c in all_cases)
    role_counts = Counter(a["role"] for c in all_cases for a in c["reference_approaches"])
    prov_counts = Counter(
        a["provenance_kind"] for c in all_cases for a in c["reference_approaches"]
    )
    cached_count = sum(1 for c in all_cases if c.get("cached_v30_eval_path"))

    return {
        "schema_version": SCHEMA_VERSION,
        "purpose": (
            "Target-blind benchmark for evaluating the completeness (approach recall) and "
            "objectivity (routine-solve sensitivity) of the pf-three-role/v3.0 solver across "
            "published PF tasks, routine/control tasks, and multi-topic pipeline PF designs."
        ),
        "methodology": {
            "motivation": (
                "Because approach_limits and the empirical check of room_for_invention depend "
                "on the candidate approaches proposed by the solver, the evaluator is objective "
                "only if the solver reliably recovers (1) the direct prior-knowledge baseline "
                "traps (baseline_trap) and (2) the working resolving or routine routes "
                "(resolving_route / routine_solution) within its 4-approach budget."
            ),
            "target_blind_invariant": (
                "Every solver_input contains strictly {student_task, learner_context}. Neither "
                "learning_target, reference_approaches, selected_brief, nor source solutions "
                "ever enter solver_input. Every assumed_prior_knowledge item contains strictly "
                "{resource, taught_as} with no error hints or falls_short_because notes."
            ),
            "primary_metrics": {
                "complete_approach_recall": (
                    "Fraction of complete reference approaches (baseline_trap, resolving_route, "
                    "routine_solution, diagnostic_control_check) recovered by the solver."
                ),
                "baseline_trap_recall": (
                    "Fraction of reference baseline_trap approaches recovered on PF tasks."
                ),
                "resolving_route_recall": (
                    "Fraction of reference resolving_route approaches recovered on PF tasks."
                ),
                "routine_solution_recall": (
                    "Fraction of reference routine_solution approaches recovered on routine "
                    "tasks (testing that the solver does not fake failure on solvable exercises)."
                ),
                "task_level_dual_coverage": (
                    "Fraction of PF tasks where the solver recovers at least one baseline_trap "
                    "AND at least one resolving_route in the same 4-approach run."
                ),
            },
        },
        "summary_counts": {
            "total_tasks": len(all_cases),
            "distinct_topics": len({c["topic"] for c in all_cases}),
            "tasks_with_cached_v30_runs": cached_count,
            "total_reference_approaches": sum(len(c["reference_approaches"]) for c in all_cases),
            "primary_complete_approaches": sum(
                1
                for c in all_cases
                for a in c["reference_approaches"]
                if a["role"] in PRIMARY_COMPLETE_ROLES
            ),
            "tasks_by_cohort": dict(cohort_counts),
            "approaches_by_role": dict(role_counts),
            "approaches_by_provenance": dict(prov_counts),
        },
        "cases": all_cases,
    }


def verify_dataset(dataset: dict[str, Any]) -> None:
    if dataset.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unexpected schema_version")
    cases = dataset.get("cases") or []
    if not cases:
        raise ValueError("No cases in dataset")

    seen_ids: set[str] = set()
    seen_task_hashes: dict[str, str] = {}
    for c in cases:
        cid = c["case_id"]
        if cid in seen_ids:
            raise ValueError(f"Duplicate case_id: {cid}")
        seen_ids.add(cid)

        # Check non-overlap of identical (student_task, learner_context) pairs
        pair_hash = canonical_sha256(c["solver_input"])
        if pair_hash in seen_task_hashes:
            raise ValueError(
                f"Duplicate solver_input between {cid} and {seen_task_hashes[pair_hash]}"
            )
        seen_task_hashes[pair_hash] = cid

        # Verify strict target-blind solver_input invariant
        if set(c["solver_input"].keys()) != {"student_task", "learner_context"}:
            raise ValueError(f"Non-blind solver_input in {cid}: {list(c['solver_input'].keys())}")
        if not isinstance(c["student_task"], str) or not c["student_task"].strip():
            raise ValueError(f"Empty student_task in {cid}")
        priors = c["solver_input"]["learner_context"].get("assumed_prior_knowledge") or []
        if not priors:
            raise ValueError(f"Empty assumed_prior_knowledge in {cid}")
        for p in priors:
            if set(p.keys()) != {"resource", "taught_as"}:
                raise ValueError(f"Disallowed keys in assumed_prior_knowledge for {cid}: {p}")

        refs = c.get("reference_approaches") or []
        if not refs:
            raise ValueError(f"No reference_approaches in {cid}")
        seen_app_ids: set[str] = set()
        for a in refs:
            aid = a["approach_id"]
            if aid in seen_app_ids:
                raise ValueError(f"Duplicate approach_id {aid} in {cid}")
            seen_app_ids.add(aid)
            if a["role"] not in VALID_ROLES:
                raise ValueError(f"Invalid role {a['role']} in {cid}/{aid}")
            if not a.get("action_definition", "").strip():
                raise ValueError(f"Empty action_definition in {cid}/{aid}")
            src = a.get("source") or {}
            if not (ROOT / src.get("path", "")).is_file():
                raise ValueError(f"Missing source file {src} in {cid}/{aid}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify", action="store_true", help="Verify existing file without writing"
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    if args.verify:
        data = json.loads(args.output.read_text(encoding="utf-8"))
        verify_dataset(data)
        print(json.dumps(data["summary_counts"], indent=2))
        return

    data = build_dataset()
    verify_dataset(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output.relative_to(ROOT)} (sha256={file_sha256(args.output)[:16]}...)")
    print(json.dumps(data["summary_counts"], indent=2))


if __name__ == "__main__":
    main()

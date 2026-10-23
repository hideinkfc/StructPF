"""Run the 30-task expert-example ablation for StructPF (0 vs. 1 vs. 5 unrelated examples).

Tests whether injecting 1 or 5 published human-authored Productive Failure examples
from completely unrelated domains (game-theory fair division and physics braking/collision
kinematics; Kerrigan et al., 2021; Kapur, 2008; Puech et al., 2025) across Stage 2a
(design brief proposal & selection), Stage 2b (data & condition proposal), and Stage 3
(student task writing) improves StructPF task quality on a stratified 30-task slice of
the 4 Grade-7 Rahimi settings:
  - music_compare_distributions: repeats 001..007 (7 tasks)
  - garden_composite_area:       repeats 001..007 (7 tasks)
  - sports_basketball_ratio:     repeats 001..008 (8 tasks)
  - shopping_percent:            repeats 001..008 (8 tasks)

Reuses the frozen Stage D1 (`fixed_d1.json`) and `0_examples` baseline results from
`experiments/results/pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021`.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

from scripts import design_brief_stage, design_data_stage
from scripts import run_pf_diagnostic as diagnostic
from scripts.run_pf_accessibility_sensitivity import build_chats
from scripts.run_pf_newest_pipeline_rahimi_eval import (
    ROOT,
    SETTING_PATH,
    _build_cell_inputs,
    _has_v30_api_error,
    file_sha256,
    now,
    rate_one_table1,
    save_json,
    summarize_cohort_table1,
)
from src.evaluation import pf_three_role_v31 as v31
from src.evaluation.pf_task_measures import MEASURES

BASELINE_DIR = (
    ROOT / "experiments/results/pf_newest_pipeline_rahimi_eval_optA_v31_gpt5mini_20261021"
)
DEFAULT_OUTPUT = ROOT / "experiments/results/pf_expert_examples_ablation_30_20261021"

STRATIFIED_30_SLICE: dict[str, list[int]] = {
    "music_compare_distributions": list(range(1, 8)),  # 7 tasks
    "garden_composite_area": list(range(1, 8)),        # 7 tasks
    "sports_basketball_ratio": list(range(1, 9)),      # 8 tasks
    "shopping_percent": list(range(1, 9)),            # 8 tasks
}

BASE_BRIEF_PROMPTS: dict[str, str] = yaml.safe_load(
    design_brief_stage.PROMPTS_PATH.read_text(encoding="utf-8")
)
BASE_DATA_PROMPTS: dict[str, str] = yaml.safe_load(
    design_data_stage.PROMPTS_PATH.read_text(encoding="utf-8")
)

# ---------------------------------------------------------------------------
# 5 Published Human Expert PF Examples (Unrelated Topics: Game Theory & Physics)
# ---------------------------------------------------------------------------

EXPERT_EXAMPLES_D2A: list[dict[str, Any]] = [
    # 1. Land Sharing (Kerrigan et al., 2021; Puech et al., 2025) - Continuous Fair Division
    {
        "label": "Published Expert PF Example 1 (Game Theory — Continuous Fair Division / Lone Divider, Kerrigan et al., 2021)",
        "brief": {
            "schema_version": "design-brief/v2",
            "key_idea": "When two non-dividers uniquely want the same piece, recombining and re-dividing the remaining non-contested pieces resolves the standoff while guaranteeing everyone at least 1/N of their total valuation.",
            "naive_answer": "Assign each player their highest-valued piece greedily; this fails because two players only accept Piece 2, leaving a conflict.",
            "goal": "Find a fair allocation of the four land parcels so each of the four players receives land they value at least at their fair share.",
            "situation_and_rules": "Four players want to fairly divide a land parcel worth $1,000 total to each of them. Cleo cuts the land into four pieces she values equally, and the other three players independently state their dollar valuation for each of the four pieces. Pieces may be recombined and re-cut if needed.",
            "student_question": "Describe a way for the players to fairly divide the land. Show your work and explain why each player receives a fair share.",
            "approaches": [
                {
                    "resources": ["Division and equal shares"],
                    "first_action": "Calculate the $250 fair-share threshold for each player and circle every piece valued at $250 or more.",
                    "what_it_establishes": "Which pieces each player considers acceptable on their own.",
                    "limitation": "Two players have only a single acceptable piece or collide on the same acceptable pieces, so direct one-to-one assignment is impossible."
                },
                {
                    "resources": ["Addition and subtraction of whole numbers", "Trial and adjustment"],
                    "first_action": "Assign each player the piece where their bid is highest overall.",
                    "what_it_establishes": "Maximizes total sum of valuations across the group.",
                    "limitation": "Leaves one player with a piece they value below $250, violating individual fairness."
                }
            ],
            "successful_route": "Give the contested piece to the player who accepts no other piece, give another player their distinct acceptable piece, and recombine and re-divide the remaining two pieces between the divider and the last player.",
            "learning_opportunity": "Experiencing the greedy assignment deadlock reveals why fair division requires separating proportionality thresholds from greedy item matching and recombining uncontested pieces.",
            "number_requirements": [
                "Each of the four players has a total valuation of $1,000 across the four pieces, making the proportional fair share $250 per player.",
                "Cleo values all four pieces at $250 each.",
                "Beatrice values only Piece 2 at $250 or more ($300), while valuing Pieces 1, 3, and 4 below $250, so any valid single-piece assignment must give Piece 2 to Beatrice.",
                "At least one other non-divider also values only one or two pieces at $250 or more, creating a direct assignment bottleneck if pieces are not re-divided or carefully matched."
            ]
        }
    },
    # 2. Roommate Furniture (Kerrigan et al., 2021; Puech et al., 2025) - Discrete Fair Division with Cash
    {
        "label": "Published Expert PF Example 2 (Game Theory — Discrete Fair Division with Cash / Sealed Bids, Kerrigan et al., 2021)",
        "brief": {
            "schema_version": "design-brief/v2",
            "key_idea": "To divide indivisible items fairly among N people, each person's fair share is 1/N of their own total valuation across all items; items go to highest bidders, and cash payments into and out of a common pool equalize the surplus.",
            "naive_answer": "Give each roommate the item they value most, or divide each roommate's total valuation by 4 items instead of 3 people; this leaves unequal total values or an unbalanced cash pool.",
            "goal": "Determine an allocation of the four apartment items and cash adjustments so all three roommates receive an equitable outcome.",
            "situation_and_rules": "Three graduating roommates (Ann, Bob, and Charlie) are moving out and must divide four shared indivisible apartment items (Couch, TV, Gaming Console, Surround Sound). Each roommate submits their own dollar valuation for each item, and cash may be paid or received to make the final distribution fair.",
            "student_question": "What is the fairest possible distribution of items and cash among the three roommates? Show your calculations and explain why your plan is fair.",
            "approaches": [
                {
                    "resources": ["Addition and subtraction of whole numbers"],
                    "first_action": "Award each of the four items to the roommate who placed the highest dollar bid on that item.",
                    "what_it_establishes": "Maximizes the total perceived value of the awarded items ($400 total).",
                    "limitation": "Ann and Bob receive $150 of items each while Charlie receives $100, which is unfair without cash compensation."
                },
                {
                    "resources": ["Division and equal shares"],
                    "first_action": "Sum each roommate's bids ($300) and divide by 4 items ($75) instead of 3 roommates ($100) to set target shares.",
                    "what_it_establishes": "Computes the average item value per person.",
                    "limitation": "Confuses the number of items (4) with the number of participants (3), leaving $75 unallocated."
                }
            ],
            "successful_route": "Compute each roommate's $100 fair share (1/3 of $300), award each item to its highest bidder (total value $400 vs. $300 owed), have over-allocated roommates pay their excess into a cash pool ($100 surplus), and divide the surplus equally ($33.33 each).",
            "learning_opportunity": "Comparing item-only assignment against pooled cash settlement shows how side payments resolve indivisibility and distribute the $100 bidding surplus.",
            "number_requirements": [
                "There are 3 roommates and 4 indivisible items, so the number of items does not equal the number of people.",
                "Every roommate's bids across the 4 items sum to $300, making each person's 1/3 fair share $100.",
                "Awarding each item to its unique highest bidder gives item totals of $150, $150, and $100 (summing to $400 > $300), so item-only allocation is unequal and creates a positive $100 surplus."
            ]
        }
    },
    # 3. Mall Store Time-Sharing (Kerrigan, 2018; Puech et al., 2025) - Piecewise Calendar Allocation
    {
        "label": "Published Expert PF Example 3 (Game Theory — Piecewise Calendar Time-Sharing, Kerrigan, 2018)",
        "brief": {
            "schema_version": "design-brief/v2",
            "key_idea": "When participants value calendar periods differently, splitting time by equal months fails; assigning periods by comparative valuation and splitting the high-value holiday months achieves at least half the annual value for both.",
            "naive_answer": "Give Ann the first 6 months (Jan–Jun) and Bob the last 6 months (Jul–Dec); this fails because November and December are worth $24,000 per month, leaving Ann far below half of her $108,000 annual valuation.",
            "goal": "Divide the 12 operating months of the store between Ann and Bob so that both partners receive a fair share of the year.",
            "situation_and_rules": "Ann and Bob co-own a seasonal mall store and want to divide the 12 months of the year between themselves. Each partner has estimated how much each month is worth to them across three seasonal periods (Jan–May, Jun–Oct, and Nov–Dec).",
            "student_question": "How should Ann and Bob divide the calendar year so both partners consider the schedule fair? Justify your schedule with calculations.",
            "approaches": [
                {
                    "resources": ["Division and equal shares"],
                    "first_action": "Split the year into two consecutive 6-month halves (Jan–Jun for one partner, Jul–Dec for the other).",
                    "what_it_establishes": "Gives each partner the same number of months (6 months).",
                    "limitation": "Because Nov–Dec are worth $24,000/month while Jan–May are worth $3,000–$6,000/month, the Jan–Jun partner receives only $24,000 or $36,000 out of $108,000 (well below the $54,000 fair share)."
                },
                {
                    "resources": ["Addition and subtraction of whole numbers"],
                    "first_action": "Give each partner the 5-month period they value less and split Nov–Dec equally.",
                    "what_it_establishes": "Splits the holiday peak equally.",
                    "limitation": "Gives Ann $15,000 + $24,000 = $39,000 (< $54,000), failing the 50% fairness threshold."
                }
            ],
            "successful_route": "Compute the total annual valuation ($108,000 for each partner, so a fair share is at least $54,000), assign Jun–Oct to Ann ($45,000) and Jan–May to Bob ($30,000), and split Nov–Dec (1 month each at $24,000) so Ann gets $69,000 and Bob gets $54,000.",
            "learning_opportunity": "Testing equal-time calendar splits against dollar valuations shows why fair division must weight intervals by value density rather than duration alone.",
            "number_requirements": [
                "Both Ann and Bob value the full 12-month year at $108,000, so a fair share requires at least $54,000 for each partner.",
                "Any consecutive 6-month split (Jan–Jun vs. Jul–Dec) leaves the first-half partner strictly below $54,000 because the 2 holiday months (Nov–Dec) carry $48,000 of the annual value.",
                "Ann values Jun–Oct higher ($9,000/mo vs. $3,000/mo in Jan–May), while Bob values Jan–May and Jun–Oct equally ($6,000/mo), so trading seasonal blocks plus splitting Nov–Dec gives both partners at least $54,000."
            ]
        }
    },
    # 4. Rear-End Collision Investigation (Kapur, 2008; Puech et al., 2025) - Kinematics & Collisions
    {
        "label": "Published Expert PF Example 4 (Physics — Collision Kinematics & Work-Energy, Kapur, 2008)",
        "brief": {
            "schema_version": "design-brief/v2",
            "key_idea": "Pre-impact skid marks measure only the speed lost before collision; determining the truck's initial speed requires combining pre-impact braking deceleration with the speed retained at impact (and post-impact coupled sliding).",
            "naive_answer": "Compare the 6 m truck skid mark to the 12 m car skid mark (or plug d = 6 m into v^2 = 2ad assuming v_final = 0) to claim the truck was going 30.6 km/h < 40 km/h; this fails because the truck was still moving at >= 24 km/h when it hit the car.",
            "goal": "Determine whether the truck driver was exceeding the 40 km/h speed limit before braking.",
            "situation_and_rules": "On a level street with a 40 km/h speed limit, a 1,600 kg delivery truck rear-ended a 1,200 kg sedan that had braked to a stop. Investigators measured a 12 m skid mark from the sedan before impact, a 6 m skid mark from the truck before impact, and a 9 m locked-wheel slide of both vehicles tangled together after impact. Both vehicles brake at 6.0 m/s^2 with locked wheels, and bumper damage shows the truck struck the stationary sedan at a speed of at least 24 km/h.",
            "student_question": "Was the truck driver exceeding the 40 km/h speed limit when he first hit the brakes? Build a mathematical case to support your conclusion.",
            "approaches": [
                {
                    "resources": ["Ratios and unit conversions"],
                    "first_action": "Compare the truck's 6 m pre-impact skid mark directly to the sedan's 12 m skid mark, or compute v = sqrt(2 * 6.0 * 6) = 8.49 m/s (30.6 km/h).",
                    "what_it_establishes": "The speed the truck would have had if the 6 m skid had brought it to a complete stop.",
                    "limitation": "Treats the impact speed as 0 m/s, ignoring both the 24 km/h impact threshold and the 9 m post-impact slide."
                },
                {
                    "resources": ["One-dimensional kinematics"],
                    "first_action": "Convert the 24 km/h impact speed to 6.67 m/s and combine it with the 6 m pre-impact braking distance using v_0^2 = v_f^2 + 2*a*d.",
                    "what_it_establishes": "Gives a lower bound of 10.80 m/s (38.9 km/h) from the bumper-damage threshold alone.",
                    "limitation": "Still omits the actual momentum transfer and 9 m post-impact coupled slide, which requires a higher impact speed than the 24 km/h minimum."
                }
            ],
            "successful_route": "Find the post-impact velocity of the coupled 2,800 kg mass from the 9 m slide (v_post = sqrt(2 * 6.0 * 9) = 10.39 m/s), use momentum conservation (2800 / 1600) to find the truck's actual impact speed (18.19 m/s), and add the 6 m pre-impact braking to find v_0 = 20.07 m/s (72.3 km/h > 40 km/h).",
            "learning_opportunity": "Discovering why the 6 m skid-only calculation underestimates the truck's speed shows how multi-stage motion requires linking pre-impact braking with impact momentum and post-impact work.",
            "number_requirements": [
                "The truck's pre-impact skid (6 m) is shorter than the car's pre-impact skid (12 m), and single-stage stopping v = sqrt(2 * a * d_skid) = 30.6 km/h lies strictly below the 40 km/h speed limit.",
                "Combining the 6 m pre-impact skid with the 9 m post-impact coupled slide of the 1,600 kg truck and 1,200 kg car yields a true initial truck speed strictly above the 40 km/h speed limit."
            ]
        }
    },
    # 5. Boy-Crossing Braking Case (Kapur, 2008; Puech et al., 2025) - Stopping Distance & Reaction Time
    {
        "label": "Published Expert PF Example 5 (Physics — Friction & Reaction-Time Stopping Distance, Kapur, 2008)",
        "brief": {
            "schema_version": "design-brief/v2",
            "key_idea": "Total stopping distance equals reaction-time cruise distance (v_0 * t_react) plus frictional braking distance (v_0^2 / (2 * mu * g)), and time-to-collision depends on both phases.",
            "naive_answer": "Calculate initial speed from the 15 m skid mark alone using v_0 = sqrt(2 * mu * g * d_skid) = 13.28 m/s (47.8 km/h < 55 km/h) and conclude the driver was not speeding and could not avoid the collision; this omits the 0.8 s reaction phase and the 30 m initial separation.",
            "goal": "Evaluate whether the driver's claim that he was obeying the 55 km/h limit and could not stop in time is consistent with the physical evidence.",
            "situation_and_rules": "A 1,400 kg car travels on a flat road with a 55 km/h speed limit (tire-road friction coefficient 0.6, g = 9.8 m/s^2, driver reaction time 0.8 s). A boy starts running across the 4.5 m wide road in 3.0 s when the car is 30 m away. The car strikes the boy and comes to rest after leaving a 15 m locked-wheel skid mark.",
            "student_question": "Does the physical evidence support the driver's account of the accident? Show your calculations and explain your conclusion.",
            "approaches": [
                {
                    "resources": ["Ratios and unit conversions"],
                    "first_action": "Compute the boy's crossing speed (4.5 m / 3.0 s = 1.5 m/s) and compare the car's 30 m distance over 3.0 s (10 m/s = 36 km/h).",
                    "what_it_establishes": "The constant average speed that would cover 30 m in 3.0 s.",
                    "limitation": "Assumes constant velocity rather than two-phase reaction + deceleration motion and ignores the 15 m skid mark."
                },
                {
                    "resources": ["One-dimensional kinematics"],
                    "first_action": "Use friction deceleration a = mu * g = 5.88 m/s^2 on the 15 m skid mark alone to get v_0 = sqrt(2 * 5.88 * 15) = 13.28 m/s (47.8 km/h).",
                    "what_it_establishes": "The speed at the start of the 15 m skid if the car stopped exactly at the end of the skid.",
                    "limitation": "With v_0 = 13.28 m/s and 0.8 s reaction time, total stopping distance is 13.28 * 0.8 + 15 = 25.62 m < 30 m, contradicting the claim that the car started 30 m away and still reached the boy."
                }
            ],
            "successful_route": "Compute braking deceleration a = 0.6 * 9.8 = 5.88 m/s^2, combine the 0.8 s reaction distance (13.28 * 0.8 = 10.62 m) with the 15 m braking distance (total 25.62 m < 30 m at 47.8 km/h, or 32.11 m > 30 m at the 55 km/h limit), and test consistency between the 15 m skid, 30 m separation, and 3.0 s crossing window.",
            "learning_opportunity": "Contrasting the 15 m skid-only speed (47.8 km/h) against total stopping distance (reaction + braking vs. 30 m) reveals why multi-phase motion cannot be analyzed from the braking phase alone.",
            "number_requirements": [
                "The speed implied by a 15 m full-stop skid alone, sqrt(2 * mu * g * 15) = 47.8 km/h, is strictly below the 55 km/h speed limit.",
                "At that 47.8 km/h speed, reaction distance (0.8 s * 13.28 m/s = 10.62 m) plus the 15 m skid equals 25.62 m, which is strictly less than the stated 30 m initial distance.",
                "At the 55 km/h (15.28 m/s) speed limit, total stopping distance (12.22 m reaction + 19.85 m braking = 32.07 m) exceeds 30 m but requires a 19.85 m skid mark rather than 15 m."
            ]
        }
    },
]

EXPERT_EXAMPLES_D2B: list[dict[str, Any]] = [
    # 1. Land Sharing
    {
        "label": "Published Expert PF Example 1 (Game Theory — Land Sharing, Kerrigan et al., 2021)",
        "proposal": {
            "quantities": {
                "total_value": {"description": "Each player's total valuation of the whole land parcel", "unit": "dollars", "role": "given"},
                "n_players": {"description": "Number of players dividing the land", "unit": "unitless", "role": "given"},
                "cleo_bids": {"description": "Cleo's dollar valuation for Pieces 1, 2, 3, and 4", "unit": "dollars", "role": "given"},
                "beatrice_bids": {"description": "Beatrice's dollar valuation for Pieces 1, 2, 3, and 4", "unit": "dollars", "role": "given"},
                "allan_bids": {"description": "Allan's dollar valuation for Pieces 1, 2, 3, and 4", "unit": "dollars", "role": "given"},
                "don_bids": {"description": "Don's dollar valuation for Pieces 1, 2, 3, and 4", "unit": "dollars", "role": "given"},
                "recombined_share_cleo": {"description": "Fraction of recombined Pieces 1 and 3 allocated to Cleo in a worked verification example", "unit": "unitless", "role": "teacher_example"}
            },
            "values": {
                "total_value": 1000,
                "n_players": 4,
                "cleo_bids": [250, 250, 250, 250],
                "beatrice_bids": [200, 300, 225, 225],
                "allan_bids": [100, 200, 400, 300],
                "don_bids": [250, 200, 250, 300],
                "recombined_share_cleo": 0.5
            },
            "conditions": [
                {
                    "statement": "Beatrice has only one acceptable piece (>= $250 fair share), which is Piece 2 ($300), while Pieces 1, 3, and 4 are each strictly below $250.",
                    "requirement_indices": [0, 1, 2],
                    "essential": True,
                    "calculation": {
                        "expressions": {
                            "fair_share": "total_value / n_players",
                            "b_p2": "beatrice_bids[1]",
                            "b_max_other": "max([beatrice_bids[0], beatrice_bids[2], beatrice_bids[3]])"
                        },
                        "predicate": "fair_share == 250 and b_p2 >= fair_share and b_max_other < fair_share",
                        "symbols": {}
                    },
                    "reasoning": "Verifies the $250 threshold and that Beatrice can only accept Piece 2 without recombination."
                },
                {
                    "statement": "Giving Beatrice Piece 2, Allan Piece 3 ($400), and Don Piece 4 ($300) leaves Piece 1 ($250) for Cleo, or recombining uncontested pieces yields >= $250 for every player.",
                    "requirement_indices": [3],
                    "essential": True,
                    "calculation": {
                        "expressions": {
                            "fair_share": "total_value / n_players",
                            "b_val": "beatrice_bids[1]",
                            "a_val": "allan_bids[2]",
                            "d_val": "don_bids[3]",
                            "c_val": "cleo_bids[0]"
                        },
                        "predicate": "b_val >= fair_share and a_val >= fair_share and d_val >= fair_share and c_val >= fair_share",
                        "symbols": {}
                    },
                    "reasoning": "Checks that a valid target allocation meets the >= $250 proportional share for all four players."
                }
            ]
        }
    },
    # 2. Roommate Furniture
    {
        "label": "Published Expert PF Example 2 (Game Theory — Roommate Furniture, Kerrigan et al., 2021)",
        "proposal": {
            "quantities": {
                "n_roommates": {"description": "Number of graduating roommates", "unit": "unitless", "role": "given"},
                "n_items": {"description": "Number of indivisible apartment items", "unit": "unitless", "role": "given"},
                "ann_bids": {"description": "Ann's dollar valuations for [Couch, TV, Console, Surround]", "unit": "dollars", "role": "given"},
                "bob_bids": {"description": "Bob's dollar valuations for [Couch, TV, Console, Surround]", "unit": "dollars", "role": "given"},
                "charlie_bids": {"description": "Charlie's dollar valuations for [Couch, TV, Console, Surround]", "unit": "dollars", "role": "given"}
            },
            "values": {
                "n_roommates": 3,
                "n_items": 4,
                "ann_bids": [150, 75, 50, 25],
                "bob_bids": [100, 50, 100, 50],
                "charlie_bids": [125, 100, 25, 50]
            },
            "conditions": [
                {
                    "statement": "Dividing total bids ($300) by 4 items ($75) differs from dividing by 3 roommates ($100), and awarding items to highest bidders without cash gives unequal item values ($150, $150, $100).",
                    "requirement_indices": [0, 1, 2],
                    "essential": True,
                    "calculation": {
                        "expressions": {
                            "fair_share": "sum(ann_bids) / n_roommates",
                            "wrong_item_share": "sum(ann_bids) / n_items",
                            "ann_items": "ann_bids[0]",
                            "bob_items": "bob_bids[2] + bob_bids[3]",
                            "charlie_items": "charlie_bids[1]",
                            "surplus": "(ann_items + bob_items + charlie_items) - 3 * fair_share"
                        },
                        "predicate": "fair_share == 100 and wrong_item_share == 75 and ann_items == 150 and bob_items == 150 and charlie_items == 100 and surplus == 100",
                        "symbols": {}
                    },
                    "reasoning": "Verifies both the N=3 vs M=4 division trap and that highest-bidder item assignment requires a $100 cash surplus redistribution."
                }
            ]
        }
    },
    # 3. Mall Store Time-Sharing
    {
        "label": "Published Expert PF Example 3 (Game Theory — Mall Store Time-Sharing, Kerrigan, 2018)",
        "proposal": {
            "quantities": {
                "period_months": {"description": "Number of months in [Jan-May, Jun-Oct, Nov-Dec]", "unit": "months", "role": "given"},
                "ann_monthly_rates": {"description": "Ann's monthly value in dollars for [Jan-May, Jun-Oct, Nov-Dec]", "unit": "dollars", "role": "given"},
                "bob_monthly_rates": {"description": "Bob's monthly value in dollars for [Jan-May, Jun-Oct, Nov-Dec]", "unit": "dollars", "role": "given"}
            },
            "values": {
                "period_months": [5, 5, 2],
                "ann_monthly_rates": [3000, 9000, 24000],
                "bob_monthly_rates": [6000, 6000, 24000]
            },
            "conditions": [
                {
                    "statement": "A naive 6-month calendar split (Jan-Jun vs Jul-Dec) leaves the Jan-Jun partner below the $54,000 half-year valuation, whereas trading Jan-May and Jun-Oct plus splitting Nov-Dec gives both >= $54,000.",
                    "requirement_indices": [0, 1, 2],
                    "essential": True,
                    "calculation": {
                        "expressions": {
                            "ann_total": "5 * ann_monthly_rates[0] + 5 * ann_monthly_rates[1] + 2 * ann_monthly_rates[2]",
                            "fair_share": "ann_total / 2",
                            "ann_jan_jun": "5 * ann_monthly_rates[0] + 1 * ann_monthly_rates[1]",
                            "bob_jan_jun": "5 * bob_monthly_rates[0] + 1 * bob_monthly_rates[1]",
                            "ann_trade": "5 * ann_monthly_rates[1] + 1 * ann_monthly_rates[2]",
                            "bob_trade": "5 * bob_monthly_rates[0] + 1 * bob_monthly_rates[2]"
                        },
                        "predicate": "fair_share == 54000 and ann_jan_jun < fair_share and bob_jan_jun < fair_share and ann_trade >= fair_share and bob_trade >= fair_share",
                        "symbols": {}
                    },
                    "reasoning": "Checks that any consecutive 6-month split fails the $54,000 threshold while comparative period assignment succeeds."
                }
            ]
        }
    },
    # 4. Rear-End Collision Investigation
    {
        "label": "Published Expert PF Example 4 (Physics — Rear-End Collision Investigation, Kapur, 2008)",
        "proposal": {
            "quantities": {
                "speed_limit_kmh": {"description": "Posted speed limit on the street", "unit": "km/h", "role": "given"},
                "truck_mass": {"description": "Mass of the delivery truck", "unit": "kg", "role": "given"},
                "car_mass": {"description": "Mass of the stationary sedan", "unit": "kg", "role": "given"},
                "car_skid": {"description": "Pre-impact skid mark length of the sedan", "unit": "m", "role": "given"},
                "truck_skid": {"description": "Pre-impact skid mark length of the truck", "unit": "m", "role": "given"},
                "post_impact_slide": {"description": "Post-impact coupled slide distance of both vehicles", "unit": "m", "role": "given"},
                "decel": {"description": "Locked-wheel braking deceleration magnitude", "unit": "m/s^2", "role": "given"}
            },
            "values": {
                "speed_limit_kmh": 40,
                "truck_mass": 1600,
                "car_mass": 1200,
                "car_skid": 12,
                "truck_skid": 6,
                "post_impact_slide": 9,
                "decel": 6.0
            },
            "conditions": [
                {
                    "statement": "Naive single-stage stopping from the 6 m truck skid alone gives 30.6 km/h (< 40 km/h limit), whereas including the 9 m post-impact coupled slide via momentum and work-energy gives 72.3 km/h (> 40 km/h limit).",
                    "requirement_indices": [0, 1],
                    "essential": True,
                    "calculation": {
                        "expressions": {
                            "v_naive_kmh": "sqrt(2 * decel * truck_skid) * 3.6",
                            "v_post_ms": "sqrt(2 * decel * post_impact_slide)",
                            "v_impact_ms": "((truck_mass + car_mass) / truck_mass) * v_post_ms",
                            "v_true_kmh": "sqrt(v_impact_ms ** 2 + 2 * decel * truck_skid) * 3.6"
                        },
                        "predicate": "v_naive_kmh < speed_limit_kmh and v_true_kmh > speed_limit_kmh",
                        "symbols": {}
                    },
                    "reasoning": "Verifies the opposite conclusion between the 1-stage skid shortcut and the full collision-plus-braking analysis."
                }
            ]
        }
    },
    # 5. Boy-Crossing Braking Case
    {
        "label": "Published Expert PF Example 5 (Physics — Boy-Crossing Braking Case, Kapur, 2008)",
        "proposal": {
            "quantities": {
                "speed_limit_kmh": {"description": "Posted speed limit", "unit": "km/h", "role": "given"},
                "mu": {"description": "Tire-road coefficient of friction", "unit": "unitless", "role": "given"},
                "g": {"description": "Gravitational acceleration", "unit": "m/s^2", "role": "given"},
                "reaction_time": {"description": "Driver braking reaction time", "unit": "s", "role": "given"},
                "skid_distance": {"description": "Measured locked-wheel skid mark length", "unit": "m", "role": "given"},
                "initial_distance": {"description": "Reported distance from the boy when he started crossing", "unit": "m", "role": "given"}
            },
            "values": {
                "speed_limit_kmh": 55,
                "mu": 0.6,
                "g": 9.8,
                "reaction_time": 0.8,
                "skid_distance": 15,
                "initial_distance": 30
            },
            "conditions": [
                {
                    "statement": "A 15 m full-stop skid implies v0 = 47.8 km/h (< 55 km/h), but at that speed reaction + braking distance is 25.62 m (< 30 m), contradicting the claim that the car could not stop inside 30 m.",
                    "requirement_indices": [0, 1, 2],
                    "essential": True,
                    "calculation": {
                        "expressions": {
                            "a": "mu * g",
                            "v_skid_ms": "sqrt(2 * a * skid_distance)",
                            "v_skid_kmh": "v_skid_ms * 3.6",
                            "stop_dist_at_v_skid": "v_skid_ms * reaction_time + skid_distance"
                        },
                        "predicate": "v_skid_kmh < speed_limit_kmh and stop_dist_at_v_skid < initial_distance",
                        "symbols": {}
                    },
                    "reasoning": "Checks that the 15 m skid-only speed and the 30 m collision claim contradict each other once reaction distance is included."
                }
            ]
        }
    },
]

EXPERT_EXAMPLES_D3: list[dict[str, Any]] = [
    # 1. Land Sharing
    {
        "label": "Published Expert PF Example 1 (Game Theory — Land Sharing, Kerrigan et al., 2021)",
        "task": {
            "status": "ready",
            "blocking_issues": [],
            "title": "Dividing the Inherited Land",
            "body": (
                "Cleo, Beatrice, Allan, and Don want to fairly divide a parcel of land that is worth "
                "$1,000 in total to each of them. Cleo cuts the land into four pieces (Piece 1, Piece 2, "
                "Piece 3, and Piece 4) that she values equally at $250 each.\n\n"
                "The other three players independently evaluate the four pieces and assign the following "
                "dollar values:\n"
                "- Cleo: Piece 1 = $250, Piece 2 = $250, Piece 3 = $250, Piece 4 = $250\n"
                "- Beatrice: Piece 1 = $200, Piece 2 = $300, Piece 3 = $225, Piece 4 = $225\n"
                "- Allan: Piece 1 = $100, Piece 2 = $200, Piece 3 = $400, Piece 4 = $300\n"
                "- Don: Piece 1 = $250, Piece 2 = $200, Piece 3 = $250, Piece 4 = $300\n\n"
                "Any pieces of land can be recombined and re-cut if needed."
            ),
            "question": "Describe a way for the players to fairly divide the land. Show your work and explain why each player receives a fair share.",
            "withheld": []
        }
    },
    # 2. Roommate Furniture
    {
        "label": "Published Expert PF Example 2 (Game Theory — Roommate Furniture, Kerrigan et al., 2021)",
        "task": {
            "status": "ready",
            "blocking_issues": [],
            "title": "Moving Out After Graduation",
            "body": (
                "Ann, Bob, and Charlie are graduating roommates who need to divide four shared apartment "
                "items—a Couch, a TV, a Gaming Console, and a Surround Sound system—that cannot be physically "
                "split. Each roommate privately writes down the dollar value they place on each item:\n"
                "- Ann: Couch = $150, TV = $75, Gaming Console = $50, Surround Sound = $25\n"
                "- Bob: Couch = $100, TV = $50, Gaming Console = $100, Surround Sound = $50\n"
                "- Charlie: Couch = $125, TV = $100, Gaming Console = $25, Surround Sound = $50\n\n"
                "The roommates can also pay or receive cash to make the final outcome fair."
            ),
            "question": "What is the fairest possible distribution of the items and cash among Ann, Bob, and Charlie? Show your calculations and explain why your plan is fair.",
            "withheld": []
        }
    },
    # 3. Mall Store Time-Sharing
    {
        "label": "Published Expert PF Example 3 (Game Theory — Mall Store Time-Sharing, Kerrigan, 2018)",
        "task": {
            "status": "ready",
            "blocking_issues": [],
            "title": "Sharing the Seasonal Store",
            "body": (
                "Ann and Bob co-own a retail store at a shopping mall and want to divide the 12 operating "
                "months of the year between themselves. Because customer traffic changes across the year, "
                "each partner values the three seasonal periods differently:\n"
                "- January 1 to May 31 (5 months): Ann values each month at $3,000; Bob values each month at $6,000.\n"
                "- June 1 to October 31 (5 months): Ann values each month at $9,000; Bob values each month at $6,000.\n"
                "- November 1 to December 31 (2 months): Ann values each month at $24,000; Bob values each month at $24,000."
            ),
            "question": "How should Ann and Bob divide the 12 months of the calendar year so that both partners receive a fair share? Show your work and justify your schedule.",
            "withheld": []
        }
    },
    # 4. Rear-End Collision Investigation
    {
        "label": "Published Expert PF Example 4 (Physics — Rear-End Collision Investigation, Kapur, 2008)",
        "task": {
            "status": "ready",
            "blocking_issues": [],
            "title": "The Rear-End Collision Case",
            "body": (
                "On a flat, straight city street with a 40 km/h speed limit, a 1,600 kg delivery truck "
                "rear-ended a 1,200 kg sedan that had just braked to a full stop. Scene investigators "
                "recorded the following measurements:\n"
                "- The sedan left a 12 m skid mark before coming to a stop.\n"
                "- The truck left a 6 m skid mark immediately before colliding with the stationary sedan.\n"
                "- After impact, the truck and sedan stayed locked together and skidded an additional 9 m before stopping.\n"
                "- Under locked-wheel braking on this road surface, both vehicles decelerate at 6.0 m/s^2, and bumper-crush tests indicate the truck was still traveling at least 24 km/h at the moment of impact.\n\n"
                "The truck driver claims he was driving below the 40 km/h speed limit because his 6 m pre-impact skid mark was only half as long as the sedan's 12 m skid mark."
            ),
            "question": "Was the truck driver exceeding the 40 km/h speed limit when he first applied his brakes? Build a mathematical case to support your conclusion.",
            "withheld": []
        }
    },
    # 5. Boy-Crossing Braking Case
    {
        "label": "Published Expert PF Example 5 (Physics — Boy-Crossing Braking Case, Kapur, 2008)",
        "task": {
            "status": "ready",
            "blocking_issues": [],
            "title": "The Crosswalk Braking Investigation",
            "body": (
                "A 1,400 kg car was traveling along a flat road with a 55 km/h speed limit when a boy "
                "started running across the 4.5 m wide road in 3.0 s. The driver claims the boy began "
                "crossing when the car was 30 m away, and that although he was driving within the 55 km/h "
                "limit, he could not stop in time.\n\n"
                "Accident reconstruction measurements show:\n"
                "- The car left a 15 m locked-wheel skid mark and came to rest just as it struck the boy.\n"
                "- The tire-road coefficient of friction is 0.6 (with gravitational acceleration g = 9.8 m/s^2).\n"
                "- The driver's reaction time before the brakes locked was 0.8 s."
            ),
            "question": "Does the physical evidence support the driver's account of the accident? Show your calculations and explain your conclusion.",
            "withheld": []
        }
    },
]


def build_brief_prompts(n_examples: int) -> dict[str, str]:
    prompts = copy.deepcopy(BASE_BRIEF_PROMPTS)
    if n_examples <= 0:
        return prompts
    chosen = EXPERT_EXAMPLES_D2A[:n_examples]
    blocks = []
    for item in chosen:
        blocks.append(
            f"  # {item['label']}\n  "
            + json.dumps(item["brief"], ensure_ascii=False, indent=2).replace("\n", "\n  ")
        )
    joined = "\n\n".join(blocks)
    propose_addition = (
        f"\n\n  PUBLISHED HUMAN EXPERT PF DESIGN BRIEF EXAMPLES ({n_examples}-SHOT, UNRELATED DOMAINS)\n"
        "  Study how these published expert PF tasks (from game-theory fair division and physics\n"
        "  accident reconstruction, completely unrelated to your target topic) achieve BOTH:\n"
        "  (1) Complete familiar-approach failure: every tempting familiar approach—both single-step\n"
        "      shortcuts and multi-step greedy/partial procedures—hits a concrete mathematical deadlock,\n"
        "      tie, or contradiction locked into number_requirements.\n"
        "  (2) Un-coached student wording: situation_and_rules states only the raw scenario, rules, and\n"
        "      permissions, and student_question asks ONE direct open question ('Describe a way...',\n"
        "      'What is the fairest possible distribution...', 'Was the truck driver exceeding...')\n"
        "      with ZERO procedural hints, ZERO intermediate-step instructions, and ZERO coaching menus.\n"
        "  Transfer only these structural PF design principles; never copy these unrelated domains.\n\n"
        f"{joined}\n"
    )
    select_addition = (
        f"\n\n  PUBLISHED HUMAN EXPERT PF SELECTION BENCHMARK ({n_examples}-SHOT, UNRELATED DOMAINS)\n"
        "  Compare your candidate briefs against these published human expert PF designs:\n"
        "  - Reject or flag in main_concern any candidate whose situation_and_rules or student_question\n"
        "    explains intermediate calculation steps, names which reference base or statistic to use, or\n"
        "    coaches the student's procedure (notice how every expert student_question below is a single,\n"
        "    direct, un-coached question).\n"
        "  - Reject or flag in main_concern any candidate where a multi-step or sequential familiar\n"
        "    procedure from learner_context still resolves the goal without hitting an exact tie,\n"
        "    deadlock, or opposite ranking in number_requirements.\n\n"
        f"{joined}\n"
    )
    prompts["PROPOSE_BRIEF_SYSTEM"] = prompts["PROPOSE_BRIEF_SYSTEM"].rstrip() + propose_addition
    prompts["SELECT_BRIEF_SYSTEM"] = prompts["SELECT_BRIEF_SYSTEM"].rstrip() + select_addition
    return prompts


def build_data_prompts(n_examples: int) -> dict[str, str]:
    prompts = copy.deepcopy(BASE_DATA_PROMPTS)
    if n_examples <= 0:
        return prompts
    chosen_d2b = EXPERT_EXAMPLES_D2B[:n_examples]
    d2b_blocks = []
    for item in chosen_d2b:
        d2b_blocks.append(
            f"  # {item['label']}\n  "
            + json.dumps(item["proposal"], ensure_ascii=False, indent=2).replace("\n", "\n  ")
        )
    d2b_addition = (
        f"\n\n  PUBLISHED HUMAN EXPERT PF DATA & CONDITION EXAMPLES ({n_examples}-SHOT, UNRELATED DOMAINS)\n"
        "  Study how these published expert PF tasks instantiate clean numbers and exact calculator\n"
        "  predicates so that EVERY tempting familiar approach (not just a straw-man 1-step average,\n"
        "  but also greedy/sequential prior procedures) hits an exact mathematical tie, threshold failure,\n"
        "  or opposite conclusion, while all raw problem inputs remain role: 'given'.\n\n"
        + "\n\n".join(d2b_blocks)
        + "\n"
    )

    chosen_d3 = EXPERT_EXAMPLES_D3[:n_examples]
    d3_blocks = []
    for item in chosen_d3:
        d3_blocks.append(
            f"  # {item['label']}\n  "
            + json.dumps(item["task"], ensure_ascii=False, indent=2).replace("\n", "\n  ")
        )
    d3_addition = (
        f"\n\n  PUBLISHED HUMAN EXPERT PF STUDENT TASK EXAMPLES ({n_examples}-SHOT, UNRELATED DOMAINS)\n"
        "  Study how these published expert PF tasks present the student-facing text:\n"
        "  - body states the concrete scenario, raw data table/measurements, and rules in plain language,\n"
        "    with ZERO hints about intermediate bases, formulas, or which summary measures to combine.\n"
        "  - question asks ONE concise, open-ended decision or construction question without any\n"
        "    multi-part checklist or representation coaching.\n\n"
        + "\n\n".join(d3_blocks)
        + "\n"
    )
    prompts["PROPOSE_DATA_SYSTEM"] = prompts["PROPOSE_DATA_SYSTEM"].rstrip() + d2b_addition
    prompts["WRITE_DATA_TASK_SYSTEM"] = prompts["WRITE_DATA_TASK_SYSTEM"].rstrip() + d3_addition
    return prompts


def run_ablation_generation_worker(
    cell: dict[str, Any],
    repeat: int,
    n_examples: int,
    out_dir: Path,
    gen_model: str,
) -> dict[str, Any]:
    cell_id = cell["cell_id"]
    arm_name = f"examples_{n_examples}"
    key = f"rahimi_{cell_id}_{arm_name}_{repeat:03d}"
    attempt_dir = out_dir / arm_name / "generation" / cell_id / f"attempt_{repeat:03d}"
    result_path = attempt_dir / "result.json"
    if result_path.exists():
        saved = json.loads(result_path.read_text(encoding="utf-8"))
        task = ((saved.get("stages") or {}).get("D2_D3") or {}).get("task")
        if isinstance(task, dict) and task.get("status") == "ready" and task.get("body"):
            return {"key": key, "cell_id": cell_id, "repeat": repeat, "n_examples": n_examples, "result": saved}
        shutil.rmtree(attempt_dir)

    # Monkeypatch Stage 2a, Stage 2b, and Stage 3 prompt loaders in this worker process
    brief_prompts = build_brief_prompts(n_examples)
    data_prompts = build_data_prompts(n_examples)
    design_brief_stage._prompts = lambda path=None: copy.deepcopy(brief_prompts)
    design_data_stage._prompts = lambda: copy.deepcopy(data_prompts)

    case, grounding_evidence, shared_context = _build_cell_inputs(cell, key)
    fixed_d1_path = BASELINE_DIR / "rahimi_cells_generation" / cell_id / "fixed_d1.json"
    attempt_dir.parent.mkdir(parents=True, exist_ok=True)
    reused_d1_for_key = attempt_dir.parent / f"_d1_reused_{repeat:03d}.json"
    if fixed_d1_path.exists():
        d1_data = json.loads(fixed_d1_path.read_text(encoding="utf-8"))
        d1_data["records"][0]["case_id"] = key
        save_json(reused_d1_for_key, d1_data)

    res: dict[str, Any] = {}
    for _attempt in range(3):
        if attempt_dir.exists():
            shutil.rmtree(attempt_dir)
        try:
            res = diagnostic.run_case_worker(
                key,
                str(attempt_dir),
                gen_model,
                2,
                str(reused_d1_for_key) if reused_d1_for_key.exists() else None,
                case_override=case,
                shared_context=shared_context,
                evidence_k=6,
                max_resources=4,
                d1_condition="grounded",
                grounding_evidence=grounding_evidence if not reused_d1_for_key.exists() else None,
            )
            if ((res.get("stages") or {}).get("D2_D3") or {}).get("task"):
                break
        except Exception as exc:
            res = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    if reused_d1_for_key.exists():
        reused_d1_for_key.unlink()
    return {"key": key, "cell_id": cell_id, "repeat": repeat, "n_examples": n_examples, "result": res}


def evaluate_ablation_task_v31(
    key: str,
    cell: dict[str, Any],
    student_task: str,
    chats: dict[str, Any],
    arm_dir: Path,
    solvers: tuple[str, ...] = ("luna", "gpt41"),
) -> dict[str, Any]:
    out_path = arm_dir / "v31_eval" / f"{key}.json"
    if out_path.exists():
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        if saved.get("status") == "completed" and not _has_v30_api_error(saved.get("result") or {}):
            return saved
    solver_chats = {s: chats[s] for s in solvers}
    res = None
    for _attempt in range(3):
        res = v31.evaluate_v31(
            student_task,
            cell["case"]["target_concept"],
            copy.deepcopy(cell["learner_context"]),
            solver_chats=solver_chats,
            judge_chat=chats["luna"],
        )
        if not _has_v30_api_error(res):
            break
    rec = {
        "key": key,
        "cell_id": cell["cell_id"],
        "status": "completed",
        "result": res,
        "finished_at": now(),
    }
    save_json(out_path, rec)
    return rec


def summarize_v31_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {m: Counter() for m in MEASURES}
    all5 = 0
    for r in records:
        ms = (r.get("result") or {}).get("measures") or {}
        if not ms:
            continue
        for m in MEASURES:
            m_obj = ms.get(m) or {}
            val = m_obj.get("value") if m_obj.get("status") == "assessed" else m_obj.get("status")
            counts[m][str(val)] += 1
        if all((ms.get(m) or {}).get("value") == "yes" for m in MEASURES):
            all5 += 1
    n = len(records)
    return {
        "n_evaluated": n,
        "all_5_yes": all5,
        "all_5_yes_pct": round(100.0 * all5 / max(1, n), 1),
        "measures": {
            m: {
                **dict(c),
                "yes_pct": round(100.0 * c.get("yes", 0) / max(1, n), 1),
            }
            for m, c in counts.items()
        },
    }


def collect_baseline_0_examples(cells_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    v31_records = []
    t1_records = []
    by_cell_v31: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_cell_t1: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cell_id, repeats in STRATIFIED_30_SLICE.items():
        for rep in repeats:
            base_key = f"{cell_id}__pipeline_lc__{rep:03d}"
            v31_path = BASELINE_DIR / "rahimi_cells_v30" / f"{base_key}.json"
            t1_path = BASELINE_DIR / "table1_ratings" / f"{base_key}.json"
            if v31_path.exists():
                rec = json.loads(v31_path.read_text(encoding="utf-8"))
                v31_records.append(rec)
                by_cell_v31[cell_id].append(rec)
            if t1_path.exists():
                rec_t1 = json.loads(t1_path.read_text(encoding="utf-8"))
                t1_records.append(rec_t1)
                by_cell_t1[cell_id].append(rec_t1)
    return {
        "n_tasks": len(v31_records),
        "v31_overall": summarize_v31_records(v31_records),
        "v31_by_cell": {cid: summarize_v31_records(recs) for cid, recs in by_cell_v31.items()},
        "table1_overall": summarize_cohort_table1(t1_records),
        "table1_by_cell": {cid: summarize_cohort_table1(recs) for cid, recs in by_cell_t1.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gen-model", default="gpt5mini")
    parser.add_argument("--arms", default="1,5", help="Comma-separated example counts to generate (e.g. 1,5)")
    parser.add_argument("--limit-per-cell", type=int, default=0, help="Optional cap per cell for smoke calibration")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    out_dir = args.output.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    setting = json.loads(SETTING_PATH.read_text(encoding="utf-8"))
    cells_by_id = {c["cell_id"]: c for c in setting["cells"]}
    arms = [int(x.strip()) for x in args.arms.split(",") if x.strip()]

    # Save exact prompt snapshots for reproducibility
    for n_ex in arms:
        arm_dir = out_dir / f"examples_{n_ex}"
        arm_dir.mkdir(parents=True, exist_ok=True)
        save_json(arm_dir / "prompts_d2a.json", build_brief_prompts(n_ex))
        save_json(arm_dir / "prompts_d2b_d3.json", build_data_prompts(n_ex))

    # Build generation jobs across requested arms
    gen_jobs: list[tuple[dict[str, Any], int, int]] = []
    for n_ex in arms:
        for cell_id, repeats in STRATIFIED_30_SLICE.items():
            use_repeats = repeats[: args.limit_per_cell] if args.limit_per_cell > 0 else repeats
            for rep in use_repeats:
                gen_jobs.append((cells_by_id[cell_id], rep, n_ex))

    print(f"[ablation] Running {len(gen_jobs)} StructPF generation jobs with workers={args.workers}...", flush=True)
    gen_records_by_arm: dict[int, list[dict[str, Any]]] = defaultdict(list)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(
                run_ablation_generation_worker,
                cell,
                rep,
                n_ex,
                out_dir,
                args.gen_model,
            ): (cell["cell_id"], rep, n_ex)
            for cell, rep, n_ex in gen_jobs
        }
        for fut in as_completed(futs):
            rec = fut.result()
            task_obj = ((rec["result"].get("stages") or {}).get("D2_D3") or {}).get("task") or {}
            gen_records_by_arm[rec["n_examples"]].append(rec)
            print(
                f"[gen-ex{rec['n_examples']}] {rec['key']}: status={task_obj.get('status')} title={task_obj.get('title')!r}",
                flush=True,
            )

    # Evaluate all ready tasks with PF Eval (v3.1) and Table 1 rubric in parallel threads
    chats = build_chats()
    eval_Summary: dict[str, Any] = {
        "generated_at": now(),
        "gen_model": args.gen_model,
        "slice_definition": STRATIFIED_30_SLICE,
        "unrelated_expert_examples": {
            "1_example": [EXPERT_EXAMPLES_D2A[0]["label"]],
            "5_examples": [x["label"] for x in EXPERT_EXAMPLES_D2A],
        },
        "source_hashes": {
            "script": file_sha256(Path(__file__)),
            "design_briefs_yaml": file_sha256(design_brief_stage.PROMPTS_PATH),
            "design_data_yaml": file_sha256(design_data_stage.PROMPTS_PATH),
            "v31_fingerprint": v31.fingerprint(),
        },
        "arms": {
            "examples_0": collect_baseline_0_examples(cells_by_id),
        },
    }

    for n_ex in arms:
        arm_name = f"examples_{n_ex}"
        arm_dir = out_dir / arm_name
        ready_items: list[tuple[str, dict[str, Any], str]] = []
        for rec in sorted(gen_records_by_arm[n_ex], key=lambda r: r["key"]):
            task = ((rec["result"].get("stages") or {}).get("D2_D3") or {}).get("task") or {}
            if task.get("status") == "ready" and task.get("body"):
                text = f"{task.get('title', '')}\n\n{task['body']}\n\n{task.get('question', '')}".strip()
                ready_items.append((rec["key"], cells_by_id[rec["cell_id"]], text))

        v31_recs: list[dict[str, Any]] = []
        t1_recs: list[dict[str, Any]] = []
        by_cell_v31: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_cell_t1: dict[str, list[dict[str, Any]]] = defaultdict(list)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            v31_futs = {
                pool.submit(evaluate_ablation_task_v31, key, cell, text, chats, arm_dir): (key, cell["cell_id"])
                for key, cell, text in ready_items
            }
            t1_futs = {
                pool.submit(
                    rate_one_table1,
                    key,
                    f"rahimi_{cell['cell_id']}_{arm_name}",
                    text,
                    cell["learner_context"],
                    chats["luna"],
                    arm_dir,
                    case_setting=cell["case"],
                ): (key, cell["cell_id"])
                for key, cell, text in ready_items
            }
            for fut in as_completed(v31_futs):
                v_rec = fut.result()
                v31_recs.append(v_rec)
                by_cell_v31[v_rec["cell_id"]].append(v_rec)
                ms = (v_rec.get("result") or {}).get("measures") or {}
                summary_flags = {m: (ms.get(m) or {}).get("value") for m in MEASURES}
                print(f"[v31-ex{n_ex}] {v_rec['key']}: {summary_flags}", flush=True)
            for fut in as_completed(t1_futs):
                t_rec = fut.result()
                t1_recs.append(t_rec)
                cid = t1_futs[fut][1]
                by_cell_t1[cid].append(t_rec)
                print(
                    f"[t1-ex{n_ex}] {t_rec['task_id']}: TOTAL={t_rec.get('mean_scores', {}).get('TOTAL')}",
                    flush=True,
                )

        eval_Summary["arms"][arm_name] = {
            "n_attempted": len([j for j in gen_jobs if j[2] == n_ex]),
            "n_ready": len(ready_items),
            "v31_overall": summarize_v31_records(v31_recs),
            "v31_by_cell": {cid: summarize_v31_records(recs) for cid, recs in sorted(by_cell_v31.items())},
            "table1_overall": summarize_cohort_table1(t1_recs),
            "table1_by_cell": {cid: summarize_cohort_table1(recs) for cid, recs in sorted(by_cell_t1.items())},
        }
        save_json(out_dir / "summary.json", eval_Summary)

    save_json(out_dir / "summary.json", eval_Summary)
    print(f"[done] Saved summary to {out_dir / 'summary.json'}", flush=True)


if __name__ == "__main__":
    main()

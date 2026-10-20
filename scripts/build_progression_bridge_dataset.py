"""Build and validate the 10-case Learning Commons Progression Bridge dataset.

Each case pairs a Common Core target standard (S_target) with its official
Learning Commons v1.14.0 `buildsTowards` prerequisite standards (S_prior),
the `supports` learning components attached to S_prior and S_target, the
common ungrounded input (grade, subject, topic, target_concept), and the
single 0/1/2 Progression Bridge Fit rubric anchor.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.build_learning_commons_snapshot import read_jsonl

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = (
    Path.home() / "Library" / "Caches" / "learning-commons" / "knowledge-graph" / "v1.14.0"
)
DEFAULT_DATASET_PATH = ROOT / "data" / "learning_commons" / "progression_bridge_dataset_v1.json"
DEFAULT_SLICE_DIR = ROOT / "data" / "learning_commons" / "progression_bridge_v1"
SCHEMA_VERSION = "pf-progression-bridge-dataset/v1"
ALLOWED_LICENSES = {
    "https://creativecommons.org/licenses/by/4.0/",
    "https://creativecommons.org/publicdomain/zero/1.0/",
}

CASE_SPECS: list[dict[str, Any]] = [
    {
        "id": "g5_fraction_addition_unlike_denominators",
        "target_code": "5.NF.A.1",
        "grade": 5,
        "subject": "mathematics",
        "domain": "Number and Operations - Fractions",
        "topic": "adding and subtracting fractions with unlike denominators",
        "target_concept": (
            "Adding and subtracting fractions with unlike denominators by replacing "
            "given fractions with equivalent fractions that share a common denominator."
        ),
        "exclude_prior_terms": [
            "common denominator",
            "least common denominator",
            "unlike denominators",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Add and subtract fractions with like denominators (4.NF.B.3) and "
                "recognize equivalent fractions (4.NF.A.1)."
            ),
            "s_target_summary": (
                "Add and subtract fractions with unlike denominators using equivalent "
                "fractions with a common unit (5.NF.A.1)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 leaks common-denominator addition of unlike fractions as already "
                "taught, or drops to whole-number counting without fractions."
            ),
            "score_1_loose_match": (
                "Task uses like-denominator fractions that can be added directly without "
                "needing a common unit, or fails only on a wording trick."
            ),
            "score_2_exact_bridge": (
                "Students can start with like-denominator parts or visual fraction "
                "comparisons, hit unequal partition sizes where adding numerators/denominators "
                "fails, and must construct a common unit to combine or compare them."
            ),
        },
    },
    {
        "id": "g5_composite_rectangular_prism_volume",
        "target_code": "5.MD.C.5.c",
        "grade": 5,
        "subject": "mathematics",
        "domain": "Measurement and Data",
        "topic": "volume of composite solid figures made of non-overlapping rectangular prisms",
        "target_concept": (
            "Recognizing volume as additive and finding the total volume of solid "
            "figures composed of two non-overlapping right rectangular prisms by "
            "decomposing them into individual prisms."
        ),
        "exclude_prior_terms": [
            "decompose into non-overlapping prisms",
            "additive volume formula",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Compute the volume of a single right rectangular prism using "
                "V = l * w * h or V = b * h (5.MD.C.5.b) and unit cubes (5.MD.C.3)."
            ),
            "s_target_summary": (
                "Find volumes of composite L-shaped or stepped solid figures by adding "
                "the volumes of non-overlapping rectangular prisms (5.MD.C.5.c)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 instructs students how to split the composite solid into two "
                "prisms, or only asks for the volume of a single plain box."
            ),
            "score_1_loose_match": (
                "The two prism pieces are already given separately with all three edge "
                "lengths labeled on each piece."
            ),
            "score_2_exact_bridge": (
                "Students can apply V = l * w * h from 5.MD.C.5.b, find that multiplying "
                "the outer overall length, width, and height overcounts the missing step "
                "or corner, and must partition the solid and deduce the missing edge length."
            ),
        },
    },
    {
        "id": "g5_multiplication_as_scaling_fractions",
        "target_code": "5.NF.B.5",
        "grade": 5,
        "subject": "mathematics",
        "domain": "Number and Operations - Fractions",
        "topic": "interpreting multiplication by a fraction as scaling or resizing",
        "target_concept": (
            "Interpreting multiplication as scaling by comparing the size of a product "
            "to the size of one factor on the basis of whether the other factor is "
            "greater than 1, equal to 1, or less than 1."
        ),
        "exclude_prior_terms": [
            "scaling factor greater or less than 1 rule",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Whole-number multiplicative comparison (4.OA.A.1), fraction equivalence "
                "(4.NF.A.1), and multiplying a fraction by a whole number (5.NF.B.4)."
            ),
            "s_target_summary": (
                "Reason about how multiplying by a fraction greater than or less than 1 "
                "scales a quantity without relying on whole-number 'multiplication makes "
                "bigger' intuition (5.NF.B.5)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states the >1 vs <1 scaling rule directly, or uses only whole-number "
                "multipliers."
            ),
            "score_1_loose_match": (
                "All multipliers are greater than 1, so whole-number intuition already "
                "gives the right ordering."
            ),
            "score_2_exact_bridge": (
                "Students can apply 5.NF.B.4 fraction multiplication or 4.OA.A.1 "
                "'multiplication makes larger' intuition, hit a contradiction when a "
                "multiplier with large numerator/denominator is still less than 1, and "
                "must compare each multiplier to 1 whole."
            ),
        },
    },
    {
        "id": "g6_unit_rate_comparison",
        "target_code": "6.RP.A.3.b",
        "grade": 6,
        "subject": "mathematics",
        "domain": "Ratios and Proportional Relationships",
        "topic": "unit rates for comparing pricing and constant speed",
        "target_concept": (
            "Solving unit rate problems (a/b per 1 unit of b) to compare ratio "
            "relationships across different quantities or durations."
        ),
        "exclude_prior_terms": [
            "normalize both options to a per-unit rate to compare",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Describe ratio relationships (6.RP.A.1), tables of equivalent whole-number "
                "ratios (6.RP.A.3.a), and fraction as division (5.NF.B.3)."
            ),
            "s_target_summary": (
                "Solve unit rate problems to compare options with unequal "
                "denominators (6.RP.A.3.b)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states the unit-rate division rule directly or uses only single-number "
                "addition/subtraction without ratio quantities."
            ),
            "score_1_loose_match": (
                "Denominators are equal or integer multiples so whole-number scaling "
                "settles the comparison without unit rates."
            ),
            "score_2_exact_bridge": (
                "Students can start with ratio tables or additive differences (a - b), "
                "see that raw totals and additive gaps disagree across unequal denominators, "
                "and must normalize to a per-unit rate."
            ),
        },
    },
    {
        "id": "g6_polygon_area_decomposition",
        "target_code": "6.G.A.1",
        "grade": 6,
        "subject": "mathematics",
        "domain": "Geometry",
        "topic": "area of triangles and polygons by composition and decomposition",
        "target_concept": (
            "Finding the area of triangles, special quadrilaterals, and composite "
            "polygons by composing into rectangles or decomposing into rectangles and triangles."
        ),
        "exclude_prior_terms": [
            "triangle area formula",
            "1/2 base times height",
            "trapezoid area formula",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Apply area and perimeter formulas for rectangles (4.MD.A.3) and "
                "multiply fractions/whole numbers (5.NF.B.4)."
            ),
            "s_target_summary": (
                "Find area of non-rectangular triangles and polygons via composition or "
                "decomposition into rectangles (6.G.A.1)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 gives away 1/2 * b * h or trapezoid formulas, or only asks for "
                "the area of a plain rectangle."
            ),
            "score_1_loose_match": (
                "Task can be solved by a single rectangle length * width calculation "
                "without decomposition."
            ),
            "score_2_exact_bridge": (
                "Students can apply rectangle area/perimeter, find that multiplying "
                "slanted sides or comparing perimeters fails on the non-rectangular shape, "
                "and must enclose or dissect the figure into rectangles."
            ),
        },
    },
    {
        "id": "g6_fraction_division_quotients",
        "target_code": "6.NS.A.1",
        "grade": 6,
        "subject": "mathematics",
        "domain": "The Number System",
        "topic": "interpreting and computing quotients of fractions in word problems",
        "target_concept": (
            "Interpreting and computing quotients of general fractions (a/b) / (c/d) "
            "by reasoning about how many fractional groups of size c/d fit into a/b, "
            "including fractional parts of a group."
        ),
        "exclude_prior_terms": [
            "invert and multiply",
            "multiply by the reciprocal",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Divide unit fractions by whole numbers and whole numbers by unit "
                "fractions (5.NF.B.7) using inverse multiplication (3.OA.B.6)."
            ),
            "s_target_summary": (
                "Compute quotients of non-unit fractions and interpret fractional "
                "remainders in terms of the divisor unit (6.NS.A.1)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states 'multiply by the reciprocal' or only divides by a unit "
                "fraction 1/n where 5.NF.B.7 already suffices."
            ),
            "score_1_loose_match": (
                "The dividend is an exact integer multiple of the divisor fraction so no "
                "fractional remainder of a batch occurs."
            ),
            "score_2_exact_bridge": (
                "Students can partition into unit fractions using 5.NF.B.7, hit a leftover "
                "piece when grouping by a non-unit fraction c/d, and must express the "
                "remainder as a fraction of the c/d batch rather than of the whole."
            ),
        },
    },
    {
        "id": "g6_absolute_value_vs_signed_order",
        "target_code": "6.NS.C.7.d",
        "grade": 6,
        "subject": "mathematics",
        "domain": "The Number System",
        "topic": "distinguishing comparisons of absolute value from statements about signed order",
        "target_concept": (
            "Distinguishing comparisons of magnitude (absolute value |x|, distance from "
            "zero or reference target) from comparisons of signed order on the number line."
        ),
        "exclude_prior_terms": [
            "absolute value bars |x|",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Order positive and negative numbers on a number line (6.NS.C.7.a-b) and "
                "recognize distance from 0 (6.NS.C.7.c)."
            ),
            "s_target_summary": (
                "Distinguish signed order from magnitude of change or deviation in context "
                "(6.NS.C.7.d)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 tells students to take absolute values, or uses only positive numbers."
            ),
            "score_1_loose_match": (
                "Signed order and magnitude order give the same winner (for example, "
                "comparing positive deviations)."
            ),
            "score_2_exact_bridge": (
                "Students can order the signed numbers on a number line (e.g., -18 < -7), "
                "which gives the opposite ranking from the largest magnitude change or "
                "closest distance to the target reference."
            ),
        },
    },
    {
        "id": "g7_average_speed_complex_rates",
        "target_code": "7.RP.A.1",
        "grade": 7,
        "subject": "mathematics",
        "domain": "Ratios and Proportional Relationships",
        "topic": "unit rates and average speed across fractional or multi-stage intervals",
        "target_concept": (
            "Computing unit rates associated with ratios of fractions or multi-stage "
            "quantities, including overall rates across intervals measured in like or "
            "different units."
        ),
        "exclude_prior_terms": [
            "harmonic mean",
            "total distance divided by total elapsed time",
            "weighted average of speeds",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": ("Understand simple unit rate a/b for a single ratio (6.RP.A.2)."),
            "s_target_summary": (
                "Compute unit rates across fractional or composite quantities (7.RP.A.1)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states total distance divided by total time as a given formula, "
                "or omits rate relationships."
            ),
            "score_1_loose_match": (
                "Single-stage unit rate (or unweighted mean of stage speeds) already "
                "gives the right answer because stage times are equal."
            ),
            "score_2_exact_bridge": (
                "Students can compute each stage's unit rate using 6.RP.A.2, but "
                "averaging those stage rates conflicts with the complete journey time "
                "when stage durations differ."
            ),
        },
    },
    {
        "id": "g7_proportional_vs_offset_relationships",
        "target_code": "7.RP.A.2",
        "grade": 7,
        "subject": "mathematics",
        "domain": "Ratios and Proportional Relationships",
        "topic": "recognizing and representing proportional relationships",
        "target_concept": (
            "Recognizing and representing proportional relationships between quantities "
            "and deciding whether two quantities are in a proportional relationship."
        ),
        "exclude_prior_terms": [
            "constant of proportionality",
            "y = kx",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Compute single unit rates and equivalent ratios (6.RP.A.2, 6.RP.A.3, 7.RP.A.1)."
            ),
            "s_target_summary": (
                "Recognize and test whether a relationship across multiple pairs is "
                "proportional (7.RP.A.2)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 defines constant of proportionality y/x = k up front, or only asks "
                "for arithmetic subtraction."
            ),
            "score_1_loose_match": (
                "A single ratio pair or constant additive step settles the question without "
                "exposing the difference between constant gap and constant ratio."
            ),
            "score_2_exact_bridge": (
                "Students can compute single ratios or constant differences from 6.RP, "
                "hit a conflict between equal additive steps and equal ratios across "
                "multiple pairs, and must test multiplicative invariance."
            ),
        },
    },
    {
        "id": "g7_comparative_sampling_center_and_variability",
        "target_code": "7.SP.B.4",
        "grade": 7,
        "subject": "mathematics",
        "domain": "Statistics and Probability",
        "topic": "comparing two populations using measures of center and variability",
        "target_concept": (
            "Using measures of center and measures of variability for numerical data from "
            "random samples to draw informal comparative inferences about two populations."
        ),
        "exclude_prior_terms": [
            "two-sample t-test",
            "difference in centers as a multiple of variability",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Draw single-sample inferences (7.SP.A.2) and compute basic center/spread "
                "on one distribution (6.SP.B.5, 7.SP.B.3)."
            ),
            "s_target_summary": (
                "Compare two populations by coordinating center and variability (7.SP.B.4)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 prescribes the comparative center-to-variability decision rule, "
                "or requires no statistical summary."
            ),
            "score_1_loose_match": (
                "One sample has both a higher mean and tighter spread, so comparing means "
                "alone already settles the decision."
            ),
            "score_2_exact_bridge": (
                "Students can compute sample means and ranges from 6.SP/7.SP.A.2, find "
                "that mean or range ties (or conflicts with sample consistency), and must "
                "account for interior variability across all sample observations."
            ),
        },
    },
    {
        "id": "g7_multistep_percent_change",
        "target_code": "7.RP.A.3",
        "grade": 7,
        "subject": "mathematics",
        "domain": "Ratios and Proportional Relationships",
        "topic": "multistep ratio and successive percent change problems",
        "target_concept": (
            "Using proportional relationships to solve multistep ratio and percent "
            "problems such as markups, markdowns, taxes, and percent increase or decrease."
        ),
        "exclude_prior_terms": [
            "compound multiplier (1 + p)(1 - q)",
            "successive percent formula",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Find a single percent of a fixed quantity as a rate per 100 (6.RP.A.3.c) "
                "and represent proportional relationships (7.RP.A.2)."
            ),
            "s_target_summary": (
                "Chain multistep percent changes across changing base quantities (7.RP.A.3)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states that successive percents multiply or must be applied to the "
                "new base, or includes only a single-step percent."
            ),
            "score_1_loose_match": (
                "Both options apply a single percent to the same initial base, so adding "
                "percentages gives the right ranking."
            ),
            "score_2_exact_bridge": (
                "Students can compute single percentages from 6.RP.A.3, try adding two "
                "successive percent changes (e.g., +25% then -25% = 0%), and discover a "
                "conflict with step-by-step dollar tracking on the updated base."
            ),
        },
    },
    {
        "id": "g7_scale_drawing_area_vs_length",
        "target_code": "7.G.A.1",
        "grade": 7,
        "subject": "mathematics",
        "domain": "Geometry",
        "topic": "scale drawings of geometric figures: lengths versus areas",
        "target_concept": (
            "Solving problems involving scale drawings of geometric figures, including "
            "coordinating how linear scale factors affect both side lengths and areas."
        ),
        "exclude_prior_terms": [
            "area scales by the square of the scale factor",
            "k^2 area scaling rule",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Find polygon areas (6.G.A.1) and apply linear proportional scaling to "
                "lengths (7.RP.A.2)."
            ),
            "s_target_summary": (
                "Compute actual lengths and areas from scale drawings across different "
                "scales (7.G.A.1)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states the k^2 area scaling rule or only asks for a single scaled "
                "side length."
            ),
            "score_1_loose_match": (
                "Comparing linear perimeters or unscaled drawing areas already gives the "
                "same winner."
            ),
            "score_2_exact_bridge": (
                "Students can compute the drawing's area (6.G.A.1) and scale lengths "
                "(7.RP.A.2), find that multiplying drawing area once by the linear scale "
                "factor disagrees with converting both dimensions first, and must "
                "coordinate two-dimensional scaling."
            ),
        },
    },
    {
        "id": "g7_theoretical_vs_empirical_probability",
        "target_code": "7.SP.C.7",
        "grade": 7,
        "subject": "mathematics",
        "domain": "Statistics and Probability",
        "topic": "comparing theoretical probability models to observed frequencies",
        "target_concept": (
            "Developing a probability model from the structure of the chance process "
            "and comparing its theoretical probabilities against observed frequencies."
        ),
        "exclude_prior_terms": [
            "theoretical sample space formula",
            "law of large numbers",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Approximate probability from observed relative frequency in trials "
                "(7.SP.C.6) and solve ratio/percent problems (7.RP.A.3)."
            ),
            "s_target_summary": (
                "Construct a theoretical probability model and reconcile discrepancies "
                "with observed trial frequencies (7.SP.C.7)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 gives away the theoretical probabilities of each outcome, or "
                "includes no chance mechanism."
            ),
            "score_1_loose_match": (
                "Observed frequencies in the small sample already match the theoretical ranking."
            ),
            "score_2_exact_bridge": (
                "Students can compute observed relative frequencies (7.SP.C.6) or count "
                "outcome labels, which predicts the opposite winner from enumeration of "
                "the underlying equally likely outcomes."
            ),
        },
    },
    {
        "id": "g8_proportional_slope_across_representations",
        "target_code": "8.EE.B.5",
        "grade": 8,
        "subject": "mathematics",
        "domain": "Expressions and Equations",
        "topic": "comparing proportional relationships across graphs, tables, and equations",
        "target_concept": (
            "Interpreting the unit rate as the slope of a proportional graph and "
            "comparing two proportional relationships given in different representations "
            "(such as a table or verbal rate versus coordinate points on scaled axes)."
        ),
        "exclude_prior_terms": [
            "slope formula (y2 - y1)/(x2 - x1)",
            "unit rate is the slope",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Recognize and represent a single proportional relationship in a table "
                "or ratio pair (7.RP.A.2)."
            ),
            "s_target_summary": (
                "Compare two proportional relationships across different representations "
                "and axis scales by coordinating slope/unit rate (8.EE.B.5)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states the slope formula or puts both options in the exact same "
                "single-column table."
            ),
            "score_1_loose_match": (
                "Comparing raw y-values at a single shared x-value settles the question "
                "without translating representations."
            ),
            "score_2_exact_bridge": (
                "Students can read values from each representation using 7.RP.A.2, but "
                "unmatched x-intervals or axis scales make direct visual/row comparison "
                "fail until both are normalized to a common rate of change."
            ),
        },
    },
    {
        "id": "g8_linear_function_rate_and_initial_value",
        "target_code": "8.F.B.4",
        "grade": 8,
        "subject": "mathematics",
        "domain": "Functions",
        "topic": "constructing a linear function with rate of change and initial value",
        "target_concept": (
            "Constructing a linear relationship y = mx + b from two (x, y) observations "
            "by separating the constant rate of change (m) from a non-zero initial value (b)."
        ),
        "exclude_prior_terms": [
            "two-point slope formula",
            "point-slope form",
            "solve for m and b",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Proportional relationships y = kx through the origin (7.RP.A.2) and "
                "recognizing y = mx + b qualitatively (8.F.A.3)."
            ),
            "s_target_summary": (
                "Determine both rate of change and non-zero initial value from two (x, y) "
                "values or a table (8.F.B.4)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 gives the initial value b = 0 (pure proportion) or states the "
                "(y2 - y1)/(x2 - x1) procedure."
            ),
            "score_1_loose_match": (
                "The initial value (x = 0) is explicitly given in the table, so single-step "
                "subtraction gives the rate."
            ),
            "score_2_exact_bridge": (
                "Students can try the 7.RP.A.2 shortcut of dividing y/x at one point, "
                "discover that y1/x1 != y2/x2 because of an unstated base amount, and "
                "must use the change between two points to isolate the per-unit rate."
            ),
        },
    },
    {
        "id": "g8_simultaneous_linear_equations",
        "target_code": "8.EE.C.8",
        "grade": 8,
        "subject": "mathematics",
        "domain": "Expressions and Equations",
        "topic": "analyzing and solving pairs of simultaneous linear constraints",
        "target_concept": (
            "Analyzing and solving pairs of simultaneous linear equations where two "
            "independent linear relationships or constraints must be satisfied jointly."
        ),
        "exclude_prior_terms": [
            "system of linear equations",
            "elimination method",
            "substitution method for two variables",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Solve single-variable linear equations px + q = r (7.EE.B.4.a), check "
                "values by substitution (6.EE.B.5), and use constant rate/slope (8.EE.B.6)."
            ),
            "s_target_summary": (
                "Coordinate two simultaneous linear relationships to find the unique pair "
                "or intersection point (8.EE.C.8)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 writes out the two-variable system and elimination steps, or only "
                "imposes a single linear constraint."
            ),
            "score_1_loose_match": (
                "One constraint alone determines the answer without needing the second constraint."
            ),
            "score_2_exact_bridge": (
                "Students can satisfy the first constraint using 7.EE.B.4.a or trial "
                "substitution (6.EE.B.5), see that naive splits violate the second "
                "constraint, and must use the per-item rate difference to satisfy both."
            ),
        },
    },
    {
        "id": "g8_pythagorean_coordinate_distance",
        "target_code": "8.G.B.8",
        "grade": 8,
        "subject": "mathematics",
        "domain": "Geometry",
        "topic": "finding straight-line distance between points in the coordinate plane",
        "target_concept": (
            "Applying the Pythagorean Theorem to determine the straight-line distance "
            "between two points in a coordinate plane by forming a right triangle from "
            "horizontal and vertical coordinate differences."
        ),
        "exclude_prior_terms": [
            "distance formula sqrt((x2-x1)^2 + (y2-y1)^2)",
            "construct a right triangle from coordinate differences",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Find lengths of horizontal and vertical segments in the coordinate plane "
                "(6.G.A.3) and apply the Pythagorean Theorem on a given right triangle "
                "(8.G.B.7)."
            ),
            "s_target_summary": (
                "Find diagonal distance between coordinate points where no triangle is "
                "drawn (8.G.B.8)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states the coordinate distance formula, or places all points on "
                "the same horizontal/vertical line."
            ),
            "score_1_loose_match": (
                "Grid distance (|dx| + |dy|) and straight-line distance rank the candidate "
                "routes in the same order."
            ),
            "score_2_exact_bridge": (
                "Students can compute horizontal and vertical coordinate steps (6.G.A.3), "
                "find that Manhattan sum (|dx| + |dy|) ranks two diagonal paths opposite "
                "to their true straight-line length, and must form right-triangle legs."
            ),
        },
    },
    {
        "id": "g9_linear_vs_exponential_growth",
        "target_code": "HSF-LE.A.1",
        "grade": 9,
        "subject": "mathematics",
        "domain": "Functions - Linear, Quadratic, and Exponential Models",
        "topic": "distinguishing linear growth from exponential growth over equal intervals",
        "target_concept": (
            "Distinguishing situations modeled by linear functions (constant additive "
            "change over equal intervals) from exponential functions (constant "
            "multiplicative factor over equal intervals)."
        ),
        "exclude_prior_terms": [
            "exponential function formula a * b^x",
            "geometric sequence formula",
            "constant multiplicative factor",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Construct linear functions with constant rate of change (8.F.A.3, 8.F.B.4) "
                "and describe qualitative graph changes (8.F.B.5)."
            ),
            "s_target_summary": (
                "Distinguish constant additive change from constant multiplicative factor "
                "over equal intervals (HSF-LE.A.1)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 names exponential equations y = a*b^x or only includes linear options."
            ),
            "score_1_loose_match": (
                "The comparison ends at an early interval where linear extrapolation and "
                "multiplicative growth give the same ranking."
            ),
            "score_2_exact_bridge": (
                "Students can apply 8.F.B.4 constant-difference extrapolation from the "
                "first interval, which predicts the opposite long-term winner from the "
                "multiplicative pattern."
            ),
        },
    },
    {
        "id": "g9_conditional_probability_two_way_tables",
        "target_code": "HSS-CP.B.6",
        "grade": 9,
        "subject": "mathematics",
        "domain": "Statistics and Probability - Conditional Probability",
        "topic": "conditional probability of A given B in two-way frequency tables",
        "target_concept": (
            "Finding the conditional probability of A given B as the fraction of B's "
            "outcomes that also belong to A, and interpreting the answer in terms of "
            "the model."
        ),
        "exclude_prior_terms": [
            "conditional probability formula P(A and B)/P(B)",
            "restrict the denominator to subgroup B",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Compute compound probabilities over the full sample space (7.SP.C.8) and "
                "describe events as subsets of a sample space (HSS-CP.A.1, HSS-CP.A.3)."
            ),
            "s_target_summary": (
                "Compute and interpret conditional probabilities P(A|B) as fractions of "
                "the conditioning subgroup B (HSS-CP.B.6)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states which row or column total to divide by, or provides no "
                "cross-classified counts."
            ),
            "score_1_loose_match": (
                "Subgroup totals are equal, so raw joint counts and conditional rates give "
                "the same winner."
            ),
            "score_2_exact_bridge": (
                "Students can compute fractions of the grand total (7.SP.C.8) or compare "
                "raw cell counts, which gives the opposite ranking from the rate within "
                "each unequal conditioning subgroup."
            ),
        },
    },
    {
        "id": "g10_distribution_spread_and_outliers",
        "target_code": "HSS-ID.A.2",
        "grade": 10,
        "subject": "mathematics",
        "domain": "Statistics and Probability - Interpreting Categorical and Quantitative Data",
        "topic": "comparing center and spread across data distributions",
        "target_concept": (
            "Using statistics appropriate to the shape of the data distribution to "
            "compare center and spread of two or more different data sets."
        ),
        "exclude_prior_terms": [
            "standard deviation formula",
            "sample variance formula",
            "root mean square deviation",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Compute mean, median, range, and informal visual overlap (6.SP.A.2, "
                "6.SP.A.3, 6.SP.B.5, 7.SP.B.3, 7.SP.B.4)."
            ),
            "s_target_summary": (
                "Compare center and spread across distributions using a distribution-wide "
                "measure (HSS-ID.A.2)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 gives away variance/standard deviation in student text or prior "
                "knowledge, or provides no numerical distributions to compare."
            ),
            "score_1_loose_match": (
                "Mean or range differs between the groups, so 6.SP mean/range settles "
                "the comparison without needing a spread measure across all observations."
            ),
            "score_2_exact_bridge": (
                "Students can compute 6.SP mean and range, find that both tie across the "
                "groups while internal clustering differs, and must construct a deviation "
                "measure using all observations."
            ),
        },
    },
    {
        "id": "g5_fraction_as_division_equal_sharing",
        "target_code": "5.NF.B.3",
        "grade": 5,
        "subject": "mathematics",
        "domain": "Number and Operations - Fractions",
        "topic": "interpreting a fraction as division of the numerator by the denominator",
        "target_concept": (
            "Interpreting a fraction a/b as division of the numerator by the denominator "
            "(a divided by b) and solving equal-sharing word problems leading to "
            "fractional or mixed-number quotients."
        ),
        "exclude_prior_terms": [
            "a/b = a divided by b",
            "fraction as quotient rule",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Whole-number division and equal sharing (3.OA.A.2, 3.OA.B.6) and "
                "multiplicative comparison (4.OA.A.1, 4.OA.A.2)."
            ),
            "s_target_summary": (
                "Interpret non-integer quotients a / b as exact fractional shares a/b (5.NF.B.3)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states the a/b = a divided by b rule directly, or uses dividends "
                "that divide evenly into whole numbers."
            ),
            "score_1_loose_match": (
                "Whole-number quotient and remainder ordering already agrees with exact "
                "per-person share ordering."
            ),
            "score_2_exact_bridge": (
                "Students can divide whole numbers with remainders (3.OA/4.OA), find that "
                "whole-number quotients or raw remainders tie across unequal group sizes, "
                "and must partition the remainder into fractional shares of the divisor."
            ),
        },
    },
    {
        "id": "g5_two_numerical_patterns_relationships",
        "target_code": "5.OA.B.3",
        "grade": 5,
        "subject": "mathematics",
        "domain": "Operations and Algebraic Thinking",
        "topic": (
            "generating two numerical patterns and identifying relationships "
            "between corresponding terms"
        ),
        "target_concept": (
            "Generating two numerical patterns using two given rules and identifying "
            "relationships between corresponding terms across the two sequences."
        ),
        "exclude_prior_terms": [
            "linear relation between sequences",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Generate a single number pattern from a given step-by-step rule and "
                "identify features of that single sequence (4.OA.C.5)."
            ),
            "s_target_summary": (
                "Coordinate two numerical patterns simultaneously to express the "
                "relationship between corresponding terms (5.OA.B.3)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states the cross-sequence formula relating the two patterns, or "
                "only asks about one sequence."
            ),
            "score_1_loose_match": (
                "Listing the first two or three terms of one pattern settles the question "
                "without relating corresponding terms across both patterns."
            ),
            "score_2_exact_bridge": (
                "Students can extend each pattern step-by-step (4.OA.C.5), see that term-by-term "
                "listing becomes impractical or that initial lead reverses, and must relate "
                "corresponding terms across the two rules."
            ),
        },
    },
    {
        "id": "g6_prism_volume_fractional_edges",
        "target_code": "6.G.A.2",
        "grade": 6,
        "subject": "mathematics",
        "domain": "Geometry",
        "topic": "volume of right rectangular prisms with fractional edge lengths",
        "target_concept": (
            "Finding the volume of a right rectangular prism with fractional edge lengths "
            "by packing it with unit fraction cubes and relating fractional cube counts "
            "to multiplying the edge lengths."
        ),
        "exclude_prior_terms": [
            "fractional cube packing formula",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Find the volume of a right rectangular prism with whole-number side "
                "lengths by packing unit cubes and multiplying l * w * h (5.MD.C.5.a-b)."
            ),
            "s_target_summary": (
                "Coordinate fractional unit-cube packing and volume for prisms with "
                "fractional edge lengths (6.G.A.2)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states how many (1/k)-edge cubes fit in 1 cubic unit, or uses only "
                "whole-number edge lengths."
            ),
            "score_1_loose_match": (
                "Comparing a single edge or whole-number unit cubes already settles the question."
            ),
            "score_2_exact_bridge": (
                "Students can apply whole-number prism volume (5.MD.C.5), hit a discrepancy "
                "between counting 1/k-edge cubes along one dimension versus three dimensions, "
                "and must coordinate fractional edge scaling across all three dimensions."
            ),
        },
    },
    {
        "id": "g6_measure_of_center_vs_variation",
        "target_code": "6.SP.A.3",
        "grade": 6,
        "subject": "mathematics",
        "domain": "Statistics and Probability",
        "topic": "distinguishing a measure of center from a measure of variation in a data set",
        "target_concept": (
            "Recognizing that a measure of center for a numerical data set summarizes all "
            "of its values with a single number, while a measure of variation describes "
            "how its values vary with a single number."
        ),
        "exclude_prior_terms": [
            "mean absolute deviation",
            "interquartile range",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Recognize statistical variability (6.SP.A.1) and describe the overall "
                "distribution of a data set collected to answer a question (6.SP.A.2)."
            ),
            "s_target_summary": (
                "Distinguish what a single-number summary of center captures from what a "
                "single-number summary of variation captures (6.SP.A.3)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 defines formal spread measures up front or provides only a single "
                "data value."
            ),
            "score_1_loose_match": (
                "Center and spread rank the data sets in the same direction so one summary "
                "number suffices."
            ),
            "score_2_exact_bridge": (
                "Students can inspect the distributions or compute a single total/average "
                "(6.SP.A.2), see that identical totals/averages mask opposite consistency "
                "patterns, and must separate center from variation."
            ),
        },
    },
    {
        "id": "g8_comparing_functions_across_representations",
        "target_code": "8.F.A.2",
        "grade": 8,
        "subject": "mathematics",
        "domain": "Functions",
        "topic": "comparing properties of two functions represented in different ways",
        "target_concept": (
            "Comparing properties of two functions each represented in a different way "
            "(algebraically, graphically, numerically in tables, or by verbal descriptions)."
        ),
        "exclude_prior_terms": [
            "convert both functions to y = mx + b",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Understand functions as input-output rules (8.F.A.1) and analyze "
                "proportional rates/slopes through the origin (7.RP.A.2, 8.EE.B.5, 8.EE.B.6)."
            ),
            "s_target_summary": (
                "Compare rates of change and initial values across two functions with "
                "different representations and starting offsets (8.F.A.2)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 presents both functions in the same representation with the rate "
                "and initial value already labeled."
            ),
            "score_1_loose_match": (
                "Both functions start at 0 or one function dominates at every input value."
            ),
            "score_2_exact_bridge": (
                "Students can read outputs or compute y/x from 7.RP.A.2/8.EE.B.5, find "
                "that higher early outputs conflict with the per-unit rate across representations, "
                "and must separate rate of change from starting value."
            ),
        },
    },
    {
        "id": "g8_linear_model_bivariate_data",
        "target_code": "8.SP.A.3",
        "grade": 8,
        "subject": "mathematics",
        "domain": "Statistics and Probability",
        "topic": (
            "using a linear model for bivariate measurement data to interpret slope and intercept"
        ),
        "target_concept": (
            "Using a linear model to solve problems in the context of bivariate "
            "measurement data and interpreting the slope and intercept in context."
        ),
        "exclude_prior_terms": [
            "least-squares regression formula",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Informally fit a straight line to a scatter plot that suggests a linear "
                "association and judge closeness of points to the line (8.SP.A.2)."
            ),
            "s_target_summary": (
                "Extract and coordinate the contextual rate of change (slope) and baseline "
                "(intercept) of a linear model across noisy bivariate data (8.SP.A.3)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 gives the fitted linear equation and states the meaning of its slope "
                "and intercept."
            ),
            "score_1_loose_match": (
                "All data points lie on an exact proportional line through (0, 0) with no "
                "scatter or baseline offset."
            ),
            "score_2_exact_bridge": (
                "Students can connect two single noisy points or take a single y/x ratio, "
                "see that noisy point-to-point jumps conflict with the overall trend and "
                "baseline offset, and must model both trend rate and intercept."
            ),
        },
    },
    {
        "id": "g9_average_rate_of_change_nonlinear",
        "target_code": "HSF-IF.B.6",
        "grade": 9,
        "subject": "mathematics",
        "domain": "Functions - Interpreting Functions",
        "topic": (
            "calculating and interpreting the average rate of change of a function over an interval"
        ),
        "target_concept": (
            "Calculating and interpreting the average rate of change of a function "
            "(presented symbolically or as a table) over a specified interval."
        ),
        "exclude_prior_terms": [
            "secant slope formula (f(b) - f(a)) / (b - a)",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Construct linear functions with constant rate of change from two (x, y) "
                "values (8.F.B.4)."
            ),
            "s_target_summary": (
                "Compute and interpret the average rate of change of a nonlinear or "
                "variable-step function over a specified interval (HSF-IF.B.6)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states (f(b) - f(a))/(b - a) or uses a purely linear function "
                "where every interval has the same slope."
            ),
            "score_1_loose_match": (
                "All table intervals have equal step sizes so raw row differences already "
                "rank the intervals correctly."
            ),
            "score_2_exact_bridge": (
                "Students can compute raw output changes or single-step slopes (8.F.B.4), "
                "find that unequal interval widths or curvature make raw changes and unweighted "
                "averages of sub-slopes fail, and must normalize total change by interval width."
            ),
        },
    },
    {
        "id": "g9_independent_events_probability",
        "target_code": "HSS-CP.A.2",
        "grade": 9,
        "subject": "mathematics",
        "domain": "Statistics and Probability - Conditional Probability",
        "topic": "understanding and testing whether two events are independent",
        "target_concept": (
            "Understanding that two events A and B are independent if the probability "
            "of A and B occurring together is the product of their probabilities, and "
            "using this characterization to determine if they are independent."
        ),
        "exclude_prior_terms": [
            "P(A and B) = P(A) * P(B) independence test",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Find probabilities of compound events using tables or lists (7.SP.C.8) "
                "and describe events as subsets of a sample space (HSS-CP.A.1)."
            ),
            "s_target_summary": (
                "Determine whether two events are independent by comparing joint "
                "proportions against marginal proportions (HSS-CP.A.2)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states the P(A and B) = P(A)P(B) rule directly in student text or "
                "prior knowledge."
            ),
            "score_1_loose_match": (
                "Subgroup sizes are equal so raw overlap counts already settle independence."
            ),
            "score_2_exact_bridge": (
                "Students can count overlap outcomes in the sample space (7.SP.C.8/HSS-CP.A.1), "
                "confuse non-zero overlap (mutually exclusive vs independent) or raw overlap "
                "count with independence, and must compare overlap rate to overall baseline rate."
            ),
        },
    },
    {
        "id": "g10_density_area_and_volume_modeling",
        "target_code": "HSG-MG.A.2",
        "grade": 10,
        "subject": "mathematics",
        "domain": "Geometry - Modeling with Geometry",
        "topic": "applying concepts of density based on area and volume in modeling situations",
        "target_concept": (
            "Applying concepts of density based on area and volume in modeling "
            "situations (such as population per unit area or mass per unit volume)."
        ),
        "exclude_prior_terms": [
            "density = mass / volume",
            "population density formula",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Compute one-dimensional unit rates associated with ratios of quantities "
                "(7.RP.A.1)."
            ),
            "s_target_summary": (
                "Coordinate multi-dimensional area or volume measurements with total "
                "quantity to compare densities (HSG-MG.A.2)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 gives the area/volume already computed and states the density "
                "formula, reducing the task to a single 7.RP.A.1 division."
            ),
            "score_1_loose_match": (
                "Regions have the same area/volume or the same linear side length ranking "
                "as their area/volume density."
            ),
            "score_2_exact_bridge": (
                "Students can divide quantity by a single linear dimension or perimeter "
                "(7.RP.A.1), find that linear rate disagrees with true 2D/3D crowding when "
                "shapes or dimensions differ, and must normalize by computed area or volume."
            ),
        },
    },
    {
        "id": "g10_quadratic_completing_square_extrema",
        "target_code": "HSA-SSE.B.3.b",
        "grade": 10,
        "subject": "mathematics",
        "domain": "Algebra - Seeing Structure in Expressions",
        "topic": (
            "rewriting a quadratic expression to reveal the maximum or minimum "
            "value of the function"
        ),
        "target_concept": (
            "Completing the square in a quadratic expression to reveal the maximum or "
            "minimum value of the function it defines."
        ),
        "exclude_prior_terms": [
            "vertex formula -b/(2a)",
            "completing the square vertex form a(x - h)^2 + k",
        ],
        "bridge_rubric_anchor": {
            "s_prior_summary": (
                "Add, subtract, factor, and expand linear/algebraic expressions (7.EE.A.1) "
                "and rewrite expressions in different forms to shed light on a problem (7.EE.A.2)."
            ),
            "s_target_summary": (
                "Locate the exact extremum of a quadratic relationship and justify why no "
                "input can exceed or fall below it (HSA-SSE.B.3.b)."
            ),
            "score_0_boundary_miss": (
                "D1/D3 states x = -b/(2a) or gives the expression already in vertex form "
                "a(x - h)^2 + k."
            ),
            "score_1_loose_match": (
                "The maximum/minimum occurs at a listed integer table value where neighboring "
                "symmetric points are already shown."
            ),
            "score_2_exact_bridge": (
                "Students can evaluate or factor the expression at whole-number inputs "
                "(7.EE.A.1-2), find two symmetric inputs that tie while the true peak/trough "
                "lies between them, and must use symmetry or a squared-deviation form to "
                "pin down the exact extremum."
            ),
        },
    },
]


def _validate_license(record: dict[str, Any], record_type: str) -> None:
    props = record.get("properties", {})
    lic = props.get("license") if isinstance(props, dict) else None
    if lic not in ALLOWED_LICENSES:
        raise ValueError(
            f"{record_type} {record.get('identifier')} has unapproved license: {lic!r}"
        )
    if "/licenses/by/4.0/" in lic and not props.get("attributionStatement"):
        raise ValueError(
            f"{record_type} {record.get('identifier')} is CC BY 4.0 without attribution"
        )


def _compact_node(node: dict[str, Any]) -> dict[str, Any]:
    props = node.get("properties", {})
    return {
        "identifier": node["identifier"],
        "caseIdentifierUUID": props.get("caseIdentifierUUID"),
        "statementCode": props.get("statementCode"),
        "gradeLevel": props.get("gradeLevel"),
        "academicSubject": props.get("academicSubject"),
        "jurisdiction": props.get("jurisdiction"),
        "description": props.get("description"),
        "author": props.get("author"),
        "provider": props.get("provider"),
        "license": props.get("license"),
        "attributionStatement": props.get("attributionStatement"),
    }


def build_dataset(
    source_dir: Path = DEFAULT_SOURCE_DIR,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    slice_dir: Path = DEFAULT_SLICE_DIR,
) -> dict[str, Any]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Learning Commons export directory not found: {source_dir}")

    target_codes = {spec["target_code"] for spec in CASE_SPECS}
    builds_towards: dict[str, list[dict[str, Any]]] = defaultdict(list)
    supports: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for edge in read_jsonl(source_dir / "relationships.jsonl"):
        label = edge.get("label")
        if label == "buildsTowards":
            builds_towards[edge["target_identifier"]].append(edge)
        elif label == "supports":
            supports[edge["target_identifier"]].append(edge)

    target_id_by_code: dict[str, str] = {}
    for node in read_jsonl(source_dir / "nodes.jsonl"):
        if "StandardsFrameworkItem" not in node.get("labels", []):
            continue
        code = node.get("properties", {}).get("statementCode")
        nid = node.get("identifier")
        if code in target_codes and nid in builds_towards:
            target_id_by_code[code] = nid

    missing_codes = sorted(target_codes - target_id_by_code.keys())
    if missing_codes:
        raise ValueError(f"Target codes missing buildsTowards edges: {missing_codes}")

    needed_node_ids: set[str] = set()
    kept_edges: dict[str, dict[str, Any]] = {}
    for code, tid in target_id_by_code.items():
        needed_node_ids.add(tid)
        for edge in builds_towards[tid]:
            _validate_license(edge, "relationship")
            kept_edges[edge["identifier"]] = edge
            pid = edge["source_identifier"]
            needed_node_ids.add(pid)
            for comp_edge in supports.get(pid, []):
                _validate_license(comp_edge, "relationship")
                kept_edges[comp_edge["identifier"]] = comp_edge
                needed_node_ids.add(comp_edge["source_identifier"])
        for comp_edge in supports.get(tid, []):
            _validate_license(comp_edge, "relationship")
            kept_edges[comp_edge["identifier"]] = comp_edge
            needed_node_ids.add(comp_edge["source_identifier"])

    nodes_by_id: dict[str, dict[str, Any]] = {}
    for node in read_jsonl(source_dir / "nodes.jsonl"):
        nid = node.get("identifier")
        if nid in needed_node_ids:
            _validate_license(node, "node")
            nodes_by_id[nid] = node

    if len(nodes_by_id) != len(needed_node_ids):
        missing = sorted(needed_node_ids - nodes_by_id.keys())
        raise ValueError(f"Missing node records in export: {missing}")

    cases: list[dict[str, Any]] = []
    for spec in CASE_SPECS:
        tid = target_id_by_code[spec["target_code"]]
        target_node = _compact_node(nodes_by_id[tid])
        prereq_edges = sorted(
            builds_towards[tid],
            key=lambda e: (
                nodes_by_id[e["source_identifier"]]["properties"].get("statementCode") or "",
                e["source_identifier"],
            ),
        )
        prereq_standards = [
            _compact_node(nodes_by_id[e["source_identifier"]]) for e in prereq_edges
        ]
        prereq_components: list[dict[str, Any]] = []
        seen_comp: set[str] = set()
        for e in prereq_edges:
            pid = e["source_identifier"]
            p_code = nodes_by_id[pid]["properties"].get("statementCode")
            for comp_edge in sorted(supports.get(pid, []), key=lambda ce: ce["source_identifier"]):
                cid = comp_edge["source_identifier"]
                if cid in seen_comp:
                    continue
                seen_comp.add(cid)
                comp = _compact_node(nodes_by_id[cid])
                comp["supports_standard_code"] = p_code
                prereq_components.append(comp)

        target_components = [
            {
                **_compact_node(nodes_by_id[ce["source_identifier"]]),
                "supports_standard_code": spec["target_code"],
            }
            for ce in sorted(supports.get(tid, []), key=lambda ce: ce["source_identifier"])
        ]

        cases.append(
            {
                "id": spec["id"],
                "grade": spec["grade"],
                "subject": spec["subject"],
                "domain": spec["domain"],
                "topic": spec["topic"],
                "target_concept": spec["target_concept"],
                "exclude_prior_terms": spec["exclude_prior_terms"],
                "progression_bridge": {
                    "target_standard": target_node,
                    "prerequisite_standards_builds_towards": prereq_standards,
                    "prerequisite_learning_components": prereq_components,
                    "target_learning_components": target_components,
                },
                "bridge_rubric_anchor": spec["bridge_rubric_anchor"],
            }
        )

    dataset = {
        "schema_version": SCHEMA_VERSION,
        "source_version": "Learning Commons Knowledge Graph v1.14.0",
        "evaluation_measure": {
            "name": "progression_bridge_fit",
            "scale": [0, 1, 2],
            "labels": {
                "0": "Boundary Miss (leaks target standard or skips prerequisite skill)",
                "1": (
                    "Loose Topic Match (uses prerequisite, but prerequisite solves "
                    "the task without an impasse)"
                ),
                "2": (
                    "Exact Progression Bridge (starts with prerequisite skill and hits "
                    "a built-in limit that motivates the target standard)"
                ),
            },
        },
        "n_cases": len(cases),
        "cases": cases,
    }

    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text(
        json.dumps(dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    slice_dir.mkdir(parents=True, exist_ok=True)
    sorted_nodes = [nodes_by_id[k] for k in sorted(nodes_by_id)]
    sorted_edges = [kept_edges[k] for k in sorted(kept_edges)]
    (slice_dir / "nodes.jsonl").write_text(
        "".join(
            json.dumps(n, ensure_ascii=False, separators=(",", ":")) + "\n" for n in sorted_nodes
        ),
        encoding="utf-8",
    )
    (slice_dir / "relationships.jsonl").write_text(
        "".join(
            json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n" for e in sorted_edges
        ),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source_version": "v1.14.0",
        "n_cases": len(cases),
        "n_nodes": len(sorted_nodes),
        "n_relationships": len(sorted_edges),
        "target_codes": [
            c["progression_bridge"]["target_standard"]["statementCode"] for c in cases
        ],
    }
    (slice_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return dataset


def load_progression_bridge_dataset(
    dataset_path: Path = DEFAULT_DATASET_PATH,
) -> dict[str, Any]:
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unexpected schema_version in {dataset_path}")
    return data


def progression_bridge_bundle(
    case_id: str,
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
) -> dict[str, Any]:
    """Return the Learning Commons grounding bundle for a dataset case."""
    dataset = load_progression_bridge_dataset(dataset_path)
    case = next((c for c in dataset["cases"] if c["id"] == case_id), None)
    if case is None:
        raise KeyError(f"Unknown progression bridge case: {case_id}")
    bridge = case["progression_bridge"]
    return {
        "source": dataset["source_version"],
        "case_id": case["id"],
        "usage_rule": (
            "Use prerequisite_standards_builds_towards and prerequisite_learning_components "
            "to ground the student's prior-knowledge starting methods (S_prior). Use "
            "target_standard only to align the invention goal (S_target); never leak "
            "target_standard or target_learning_components as already taught."
        ),
        "target_standards": [
            {
                "statementCode": bridge["target_standard"]["statementCode"],
                "gradeLevel": bridge["target_standard"]["gradeLevel"],
                "description": bridge["target_standard"]["description"],
            }
        ],
        "prerequisite_standards_builds_towards": [
            {
                "statementCode": s["statementCode"],
                "gradeLevel": s["gradeLevel"],
                "description": s["description"],
            }
            for s in bridge["prerequisite_standards_builds_towards"]
        ],
        "supporting_learning_components": [
            {
                "supports_standard_code": c["supports_standard_code"],
                "gradeLevel": c["gradeLevel"],
                "description": c["description"],
            }
            for c in bridge["prerequisite_learning_components"]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--dataset-path", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--slice-dir", type=Path, default=DEFAULT_SLICE_DIR)
    args = parser.parse_args()
    dataset = build_dataset(args.source_dir, args.dataset_path, args.slice_dir)
    for case in dataset["cases"]:
        b = case["progression_bridge"]
        t_code = b["target_standard"]["statementCode"]
        p_codes = [p["statementCode"] for p in b["prerequisite_standards_builds_towards"]]
        n_pcomp = len(b["prerequisite_learning_components"])
        n_tcomp = len(b["target_learning_components"])
        print(
            f"{case['id']:<48} G{case['grade']:<2} | "
            f"{p_codes} --buildsTowards--> {t_code} "
            f"(prereq_comps={n_pcomp}, target_comps={n_tcomp})"
        )


if __name__ == "__main__":
    main()

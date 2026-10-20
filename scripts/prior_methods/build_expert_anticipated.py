"""Extract expert-anticipated student methods from data/pf_exercises YAMLs.

Implements the strategy extension in PRIOR_METHODS_BENCHMARK.md section 11.
Sources differ in schema across the four expert YAMLs:
- loibl_rummel_2014:  expected_student_solutions (list of dicts)
- kapur_bielaczyc_2012: expected_student_rsms (list of dicts)
- puech_macina_2025_stratl: expected_student_rsms (flat list of strings)
- kerrigan_weber_chinn_2021: expected_student_behaviors (flat list of strings)

Types: correct_but_insufficient / partial_canonical / misconception.
Mapping: leads_to_solution=false -> correct_but_insufficient (a method students
legitimately bring that falls short); leads_to_solution=true -> partial_canonical;
behavioral strings (Kerrigan) -> correct_but_insufficient unless clearly not a method.
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EXERCISES = ROOT / "data" / "pf_exercises"
OUT = ROOT / "experiments" / "data" / "prior_methods_benchmark" / "expert_anticipated.json"

# Closest benchmark concept per exercise (for the descriptive comparison).
CONCEPT_LINK = {
    "loibl2014_invention_1": ["x_range", "x_avgfreq"],
    "puech2025_consistency": ["x_range", "x_avgfreq"],
    "kapur2012_complex_1": ["c4_partwhole"],
    "kerrigan2021_invention_1": [],
}

NOT_A_METHOD = {"Discover the standoff (Cleo & Beatrice both need piece 2)",
                "Struggle with resolution — this is where productive failure occurs"}


def norm_dict_method(m: dict) -> dict:
    leads = m.get("leads_to_solution", False)
    return {
        "name": m.get("name", "").strip(),
        "description": (m.get("description") or "").strip(),
        "why_fails": (m.get("why_fails") or "").strip() or None,
        "type": "partial_canonical" if leads else "correct_but_insufficient",
    }


def norm_str_method(s: str) -> dict | None:
    text = s.strip()
    if text in NOT_A_METHOD:
        return None
    return {
        "name": text,
        "description": "",
        "why_fails": None,
        "type": "correct_but_insufficient",
    }


def main() -> None:
    records = []
    for path in sorted(EXERCISES.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        source = data["metadata"]["source"]
        for ex in data.get("exercises", []):
            ex_id = ex.get("id")
            if ex.get("phase") != "generation":
                continue
            methods = []
            for key in ("expected_student_solutions", "expected_student_rsms"):
                for m in ex.get(key) or []:
                    if isinstance(m, dict):
                        methods.append(norm_dict_method(m))
                    elif isinstance(m, str):
                        nm = norm_str_method(m)
                        if nm:
                            methods.append(nm)
            for b in ex.get("expected_student_behaviors") or []:
                nm = norm_str_method(str(b))
                if nm:
                    methods.append(nm)
            if not methods:
                continue
            records.append({
                "exercise": ex_id,
                "source": source,
                "topic": ex.get("topic"),
                "closest_benchmark_concepts": CONCEPT_LINK.get(ex_id, []),
                "methods": methods,
            })

    OUT.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    for r in records:
        types = {}
        for m in r["methods"]:
            types[m["type"]] = types.get(m["type"], 0) + 1
        linked = r["closest_benchmark_concepts"]
        print(f"{r['exercise']:28s} methods={len(r['methods']):2d} {types} -> {linked}")


if __name__ == "__main__":
    main()

"""Inventory saved generated PF tasks without generating, judging, or repairing them.

The JSON catalog is an immutable, provenance-bearing input to later measurement.
Only exact (student text, recorded target, normalized learner context) triples merge.
Run from the repository: python scripts/build_pf_measure_catalog.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("experiments/results/pf_measure_campaign_20261014/catalog.json")
SCHEMA_VERSION = "pf-saved-measure-catalog/v1"
TASK_FIELDS = ("title", "body", "question")
CONTEXT_FIELDS = (
    "grade",
    "subject",
    "jurisdiction",
    "age_range",
    "language",
    "profile_status",
    "prior_boundary",
    "topic",
)
INTERNAL_HEADING = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*|\*{2})?(?:CONSOLIDATION(?: NOTE)?|"
    r"(?:WORKED |MODEL |SUGGESTED )?SOLUTIONS?|TEACHER(?: ONLY| NOTES?| COMMENTARY)?|"
    r"INTERNAL(?: DESIGN)? NOTES?|EXPECTED STUDENT (?:SOLUTIONS?|ATTEMPTS?))"
    r"(?:\s*\*{2})?(?:\s*[:(]|\s*$)"
)
COPY_PARTS = {
    "judgments",
    "ratings",
    "gallery",
    "model_review",
    "audit",
    "audits",
    "evidence_audit",
    "review",
    "inputs",
}
COPY_NAMES = {
    "summary.json",
    "assessment.json",
    "inspection.json",
    "scores.json",
    "all_tasks.json",
    "calibration_tasks.json",
    "evaluator_input.json",
    "all_tasks_legacy_list.json",
    "calibration_tasks_legacy_list.json",
    "evaluator_input_legacy_list.json",
    "judgment.json",
    "rating.json",
    "blind_mapping_private.json",
    "source_result.json",
}
WRITER_STAGE = re.compile(
    r"(?:^D3[.]|writer|^V[123][.]generate$|^V1[.]gpt|^direct[.]generate$|"
    r"^direct_once$|^task[.]revision$)",
    re.I,
)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pointer_get(value: Any, pointer: str) -> Any:
    for part in pointer.strip("/").split("/") if pointer else []:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return None
    return value


def strip_internal(text: str) -> str:
    match = INTERNAL_HEADING.search(text)
    return text[: match.start()].rstrip() if match else text


def parse_saved_json(text: Any) -> Any:
    if not isinstance(text, str):
        return None
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)[:-3].strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def student_text(task: Any) -> tuple[str | None, str]:
    """Extract only explicit student fields; never stringify an entire envelope."""
    if isinstance(task, str):
        parsed = parse_saved_json(task)
        if isinstance(parsed, dict):
            return student_text(parsed)
        if task.lstrip().startswith(("{", "[")):
            return None, "unparseable_structured_task"
        text = strip_internal(task)
        return (text if text.strip() else None), "explicit_student_text"
    if not isinstance(task, dict):
        return None, "no_student_task"
    if isinstance(task.get("sections"), dict):
        sections = task["sections"]
        allowed = ("TITLE", "NARRATIVE", "BODY", "TASK", "QUESTION")
        parts = [
            strip_internal(sections[key])
            for key in allowed
            if isinstance(sections.get(key), str) and sections[key].strip()
        ]
        if not any(sections.get(key) for key in ("TASK", "QUESTION")):
            return None, "incomplete_formatted_sections"
        return "\n\n".join(part for part in parts if part) or None, "formatted_student_sections"
    if isinstance(task.get("body"), str) and isinstance(task.get("question"), str):
        if not task["body"].strip() or not task["question"].strip():
            return None, "incomplete_student_fields"
        return "\n\n".join(
            strip_internal(task[key])
            for key in TASK_FIELDS
            if isinstance(task.get(key), str) and task[key].strip()
        ), "title_body_question"
    for key in ("student_task", "task_text"):
        if isinstance(task.get(key), str):
            return student_text(task[key])
    return None, "incomplete_student_fields"


def normalize_context(context: Any) -> dict | None:
    if not isinstance(context, dict):
        return None
    normalized = {
        key: value
        for key, value in context.items()
        if key
        not in {
            "assumed_prior_knowledge",
            "recently_taught",
            "teacher_recently_taught",
            "teacher_skills",
            "target_concept",
            "learning_target",
            "benchmark_context",
            "misconceptions",
            "expected_errors",
            "solutions",
            "target_method",
        }
    }
    history = None
    for key in (
        "assumed_prior_knowledge",
        "recently_taught",
        "teacher_recently_taught",
        "teacher_skills",
    ):
        if key in context and isinstance(context[key], list):
            history = context[key]
            break
    if history is not None:
        resources = []
        for item in history:
            if isinstance(item, str):
                resources.append({"resource": item, "taught_as": None})
            elif isinstance(item, dict) and "resource" in item:
                resources.append({"resource": item["resource"], "taught_as": item.get("taught_as")})
            else:
                resources.append({"unmapped_recorded_prerequisite": item})
        # Reordering an identical repertoire is not a different prerequisite context.
        normalized["assumed_prior_knowledge"] = sorted(resources, key=canonical)
    return normalized or None


def has_history(context: Any) -> bool:
    if not isinstance(context, dict) or not isinstance(
        context.get("assumed_prior_knowledge"), list
    ):
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get("resource"), str)
        and bool(item["resource"].strip())
        and (item.get("taught_as") is None or isinstance(item.get("taught_as"), str))
        for item in context["assumed_prior_knowledge"]
    )


def labeled_json(text: Any, label: str) -> Any:
    if not isinstance(text, str):
        return None
    match = re.search(re.escape(label) + r"\s*:\s*", text, re.I)
    if match:
        try:
            return json.JSONDecoder().raw_decode(text[match.end() :].lstrip())[0]
        except ValueError:
            pass
    return None


def is_copy(path: Path) -> bool:
    parts = path.parts
    name = path.name.lower()
    return (
        any("snapshot" in part or "legacy_batches" in part for part in parts)
        or any(part in COPY_PARTS for part in parts)
        or path.name in COPY_NAMES
        or any(
            word in name
            for word in (
                "catalog",
                "review_packet",
                "review_key",
                "review_rating",
                "rerating",
                "text_pattern_audit",
                "independent_math",
                "numeric_inputs",
                "blind",
            )
        )
        or "judgment" in name
        or "rubric_review" in name
    )


class Inventory:
    def __init__(self, root: Path, results: Path, excluded: Path | None = None):
        self.root = root.resolve()
        self.results = results
        self.excluded = excluded
        self.documents: dict[Path, Any] = {}
        self.hashes: dict[Path, str] = {}
        self.files: list[dict] = []
        self.parse_errors: list[dict] = []
        self.missing_sources: set[tuple[str, str]] = set()
        self.cases: dict[str, dict] = {}
        self.unassessable: list[dict] = []
        self.terminal: list[dict] = []
        self.references: list[dict] = []
        self.context_cache: dict[Path, list[tuple[dict, dict]]] = {}

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def source(self, path: Path, pointer: str = "") -> dict:
        if path not in self.hashes:
            self.hashes[path] = digest(path.read_bytes())
        return {
            "path": self.relative(path),
            "sha256": self.hashes[path],
            "json_pointer": pointer,
        }

    def safe_path(self, recorded: Any, near: Path) -> Path | None:
        if not isinstance(recorded, str) or not recorded:
            return None
        raw = Path(recorded)
        candidates = [raw] if raw.is_absolute() else [self.root / raw, near.parent / raw]
        if "/experiments/" in recorded:
            candidates.append(self.root / "experiments" / recorded.split("/experiments/", 1)[1])
        for path in candidates:
            path = path.resolve()
            if (
                path.is_relative_to(self.root)
                and not any(
                    part.startswith(".") or any(s in part.lower() for s in ("credential", "secret"))
                    for part in path.relative_to(self.root).parts
                )
                and path.is_file()
                and not path.is_symlink()
            ):
                return path
        self.missing_sources.add((self.relative(near), recorded))
        return None

    def scan(self) -> None:
        for path in sorted(self.results.rglob("*")):
            if (
                not path.is_file()
                or path.is_symlink()
                or (self.excluded and path.is_relative_to(self.excluded))
                or any(
                    part.startswith(".")
                    or any(word in part.lower() for word in ("credential", "secret"))
                    for part in path.relative_to(self.results).parts
                )
            ):
                continue
            data = path.read_bytes()
            self.hashes[path] = digest(data)
            entry = {
                "path": self.relative(path),
                "sha256": self.hashes[path],
                "format": path.suffix.lstrip("."),
                "bytes": len(data),
                "disposition": "non_record_artifact",
            }
            self.files.append(entry)
            if path.suffix not in {".json", ".jsonl"}:
                continue
            entry["disposition"] = "inspected_json"
            try:
                text = data.decode("utf-8")
                if path.suffix == ".json":
                    self.documents[path] = json.loads(text)
                else:
                    records = []
                    for line_number, line in enumerate(text.splitlines(), 1):
                        if not line.strip():
                            continue
                        try:
                            records.append((line_number, json.loads(line)))
                        except ValueError as error:
                            self.parse_errors.append(
                                {
                                    **self.source(path),
                                    "line": line_number,
                                    "error": str(error),
                                }
                            )
                    self.documents[path] = records
            except (ValueError, UnicodeError) as error:
                entry["disposition"] = "parse_error"
                self.parse_errors.append({**self.source(path), "error": str(error)})

    def document(self, path: Path) -> Any:
        if path in self.documents:
            return self.documents[path]
        if path.is_file() and path.suffix == ".json":
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                self.documents[path] = value
                return value
            except (ValueError, UnicodeError):
                return None
        return None

    def evidence_objects(self, path: Path) -> list[tuple[dict, dict]]:
        if path in self.context_cache:
            return self.context_cache[path]
        objects = []
        # Start events retain the request when finish events retain only the response.
        for name in ("model_calls.jsonl", "model_trace.jsonl", "direct_calls.jsonl"):
            candidate = path.parent / name
            for line, value in self.documents.get(candidate, []):
                if (
                    isinstance(value, dict)
                    and WRITER_STAGE.search(str(value.get("stage", "")))
                    and any(key in value for key in ("user_prompt", "user"))
                ):
                    objects.append((value, self.source(candidate, f"/line/{line}")))
        for directory in [path.parent, *path.parent.parents]:
            if not directory.is_relative_to(self.results):
                break
            for name in (
                "input.json",
                "result.json",
                "source_result.json",
                "d1.json",
                "config.json",
                "shared_context.json",
                "manifest.json",
                "protocol.json",
            ):
                candidate = directory / name
                if candidate == path:
                    continue
                value = self.document(candidate)
                if isinstance(value, dict):
                    objects.append((value, self.source(candidate)))
                    if name == "manifest.json":
                        config = value.get("config_path")
                        if config:
                            linked = self.safe_path(config, candidate)
                            expected = value.get("config_sha256")
                            if linked and expected and digest(linked.read_bytes()) == expected:
                                saved = self.document(linked)
                                if isinstance(saved, dict):
                                    objects.append((saved, self.source(linked)))
                        if value.get("config_sha256"):
                            for linked, sha in list(self.hashes.items()):
                                if sha == value["config_sha256"] and linked.suffix == ".json":
                                    saved = self.document(linked)
                                    if isinstance(saved, dict):
                                        objects.append((saved, self.source(linked)))
                        # Some runs retain a hash rather than a configuration snapshot.
                        if value.get("config_sha256") and not isinstance(value.get("config"), dict):
                            for linked in sorted(
                                (self.root / "experiments/configs").glob("*.json")
                            ):
                                if (
                                    linked.is_symlink()
                                    or linked.name.startswith(".")
                                    or any(
                                        word in linked.name.lower()
                                        for word in ("credential", "secret")
                                    )
                                ):
                                    continue
                                if digest(linked.read_bytes()) == value["config_sha256"]:
                                    saved = self.document(linked)
                                    if isinstance(saved, dict):
                                        objects.append((saved, self.source(linked)))
            if directory == self.results:
                break
        self.context_cache[path] = objects
        return objects

    @staticmethod
    def variants(value: dict, source: dict, record: dict) -> list[tuple[dict, dict]]:
        variants = [(value, source)]
        for key in ("case_input", "case", "config", "frozen_inputs", "shared_context"):
            if isinstance(value.get(key), dict):
                child = value[key]
                ref = {**source, "json_pointer": source["json_pointer"] + "/" + key}
                variants.extend(Inventory.variants(child, ref, record))
        for key in ("cells", "cases", "calibration_cases"):
            items = value.get(key)
            if isinstance(items, list):
                for index, item in enumerate(items):
                    if isinstance(item, dict) and (
                        item.get("cell_id") == record.get("cell_id")
                        and record.get("cell_id")
                        or item.get("id") in (record.get("case_id"), record.get("case"))
                        and item.get("id") is not None
                    ):
                        ref = {**source, "json_pointer": source["json_pointer"] + f"/{key}/{index}"}
                        variants.extend(Inventory.variants(item, ref, record))
        return variants

    def inputs(
        self, path: Path, record: dict, source_pointer: str = "", parent: dict | None = None
    ) -> tuple[Any, Any, list[dict], dict]:
        base = [(record, self.source(path, source_pointer))]
        if parent and parent is not record:
            base.append((parent, self.source(path)))
        base.extend(
            (value, source)
            for value, source in self.evidence_objects(path)
            if not (
                record.get("call_id")
                and value.get("call_id")
                and source["path"] == self.relative(path)
                and record["call_id"] != value["call_id"]
            )
        )
        for value, source in list(base):
            for key in ("source_result", "reused_from"):
                if isinstance(value.get(key), str):
                    linked = self.safe_path(value[key], self.root / source["path"])
                    if linked:
                        saved = self.document(linked)
                        expected = value.get("source_sha256") if key == "source_result" else None
                        if isinstance(saved, dict) and (
                            not expected or digest(linked.read_bytes()) == expected
                        ):
                            base.append((saved, self.source(linked)))
        objects = []
        for value, source in base:
            objects.extend(self.variants(value, source, record))
        target = None
        target_ref = None
        context = None
        context_ref = None
        # Explicit learner records take priority over derived D1 resource lists.
        for value, source in objects:
            for key in ("learning_target", "target_concept", "internal_learning_target"):
                if target is None and isinstance(value.get(key), str) and value[key].strip():
                    target = value[key]
                    target_ref = {**source, "field": key}
            for key in (
                "learner_context",
                "new_writer_context",
                "student_context",
                "writer_context",
            ):
                candidate = value.get(key)
                if isinstance(candidate, dict) and "student_context" in candidate:
                    candidate = candidate["student_context"]
                normalized = normalize_context(candidate)
                if context is None and has_history(normalized):
                    context, context_ref = normalized, {**source, "field": key}
        for value, source in objects:
            for key in (
                "user_prompt",
                "user",
                "writer_request",
                "new_writer_request",
                "planned_writer_request",
            ):
                prompt = value.get(key)
                if isinstance(prompt, dict):
                    prompt = prompt.get("user") or prompt.get("user_prompt")
                saved_prompt = parse_saved_json(prompt)
                if isinstance(saved_prompt, dict):
                    if context is None and has_history(
                        normalize_context(saved_prompt.get("learner_context"))
                    ):
                        context = normalize_context(saved_prompt["learner_context"])
                        context_ref = {**source, "field": key, "prompt_field": "learner_context"}
                    if target is None and isinstance(
                        saved_prompt.get("internal_learning_target"), str
                    ):
                        target = saved_prompt["internal_learning_target"]
                        target_ref = {
                            **source,
                            "field": key,
                            "prompt_field": "internal_learning_target",
                        }
                for label in ("STUDENT CONTEXT", "LEARNER CONTEXT", "SHARED CONTEXT"):
                    saved = labeled_json(prompt, label)
                    if isinstance(saved, dict):
                        candidate = saved.get("learner_context", saved)
                        normalized = normalize_context(candidate)
                        if context is None and has_history(normalized):
                            context, context_ref = (
                                normalized,
                                {**source, "field": key, "label": label},
                            )
                if target is None:
                    for label in ("TARGET CONCEPT", "LEARNING TARGET", "TARGET"):
                        if isinstance(prompt, str):
                            match = re.search(r"(?:^|\n)" + label + r":\s*([^\n]+)", prompt, re.I)
                            if match:
                                target = match.group(1).strip()
                                target_ref = {**source, "field": key, "label": label}
                                break
        # Study arm-specific context is saved separately from each attempt.
        for value, source in objects:
            schedule = value.get("schedule")
            if isinstance(schedule, list):
                for item in schedule:
                    if not isinstance(item, dict) or not item.get("attempt_path"):
                        continue
                    directory = (self.root / source["path"]).parent
                    if path.is_relative_to(directory / item["attempt_path"]):
                        shared = (
                            directory / "inputs" / item["case_id"] / f"context_{item['arm']}.json"
                        )
                        saved = self.document(shared)
                        if isinstance(saved, dict):
                            normalized = normalize_context(saved.get("learner_context"))
                            if has_history(normalized):
                                context, context_ref = (
                                    normalized,
                                    {**self.source(shared), "field": "learner_context"},
                                )
        if context is None:
            for value, source in objects:
                prior = value.get("prior_context")
                if isinstance(prior, dict) and isinstance(prior.get("recommendations"), list):
                    case = value.get("case_input") or value.get("case")
                    candidate = {
                        key: case[key]
                        for key in CONTEXT_FIELDS
                        if isinstance(case, dict) and key in case
                    }
                    candidate["assumed_prior_knowledge"] = prior["recommendations"]
                    context, context_ref = (
                        normalize_context(candidate),
                        {**source, "field": "prior_context.recommendations"},
                    )
                    break
        if context is None:
            for value, source in objects:
                records = value.get("records")
                if not isinstance(records, list):
                    continue
                matching = [
                    item
                    for item in records
                    if isinstance(item, dict)
                    and (len(records) == 1 or item.get("case_id") == record.get("case_id"))
                ]
                for item in matching:
                    result = item.get("result", {})
                    recommendations = (
                        result.get("recommendations") if isinstance(result, dict) else None
                    )
                    if isinstance(recommendations, list):
                        context = normalize_context({"assumed_prior_knowledge": recommendations})
                        context_ref = {**source, "field": "records.result.recommendations"}
                        break
                if context is not None:
                    break
        if context is None:
            for value, source in objects:
                if any(
                    isinstance(value.get(key), list)
                    for key in (
                        "assumed_prior_knowledge",
                        "recently_taught",
                        "teacher_recently_taught",
                        "teacher_skills",
                    )
                ):
                    candidate = {
                        key: value[key]
                        for key in (
                            *CONTEXT_FIELDS,
                            "assumed_prior_knowledge",
                            "recently_taught",
                            "teacher_recently_taught",
                            "teacher_skills",
                        )
                        if key in value
                    }
                    context, context_ref = normalize_context(candidate), source
                    break
        refs = [ref for ref in (target_ref, context_ref) if ref]
        provenance = {}
        for value, source in objects:
            for key in (
                "schema_version",
                "d1_mode",
                "frozen_settings",
                "settings",
                "protocol",
                "source_hashes",
                "source_provenance",
                "prior_context",
                "input_artifacts",
                "case_input_provenance",
                "condition",
                "arm",
                "phase",
            ):
                if key in value:
                    provenance.setdefault(key, []).append(
                        {
                            **source,
                            "field": key,
                            "recorded_value": value[key]
                            if key in {"schema_version", "d1_mode", "condition", "arm", "phase"}
                            else None,
                        }
                    )
        return target, context, refs, provenance

    def run_id(self, path: Path) -> str:
        for directory in [path.parent, *path.parent.parents]:
            if not directory.is_relative_to(self.results):
                break
            if (directory / "manifest.json").is_file():
                return self.relative(directory)
        return self.relative(path.parent)

    def occurrence(self, path: Path, record: dict, pointer: str, role: str, task: Any) -> dict:
        parts = path.parts
        companion_path = path.parent / "study_attempt.json"
        companion = self.document(companion_path)
        metadata = companion if isinstance(companion, dict) else {}
        condition = record.get("condition")
        if condition is None:
            condition = next(
                (p for p in reversed(parts) if p in {"V1", "V2", "V3", "PIPELINE"}), None
            )
        if condition == "PIPELINE" or "stages" in record or "pipeline" in parts:
            method = "pipeline"
        elif condition in {"V1", "V2", "V3"} or "direct" in parts or "cell_id" in record:
            method = "direct"
        elif "writer" in str(record.get("stage", "")).lower():
            method = "pipeline_writer"
        elif any("revision" in part for part in parts):
            method = "task_revision"
        else:
            method = "unavailable"
        status = record.get("status")
        task_status = task.get("status") if isinstance(task, dict) else None
        flagged = (
            bool(record.get("quality_findings"))
            or isinstance(task, dict)
            and (
                task.get("quality_status") not in (None, "", "pass", "passed", "ready")
                or bool(task.get("quality_findings"))
                or bool(task.get("blocking_issues"))
            )
        )
        invalid = (
            isinstance(status, str)
            and (
                status.startswith("invalid")
                or status in {"failed", "parse_error", "error", "api_error"}
            )
        ) or task_status not in (None, "ready", "usable", "produced")
        return {
            "source": self.source(path, pointer),
            "record_role": role,
            "run_id": self.run_id(path),
            "method": method,
            "condition": condition,
            "arm": record.get("arm") or metadata.get("arm"),
            "phase": record.get("phase") or metadata.get("phase"),
            "attempt_id": record.get("attempt_id")
            or record.get("key")
            or record.get("id")
            or metadata.get("task_id"),
            "case_id": record.get("case_id") or record.get("cell_id") or record.get("case"),
            "repeat": record.get("repeat")
            or record.get("number")
            or record.get("index")
            or metadata.get("repeat"),
            "model": record.get("model_name")
            or record.get("model_requested")
            or record.get("model"),
            "stage": record.get("stage"),
            "call_id": record.get("call_id"),
            "saved_status": status,
            "saved_task_status": task_status,
            "envelope_status": "invalid"
            if invalid
            else ("flagged_usable_draft" if flagged else "as_saved"),
            "error": record.get("error"),
            "quality_status": task.get("quality_status") if isinstance(task, dict) else None,
            "quality_findings": task.get("quality_findings") if isinstance(task, dict) else None,
            "finish_reason": record.get("finish_reason"),
            "truncated": record.get("truncated") or record.get("effective_truncation"),
            "companion_attempt_source": self.source(companion_path) if metadata else None,
        }

    def add(
        self,
        path: Path,
        record: dict,
        pointer: str,
        task: Any,
        role: str,
        parent: dict | None = None,
        terminal: bool = False,
    ) -> None:
        text, extraction = student_text(task)
        if text is None:
            for key in ("task_raw_text", "raw_text", "raw_response"):
                parsed = parse_saved_json(record.get(key))
                recovered, mode = student_text(parsed)
                if recovered:
                    text, extraction = recovered, "saved_raw_json/" + mode
                    break
        target, context, refs, historical = self.inputs(path, record, pointer, parent)
        occurrence = self.occurrence(path, record, pointer, role, task)
        occurrence["extraction"] = extraction
        occurrence["input_sources"] = refs
        occurrence["historical_condition_evidence"] = historical
        input_status = {
            "student_task": "available" if text else "unavailable",
            "learning_target": "available" if target else "unavailable",
            "learner_prerequisites": "available" if has_history(context) else "unavailable",
            "empty_recorded_prerequisite_list": bool(
                has_history(context) and not context["assumed_prior_knowledge"]
            ),
        }
        if terminal:
            self.terminal.append(
                {
                    "source_path": self.relative(path),
                    "run_id": occurrence["run_id"],
                    "method": occurrence["method"],
                    "condition": occurrence["condition"],
                    "saved_status": occurrence["saved_status"],
                    "has_student_task": bool(text),
                }
            )
        if not text:
            self.unassessable.append(
                {
                    "student_task": None,
                    "learning_target": target,
                    "learner_context": context,
                    "input_status": input_status,
                    "reason": extraction,
                    "occurrences": [occurrence],
                }
            )
            return
        key = digest(canonical([text, target, context]).encode("utf-8"))
        if key not in self.cases:
            self.cases[key] = {
                "case_id": "pf-" + key[:20],
                "student_task": text,
                "learning_target": target,
                "learner_context": context,
                "occurrences": [],
                "input_status": input_status,
            }
        self.cases[key]["occurrences"].append(occurrence)

    def roots(self, path: Path, value: Any) -> None:
        if not isinstance(value, dict):
            return
        if path.name == "human_evaluation_pool_round1_deepseek.json":
            for index, record in enumerate(value.get("records", [])):
                if isinstance(record, dict) and isinstance(record.get("exercise"), dict):
                    self.add(
                        path,
                        {**record, **record["exercise"]},
                        f"/records/{index}/exercise",
                        record["exercise"],
                        "surviving_legacy_generation_pool",
                        value,
                        terminal=True,
                    )
            return
        if is_copy(path) or path.name in {
            "input.json",
            "config.json",
            "protocol.json",
            "manifest.json",
            "d1.json",
            "fixed_d1.json",
            "completed.json",
            "study_attempt.json",
        }:
            self.copy_references(path, value)
            return
        if "phase1_mcq" in path.parts or "prior_methods_benchmark" in path.parts:
            return
        stage = (
            value.get("stages", {}).get("D2_D3") if isinstance(value.get("stages"), dict) else None
        )
        if isinstance(stage, dict):
            self.add(
                path,
                value,
                "/stages/D2_D3/task",
                stage.get("task"),
                "generation_result",
                terminal=True,
            )
            self.writer_attempts(path, value, stage.get("task"), "/stages/D2_D3/task")
        elif "task" in value and any(
            key in value
            for key in (
                "status",
                "case",
                "case_id",
                "attempt_id",
                "key",
                "model",
                "model_selector",
                "reused_from",
                "source_result",
                "writer_request",
            )
        ):
            role = (
                "attempt_result_mirror"
                if path.name == "attempt.json" and (path.parent / "result.json").is_file()
                else "generation_result"
            )
            self.add(
                path, value, "/task", value["task"], role, terminal=role != "attempt_result_mirror"
            )
            self.writer_attempts(path, value, value["task"], "/task")
        elif path.name == "attempt.json" and value.get("attempt_id"):
            result = self.document(path.parent / "result.json")
            if not isinstance(result, dict):
                self.add(path, value, "", None, "original_attempt", terminal=True)
        elif path.name == "result.json" and (
            "case_input" in value
            or str(value.get("schema_version", "")).startswith("pf-diagnostic")
        ):
            self.add(path, value, "", None, "generation_result", terminal=True)

    def writer_attempts(self, path: Path, record: dict, task: Any, pointer: str) -> None:
        if not isinstance(task, dict):
            return
        for index, attempt in enumerate(task.get("writer_attempts", [])):
            if isinstance(attempt, dict):
                self.add(
                    path,
                    attempt,
                    pointer + f"/writer_attempts/{index}/payload",
                    attempt.get("payload"),
                    "writer_attempt",
                    parent=record,
                )

    def trace(self, path: Path, line: int, value: Any) -> None:
        if not isinstance(value, dict) or is_copy(path):
            return
        stage = str(value.get("stage", ""))
        if path.name == "deleted_api_errors.jsonl":
            if value.get("stage") in {"generation", "generate"}:
                self.add(path, value, f"/line/{line}", None, "failed_original_attempt")
            return
        if not WRITER_STAGE.search(stage):
            if path.name != "model_trace.jsonl" or "attempts" not in path.parts:
                return
            if not any("pf_rahimi_scale_comparison" in part for part in path.parts):
                return
        if value.get("event") in {"model_call_started", "start"}:
            return
        if not any(key in value for key in ("payload", "raw_text", "raw_response", "error")):
            return
        parsed = value.get("payload")
        if not isinstance(parsed, dict):
            parsed = parse_saved_json(value.get("raw_text") or value.get("raw_response"))
        task = parsed.get("task", parsed) if isinstance(parsed, dict) else None
        self.add(path, value, f"/line/{line}", task, "generation_call_trace")

    def copy_references(self, path: Path, value: Any, pointer: str = "") -> None:
        if isinstance(value, dict):
            task = value.get("task") or value.get("student_task")
            if task:
                text, _ = student_text(task)
                if text:
                    self.references.append(
                        {
                            "student_task": text,
                            "source": self.source(path, pointer),
                            "recorded_origin": value.get("source_path")
                            or value.get("source_result"),
                            "recorded_origin_sha256": value.get("source_sha256"),
                        }
                    )
            for key, item in value.items():
                if isinstance(item, (dict, list)) and key not in {
                    "task",
                    "student_task",
                    "source_hashes",
                }:
                    self.copy_references(path, item, pointer + "/" + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                self.copy_references(path, item, pointer + f"/{index}")

    def link_references(self) -> dict:
        by_text = defaultdict(list)
        for case in self.cases.values():
            by_text[case["student_task"]].append(case)
        linked = 0
        orphan = []
        for reference in self.references:
            candidates = by_text.get(reference.pop("student_task"), [])
            if reference["recorded_origin"]:
                origin = reference["recorded_origin"]
                exact = [
                    case
                    for case in candidates
                    if any(
                        item["source"]["path"] == origin
                        or origin.endswith("/" + item["source"]["path"])
                        for item in case["occurrences"]
                    )
                ]
                candidates = exact or candidates
            if candidates:
                for case in candidates:
                    case.setdefault("origin_references", []).append(
                        {
                            **reference,
                            "link_basis": "exact_student_text",
                            "context_match_asserted": False,
                        }
                    )
                linked += 1
            else:
                orphan.append(reference)
        return {"linked_copy_records": linked, "unmatched_copy_records": orphan}

    def summary(self, copy_summary: dict) -> dict:
        runs = defaultdict(lambda: Counter())
        for row in self.terminal:
            run = runs[row["run_id"]]
            run["terminal_records"] += 1
            run["with_student_task" if row["has_student_task"] else "without_student_task"] += 1
            run["condition:" + str(row["condition"])] += 1
            run["status:" + str(row["saved_status"])] += 1
            run["method:" + row["method"]] += 1
        cases = list(self.cases.values())
        checks = []
        specifications = [
            ("multi_theme_main", "pf_rahimi_multi_theme_20261013/main_30", 240, 238),
            ("benchmark_v1", "pf_paper_benchmark/20260923_luna_v1", 120, None),
            ("benchmark_v2", "pf_paper_benchmark/20260923_luna_v2", 120, 10),
            ("benchmark_v3", "pf_paper_benchmark/20260923_luna_v3", 120, 12),
            ("benchmark_v4", "pf_paper_benchmark/20260923_luna_v4", 120, None),
        ]
        for name, suffix, expected, ready in specifications:
            rows = [
                row
                for row in self.terminal
                if row["run_id"].endswith(suffix)
                and "/attempts/" in row["source_path"]
                and not "/pipeline/" in row["source_path"]  # noqa: E713 - Preserve frozen AST.
            ]
            if rows:
                ready_count = sum(row["saved_status"] == "ready" for row in rows)
                checks.append(
                    {
                        "name": name,
                        "expected_terminal_records": expected,
                        "observed_terminal_records": len(rows),
                        "observed_with_student_task": sum(row["has_student_task"] for row in rows),
                        "expected_ready": ready,
                        "observed_ready": ready_count,
                        "pending_unexecuted_slots": sum(
                            row["saved_status"] == "pending" for row in rows
                        ),
                        "pass": len(rows) == expected and (ready is None or ready_count == ready),
                        "by_condition": dict(Counter(row["condition"] for row in rows)),
                    }
                )
        for name, fragment, expected in [
            (
                "latest_method_comparison_fresh",
                "pf_method_comparison_draft_first_20261011/fresh/",
                18,
            ),
            ("grounding_main", "pf_grounding_study_20261013/attempts/main/", 60),
        ]:
            rows = [
                row
                for row in self.terminal
                if fragment in row["source_path"] and row["source_path"].endswith("/result.json")
            ]
            if rows:
                checks.append(
                    {
                        "name": name,
                        "expected_terminal_records": expected,
                        "observed_terminal_records": len(rows),
                        "observed_with_student_task": sum(row["has_student_task"] for row in rows),
                        "by_method": dict(Counter(row["method"] for row in rows)),
                        "pass": len(rows) == expected,
                    }
                )
        return {
            "inspected_file_count": len(self.files),
            "inspected_structured_file_count": sum(
                p.suffix in {".json", ".jsonl"} for p in self.hashes
            ),
            "files": self.files,
            "parse_error_count": len(self.parse_errors),
            "parse_errors": self.parse_errors,
            "unique_case_count": len(cases),
            "occurrence_count": sum(len(case["occurrences"]) for case in cases),
            "unassessable_record_count": len(self.unassessable),
            "field_coverage_cases": {
                "student_task": len(cases),
                "learning_target": sum(bool(case["learning_target"]) for case in cases),
                "learner_prerequisites": sum(
                    has_history(case["learner_context"]) for case in cases
                ),
                "all_three": sum(
                    bool(case["learning_target"]) and has_history(case["learner_context"])
                    for case in cases
                ),
            },
            "envelope_occurrence_counts": dict(
                Counter(
                    occurrence["envelope_status"]
                    for case in cases
                    for occurrence in case["occurrences"]
                )
            ),
            "missing_sources": [
                {"referenced_by": near, "recorded_path": recorded}
                for near, recorded in sorted(self.missing_sources)
            ],
            "unavailable_case_inputs": [
                {
                    "case_id": case["case_id"],
                    "input_status": case["input_status"],
                    "source": case["occurrences"][0]["source"],
                }
                for case in cases
                if not case["learning_target"] or not has_history(case["learner_context"])
            ],
            "per_run_terminal_records": {run: dict(counts) for run, counts in sorted(runs.items())},
            "known_run_checks": checks,
            **copy_summary,
            "extraction_caveats": [
                "Catalog membership is not a quality or mathematical-validity judgment.",
                (
                    "Complete task text in invalid envelopes is retained with the saved "
                    "invalid status."
                ),
                (
                    "Task text includes only student-facing fields; solutions, withheld notes "
                    "and consolidation are excluded."
                ),
                (
                    "Strings in recorded recently-taught lists retain null taught_as; "
                    "no teaching detail is invented."
                ),
                (
                    "An absent target or prerequisite list stays unavailable; an explicit "
                    "empty list is distinguished."
                ),
                (
                    "Historical prompts, inputs and hash-verified configurations are evidence; "
                    "current generator code is not."
                ),
                (
                    "Review and snapshot copies link by exact text without asserting their "
                    "contexts match."
                ),
                (
                    "Trace, result and attempt mirrors are provenance occurrences, "
                    "not independent new generations."
                ),
                (
                    "Legacy human-evaluation-pool exercises are surviving generation records; "
                    "original learner history may be absent."
                ),
                (
                    "Whitespace in student fields is retained; explicit internal-note suffixes "
                    "are excluded."
                ),
            ],
        }

    def build(self) -> dict:
        self.scan()
        for path, value in list(self.documents.items()):
            if path.suffix == ".jsonl":
                for line, record in value:
                    self.trace(path, line, record)
            else:
                self.roots(path, value)
        copy_summary = self.link_references()
        return {
            "schema_version": SCHEMA_VERSION,
            "scope": {
                "source_root": self.relative(self.results),
                "generated_tasks_only": True,
                "expert_yaml_references_included": False,
                "regeneration": False,
                "evaluation": False,
                "deduplication": (
                    "Exact student text, saved target and normalized recorded learner context only."
                ),
                "excluded_output_directory": self.relative(self.excluded)
                if self.excluded
                else None,
                "builder": {
                    "path": "scripts/build_pf_measure_catalog.py",
                    "sha256": digest(Path(__file__).read_bytes()),
                },
            },
            "cases": sorted(self.cases.values(), key=lambda case: case["case_id"]),
            "unassessable": self.unassessable,
            "inventory_summary": self.summary(copy_summary),
        }


def build_catalog(root: Path = ROOT, output: Path | None = None) -> dict:
    root = root.resolve()
    output = output or root / DEFAULT_OUTPUT
    return Inventory(root, root / "experiments/results", output.parent).build()


def write_frozen_catalog(catalog: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation is intentional: historical catalogs must never be overwritten.
    with output.open("x", encoding="utf-8") as stream:
        json.dump(catalog, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check-only", action="store_true", help="Inspect and validate counts without writing."
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    if output.exists() and not args.check_only:
        parser.error(f"Frozen output already exists; refusing to overwrite: {output}")
    catalog = build_catalog(root, output)
    summary = catalog["inventory_summary"]
    failures = [item for item in summary["known_run_checks"] if not item["pass"]]
    compact = {
        key: summary[key]
        for key in (
            "inspected_file_count",
            "unique_case_count",
            "occurrence_count",
            "unassessable_record_count",
            "field_coverage_cases",
            "parse_error_count",
            "known_run_checks",
        )
    }
    print(json.dumps(compact, indent=2))
    if failures:
        raise SystemExit("Known-run coverage check failed; catalog was not frozen.")
    if not args.check_only:
        write_frozen_catalog(catalog, output)
        print(f"Frozen catalog: {output}")


if __name__ == "__main__":
    main()

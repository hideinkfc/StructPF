"""Coarse, source-quoted coding of resource use in written model attempts."""

FLAGS = (
    "prerequisite_applied",
    "prerequisite_mentioned_only",
    "advanced_applied",
    "advanced_mentioned_only",
    "advanced_named_as_recall",
    "construction_visible",
    "self_described_gap",
    "record_bound_stop",
)


def parse_coding(payload: object, packet: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"provenance", "attempts"}:
        raise ValueError("Record coding requires provenance and attempts")
    if not isinstance(payload["provenance"], str) or not payload["provenance"].strip():
        raise ValueError("Coding provenance must be explicit")
    rows = payload["attempts"]
    if not isinstance(rows, dict) or set(rows) != set(packet):
        raise ValueError("Record coding must cover every attempted response")
    for label, row in rows.items():
        if not isinstance(row, dict) or set(row) != {
            *FLAGS,
            "evidence",
            "mathematics_status",
            "rationale",
        }:
            raise ValueError(f"Invalid record coding fields: {label}")
        if any(row[flag] not in {"yes", "no", "unknown"} for flag in FLAGS):
            raise ValueError(f"Unknown record-use classification: {label}")
        if row["mathematics_status"] not in {"supported", "invalid", "unknown"}:
            raise ValueError(f"Unknown mathematics classification: {label}")
        for prefix in ("prerequisite", "advanced"):
            if row[f"{prefix}_applied"] == row[f"{prefix}_mentioned_only"] == "yes":
                raise ValueError("Applied and mention-only coding cannot both be positive")
        if row["advanced_named_as_recall"] == "yes" and row["advanced_applied"] != "yes":
            raise ValueError("Named applied recall requires actual advanced-method application")
        evidence = row["evidence"]
        if not isinstance(evidence, dict) or set(evidence) != set(FLAGS):
            raise ValueError(f"Evidence must cover the fixed flags: {label}")
        attempt = packet[label]["attempt"]
        text = (
            attempt["written_work"] + "\n" + attempt["answer"]
            if attempt is not None
            else packet[label]["unparsed_raw_text"] or ""
        )
        for flag, quotes in evidence.items():
            if not isinstance(quotes, list) or (row[flag] == "yes" and not quotes):
                raise ValueError(f"Positive flag requires quoted evidence: {label}/{flag}")
            for quote in quotes:
                if not isinstance(quote, str) or not quote.strip() or quote not in text:
                    raise ValueError(f"Quote does not match written attempt: {label}/{flag}")
        if not isinstance(row["rationale"], str) or not row["rationale"].strip():
            raise ValueError(f"Coding rationale is required: {label}")
    return payload

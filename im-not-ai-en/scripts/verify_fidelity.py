#!/usr/bin/env python3
"""Verify deterministic fidelity invariants between English source and revision.

This is an editorial safety gate, not an authorship classifier or semantic
equivalence checker. It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Mapping


REGEX_EXTRACTORS: dict[str, tuple[re.Pattern[str], int]] = {
    "emails": (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        0,
    ),
    "date_times": (
        re.compile(
            r"(?<![\w])(?:"
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
            r"|\d{1,2}(?::\d{2}(?::\d{2})?)?\s*(?:a\.?m\.?|p\.?m\.?)"
            r"|\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:UTC|GMT))?"
            r")(?![\w])",
            re.IGNORECASE,
        ),
        0,
    ),
    "month_names": (
        re.compile(
            r"\b(?:January|February|March|April|June|July|August|September|October|November|December)\b"
            r"|\bMay\s+(?:\d{1,2}(?:st|nd|rd|th)?(?:,\s*|\s+)?\d{0,4}|\d{4})\b"
        ),
        0,
    ),
    "numbers": (
        re.compile(
            r"(?<![A-Za-z0-9_])"
            r"(?:[$€£¥]\s*)?[+-]?"
            r"(?:\d{1,3}(?:,\d{3})+|\d+)"
            r"(?:\.\d+)*"
            r"(?:%|x|×|[KMB]|\s*(?:ms|s|min|h|KB|MB|GB|TB|USD|EUR|tokens?|requests?|runs?|attempts?))?"
            r"(?![A-Za-z0-9_])",
            re.IGNORECASE,
        ),
        0,
    ),
    "citations": (
        re.compile(
            r"\[@[^\[\]\n]+\]"
            r"|\[\^[^\[\]\n]+\]"
            r"|\[(?:\d+(?:\s*[-,]\s*\d+)*)\]"
        ),
        0,
    ),
    "block_quotes": (
        re.compile(r"(?m)(?:^ {0,3}>[^\n]*(?:\n|$))+"),
        0,
    ),
}

FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[^\r\n]*(?:\r?\n|$)")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`+|~+)[ \t]*(?:\r?\n|$)")
URL_CANDIDATE_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
REFERENCE_DEFINITION_RE = re.compile(
    r"(?m)^ {0,3}\[(?P<label>[^\]\r\n]+)\]:[ \t]*"
)
REFERENCE_USE_RE = re.compile(
    r"(?<!\\)\[([^\[\]\r\n]+)\](?:\[([^\[\]\r\n]*)\])?"
)

FORCE_MARKERS = {
    "modals": re.compile(r"\b(?:may|might|can|could|should|must|will|would)\b", re.I),
    "hedges": re.compile(
        r"\b(?:perhaps|maybe|possibly|probably|likely|apparently)\b"
        r"|\b(?:seems?|appears?)\b",
        re.I,
    ),
    "negation": re.compile(r"\b(?:not|never|no|cannot|can't|won't|without)\b", re.I),
    "scope": re.compile(r"\b(?:only|unless|except|at least|at most)\b", re.I),
}

PREAMBLE_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:"
    r"(?:sure|certainly|of course)[,!:]?(?:\s+(?:here(?:'s| is)|below is)\b)?"
    r"|(?:here(?:'s| is)|below is)\s+(?:the\s+)?(?:revised|edited|polished)\b"
    r"|(?:revised|edited|polished)(?:\s+(?:text|version|copy))?\s*:"
    r"|i(?:'ve| have)?\s+(?:revised|edited|polished)\b"
    r")",
    re.IGNORECASE,
)

NOTES_RE = re.compile(
    r"(?im)^(?:#{1,6}\s*)?(?:editorial\s+)?(?:notes?|changes|what i changed)(?:\s*:.*)?$"
)

REDACTED_VALUE = "<redacted>"
CHANGE_RATE_SEQUENCE_LIMIT = 4096
CHANGE_RATE_SAMPLE_BLOCKS = 32
MARKDOWN_SCAN_MIN_BUDGET = 65_536
MARKDOWN_SCAN_MAX_BUDGET = 2_000_000
MARKDOWN_SCAN_BUDGET_MULTIPLIER = 8


class _MarkdownScanLimitError(RuntimeError):
    """Raised when malformed Markdown would require excessive rescanning."""


def _consume_scan_budget(scan_budget: list[int] | None, amount: int = 1) -> None:
    if scan_budget is None:
        return
    scan_budget[0] -= max(1, amount)
    if scan_budget[0] < 0:
        raise _MarkdownScanLimitError


def _extract(pattern: re.Pattern[str], text: str, group: int = 0) -> Counter[str]:
    return Counter(match.group(group) for match in pattern.finditer(text))


def _is_escaped(text: str, position: int) -> bool:
    backslashes = 0
    position -= 1
    while position >= 0 and text[position] == "\\":
        backslashes += 1
        position -= 1
    return backslashes % 2 == 1


def _mask_ranges(text: str, ranges: Iterable[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in ranges:
        for index in range(start, end):
            if chars[index] not in "\r\n":
                chars[index] = " "
    return "".join(chars)


def _fenced_code_ranges(text: str) -> list[tuple[int, int]]:
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)

    ranges: list[tuple[int, int]] = []
    index = 0
    while index < len(lines):
        opener = FENCE_OPEN_RE.match(lines[index])
        if not opener:
            index += 1
            continue

        fence = opener.group(1)
        marker = fence[0]
        width = len(fence)
        end_index = index
        for candidate in range(index + 1, len(lines)):
            closer = FENCE_CLOSE_RE.match(lines[candidate])
            if closer and closer.group(1)[0] == marker and len(closer.group(1)) >= width:
                end_index = candidate
                break
        else:
            end_index = len(lines) - 1

        start = offsets[index]
        end = offsets[end_index] + len(lines[end_index])
        ranges.append((start, end))
        index = end_index + 1
    return ranges


def _inline_code_ranges(text: str, fenced: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    masked = _mask_ranges(text, fenced)
    runs = [
        match
        for match in re.finditer(r"`+", masked)
        if not _is_escaped(masked, match.start())
    ]
    ranges: list[tuple[int, int]] = []
    index = 0
    while index < len(runs):
        opener = runs[index]
        width = len(opener.group(0))
        for candidate in range(index + 1, len(runs)):
            closer = runs[candidate]
            if len(closer.group(0)) == width:
                ranges.append((opener.start(), closer.end()))
                index = candidate + 1
                break
        else:
            index += 1
    return ranges


def _parse_destination_span(
    text: str,
    start: int,
    *,
    outer_parenthesis: bool,
    scan_budget: list[int] | None = None,
) -> tuple[str, int] | None:
    while start < len(text) and text[start] in " \t\r\n":
        _consume_scan_budget(scan_budget)
        start += 1
    if start >= len(text):
        return None

    if text[start] == "<":
        end = start + 1
        while end < len(text):
            _consume_scan_budget(scan_budget)
            if text[end] == ">" and not _is_escaped(text, end):
                return text[start + 1 : end], end + 1
            end += 1
        return None

    depth = 0
    end = start
    while end < len(text):
        _consume_scan_budget(scan_budget)
        char = text[end]
        if char == "\\" and end + 1 < len(text):
            end += 2
            continue
        if char.isspace() and depth == 0:
            break
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                break
            depth -= 1
        end += 1
    if outer_parenthesis and end >= len(text):
        return None
    target = text[start:end]
    return (target, end) if target else None


def _parse_destination(
    text: str,
    start: int,
    *,
    outer_parenthesis: bool,
    scan_budget: list[int] | None = None,
) -> str | None:
    parsed = _parse_destination_span(
        text,
        start,
        outer_parenthesis=outer_parenthesis,
        scan_budget=scan_budget,
    )
    return parsed[0] if parsed else None


def _markdown_targets(text: str, scan_budget: list[int] | None = None) -> Counter[str]:
    fenced = _fenced_code_ranges(text)
    inline = _inline_code_ranges(text, fenced)
    masked = _mask_ranges(text, [*fenced, *inline])
    targets: list[str] = []

    position = 0
    while True:
        marker = masked.find("](", position)
        if marker < 0:
            break
        if not _is_escaped(masked, marker):
            target = _parse_destination(
                text,
                marker + 2,
                outer_parenthesis=True,
                scan_budget=scan_budget,
            )
            if target is not None:
                targets.append(target)
        position = marker + 2

    for match in REFERENCE_DEFINITION_RE.finditer(masked):
        target = _parse_destination(
            text,
            match.end(),
            outer_parenthesis=False,
            scan_budget=scan_budget,
        )
        if target is not None:
            targets.append(target)
    return Counter(targets)


def _urls(text: str) -> Counter[str]:
    urls: list[str] = []
    for match in URL_CANDIDATE_RE.finditer(text):
        candidate = match.group(0)
        candidate = candidate.rstrip(".,;:!?")
        pairs = (("(", ")"), ("[", "]"), ("{", "}"))
        excess_closers = {
            closing: max(0, candidate.count(closing) - candidate.count(opening))
            for opening, closing in pairs
        }
        end = len(candidate)
        while end and excess_closers.get(candidate[end - 1], 0):
            excess_closers[candidate[end - 1]] -= 1
            end -= 1
        candidate = candidate[:end]
        if candidate:
            urls.append(candidate)
    return Counter(urls)


def _normalize_reference_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip()).casefold()


def _reference_uses(
    text: str,
    scan_budget: list[int] | None = None,
) -> Counter[str]:
    fenced = _fenced_code_ranges(text)
    inline = _inline_code_ranges(text, fenced)
    masked = _mask_ranges(text, [*fenced, *inline])
    definitions: dict[str, str] = {}
    definition_lines: list[tuple[int, int]] = []

    for match in REFERENCE_DEFINITION_RE.finditer(masked):
        target = _parse_destination(
            text,
            match.end(),
            outer_parenthesis=False,
            scan_budget=scan_budget,
        )
        if target is not None:
            definitions.setdefault(
                _normalize_reference_label(match.group("label")),
                target,
            )
        line_end = masked.find("\n", match.end())
        definition_lines.append(
            (match.start(), len(masked) if line_end < 0 else line_end + 1)
        )

    body = _mask_ranges(masked, definition_lines)
    uses: list[str] = []
    for match in REFERENCE_USE_RE.finditer(body):
        if match.group(2) is None and match.end() < len(body) and body[match.end()] == "(":
            continue
        label = match.group(2)
        if label is None:
            label = match.group(1)
        elif not label:
            label = match.group(1)
        target = definitions.get(_normalize_reference_label(label))
        if target is not None:
            uses.append(target)
    return Counter(uses)


def _is_markdown_link_title(
    text: str,
    start: int,
    end: int,
    scan_budget: list[int] | None = None,
) -> bool:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    _consume_scan_budget(
        scan_budget,
        (start - line_start) + (line_end - end),
    )
    prefix = text[line_start:start]
    suffix = text[end:line_end]
    search_end = start
    marker = text.rfind("](", 0, search_end)
    while marker >= 0:
        _consume_scan_budget(scan_budget, search_end - marker)
        parsed = _parse_destination_span(
            text,
            marker + 2,
            outer_parenthesis=True,
            scan_budget=scan_budget,
        )
        if parsed:
            _, destination_end = parsed
            title_start = destination_end
            while title_start < len(text) and text[title_start] in " \t\r\n":
                title_start += 1
            after_title = end
            while after_title < len(text) and text[after_title] in " \t\r\n":
                after_title += 1
            if title_start == start and after_title < len(text) and text[after_title] == ")":
                return True
        search_end = marker
        marker = text.rfind("](", 0, search_end)
    _consume_scan_budget(scan_budget, search_end)
    if re.match(r"^ {0,3}\[[^\]]+\]:[ \t]*\S+[ \t]+$", prefix) and not suffix.strip():
        return True
    if re.fullmatch(r" {0,3}", prefix) and not suffix.strip() and line_start > 0:
        previous_end = line_start - 1
        if previous_end > 0 and text[previous_end - 1] == "\r":
            previous_end -= 1
        previous_start = text.rfind("\n", 0, previous_end) + 1
        previous_line = text[previous_start:previous_end]
        definition = re.match(r"^ {0,3}\[[^\]]+\]:[ \t]*", previous_line)
        if definition:
            parsed = _parse_destination_span(
                previous_line,
                definition.end(),
                outer_parenthesis=False,
                scan_budget=scan_budget,
            )
            if parsed and not previous_line[parsed[1] :].strip():
                return True
    return False


def _long_quotes(text: str, scan_budget: list[int] | None = None) -> Counter[str]:
    pattern = re.compile(r'"[^"\n]{8,}"|“[^“”\n]{8,}”|‘[^‘’\n]{8,}’')
    return Counter(
        match.group(0)
        for match in pattern.finditer(text)
        if not (
            match.group(0).startswith('"')
            and _is_markdown_link_title(
                text,
                match.start(),
                match.end(),
                scan_budget=scan_budget,
            )
        )
    )


def _literal_counters(text: str) -> dict[str, Counter[str]]:
    fenced = _fenced_code_ranges(text)
    inline = _inline_code_ranges(text, fenced)
    scan_budget = [
        max(
            MARKDOWN_SCAN_MIN_BUDGET,
            min(
                MARKDOWN_SCAN_MAX_BUDGET,
                len(text) * MARKDOWN_SCAN_BUDGET_MULTIPLIER,
            ),
        )
    ]
    counters: dict[str, Counter[str]] = {
        "fenced_code": Counter(text[start:end].replace("\r\n", "\n") for start, end in fenced),
        "inline_code": Counter(text[start:end].replace("\r\n", "\n") for start, end in inline),
        "markdown_targets": _markdown_targets(text, scan_budget),
        "reference_uses": _reference_uses(text, scan_budget),
        "urls": _urls(text),
        "long_quotes": _long_quotes(text, scan_budget),
    }
    for name, (pattern, group) in REGEX_EXTRACTORS.items():
        counters[name] = _extract(pattern, text, group)
    return counters


def _counter_delta(before: Counter[str], after: Counter[str]) -> dict[str, int]:
    return dict(before - after)


def _reported_counts(values: Mapping[str, int], *, show_values: bool) -> dict[str, int]:
    if show_values:
        return dict(values)
    total = sum(values.values())
    return {REDACTED_VALUE: total} if total else {}


def _reported_value(value: str, *, show_values: bool) -> str:
    return value if show_values else REDACTED_VALUE


def _configuration_error(
    message: str,
    *,
    value: object,
    show_values: bool,
) -> str:
    return f"{message}: {value!r}" if show_values else message


def _sample_for_change_rate(text: str) -> str:
    """Return deterministic, evenly distributed blocks within the sequence limit."""
    if len(text) <= CHANGE_RATE_SEQUENCE_LIMIT:
        return text

    block_size = max(1, CHANGE_RATE_SEQUENCE_LIMIT // CHANGE_RATE_SAMPLE_BLOCKS)
    last_start = len(text) - block_size
    chunks = []
    for index in range(CHANGE_RATE_SAMPLE_BLOCKS):
        start = round(index * last_start / (CHANGE_RATE_SAMPLE_BLOCKS - 1))
        chunks.append(text[start : start + block_size])
    return "".join(chunks)[:CHANGE_RATE_SEQUENCE_LIMIT]


def _maximum_similarity(left_length: int, right_length: int) -> float:
    total = left_length + right_length
    return 1.0 if total == 0 else (2 * min(left_length, right_length)) / total


def _change_rate(original: str, revised: str) -> tuple[float, str]:
    """Return an exact small-input rate or a bounded, disclosed large-input estimate."""
    if max(len(original), len(revised)) <= CHANGE_RATE_SEQUENCE_LIMIT:
        ratio = SequenceMatcher(None, original, revised, autojunk=False).ratio()
        return 1 - ratio, "exact"

    original_sample = _sample_for_change_rate(original)
    revised_sample = _sample_for_change_rate(revised)
    sample_ceiling = _maximum_similarity(len(original_sample), len(revised_sample))
    sample_ratio = SequenceMatcher(
        None,
        original_sample,
        revised_sample,
        autojunk=True,
    ).ratio()
    content_similarity = min(1.0, sample_ratio / sample_ceiling) if sample_ceiling else 1.0
    full_ceiling = _maximum_similarity(len(original), len(revised))
    return 1 - (content_similarity * full_ceiling), "sampled"


def _structure_text(text: str) -> str:
    fenced = _fenced_code_ranges(text)
    inline = _inline_code_ranges(text, fenced)
    return _mask_ranges(text, [*fenced, *inline])


def _heading_shape(text: str) -> list[int]:
    lines = _structure_text(text).splitlines()
    shape: list[int] = []
    index = 0
    while index < len(lines):
        atx = re.match(r"^ {0,3}(#{1,6})(?:\s+|$)", lines[index])
        if atx:
            shape.append(len(atx.group(1)))
            index += 1
            continue
        if index + 1 < len(lines) and lines[index].strip():
            setext = re.match(r"^ {0,3}(=+|-+)[ \t]*$", lines[index + 1])
            if setext:
                shape.append(1 if setext.group(1).startswith("=") else 2)
                index += 2
                continue
        index += 1
    return shape


def _split_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if "|" not in stripped:
        return None
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in stripped:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            current.append(char)
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    cells.append("".join(current).strip())
    if cells and not cells[0]:
        cells = cells[1:]
    if cells and not cells[-1]:
        cells = cells[:-1]
    return cells or None


def _table_shape(text: str) -> list[list[int]]:
    lines = _structure_text(text).splitlines()
    shape: list[list[int]] = []
    index = 0
    while index + 1 < len(lines):
        header = _split_table_row(lines[index])
        separator = _split_table_row(lines[index + 1])
        if (
            not header
            or not separator
            or len(header) != len(separator)
            or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator)
        ):
            index += 1
            continue

        rows = [len(header), len(separator)]
        cursor = index + 2
        while cursor < len(lines):
            row = _split_table_row(lines[cursor])
            if not row:
                break
            rows.append(len(row))
            cursor += 1
        shape.append(rows)
        index = cursor
    return shape


def _list_shape(text: str) -> list[dict[str, int | str]]:
    shape: list[dict[str, int | str]] = []
    for line in _structure_text(text).splitlines():
        item = re.match(r"^([ \t]*)([-+*]|\d{1,9}[.)])[ \t]+(?=\S)", line)
        if not item:
            continue
        marker = item.group(2)
        task = re.match(r"\[([ xX])\](?:[ \t]+|$)", line[item.end() :])
        task_state = (
            "checked"
            if task and task.group(1).lower() == "x"
            else "unchecked"
            if task
            else "none"
        )
        shape.append(
            {
                "indent": len(item.group(1).expandtabs(4)),
                "kind": "ordered" if marker[0].isdigit() else "unordered",
                "task": task_state,
            }
        )
    return shape


def _notes(text: str) -> Counter[str]:
    return Counter(match.group(0).strip().lower() for match in NOTES_RE.finditer(text))


def _force_counts(text: str) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for name, pattern in FORCE_MARKERS.items():
        counts = Counter(match.group(0).lower() for match in pattern.finditer(text))
        result[name] = dict(counts)
    return result


def verify(
    original: str,
    revised: str,
    *,
    protected_spans: Iterable[str | Mapping[str, str]] = (),
    copy_ready: bool = False,
    warn_change_rate: float | None = None,
    show_values: bool = False,
) -> dict:
    failures: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    configuration_errors: list[str] = []

    if not revised.strip():
        failures.append({"code": "empty_output", "message": "The revision is empty."})

    if warn_change_rate is not None and not 0 <= warn_change_rate <= 1:
        configuration_errors.append("warn_change_rate must be between 0 and 1")

    literal_report: dict[str, dict[str, dict[str, int]]] = {}
    try:
        before_literals = _literal_counters(original)
        after_literals = _literal_counters(revised)
    except _MarkdownScanLimitError:
        configuration_errors.append(
            "Markdown literal scanning exceeded the safe complexity limit."
        )
    else:
        for name, before in before_literals.items():
            after = after_literals[name]
            missing_values = _counter_delta(before, after)
            added_values = _counter_delta(after, before)
            missing = _reported_counts(missing_values, show_values=show_values)
            added = _reported_counts(added_values, show_values=show_values)
            literal_report[name] = {"missing": missing, "added": added}
            if missing_values or added_values:
                failures.append(
                    {
                        "code": "protected_literal_changed",
                        "category": name,
                        "missing": missing,
                        "added": added,
                    }
                )

    explicit_report: list[dict[str, object]] = []
    for item in protected_spans:
        if isinstance(item, str):
            span = item
            mode = "exact"
        elif isinstance(item, Mapping):
            span = item.get("text", "")
            mode = item.get("mode", "exact")
        else:
            configuration_errors.append(
                _configuration_error(
                    "Invalid protected-span contract",
                    value=item,
                    show_values=show_values,
                )
            )
            continue
        if (
            not isinstance(span, str)
            or not span
            or not isinstance(mode, str)
            or mode not in {"exact", "at_least"}
        ):
            configuration_errors.append(
                _configuration_error(
                    "Invalid protected-span contract",
                    value=item,
                    show_values=show_values,
                )
            )
            continue
        expected = original.count(span)
        actual = revised.count(span)
        if expected == 0:
            configuration_errors.append(
                _configuration_error(
                    "Protected span is absent from source",
                    value=span,
                    show_values=show_values,
                )
            )
            continue
        entry = {
            "span": _reported_value(span, show_values=show_values),
            "mode": mode,
            "expected_count": expected,
            "actual_count": actual,
        }
        explicit_report.append(entry)
        violated = actual != expected if mode == "exact" else actual < expected
        if violated:
            failures.append({"code": "protected_span_changed", **entry})

    structure = {
        "headings_before": _heading_shape(original),
        "headings_after": _heading_shape(revised),
        "tables_before": _table_shape(original),
        "tables_after": _table_shape(revised),
        "lists_before": _list_shape(original),
        "lists_after": _list_shape(revised),
    }
    if structure["headings_before"] != structure["headings_after"]:
        failures.append(
            {
                "code": "structure_changed",
                "structure": "markdown_headings",
                "before": structure["headings_before"],
                "after": structure["headings_after"],
            }
        )
    if structure["tables_before"] != structure["tables_after"]:
        failures.append(
            {
                "code": "structure_changed",
                "structure": "markdown_tables",
                "before": structure["tables_before"],
                "after": structure["tables_after"],
            }
        )
    if structure["lists_before"] != structure["lists_after"]:
        failures.append(
            {
                "code": "structure_changed",
                "structure": "markdown_lists",
                "before": structure["lists_before"],
                "after": structure["lists_after"],
            }
        )

    original_first_line = original.lstrip().splitlines()[0] if original.strip() else ""
    first_line = revised.lstrip().splitlines()[0] if revised.strip() else ""
    if copy_ready and PREAMBLE_RE.match(first_line) and not PREAMBLE_RE.match(original_first_line):
        failures.append(
            {
                "code": "output_contract",
                "message": "Copy-ready output starts with an editorial preamble.",
                "first_line": _reported_value(first_line, show_values=show_values),
            }
        )
    notes_before = _notes(original)
    notes_after = _notes(revised)
    added_notes = _counter_delta(notes_after, notes_before)
    if copy_ready and added_notes:
        failures.append(
            {
                "code": "output_contract",
                "message": "Copy-ready output adds an editorial notes wrapper.",
                "added": _reported_counts(added_notes, show_values=show_values),
            }
        )

    change_rate, change_rate_method = _change_rate(original, revised)
    if (
        warn_change_rate is not None
        and 0 <= warn_change_rate <= 1
        and change_rate > warn_change_rate
    ):
        warnings.append(
            {
                "code": "change_rate_exceeded",
                "rate": round(change_rate, 4),
                "threshold": warn_change_rate,
                "method": change_rate_method,
            }
        )

    if configuration_errors:
        status = "error"
    elif failures:
        status = "fail"
    elif warnings:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "change_rate": round(change_rate, 4),
        "change_rate_method": change_rate_method,
        "characters": {"original": len(original), "revised": len(revised)},
        "failures": failures,
        "warnings": warnings,
        "protected_literals": literal_report,
        "protected_spans": explicit_report,
        "structure": structure,
        "manual_review": {
            "force_markers_before": _force_counts(original),
            "force_markers_after": _force_counts(revised),
            "required": [
                "proper names and unquoted domain identifiers",
                "indented code blocks and other unsupported markup forms",
                "claim meaning, commitment, attribution, causality, and chronology",
                "modal force, negation, comparison, and scope",
                "hedges and recommendation strength",
                "articles, determiners, countability, number, and agreement",
                "pronoun reference, modifier attachment, and sentence boundaries",
                "prepositions, collocations, contractions, punctuation, and dialect",
                "register, point of view, tense, and recognizable voice",
            ],
        },
        "configuration_errors": configuration_errors,
        "values_shown": show_values,
        "disclaimer": "Deterministic editorial invariants only; not an AI detector or semantic proof.",
    }


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    show_values_requested = False
    for argument in arguments:
        if argument == "--":
            break
        if argument == "--show-values":
            show_values_requested = True

    parser = _JsonArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("original", type=Path)
    parser.add_argument("revised", type=Path)
    parser.add_argument("--protect", action="append", default=[])
    parser.add_argument("--copy-ready", action="store_true")
    parser.add_argument(
        "--show-values",
        action="store_true",
        help="Include raw source values and input paths in JSON diagnostics.",
    )
    parser.add_argument(
        "--warn-change-rate",
        type=float,
        help="Optional project-specific warning threshold from 0 to 1; no default threshold is imposed.",
    )
    try:
        args = parser.parse_args(arguments)
    except ValueError as exc:
        message = str(exc) if show_values_requested else "Invalid command-line arguments."
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": message,
                    "values_shown": show_values_requested,
                },
                indent=2,
            )
        )
        return 3

    if args.warn_change_rate is not None and not 0 <= args.warn_change_rate <= 1:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "--warn-change-rate must be between 0 and 1",
                    "values_shown": args.show_values,
                },
                indent=2,
            )
        )
        return 3

    try:
        original = args.original.read_text(encoding="utf-8")
        revised = args.revised.read_text(encoding="utf-8")
    except UnicodeError as exc:
        message = str(exc) if args.show_values else "An input file is not valid UTF-8."
        print(
            json.dumps(
                {"status": "error", "error": message, "values_shown": args.show_values},
                indent=2,
            )
        )
        return 3
    except OSError as exc:
        message = str(exc) if args.show_values else "Unable to read an input file."
        print(
            json.dumps(
                {"status": "error", "error": message, "values_shown": args.show_values},
                indent=2,
            )
        )
        return 3

    result = verify(
        original,
        revised,
        protected_spans=args.protect,
        copy_ready=args.copy_ready,
        warn_change_rate=args.warn_change_rate,
        show_values=args.show_values,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"pass": 0, "warn": 1, "fail": 2, "error": 3}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())

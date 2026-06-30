from __future__ import annotations

import copy
import re
from collections.abc import Callable
from typing import Any


Replacement = str | Callable[[re.Match[str]], str]

REDACTION_PATTERNS: list[tuple[str, re.Pattern[str], Replacement]] = [
    (
        "ssh_key",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "<SECRET>",
    ),
    (
        "token",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
        "Bearer <TOKEN>",
    ),
    (
        "cookie",
        re.compile(
            r"\b((?:session(?:id|_id)?|csrftoken|csrf(?:token|_token|-token)?|"
            r"xsrf(?:token|_token|-token)?|x-csrf-token|x-xsrf-token)\s*[:=]\s*)"
            r"(\"[^\"]*\"|'[^']*'|[^\s;,<>]+)",
            re.IGNORECASE,
        ),
        r"\1<COOKIE>",
    ),
    (
        "cookie",
        re.compile(
            r"\b((?:set-cookie|cookie)\s*=\s*)(\"[^\"]*\"|'[^']*'|[^\s;,<>]+)",
            re.IGNORECASE,
        ),
        r"\1<COOKIE>",
    ),
    (
        "cookie",
        re.compile(
            r"\b((?:set-cookie|cookie)\s*:\s*)(?![^\r\n]*<COOKIE>)[^\r\n]+",
            re.IGNORECASE,
        ),
        r"\1<COOKIE>",
    ),
    (
        "api_key",
        re.compile(
            r"\b((?:api[_-]?key|x-api-key)\s*[:=]\s*)"
            r"(\"[^\"]*\"|'[^']*'|[^\s;,<>]+)",
            re.IGNORECASE,
        ),
        r"\1<API_KEY>",
    ),
    (
        "api_key",
        re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"),
        "<API_KEY>",
    ),
    (
        "token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        "<TOKEN>",
    ),
    (
        "token",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
        "<TOKEN>",
    ),
    (
        "private_repo_url",
        re.compile(
            r"(?:https?|ssh)://[^\s\"'<>]*(?:private|internal|company)[^\s\"'<>]*"
            r"|git@[^\s:\"'<>]+:[^\s\"'<>]*(?:private|internal|company)[^\s\"'<>]*",
            re.IGNORECASE,
        ),
        "<PRIVATE_REPO_URL>",
    ),
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b(?!:[^\s])"),
        "<EMAIL>",
    ),
    (
        "phone",
        re.compile(
            r"(?<!\w)(?:\+1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
            r"(?:\s*(?:x|ext\.?)\s*\d{1,6})?(?!\w)"
        ),
        "<PHONE>",
    ),
    (
        "local_path",
        re.compile(r"/(?:Users/evan|private/var/folders)(?:/[^\s\"'<>]*)?(?<![.,])"),
        "<LOCAL_PATH>",
    ),
]


def merge_counts(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    merged = dict(left)
    for category, count in right.items():
        merged[category] = merged.get(category, 0) + count
    return merged


def redact_text(text: str) -> tuple[str, dict[str, int]]:
    redacted = text
    summary: dict[str, int] = {}
    for category, pattern, replacement in REDACTION_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            summary[category] = summary.get(category, 0) + count
    return redacted, summary


def _redact_value(value: Any) -> tuple[Any, dict[str, int]]:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        redacted_items: list[Any] = []
        summary: dict[str, int] = {}
        for item in value:
            redacted_item, item_summary = _redact_value(item)
            redacted_items.append(redacted_item)
            summary = merge_counts(summary, item_summary)
        return redacted_items, summary
    if isinstance(value, dict):
        redacted_dict: dict[Any, Any] = {}
        summary: dict[str, int] = {}
        for key, item in value.items():
            redacted_item, item_summary = _redact_value(item)
            redacted_dict[key] = redacted_item
            summary = merge_counts(summary, item_summary)
        return redacted_dict, summary
    return value, {}


def redact_record(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    redacted, summary = _redact_value(copy.deepcopy(record))
    return redacted, summary

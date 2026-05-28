"""Prompt heuristics for seer-agent routing gates."""

from __future__ import annotations


def looks_like_coding_request(user_message: str, keywords: tuple[str, ...]) -> bool:
    text = (user_message or "").lower()
    return any(kw in text for kw in keywords)


def looks_vague(user_message: str) -> bool:
    text = (user_message or "").strip().lower()
    if not text:
        return False
    words = text.split()
    has_scope_marker = any(
        marker in text
        for marker in (
            "acceptance criteria",
            "requirements",
            "spec",
            "milestone",
            "phase",
            "step",
            "tests",
            "instruction",
            "module",
            "file",
            "crate",
            "program id",
        )
    )
    return len(words) <= 20 and not has_scope_marker


def looks_business_vague(user_message: str, keywords: tuple[str, ...]) -> bool:
    text = (user_message or "").strip().lower()
    if not text:
        return False
    business_markers = (
        "for who",
        "target user",
        "customer",
        "problem",
        "goal",
        "success metric",
        "mvp",
        "scope",
        "revenue",
        "market",
    )
    has_business_marker = any(m in text for m in business_markers)
    return looks_like_coding_request(text, keywords) and not has_business_marker


def extract_ambiguity_topic(user_message: str) -> str:
    text = (user_message or "").strip().lower()
    if not text:
        return ""
    if "anchor" in text and any(k in text for k in ("edition", "version", "dependency", "upgrade", "migration")):
        return "anchor-toolchain-direction"
    if "mvp" in text and any(k in text for k in ("path", "direction", "scope", "priority")):
        return "mvp-direction"
    if any(k in text for k in ("architecture", "design")) and any(k in text for k in ("option", "trade-off", "choose")):
        return "architecture-direction"
    return "implementation-direction"


def looks_ambiguous_decision(user_message: str, keywords: tuple[str, ...]) -> bool:
    text = (user_message or "").strip().lower()
    if not text:
        return False
    hard_ambiguity_markers = (
        "ambiguous",
        "multiple choices",
        "several options",
        "which one",
        "choose between",
        "should we",
        "trade-off",
    )
    failure_markers = ("not working", "fails", "failing", "broken", "error")
    choice_markers = ("option", "options", "path", "direction", "choose", "either")
    domain_markers = ("anchor", "edition", "dependency", "version", "migration", "upgrade")
    has_hard_ambiguity = any(m in text for m in hard_ambiguity_markers)
    has_failure_with_choice = any(m in text for m in failure_markers) and any(m in text for m in choice_markers)
    has_ambiguity = has_hard_ambiguity or has_failure_with_choice
    has_domain = any(m in text for m in domain_markers)
    return has_ambiguity and (looks_like_coding_request(text, keywords) or has_domain)


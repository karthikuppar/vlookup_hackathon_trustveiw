"""Prompt-injection detection for AegisKB queries (ported from the PS-04 reference build).

Detection is a defence-in-depth *signal*, not the security boundary: access control happens in SQL and
route checks, and answers are extractive, so a missed injection still cannot widen scope. Flagged document
sentences are excluded from evidence and surfaced to admins; flagged questions are audited.
Text is normalised first so common obfuscation (zero-width characters, fullwidth forms, Cyrillic/Greek
lookalikes, combining marks, leetspeak, odd whitespace) does not hide a phrase from the patterns."""
from __future__ import annotations
import html, re, unicodedata

# Cyrillic / Greek letters that render like Latin ones.
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h", "ӏ": "l",
    "α": "a", "ο": "o", "ε": "e", "ν": "v", "ρ": "p", "τ": "t", "ι": "i", "κ": "k", "μ": "m", "η": "n", "υ": "u", "χ": "x",
})
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})

PATTERNS = re.compile(
    r"(?<!not )(?<!never )(?<!n't )\b(ignore|disregard|forget|override|bypass|circumvent)\b"
    r".{0,40}\b(previous|prior|above|earlier|system|safety|security|access (control|rules?)|instruction\w*|rules?|restrictions?|guidelines?|guardrails?|filters?)\b"
    r"|\b(stop following|do not follow|don'?t follow|do not obey|don'?t obey)\b"
    r"|\b(reveal|exfiltrate|leak|dump)\b.{0,30}\b(tenant|client|organi[sz]ation)\b"
    r"|\b(contents?|documents?|files?|data|records)\s+of\s+(all|every|any|other)\b.{0,15}(client|tenant|customer|organi[sz]ation)"
    r"|\b(reveal|show|print|leak|dump|exfiltrate|disclose|output|display|expose|list|give me|send me)\b.{0,40}"
    r"\b(system prompt|hidden prompt|your instructions|api keys?|passwords?|secrets?|credentials|tokens?|"
    r"(other|another|every|all|any)\s+(client|tenant|customer|organi[sz]ation|compan)\w*)"
    r"|\byou are now\b|\bact as (an? |the )?(admin\w*|root|system|assistant|ai|chatbot|dan|developer|different|another|unrestricted)\b"
    r"|\bpretend (to be|you|that|there)\b|\brole-?play\b|\bfrom now on\b.{0,30}\byou\b|\bnew instructions?\b|\bupdated instructions?\b"
    r"|\bgrant (me|us|them|everyone|the user|this user|all users)\s+(full |admin\w* |root )?(access|admin\w*|permission\w*)\b"
    r"|\bgrant (full|admin\w*|unrestricted|root) (access|rights|permissions?)\b|\bi am (an? |the )?(admin\w*|root|sysadmin|owner|from (client|tenant)|(client|tenant)\s*\w+)\b"
    r"|\b(no|without|remove (all )?|disable (all )?)\s*(restrictions?|limits?|filters?|guardrails?|safety)\b"
    r"|\bdeveloper mode\b|\bjailbreak\w*\b|\bsystem prompt\b|\bprompt injection\b|\bdo anything now\b"
    r"|<\|?\s*(im_start|im_end|system|assistant|endoftext)\s*\|?>|\[/?inst\]|<<\s*/?sys\s*>>|^\s*(system|assistant)\s*:|#{2,}\s*(system|instruction)",
    re.I | re.M)


def normalize(text: str) -> str:
    """Canonical form used only for matching; never shown to users."""
    t = unicodedata.normalize("NFKD", html.unescape(text or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")  # combining marks
    t = unicodedata.normalize("NFKC", t)
    out = []
    for c in t:
        cat = unicodedata.category(c)
        if cat in ("Cf", "Co", "Cn"):  # zero-width, bidi controls, private use, unassigned
            continue
        out.append(" " if (cat == "Zs" or c in "\t\r\f\v") else c)
    t = re.sub(r"[ ]+", " ", "".join(out).translate(_HOMOGLYPHS).lower())
    return re.sub(r"\b(?:[a-z] ){3,}[a-z]\b", lambda m: m.group(0).replace(" ", ""), t)  # "i g n o r e" -> "ignore"


def is_injection(text: str) -> bool:
    n = normalize(text)
    joined = re.sub(r"(?<=\w)[-_.*·](?=\w)", "", n)  # "ig-nore" / "ig.nore" -> "ignore"
    return any(PATTERNS.search(v) for v in (n, n.translate(_LEET), joined))


def flag_sentences(sents: list[str]) -> list[bool]:
    """Per-sentence flags. Also catches a phrase broken across a boundary, and taints the sentence that follows an injected one."""
    flags = [is_injection(s) for s in sents]
    orig = list(flags)
    for i in range(len(sents) - 1):
        if orig[i]:
            flags[i + 1] = True  # the sentence right after an injected one is the instruction it introduces
        elif not orig[i + 1] and is_injection(sents[i] + " " + sents[i + 1]):
            flags[i] = flags[i + 1] = True  # payload split across the boundary
    return flags


_SENTENCE_SPLIT = re.compile(r"(?<![0-9])(?<=[.!?])\s+")


def strip_injection(text: str) -> tuple[str, int]:
    """Remove instruction-like sentences from document text, keeping line structure.

    Returns (clean_text, removed_sentence_count). Applied to document content so that text in an uploaded
    file can never be quoted back to users as if it were policy."""
    lines = (text or "").split("\n")
    items: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        for sent in _SENTENCE_SPLIT.split(line):
            if sent.strip():
                items.append((i, sent))
    flags = flag_sentences([s for _, s in items])
    # Everything after an injected sentence on the same line is part of the same payload.
    tainted: set[int] = set()
    for k, ((line_no, _), bad) in enumerate(zip(items, flags)):
        if bad:
            tainted.add(line_no)
        elif line_no in tainted:
            flags[k] = True
    removed = sum(flags)
    if not removed:
        return text, 0
    kept: dict[int, list[str]] = {}
    for (i, sent), bad in zip(items, flags):
        if not bad:
            kept.setdefault(i, []).append(sent)
    out = [" ".join(kept[i]) if i in kept else "" for i in range(len(lines))]
    return "\n".join(out).strip(), removed

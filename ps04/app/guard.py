"""Prompt-injection detection and abuse throttling.

Detection is a defence-in-depth *signal*, not the security boundary: access control happens in SQL and
route checks, and answers are extractive, so a missed injection still cannot widen scope. Flagged document
sentences are excluded from evidence and surfaced to admins; flagged questions are audited.
Text is normalised first so common obfuscation (zero-width characters, fullwidth forms, Cyrillic/Greek
lookalikes, combining marks, leetspeak, odd whitespace) does not hide a phrase from the patterns."""
from __future__ import annotations
import html, re, threading, time, unicodedata
from collections import defaultdict, deque

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
    """Per-sentence flags. Also checks adjacent pairs so a phrase broken across a line/sentence boundary is caught."""
    flags = [is_injection(s) for s in sents]
    for i in range(len(sents) - 1):
        if not (flags[i] and flags[i + 1]) and is_injection(sents[i] + " " + sents[i + 1]):
            flags[i] = flags[i + 1] = True
    return flags


class RateLimiter:
    """In-memory sliding-window limiter keyed by (bucket, subject). `limits` is read at call time."""

    def __init__(self, limits: dict[str, tuple[int, int]]):
        self.limits = dict(limits)
        self._hits: dict[tuple, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, bucket: str, subject: str) -> bool:
        n, window = self.limits[bucket]
        now = time.monotonic()
        with self._lock:
            q = self._hits[(bucket, subject)]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= n:
                return False
            q.append(now)
            return True

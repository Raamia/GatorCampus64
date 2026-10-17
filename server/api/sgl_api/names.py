"""Display-name validation: 1-12 printable ASCII characters, simple profanity filter."""
from __future__ import annotations

import re

MAX_LEN = 12

# Deliberately short: catches the obvious; admins delete anything that slips through (§14).
# Matched as substrings of the name with separators/leetspeak removed.
_SUBSTR = (
    "fuck", "shit", "bitch", "cunt", "dick", "pussy", "nigg", "slut", "whore", "nazi", "hitler",
    "porn", "penis", "vagina", "retard", "chink", "kike", "tranny", "jizz", "dildo", "wank", "twat",
)
# Short words that would false-positive as substrings (grape, peacock, cucumber): whole tokens only.
_WHOLE = {"ass", "cum", "fag", "anal", "spic", "dyke", "tits", "kkk", "rape", "cock", "sex"}
_LEET = str.maketrans({"0": "o", "1": "i", "!": "i", "3": "e", "4": "a", "@": "a", "5": "s",
                       "$": "s", "7": "t", "+": "t", "8": "b", "9": "g", "|": "i"})


class NameInvalid(ValueError):
    pass


def _letters(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower().translate(_LEET))


def _collapse(s: str) -> str:
    return re.sub(r"(.)\1+", r"\1", s)  # "fuuuck" -> "fuck"


def is_profane(name: str) -> bool:
    raw = _letters(name)
    forms = {raw, _collapse(raw)}
    if any(w in f for w in _SUBSTR for f in forms):
        return True
    tokens = {_letters(t) for t in re.split(r"[\s._\-]+", name) if t}
    tokens |= {_collapse(t) for t in tokens}
    return bool((tokens | forms) & _WHOLE)


def validate(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        raise NameInvalid("name is required")
    if len(name) > MAX_LEN:
        raise NameInvalid(f"name must be at most {MAX_LEN} characters")
    if any(not (0x20 <= ord(c) <= 0x7E) for c in name):
        raise NameInvalid("name must be printable ASCII")
    if "\\" in name:  # coopdx djui treats \#rrggbb\ as a colour code
        raise NameInvalid("name may not contain a backslash")
    if is_profane(name):
        raise NameInvalid("please pick a different name")
    return name

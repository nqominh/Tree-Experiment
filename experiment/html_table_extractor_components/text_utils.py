import re


_NUMERIC_RE = re.compile(
    r"""
    ^\s*
    [\(\-]?
    (?:
        \d{1,3}(?:,\d{3})+|\d+
    )
    (?:\.\d+)?
    %?
    [\)]?
    \s*$
    """,
    re.VERBOSE,
)


def normalize_text(value: str) -> str:
    text = value.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def leading_indent(value: str) -> int:
    expanded = value.replace("\xa0", " ")
    return len(expanded) - len(expanded.lstrip(" "))


def is_numeric_like(value: str) -> bool:
    text = normalize_text(value)
    if not text:
        return False
    candidate = text.replace("$", "").replace("£", "").replace("€", "")
    candidate = candidate.replace("¥", "").replace(",", "").replace("*", "")
    candidate = candidate.replace("−", "-").replace("–", "-")
    return bool(_NUMERIC_RE.match(candidate))

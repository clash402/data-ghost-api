from __future__ import annotations

import re


NON_ALNUM = re.compile(r"[^a-zA-Z0-9_]+")


def slugify_identifier(value: str) -> str:
    cleaned = NON_ALNUM.sub("_", value).strip("_").lower()
    return cleaned or "dataset"

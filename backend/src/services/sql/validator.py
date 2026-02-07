from __future__ import annotations

from dataclasses import dataclass

FORBIDDEN_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "ALTER",
    "PRAGMA",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "TRUNCATE",
    "REPLACE",
    "CREATE",
    "INSERT",
}


@dataclass
class ValidationResult:
    is_valid: bool
    reason: str | None = None


def _contains_forbidden_keyword(sql: str) -> str | None:
    upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in upper:
            return keyword
    return None


def validate_safe_select(sql: str) -> ValidationResult:
    stripped = sql.strip().rstrip(";")
    if not stripped:
        return ValidationResult(is_valid=False, reason="Empty SQL")

    if ";" in stripped:
        return ValidationResult(is_valid=False, reason="Multiple statements are not allowed")

    forbidden = _contains_forbidden_keyword(stripped)
    if forbidden:
        return ValidationResult(is_valid=False, reason=f"Forbidden keyword detected: {forbidden}")

    upper = stripped.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return ValidationResult(is_valid=False, reason="Only SELECT statements are allowed")

    try:
        import sqlglot
        from sqlglot import exp
    except Exception:
        return ValidationResult(is_valid=True)

    try:
        parsed = sqlglot.parse_one(stripped, read="sqlite")
    except Exception as exc:
        return ValidationResult(is_valid=False, reason=f"Invalid SQL: {exc}")

    if not isinstance(parsed, exp.Select):
        return ValidationResult(is_valid=False, reason="Only top-level SELECT queries are allowed")

    for node in parsed.walk():
        if isinstance(node, (exp.Delete, exp.Update, exp.Drop, exp.Insert, exp.Create, exp.Command, exp.Alter)):
            return ValidationResult(is_valid=False, reason=f"Forbidden SQL node: {node.key}")

    return ValidationResult(is_valid=True)

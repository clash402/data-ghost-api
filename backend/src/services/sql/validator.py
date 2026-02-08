from __future__ import annotations

from dataclasses import dataclass
import re

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


def validate_sql_references(sql: str, *, table_name: str, allowed_columns: list[str]) -> ValidationResult:
    stripped = sql.strip()
    if not stripped:
        return ValidationResult(is_valid=False, reason="Empty SQL")

    allowed_set = set(allowed_columns)

    try:
        import sqlglot
        from sqlglot import exp
    except Exception:
        # Best-effort fallback without sqlglot: ensure the expected table appears in FROM/JOIN.
        lowered = stripped.lower()
        table_pattern = re.compile(
            rf"\b(from|join)\s+((\"{re.escape(table_name.lower())}\")|{re.escape(table_name.lower())})\b"
        )
        if re.search(r"\b(from|join)\b", lowered, re.IGNORECASE) and not table_pattern.search(lowered):
            return ValidationResult(
                is_valid=False,
                reason=f"Query must reference table \"{table_name}\".",
            )
        return ValidationResult(is_valid=True)

    try:
        parsed = sqlglot.parse_one(stripped, read="sqlite")
    except Exception as exc:
        return ValidationResult(is_valid=False, reason=f"Invalid SQL: {exc}")

    table_refs = {table.name for table in parsed.find_all(exp.Table) if table.name}
    if not table_refs:
        return ValidationResult(
            is_valid=False,
            reason=f"Query must reference dataset table \"{table_name}\".",
        )
    invalid_tables = [name for name in table_refs if name != table_name]
    if invalid_tables:
        return ValidationResult(
            is_valid=False,
            reason=f"Query references unsupported table(s): {', '.join(invalid_tables)}",
        )

    alias_names: set[str] = set()
    for select in parsed.find_all(exp.Select):
        for expression in select.expressions or []:
            alias = expression.alias
            if alias:
                alias_names.add(alias)

    column_refs = {column.name for column in parsed.find_all(exp.Column) if column.name}
    unknown_columns = sorted(
        column
        for column in column_refs
        if column not in allowed_set and column not in alias_names and column != "*"
    )
    if unknown_columns:
        return ValidationResult(
            is_valid=False,
            reason=f"Query references unknown column(s): {', '.join(unknown_columns)}",
        )

    return ValidationResult(is_valid=True)

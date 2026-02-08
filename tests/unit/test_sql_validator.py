from src.services.sql.validator import validate_safe_select


def test_validator_allows_select() -> None:
    result = validate_safe_select("SELECT 1")
    assert result.is_valid is True


def test_validator_blocks_drop() -> None:
    result = validate_safe_select("DROP TABLE dataset")
    assert result.is_valid is False
    assert "Forbidden" in (result.reason or "")


def test_validator_blocks_multiple_statements() -> None:
    result = validate_safe_select("SELECT 1; SELECT 2")
    assert result.is_valid is False

"""Unit tests for SQLValidator enhancements."""

import pytest
from pg_mcp.config.settings import SecurityConfig
from pg_mcp.models.errors import SecurityViolationError
from pg_mcp.services.sql_validator import SQLValidator

class TestSQLValidatorExtras:
    """Test SQLValidator additional features."""

    def test_explain_permissions(self) -> None:
        """Test EXPLAIN permission control."""
        # Case 1: EXPLAIN allowed
        config_allowed = SecurityConfig(allow_explain=True)
        validator_allowed = SQLValidator(config=config_allowed)
        assert validator_allowed.validate("EXPLAIN SELECT 1")[0]

        # Case 2: EXPLAIN disallowed (default)
        config_disallowed = SecurityConfig(allow_explain=False)
        validator_disallowed = SQLValidator(config=config_disallowed)
        with pytest.raises(SecurityViolationError, match="EXPLAIN statements are not allowed"):
            validator_disallowed.validate_or_raise("EXPLAIN SELECT 1")

    def test_allowed_tables(self) -> None:
        """Test allowed_tables whitelist functionality."""
        config = SecurityConfig(allowed_tables=["users", "orders"])
        validator = SQLValidator(config=config)

        # Allowed table
        assert validator.validate("SELECT * FROM users")[0]
        
        # Disallowed table
        with pytest.raises(SecurityViolationError, match="not in the allowed list"):
            validator.validate_or_raise("SELECT * FROM products")
            
        # Mixed allowed and disallowed
        with pytest.raises(SecurityViolationError, match="not in the allowed list"):
            validator.validate_or_raise("SELECT * FROM users JOIN products ON users.id = products.user_id")

    def test_allowed_tables_runtime_override(self) -> None:
        """Test that runtime allowed_tables argument passes through."""
        config = SecurityConfig()
        # allowed_tables via init arg
        validator = SQLValidator(config=config, allowed_tables=["users"])
        
        assert validator.validate("SELECT * FROM users")[0]
        with pytest.raises(SecurityViolationError):
            validator.validate_or_raise("SELECT * FROM products")

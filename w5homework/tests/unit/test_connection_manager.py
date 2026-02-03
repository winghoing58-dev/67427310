"""Unit tests for ConnectionManager."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pg_mcp.db.manager import ConnectionManager
from pg_mcp.config.settings import DatabaseConfig, SecurityConfig
from pg_mcp.models.errors import DatabaseError

class TestConnectionManager:
    """Test ConnectionManager functionality."""

    @pytest.fixture
    def security_config(self) -> SecurityConfig:
        """Create security configuration."""
        return SecurityConfig()

    @pytest.fixture
    def manager(self, security_config: SecurityConfig) -> ConnectionManager:
        """Create connection manager."""
        return ConnectionManager(security_config)

    @pytest.mark.asyncio
    async def test_register_database(self, manager: ConnectionManager) -> None:
        """Test registering a database configuration."""
        config = DatabaseConfig(name="test_db")
        await manager.register_database(config)
        assert "test_db" in manager._configs
        assert manager._default_db == "test_db"

    @pytest.mark.asyncio
    async def test_register_multiple_databases(self, manager: ConnectionManager) -> None:
        """Test registering multiple databases and default selection."""
        config1 = DatabaseConfig(name="db1")
        config2 = DatabaseConfig(name="db2")
        
        await manager.register_database(config1)
        await manager.register_database(config2, set_as_default=True)
        
        assert "db1" in manager._configs
        assert "db2" in manager._configs
        assert manager._default_db == "db2"

    @pytest.mark.asyncio
    async def test_get_pool_success(self, manager: ConnectionManager) -> None:
        """Test getting a connection pool successfully."""
        config = DatabaseConfig(name="test_db")
        await manager.register_database(config)
        
        # Mock create_pool to avoid actual DB connection
        with pytest.MonkeyPatch.context() as m:
            mock_create_pool = AsyncMock(return_value=MagicMock())
            m.setattr("pg_mcp.db.manager.create_pool", mock_create_pool)
            
            pool = await manager.get_pool("test_db")
            assert pool is not None
            assert "test_db" in manager._pools
            mock_create_pool.assert_called_once_with(config)

    @pytest.mark.asyncio
    async def test_get_pool_not_configured(self, manager: ConnectionManager) -> None:
        """Test getting a pool for unconfigured database raises error."""
        with pytest.raises(ValueError, match="not configured"):
            await manager.get_pool("unknown_db")

    @pytest.mark.asyncio
    async def test_get_executor_success(self, manager: ConnectionManager) -> None:
        """Test getting an SQL executor."""
        config = DatabaseConfig(name="test_db")
        await manager.register_database(config)
        
        with pytest.MonkeyPatch.context() as m:
            mock_create_pool = AsyncMock(return_value=MagicMock())
            m.setattr("pg_mcp.db.manager.create_pool", mock_create_pool)
            
            executor = await manager.get_executor("test_db")
            assert executor is not None
            assert "test_db" in manager._executors
            assert executor.db_config == config
            assert executor.security_config == manager.security_config

    @pytest.mark.asyncio
    async def test_get_executor_default_db(self, manager: ConnectionManager) -> None:
        """Test getting executor for default database."""
        config = DatabaseConfig(name="default_db")
        await manager.register_database(config)
        
        with pytest.MonkeyPatch.context() as m:
            mock_create_pool = AsyncMock(return_value=MagicMock())
            m.setattr("pg_mcp.db.manager.create_pool", mock_create_pool)
            
            executor = await manager.get_executor(None)
            assert executor is not None
            assert executor.db_config == config

    @pytest.mark.asyncio
    async def test_get_executor_no_default(self, manager: ConnectionManager) -> None:
        """Test getting executor with no default db raises error."""
        with pytest.raises(ValueError, match="No database specified"):
            await manager.get_executor(None)

    @pytest.mark.asyncio
    async def test_close_all(self, manager: ConnectionManager) -> None:
        """Test closing all pools."""
        config = DatabaseConfig(name="test_db")
        await manager.register_database(config)
        
        # Manually inject a mock pool
        mock_pool = MagicMock()
        manager._pools["test_db"] = mock_pool
        manager._executors["test_db"] = MagicMock()
        
        with pytest.MonkeyPatch.context() as m:
            mock_close_pools = AsyncMock()
            m.setattr("pg_mcp.db.manager.close_pools", mock_close_pools)
            
            await manager.close_all()
            
            mock_close_pools.assert_called_once()
            assert len(manager._pools) == 0
            assert len(manager._executors) == 0

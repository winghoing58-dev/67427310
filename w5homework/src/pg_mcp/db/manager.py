"""Connection manager for handling multiple database connections."""

import logging
from typing import Dict, Optional

from asyncpg import Pool

from pg_mcp.config.settings import DatabaseConfig, SecurityConfig
from pg_mcp.db.pool import create_pool, close_pools
from pg_mcp.services.sql_executor import SQLExecutor

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages database connections and executors for multiple databases.
    
    This class handles the lifecycle of database connection pools and provides
    access to SQLExecutor instances for specific databases.
    """

    def __init__(self, security_config: SecurityConfig) -> None:
        """Initialize connection manager.
        
        Args:
            security_config: Global security configuration to apply to all executors.
        """
        self.security_config = security_config
        self._configs: Dict[str, DatabaseConfig] = {}
        self._pools: Dict[str, Pool] = {}
        self._executors: Dict[str, SQLExecutor] = {}
        self._default_db: Optional[str] = None

    async def register_database(self, config: DatabaseConfig, set_as_default: bool = False) -> None:
        """Register a database configuration.
        
        Args:
            config: Database configuration.
            set_as_default: Whether to set this as the default database.
        """
        self._configs[config.name] = config
        if set_as_default or self._default_db is None:
            self._default_db = config.name
            
    async def get_pool(self, db_name: str) -> Pool:
        """Get or create connection pool for database.
        
        Args:
            db_name: Name of the database to connect to.
            
        Returns:
            Pool: asyncpg connection pool.
            
        Raises:
            ValueError: If database is not registered.
            RuntimeError: If pool creation fails.
        """
        if db_name not in self._configs:
            raise ValueError(f"Database '{db_name}' is not configured")
            
        if db_name not in self._pools:
            logger.info(f"Initializing connection pool for '{db_name}'...")
            try:
                self._pools[db_name] = await create_pool(self._configs[db_name])
            except Exception as e:
                logger.error(f"Failed to create pool for '{db_name}': {e}")
                raise
                
        return self._pools[db_name]

    async def get_executor(self, db_name: Optional[str] = None) -> SQLExecutor:
        """Get SQL executor for database.
        
        Args:
            db_name: Optional database name. Uses default if None.
            
        Returns:
            SQLExecutor: Configured executor instance.
            
        Raises:
            ValueError: If database not found or no default set.
        """
        target_db = db_name or self._default_db
        if not target_db:
            raise ValueError("No database specified and no default database configured")
            
        if target_db not in self._configs:
             raise ValueError(f"Database '{target_db}' is not configured")

        if target_db not in self._executors:
            pool = await self.get_pool(target_db)
            self._executors[target_db] = SQLExecutor(
                pool=pool,
                security_config=self.security_config,
                db_config=self._configs[target_db]
            )
            
        return self._executors[target_db]

    async def close_all(self) -> None:
        """Close all connection pools."""

        if self._pools:
            try:
                await close_pools(self._pools)
            finally:
                self._pools.clear()
                self._executors.clear()

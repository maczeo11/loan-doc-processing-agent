"""
Database session management for PostgreSQL.

Rules from AGENTS.md:
- PostgreSQL is authoritative.
- We depend on SELECT ... FOR UPDATE SKIP LOCKED, row locks, and transactional outbox commits.
"""



async def get_db_connection():
    """Yields an active database connection for transactional operations."""
    # Balaji to implement async connection pool with asyncpg / SQLAlchemy
    yield None

# Database Migration Guide

## Overview

This guide explains how to manage database schema changes in the Explainable Algorithmic Trading System.

## Current Schema Version

**Version**: 1.0.0 (Initial Schema)
**Date**: 2024
**Tables**: 7 (prices, articles, sentiment_scores, events, trading_signals, orders, backtest_results)

## Migration Strategy

### Approach

We use a hybrid approach:
1. **Initial Setup**: SQL script (`init_db.sql`)
2. **Schema Changes**: SQLAlchemy models + migration scripts
3. **Verification**: Automated schema validation

### Migration Workflow

```
1. Update SQLAlchemy Models
    ↓
2. Create Migration Script
    ↓
3. Test on Development Database
    ↓
4. Review and Approve
    ↓
5. Apply to Production
    ↓
6. Verify Schema
```

## Creating a Migration

### Step 1: Update ORM Models

Edit `src/database/models.py`:

```python
# Example: Adding a new column to Price table
class Price(Base):
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    open = Column(DECIMAL(10, 2))
    high = Column(DECIMAL(10, 2))
    low = Column(DECIMAL(10, 2))
    close = Column(DECIMAL(10, 2))
    volume = Column(BigInteger)
    adjusted_close = Column(DECIMAL(10, 2))  # NEW COLUMN
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
```

### Step 2: Create Migration Script

Create a new file in `src/database/migrations/`:

```python
# src/database/migrations/002_add_adjusted_close.py
"""
Migration: Add adjusted_close column to prices table
Version: 1.1.0
Date: 2024-XX-XX
"""

from sqlalchemy import text
from src.database.connection import DatabaseConnection


def upgrade(db_connection: DatabaseConnection) -> None:
    """Apply migration."""
    with db_connection.get_session() as session:
        # Add column
        session.execute(text(
            "ALTER TABLE prices ADD COLUMN adjusted_close DECIMAL(10, 2)"
        ))
        
        # Backfill data (if needed)
        session.execute(text(
            "UPDATE prices SET adjusted_close = close WHERE adjusted_close IS NULL"
        ))
        
        print("Migration 002: Added adjusted_close column")


def downgrade(db_connection: DatabaseConnection) -> None:
    """Rollback migration."""
    with db_connection.get_session() as session:
        session.execute(text(
            "ALTER TABLE prices DROP COLUMN adjusted_close"
        ))
        
        print("Migration 002: Removed adjusted_close column")


def verify(db_connection: DatabaseConnection) -> bool:
    """Verify migration was applied."""
    with db_connection.get_session() as session:
        result = session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'prices' AND column_name = 'adjusted_close'"
        ))
        return result.fetchone() is not None
```

### Step 3: Update Migration Manager

Update `src/database/migrations.py` to track migration versions:

```python
# Add to migrations.py
MIGRATIONS = [
    "001_initial_schema",
    "002_add_adjusted_close",
    # Add new migrations here
]

def get_current_version(db_connection: DatabaseConnection) -> str:
    """Get current schema version."""
    # Implementation to track version
    pass

def apply_migration(db_connection: DatabaseConnection, migration_name: str) -> None:
    """Apply a specific migration."""
    # Import and execute migration
    pass
```

## Common Migration Patterns

### Adding a Column

```sql
ALTER TABLE table_name 
ADD COLUMN column_name data_type [constraints];
```

Example:
```python
session.execute(text(
    "ALTER TABLE prices ADD COLUMN adjusted_close DECIMAL(10, 2)"
))
```

### Removing a Column

```sql
ALTER TABLE table_name 
DROP COLUMN column_name;
```

Example:
```python
session.execute(text(
    "ALTER TABLE prices DROP COLUMN adjusted_close"
))
```

### Adding an Index

```sql
CREATE INDEX index_name ON table_name(column_name);
```

Example:
```python
session.execute(text(
    "CREATE INDEX idx_prices_adjusted_close ON prices(adjusted_close)"
))
```

### Adding a Foreign Key

```sql
ALTER TABLE child_table 
ADD CONSTRAINT fk_name 
FOREIGN KEY (column_name) 
REFERENCES parent_table(column_name);
```

Example:
```python
session.execute(text(
    "ALTER TABLE sentiment_scores "
    "ADD CONSTRAINT fk_sentiment_article "
    "FOREIGN KEY (article_id) REFERENCES articles(id)"
))
```

### Modifying a Column Type

```sql
ALTER TABLE table_name 
ALTER COLUMN column_name TYPE new_type;
```

Example:
```python
session.execute(text(
    "ALTER TABLE prices ALTER COLUMN volume TYPE BIGINT"
))
```

### Renaming a Column

```sql
ALTER TABLE table_name 
RENAME COLUMN old_name TO new_name;
```

Example:
```python
session.execute(text(
    "ALTER TABLE prices RENAME COLUMN close TO close_price"
))
```

### Adding a Table

```python
from src.database.models import Base

# Define new model in models.py
class NewTable(Base):
    __tablename__ = "new_table"
    # ... columns ...

# In migration
Base.metadata.tables['new_table'].create(db_connection.engine)
```

### Dropping a Table

```sql
DROP TABLE IF EXISTS table_name;
```

Example:
```python
session.execute(text("DROP TABLE IF EXISTS old_table"))
```

## Data Migrations

### Backfilling Data

```python
def upgrade(db_connection: DatabaseConnection) -> None:
    """Backfill missing data."""
    with db_connection.get_session() as session:
        # Add column
        session.execute(text(
            "ALTER TABLE prices ADD COLUMN adjusted_close DECIMAL(10, 2)"
        ))
        
        # Backfill with close price
        session.execute(text(
            "UPDATE prices SET adjusted_close = close WHERE adjusted_close IS NULL"
        ))
```

### Transforming Data

```python
def upgrade(db_connection: DatabaseConnection) -> None:
    """Transform existing data."""
    with db_connection.get_session() as session:
        # Get all records
        result = session.execute(text("SELECT id, old_value FROM table_name"))
        
        # Transform and update
        for row in result:
            new_value = transform_function(row.old_value)
            session.execute(
                text("UPDATE table_name SET new_value = :val WHERE id = :id"),
                {"val": new_value, "id": row.id}
            )
```

## Testing Migrations

### Test on Development Database

```python
# test_migration.py
from src.database import initialize_database, db_connection
from src.database.migrations import apply_migration

# Initialize
initialize_database()

# Apply migration
apply_migration(db_connection, "002_add_adjusted_close")

# Verify
from src.database.migrations.002_add_adjusted_close import verify
assert verify(db_connection), "Migration verification failed"

print("Migration test passed!")
```

### Rollback Test

```python
# Test rollback
from src.database.migrations.002_add_adjusted_close import downgrade

downgrade(db_connection)

# Verify rollback
assert not verify(db_connection), "Rollback verification failed"

print("Rollback test passed!")
```

## Production Migration Checklist

- [ ] Update ORM models in `models.py`
- [ ] Create migration script with upgrade/downgrade/verify
- [ ] Test migration on development database
- [ ] Test rollback on development database
- [ ] Review migration with team
- [ ] Backup production database
- [ ] Apply migration during maintenance window
- [ ] Verify migration success
- [ ] Monitor application for issues
- [ ] Document migration in changelog

## Rollback Procedure

### Immediate Rollback

If issues are detected immediately after migration:

```python
from src.database import initialize_database, db_connection
from src.database.migrations.XXX_migration_name import downgrade

initialize_database()
downgrade(db_connection)
```

### Restore from Backup

If data corruption occurs:

```bash
# Stop application
docker-compose stop

# Restore database
docker exec -i trading_postgres psql -U trading_user trading_db < backup.sql

# Restart application
docker-compose start
```

## Best Practices

### 1. Always Create Reversible Migrations

Every migration should have:
- `upgrade()`: Apply changes
- `downgrade()`: Revert changes
- `verify()`: Check if applied

### 2. Test Thoroughly

- Test on development database first
- Test with production-like data volume
- Test rollback procedure
- Verify application still works

### 3. Backup Before Migration

```bash
# Create backup
docker exec trading_postgres pg_dump -U trading_user trading_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 4. Use Transactions

Wrap migrations in transactions when possible:

```python
with db_connection.get_session() as session:
    try:
        # Migration operations
        session.execute(...)
        session.commit()
    except Exception as e:
        session.rollback()
        raise
```

### 5. Document Changes

Include in migration script:
- Purpose of migration
- Version number
- Date
- Author
- Breaking changes (if any)

### 6. Minimize Downtime

- Use online schema changes when possible
- Add columns as nullable first, then backfill
- Create indexes concurrently
- Avoid table locks during peak hours

### 7. Version Control

- Commit migration scripts to git
- Tag releases with schema version
- Maintain changelog

## Schema Versioning

### Version Format

`MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (incompatible with old code)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Current Version Tracking

Create a `schema_version` table:

```sql
CREATE TABLE schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    description TEXT
);
```

Track migrations:

```python
def record_migration(db_connection: DatabaseConnection, version: str, description: str):
    """Record migration in schema_version table."""
    with db_connection.get_session() as session:
        session.execute(
            text("INSERT INTO schema_version (version, description) VALUES (:v, :d)"),
            {"v": version, "d": description}
        )
```

## Troubleshooting

### Migration Fails Midway

1. Check error message
2. Rollback if possible
3. Restore from backup if needed
4. Fix migration script
5. Retry

### Schema Mismatch

If ORM models don't match database:

```python
from src.database.migrations import DatabaseMigration

migration = DatabaseMigration(db_connection)
migration.verify_schema()  # Check what's missing
```

### Performance Issues After Migration

1. Check if indexes were created
2. Analyze query plans
3. Update statistics: `ANALYZE table_name;`
4. Consider adding missing indexes

## Future Enhancements

### Planned Features

1. **Automatic Migration Generation**: Compare models to database
2. **Migration History Tracking**: Record all applied migrations
3. **Dry-run Mode**: Preview migration without applying
4. **Parallel Migrations**: Apply multiple migrations safely
5. **Schema Diff Tool**: Compare schemas across environments

## Resources

- [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
- [SQLAlchemy Schema Definition](https://docs.sqlalchemy.org/en/14/core/metadata.html)
- [Database Migration Best Practices](https://www.postgresql.org/docs/current/ddl.html)

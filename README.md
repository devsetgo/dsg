
[![Coverage fury.io](coverage-badge.svg)](https://github.com/devsetgo/dsg)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
# DevSetGo.com
My personal website and blog. This is a work in progress and will be updated as I have time.

Feel free to fork the project, but the content is mine. Using Calver of YY.MM.DD


## Development SQL Scripts


Drop all tables for POSTGRES
```sql
DO $$ DECLARE
    r RECORD;
BEGIN
    -- if the schema you operate on is not "current", you will want to
    -- replace current_schema() in query with 'schematodeletetablesfrom'
    -- *and* update the generate 'DROP...' accordingly.
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
        RAISE NOTICE 'Dropping table: %', r.tablename;
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;
```

# Database Migration

We use Alembic for database migration management. The project has been initialized with a baseline migration that represents the current database schema state.

## Available Commands

### Check Current Migration Status
```bash
make alembic-current
```
Shows which migration is currently applied to the database.

### View Migration History
```bash
make alembic-history
```
Displays all available migrations and their status.

### Create a New Migration
```bash
make alembic-rev
```
After making changes to your SQLAlchemy models in `src/db_tables.py`, run this command to generate a new migration. You'll be prompted to enter a descriptive name for the migration (e.g., "add_user_bio_field", "create_audit_table").

### Apply Migrations
```bash
make alembic-migrate
```
Applies all pending migrations to upgrade your database to the latest schema version.

### Downgrade Database
```bash
make alembic-downgrade
```
Downgrades your database to a previous migration. You'll be prompted to enter the revision name to downgrade to.

## Workflow Example

1. **Make changes to your models** in `src/db_tables.py`
2. **Generate a migration**:
   ```bash
   make alembic-rev
   # Enter descriptive name when prompted
   ```
3. **Review the generated migration** in `alembic/versions/` before applying
4. **Apply the migration**:
   ```bash
   make alembic-migrate
   ```

## Important Notes

- **Always review generated migrations** before applying them, especially in production
- **Test migrations on development databases** first
- **Backup your database** before applying migrations in production
- **Commit migration files** to version control along with model changes
- The project uses a baseline migration approach for existing databases

## Configuration

- Alembic configuration: `alembic.ini`
- Environment setup: `alembic/env.py` (configured for async database operations)
- Database URL is automatically set from environment variables via `scripts/env.sh`


# Add Git credientials
Store and add username and email to git config
```bash
git config --global credential.helper store
git config --global user.name "Mike Ryan"
git config --global user.email "mikeryan56@gmail.com"
```
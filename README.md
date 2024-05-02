# www
Hugo site for DevSetGo.com and other static sites.

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

We use Alembic for database migration. Here are the steps to create and apply database migrations:

1. **Initialize Alembic**

    If you haven't already, initialize Alembic in your project:

    ```bash
    make alembic-init
    ```

    This will create a new directory named `alembic` in your project root, which contains your migration scripts.

2. **Create a New Migration**

    After you've made changes to your SQLAlchemy models, you can create a new migration script with:

    ```bash
    make alembic-rev
    ```

    You'll be prompted to enter a name for the migration. This name should describe the changes you've made.

3. **Apply Migrations**

    To apply the migrations to your database, run:

    ```bash
    make alembic-migrate
    ```

    This will upgrade your database to the latest version.

4. **Downgrade Database**

    If you need to downgrade your database to a previous version, you can use:

    ```bash
    make alembic-downgrade
    ```

    You'll be prompted to enter the name of the revision to downgrade to.

Remember to commit your migration scripts to version control along with the corresponding changes to your models.

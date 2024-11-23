#!/bin/bash
export $(grep -v '^#' .env | xargs -d '\n')

if [[ "$DB_DRIVER" == "sqlite+aiosqlite:///:memory:?cache=shared" ]]; then
    DATABASE_URL=$DB_DRIVER
elif [[ "$DB_DRIVER" == "sqlite+aiosqlite" ]]; then
    DATABASE_URL="$DB_DRIVER:///sqlite_db/$DB_NAME"
else
    DATABASE_URL="postgresql+asyncpg://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
fi

echo "In env.sh, DATABASE_URL is: $DATABASE_URL"
echo $DATABASE_URL > /tmp/db_url.txt
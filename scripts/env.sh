#!/bin/bash
export $(grep -v '^#' .env | xargs -d '\n')

if [[ "$DB_DRIVER" == "sqlite+aiosqlite:///:memory:?cache=shared" ]]; then
    DATABASE_URL=$DB_DRIVER
elif [[ "$DB_DRIVER" == "sqlite+aiosqlite" ]]; then
    if [[ "$DB_NAME" != *"."* ]]; then
        DB_NAME="$DB_NAME.db"
    fi
    DATABASE_URL="$DB_DRIVER:///sqlite_db/$DB_NAME"
else
    DATABASE_URL="$DB_DRIVER://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
fi

echo $DATABASE_URL > /tmp/db_url.txt
echo "In env.sh, DATABASE_URL is: $DATABASE_URL"
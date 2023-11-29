#!/bin/bash
set -e
set -x
#delete db
if [[ -f /workspace/src/sqlite_db/api.db ]]
then
    echo "deleting api.db"
    rm /workspace/src/sqlite_db/api.db
fi

#delete logs
if [[ -f /workspace/src/log/log.log ]]
then
    echo "deleting api.db"
    rm /workspace/src/log/log.log
fi

# run dev
uvicorn main:app --port 5000 --reload --log-level debug


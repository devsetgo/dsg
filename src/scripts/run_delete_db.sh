#!/bin/bash
set -e
set -x
#delete db
if [[ -f ~/dsg/src/sqlite_db/api.db ]]
then
    echo "deleting api.db"
    rm ~/dsg/src/sqlite_db/api.db
fi

#delete logs
if [[ -f ~/dsg/src/log/app_log.log ]]
then
    echo "deleting api.db"
    rm ~/dsg/src/log/app_log.log
fi

# run dev
uvicorn main:app --port 5000 --reload --log-level debug


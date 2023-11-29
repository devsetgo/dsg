# -*- coding: utf-8 -*-

"""
This script handles various database operations.
It includes functionality to count rows in a query,
fetch a limited set of results from a query or multiple queries,
and execute database operations like insert and update on one or many records.

The DatabaseOperations class encapsulates these functionalities and 
can be used to interact with the database asynchronously.
"""

import logging

# Importing required modules and libraries
from typing import List

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.future import select

from .database_connector import AsyncDatabase


# Class to handle Database operations
class DatabaseOperations:
    # Method to count rows in a query
    @classmethod
    async def count_query(cls, query):
        async with AsyncDatabase().get_db_session() as session:
            result = await session.execute(select(func.count()).select_from(query))
            return result.scalar()

    # Method to fetch a limited set of results from a query
    @classmethod
    async def fetch_query(cls, query, limit=500, offset=0):
        async with AsyncDatabase().get_db_session() as session:
            result = await session.execute(query.limit(limit).offset(offset))
            return result.scalars().all()

    # Method to fetch a limited set of results from multiple queries
    @classmethod
    async def fetch_queries(cls, queries: dict, limit=500, offset=0):
        results = {}
        async with AsyncDatabase().get_db_session() as session:
            for query_name, query in queries.items():
                result = await session.execute(query.limit(limit).offset(offset))
                results[query_name] = result.scalars().all()
        return results

    # Method to execute a single database operation (like insert, update) on one record
    @classmethod
    async def execute_one(cls, record):
        try:
            async with AsyncDatabase().get_db_session() as session:
                session.add(record)
                await session.commit()
            logging.info("Record operation successful")
            return record
        except IntegrityError as ex:
            logging.error(f"IntegrityError on record: {ex}")
            error_only = str(ex).split("[SQL:")[0]
            # return {"error":error_only,"details":"see logs for further information"}
            raise HTTPException(
                status_code=400,
                detail={
                    "error": error_only,
                    "details": "see logs for further information",
                },
            )

        except SQLAlchemyError as ex:
            logging.error(f"SQLAlchemyError on record: {ex}")
            error_only = str(ex).split("[SQL:")[0]
            # return {"error":error_only,"details":"see logs for further information"}
            raise HTTPException(
                status_code=400,
                detail={
                    "error": error_only,
                    "details": "see logs for further information",
                },
            )
        except Exception as ex:
            logging.error(f"Exception Failed to perform operation on record: {ex}")
            error_only = str(ex).split("[SQL:")[0]
            # return {"error":error_only,"details":"see logs for further information"}
            raise HTTPException(
                status_code=400,
                detail={
                    "error": error_only,
                    "details": "see logs for further information",
                },
            )

    # Method to execute multiple database operations (like bulk insert, update) on many records
    @classmethod
    async def execute_many(cls, records: List):
        # TODO: How to make this report back what records failed. This should be optional to fail all or allow successful records to be committed.

        try:
            async with AsyncDatabase().get_db_session() as session:
                session.add_all(records)
                await session.commit()

                num_records = len(records)
                logging.info(
                    f"Record operations were successful. {num_records} records were created."
                )

                return records
        except Exception as ex:
            error_only = str(ex).split("[SQL:")[0]
            logging.error(f"Failed to perform operations on records: {ex}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": error_only,
                    "details": "see logs for further information",
                },
            )

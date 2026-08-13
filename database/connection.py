import pyodbc
import asyncio
from functools import partial
from config import DB_CONN_STR


def _get_connection():
    return pyodbc.connect(DB_CONN_STR)


async def get_conn():
    loop = asyncio.get_event_loop()
    conn = await loop.run_in_executor(None, _get_connection)
    return conn

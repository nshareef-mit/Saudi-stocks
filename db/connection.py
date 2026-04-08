import logging
import os
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv

load_dotenv()
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class DatabaseConnection:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not set in the environment.")

    def get_connection(self):
        try:
            conn = psycopg2.connect(self.database_url)
            conn.autocommit = False
            return conn
        except Exception as exc:
            LOGGER.exception("Failed to connect to the database.")
            raise

    @contextmanager
    def connection(self):
        conn = None
        try:
            conn = self.get_connection()
            yield conn
            conn.commit()
        except Exception:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if conn is not None:
                conn.close()

    def execute_query(self, query, params=None):
        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)

    def fetch_all(self, query, params=None):
        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

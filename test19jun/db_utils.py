import psycopg2
from psycopg2 import extras

# Database configuration dictionary
DB_CONFIG = {
    "host": "localhost",
    "database": "weighbridge",   # Make sure this is the correct db
    "user": "postgres",
    "password": "CHAMP"          # Replace with your actual password or use env vars for security
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_one(query, params=None):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

def fetch_all(query, params=None):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()

def execute_query(query, params=None, fetch_lastrowid=False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch_lastrowid:
                last_id = cur.fetchone()[0]
                conn.commit()
                return last_id
            conn.commit()

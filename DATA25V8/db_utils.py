import psycopg2
from psycopg2 import extras

DB_CONFIG = {
    "host": "localhost",
    "database": "weighbridgeold",
    "user": "postgres",
    "password": "CHAMP"
}

_conn = None

def get_new_connection():
    global _conn
    if _conn is None or (_conn and getattr(_conn, "closed", False)):
        _conn = psycopg2.connect(**DB_CONFIG)
    return _conn

def fetch_one(query, params=None):
    with get_new_connection().cursor(cursor_factory=extras.DictCursor) as cur:
        cur.execute(query, params or ())
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)

def fetch_all(query, params=None):
    with get_new_connection().cursor(cursor_factory=extras.DictCursor) as cur:
        cur.execute(query, params or ())
        rows = cur.fetchall()
        return [dict(row) for row in rows]

def execute_query(query, params=None, fetch_lastrowid=False):
    conn = get_new_connection()
    with conn.cursor(cursor_factory=extras.DictCursor) as cur:
        cur.execute(query, params or ())
        if cur.description:
            result = cur.fetchall()
            conn.commit()
            return [dict(row) for row in result]
        if fetch_lastrowid:
            last_id = cur.fetchone()
            conn.commit()
            return last_id
        conn.commit()
        return None

def get_user_permissions(username):
    """
    Fetches user permissions based on the simplified 'is_admin' flag.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=extras.DictCursor)
    # --- This queries the new 'is_admin' column ---
    cur.execute("""
        SELECT username, is_admin
        FROM usermanagement
        WHERE username = %s
    """, (username,))
    user_data = cur.fetchone()
    conn.close()

    if user_data:
        # Returns a simple dictionary with the admin status.
        return {
            'username': user_data['username'],
            'is_admin': user_data['is_admin']
        }
    return None

if __name__ == "__main__":
    row = fetch_one("SELECT * FROM tickets LIMIT 1;")
    print(row)

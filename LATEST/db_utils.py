import psycopg2
from psycopg2 import extras

DB_CONFIG = {
    "host": "localhost",
    "database": "weighbridgeold",
    "user": "postgres",
    "password": "CHAMP"
}

def get_new_connection():
    """
    Establishes and returns a new database connection.
    """
    return psycopg2.connect(**DB_CONFIG)

def fetch_one(query, params=None):
    """
    Fetches a single row from the database using a new, safely-managed connection.
    """
    try:
        with get_new_connection() as conn:
            with conn.cursor(cursor_factory=extras.DictCursor) as cur:
                cur.execute(query, params or ())
                row = cur.fetchone()
                return dict(row) if row else None
    except psycopg2.Error as e:
        print(f"Database error in fetch_one: {e}")
        return None

def fetch_all(query, params=None):
    """
    Fetches all rows from the database using a new, safely-managed connection.
    """
    with get_new_connection() as conn:
        with conn.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall()
            return [dict(row) for row in rows]

def execute_query(query, params=None, fetch_lastrowid=False):
    """
    Executes a query (like INSERT, UPDATE) and commits it.
    """
    result = None
    with get_new_connection() as conn:
        with conn.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute(query, params or ())
            if fetch_lastrowid:
                result = cur.fetchone()
            elif cur.description:
                result = [dict(row) for row in cur.fetchall()]
    return result

# --- MOVED FROM first_load_window.py ---

def get_ticket_columns():
    """Fetches the set of column names for the 'tickets' table."""
    rows = fetch_all("SELECT column_name FROM information_schema.columns WHERE table_name='tickets'")
    return set(r["column_name"] for r in rows) if rows else set()

def get_ticket_column_types():
    """Fetches a dictionary of column names to their data types for the 'tickets' table."""
    rows = fetch_all("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='tickets'")
    return {r["column_name"]: r["data_type"] for r in rows} if rows else {}

def unified_save_ticket(params):
    """
    Inserts a new ticket or updates an existing one based on TicketNumber (UPSERT).
    Dynamically builds the INSERT/UPDATE query based on the provided parameters.
    """
    ticket_columns = get_ticket_columns()
    filtered_params = {k: v for k, v in params.items() if k in ticket_columns}
    if not filtered_params or "TicketNumber" not in filtered_params:
        print("Warning: unified_save_ticket requires 'TicketNumber' in params.")
        return

    ticket_column_types = get_ticket_column_types()
    for k in list(filtered_params.keys()):
        if k in ticket_column_types and ticket_column_types[k] in ("integer", "bigint", "smallint"):
            if filtered_params[k] in ("", None):
                filtered_params[k] = None
            else:
                try:
                    filtered_params[k] = int(float(filtered_params[k]))
                except (ValueError, TypeError):
                    filtered_params[k] = None
    
    update_keys = [k for k in filtered_params.keys() if k != "TicketNumber"]
    if not update_keys:
        return # Nothing to update

    set_clause = ", ".join([f'"{k}" = %({k})s' for k in update_keys])
    insert_columns = ', '.join([f'"{k}"' for k in filtered_params.keys()])
    insert_values = ', '.join([f'%({k})s' for k in filtered_params.keys()])
    
    query = f"""
    INSERT INTO tickets ({insert_columns}) VALUES ({insert_values})
    ON CONFLICT ("TicketNumber") DO UPDATE SET {set_clause}
    """
    execute_query(query, filtered_params)

def get_user_permissions(username):
    """
    Fetches user permissions.
    """
    query = "SELECT username, is_admin FROM usermanagement WHERE username = %s"
    user_data = fetch_one(query, (username,))
    if user_data:
        return {'username': user_data['username'], 'is_admin': user_data['is_admin']}
    return None

if __name__ == "__main__":
    print("Testing database connection...")
    row = fetch_one("SELECT * FROM tickets LIMIT 1;")
    if row:
        print("Successfully fetched one row:", row)
    else:
        print("Could not fetch a row.")

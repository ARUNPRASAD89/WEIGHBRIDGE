import db_utils
from psycopg2 import sql, extras
import math
from decimal import Decimal

def _round_to_nearest(value, nearest=5):
    """Rounds a number to the nearest multiple of a value (e.g., 5 or 10)."""
    if nearest == 0: return value
    return nearest * round(float(value) / nearest)

def calculate_amounts(vehicle_name, weight_kg, load_status):
    """
    Calculates amounts based on the vehicle type, weight, and load status
    using a direct tier-based lookup.
    """
    conn = db_utils.get_new_connection()
    try:
        with conn.cursor(cursor_factory=extras.DictCursor) as cur:
            cur.execute("SELECT * FROM ratechart WHERE vehiclename = %s", (vehicle_name,))
            rate_info_raw = cur.fetchone()
    finally:
        if conn: conn.close()

    if not rate_info_raw:
        return {'eamount': 0, 'lamount': 0, 'tamount': 0}

    # --- FIX: Intelligently convert only number types, leaving strings alone ---
    rate_info = {}
    for key, value in rate_info_raw.items():
        if isinstance(value, Decimal):
            rate_info[key] = float(value)  # For percentage columns
        elif isinstance(value, (int, float)):
            rate_info[key] = value         # For rate columns (now integers)
        else:
            rate_info[key] = value         # For text columns like 'vehiclename'

    eamount = 0
    lamount = 0

    if load_status == "Empty":
        eamount = rate_info.get('empty_rate', 0)
    
    elif load_status == "Load":
        weight_tons = float(weight_kg) / 1000.0
        
        if 0 <= weight_tons < 20:
            lamount = rate_info.get('load_base_rate', 0)
        elif 20 <= weight_tons < 30:
            lamount = rate_info.get('above20ton_rate', 0)
        elif 30 <= weight_tons < 40:
            lamount = rate_info.get('above30ton_rate', 0)
        elif 40 <= weight_tons < 50:
            lamount = rate_info.get('above40ton_rate', 0)
        elif 50 <= weight_tons < 60:
            lamount = rate_info.get('above50ton_rate', 0)
        else:
            lamount = rate_info.get('above60ton_rate', 0)

    # All calculations are now done with standard Python numbers
    total_amount = float(eamount + lamount)
    increase_percent = rate_info.get('increase_percentage', 0.0)
    decrease_percent = rate_info.get('decrease_percentage', 0.0)
    
    should_round = False
    if increase_percent > 0:
        total_amount += total_amount * (increase_percent / 100.0)
        should_round = True
    if decrease_percent > 0:
        total_amount -= total_amount * (decrease_percent / 100.0)
        should_round = True

    if should_round:
        total_amount = _round_to_nearest(total_amount, 5)

    # Final amounts are rounded to the nearest whole number to be stored as integers
    if load_status == "Empty":
        eamount = int(round(total_amount))
        lamount = 0
    else:
        eamount = 0
        lamount = int(round(total_amount))
        
    return {
        'eamount': eamount, 
        'lamount': lamount,
        'tamount': int(round(total_amount))
    }

def add_or_update_rate(rate_data):
    """Adds a new rate or updates an existing one based on the vehicle name."""
    conn = db_utils.get_new_connection()
    try:
        with conn.cursor() as cur:
            cols = list(rate_data.keys())
            update_assignments = ", ".join([f"{col} = EXCLUDED.{col}" for col in cols if col != 'vehiclename'])
            query = sql.SQL("""
                INSERT INTO ratechart ({fields}) VALUES ({values})
                ON CONFLICT (vehiclename) DO UPDATE SET {updates};
            """).format(
                fields=sql.SQL(', ').join(map(sql.Identifier, cols)),
                values=sql.SQL(', ').join(map(sql.Placeholder, list(rate_data.keys()))),
                updates=sql.SQL(update_assignments)
            )
            cur.execute(query, rate_data)
            conn.commit()
    finally:
        if conn: conn.close()

def get_all_vehicle_rates():
    """Retrieves all rate chart entries from the database."""
    return db_utils.fetch_all("SELECT * FROM ratechart ORDER BY id;")

import db_utils
from psycopg2 import sql, extras
import math
from decimal import Decimal

def _round_to_nearest(value, nearest=5):
    """Rounds a number to the nearest multiple of a value (e.g., 5 or 10)."""
    if nearest == 0: return value
    return nearest * round(float(value) / nearest)

def get_all_vehicle_rates():
    """
    Fetches all vehicle rate records from the 'ratechart' table, including the image path.
    """
    query = """
        SELECT 
            vehiclename, empty_rate, load_base_rate, 
            above20ton_rate, above30ton_rate, above40ton_rate, 
            above50ton_rate, above60ton_rate, increase_percentage, decrease_percentage,
            image_path 
        FROM ratechart 
        ORDER BY vehiclename
    """
    return db_utils.fetch_all(query)

def add_or_update_rate(rate_data):
    """
    Inserts a new vehicle rate or updates an existing one in the 'ratechart' table.
    Handles the new 'image_path' field.
    """
    vehicle_name = rate_data.get('vehiclename')
    if not vehicle_name:
        raise ValueError("Vehicle name is required.")

    existing_rate = db_utils.fetch_one("SELECT vehiclename FROM ratechart WHERE vehiclename = %s", (vehicle_name,))

    fields = [
        "vehiclename", "empty_rate", "load_base_rate", "above20ton_rate",
        "above30ton_rate", "above40ton_rate", "above50ton_rate", "above60ton_rate",
        "increase_percentage", "decrease_percentage", "image_path"
    ]

    if existing_rate:
        set_clauses = [f'"{field}" = %s' for field in fields if field != 'vehiclename']
        query = f'UPDATE ratechart SET {", ".join(set_clauses)} WHERE vehiclename = %s'
        params = [rate_data.get(field) for field in fields if field != 'vehiclename']
        params.append(vehicle_name)
        db_utils.execute_query(query, tuple(params))
    else:
        placeholders = ', '.join(['%s'] * len(fields))
        column_names = ', '.join([f'"{field}"' for field in fields])
        query = f'INSERT INTO ratechart ({column_names}) VALUES ({placeholders})'
        params = [rate_data.get(field) for field in fields]
        db_utils.execute_query(query, tuple(params))

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

    # Intelligently convert only number types, leaving strings alone
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

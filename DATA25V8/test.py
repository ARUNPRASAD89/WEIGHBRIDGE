from db_utils import get_new_connection

conn = get_new_connection()
cur = conn.cursor()
cur.execute('SELECT "TicketNumber" FROM tickets WHERE "Pending" = TRUE')
for row in cur.fetchall():
    print(row)
cur.close()
conn.close()

import sqlite3

conn = sqlite3.connect('garbage_tracking.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print('Tables in database:', tables)

# Check if trucks table exists
if 'trucks' in tables:
    cursor.execute('SELECT COUNT(*) FROM trucks')
    count = cursor.fetchone()[0]
    print(f'\nTrucks count: {count}')
    
    if count > 0:
        cursor.execute('SELECT id, registration_number, assigned_route_id, current_status, latitude, longitude FROM trucks LIMIT 5')
        print('\nFirst 5 trucks:')
        for row in cursor.fetchall():
            print(f'  ID: {row[0]}, Reg: {row[1]}, Route: {row[2]}, Status: {row[3]}, Lat: {row[4]}, Lng: {row[5]}')
else:
    print('\nTrucks table does not exist!')

# Check routes
if 'routes' in tables:
    cursor.execute('SELECT COUNT(*) FROM routes')
    count = cursor.fetchone()[0]
    print(f'\nRoutes count: {count}')
    
    if count > 0:
        cursor.execute('SELECT id, name, pickup_points FROM routes LIMIT 3')
        print('\nFirst 3 routes:')
        for row in cursor.fetchall():
            pickup_points = row[2][:100] if row[2] else 'None'
            print(f'  ID: {row[0]}, Name: {row[1]}, Pickup Points: {pickup_points}...')

conn.close()

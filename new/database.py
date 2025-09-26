import sqlite3
import random

DB_PATH = 'tracking.db'





def create_database_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id TEXT PRIMARY KEY,
        license_plate TEXT NOT NULL UNIQUE,
        vehicle_type TEXT NOT NULL,
        region TEXT NOT NULL,
        seats INTEGER,
        service_type TEXT DEFAULT 'Local',
        current_route_id INTEGER,
        last_known_lat REAL,
        last_known_lon REAL,
        last_segment_index INTEGER DEFAULT 0,
        direction TEXT DEFAULT 'forward',
        FOREIGN KEY (current_route_id) REFERENCES routes (route_id)
    );
    """)





    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        route_id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_name TEXT NOT NULL UNIQUE
    );
    """)




    cursor.execute("""
    CREATE TABLE IF NOT EXISTS waypoints (
        waypoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id INTEGER NOT NULL,
        sequence INTEGER NOT NULL,
        waypoint_name TEXT NOT NULL,
        is_major_stop BOOLEAN DEFAULT 0,
        is_skippable BOOLEAN DEFAULT 0,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        waypoint_type TEXT NOT NULL,
        FOREIGN KEY (route_id) REFERENCES routes (route_id),
        UNIQUE (route_id, sequence)
    );
    """)
    



    cursor.execute("""
    CREATE TABLE IF NOT EXISTS live_gps_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        speed_kmh REAL,
        heading REAL,
        status TEXT,
        gps_status TEXT DEFAULT 'functional'
    );
    """)
    



    cursor.execute("""
    CREATE TABLE IF NOT EXISTS waypoint_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id TEXT NOT NULL,
        waypoint_id INTEGER NOT NULL,
        arrival_timestamp TEXT NOT NULL,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (vehicle_id),
        FOREIGN KEY (waypoint_id) REFERENCES waypoints (waypoint_id)
    );
    """)
    



    cursor.execute("CREATE INDEX IF NOT EXISTS idx_live_vehicle_ts ON live_gps_positions (vehicle_id, timestamp DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_vehicle_ts ON waypoint_history (vehicle_id, arrival_timestamp DESC);")
    

    conn.commit()
    conn.close()
    print("Database schema created")








if __name__ == '__main__':
    create_database_schema()
    


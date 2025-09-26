import sqlite3


DB_PATH = 'tracking.db'



def populate_data(routes_data, waypoints_data, vehicles_to_populate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executemany("INSERT OR IGNORE INTO routes (route_name) VALUES (?)", [(r,) for r in routes_data])
    conn.commit()

    cursor.execute("SELECT route_id, route_name FROM routes")
    route_ids = {name: id for id, name in cursor.fetchall()}

    waypoints_with_ids = [
        (route_ids[route_name], seq, wp_name, is_major, is_skip, lat, lon, wp_type)
        for (route_name, seq, wp_name, is_major, is_skip, lat, lon, wp_type) in waypoints_data
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO waypoints (route_id, sequence, waypoint_name, is_major_stop, is_skippable, latitude, longitude, waypoint_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, waypoints_with_ids)
    conn.commit()

    cursor.execute("SELECT route_id, sequence, latitude, longitude, waypoint_name FROM waypoints")
    waypoints_map = {(row[0], row[4]): (row[1]-1, row[2], row[3]) for row in cursor.fetchall()}

    

    for item in vehicles_to_populate:
        plate, v_type, region, seats, route_name, service = item["vd"]
        route_id = route_ids[route_name]
        vehicle_id = f"{region[:2].upper()}-{v_type.upper()}-{plate[-4:]}"
        
        last_idx, last_lat, last_lon, direction = 0, None, None, 'forward'
        
        if item["init"]:
            start_wp_name, start_dir = item["init"]
            if (route_id, start_wp_name) in waypoints_map:
                last_idx, last_lat, last_lon = waypoints_map[(route_id, start_wp_name)]
                direction = start_dir
        
        cursor.execute("""
            INSERT OR IGNORE INTO vehicles 
            (vehicle_id, license_plate, vehicle_type, region, seats, service_type, current_route_id, last_segment_index, last_known_lat, last_known_lon, direction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vehicle_id, plate, v_type, region, seats, service, route_id, last_idx, last_lat, last_lon, direction))
    conn.commit()


    print("data added")
    conn.close()







def register_vehicle(license_plate, vehicle_type, region, seats, route_name, service_type='Local'):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT route_id FROM routes WHERE route_name = ?", (route_name,))
    route_result = cursor.fetchone()

    if not route_result:
        conn.close()
        return {"success": False, "message": f"Route '{route_name}' not found."}
    
    route_id = route_result[0]
    vehicle_id = f"{region[:2].upper()}-{vehicle_type.upper()}-{license_plate[-4:]}"

    try:
        cursor.execute("""
            INSERT INTO vehicles (vehicle_id, license_plate, vehicle_type, region, seats, service_type, current_route_id, last_segment_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (vehicle_id, license_plate, vehicle_type, region, seats, service_type, route_id, 0))
        conn.commit()
        conn.close()
        return {"success": True, "vehicle_id": vehicle_id}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "message": "A vehicle with this ID or license plate already exists."}





routes_data = ["Ludhiana - Jalandhar", "Ludhiana - Amritsar"]



waypoints_data = [
    ("Ludhiana - Jalandhar", 1, "Ludhiana Bus Stand", 1, 0, 30.896345, 75.845206, 'start'),
    ("Ludhiana - Jalandhar", 2, "Phillaur", 0, 0, 31.029548, 75.783800, 'stop'),
    ("Ludhiana - Jalandhar", 3, "Goraya", 0, 1, 31.123081, 75.775980, 'stop'),
    ("Ludhiana - Jalandhar", 4, "Phagwara Bypass", 0, 0, 31.173185, 75.627190, 'stop'),
    ("Ludhiana - Jalandhar", 5, "Chaheru", 0, 1, 31.262469, 75.707303, 'stop'),
    ("Ludhiana - Jalandhar", 6, "Jalandhar Bus Stand", 1, 0, 31.315593, 75.594005, 'end'),
    ("Ludhiana - Amritsar", 1, "Ludhiana Bus Stand", 1, 0, 30.896345, 75.845206, 'start'),
    ("Ludhiana - Amritsar", 2, "Jalandhar Bus Stand", 1, 0, 31.315593, 75.594005, 'stop'),
    ("Ludhiana - Amritsar", 3, "Kartarpur", 0, 1, 31.439479, 75.495102, 'stop'),
    ("Ludhiana - Amritsar", 4, "Beas", 0, 0, 31.518484, 75.288885, 'stop'),
    ("Ludhiana - Amritsar", 5, "Amritsar Bus Stand", 1, 0, 31.629586, 74.884780, 'end'),
]


vehicles_to_populate = [
        {"vd": ('PB10GH1234', 'Bus', 'Punjab', 52, 'Ludhiana - Jalandhar', 'Local'), "init": None},
        {"vd": ('PB10GH5678', 'Bus', 'Punjab', 52, 'Ludhiana - Jalandhar', 'Express'), "init": ("Phillaur", "forward")},
        {"vd": ('PB08EF9012', 'Bus', 'Punjab', 48, 'Ludhiana - Amritsar', 'Express'), "init": ("Jalandhar Bus Stand", "backward")},
        {"vd": ('PB32CD3456', 'Bus', 'Punjab', 45, 'Ludhiana - Amritsar', 'Local'), "init": None},
        {"vd": ('PB11AB7890', 'Bus', 'Punjab', 50, 'Ludhiana - Jalandhar', 'Local'), "init": ("Phagwara Bypass", "forward")},
        {"vd": ('PB65XY1122', 'Bus', 'Punjab', 52, 'Ludhiana - Jalandhar', 'Express'), "init": None},
        {"vd": ('PB02KL3344', 'Bus', 'Punjab', 48, 'Ludhiana - Amritsar', 'Local'), "init": ("Beas", "backward")},
    ]





populate_data(routes_data, waypoints_data, vehicles_to_populate)

print("\nreg vehicle")
result = register_vehicle(
    license_plate='PB65NEW4321', 
    vehicle_type='Bus', 
    region='Punjab', 
    seats=55, 
    route_name='Ludhiana - Jalandhar',
    service_type='Express'
)


print(result) 

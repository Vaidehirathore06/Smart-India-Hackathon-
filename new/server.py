import time
import sqlite3
from flask import Flask, render_template
from flask_socketio import SocketIO



DB_PATH = 'tracking.db'
app = Flask(__name__)
socketio = SocketIO(app, async_mode='gevent')







# Updated gets vehicle data by users location, eg for jalandhar bus stand 
# it fetches all busses which have that stop in common
def get_vehicles_data_by_waypoint(waypoint_name):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT
            p.vehicle_id,
            p.latitude,
            p.longitude,
            p.heading,
            p.status,
            p.speed_kmh,
            p.gps_status
        FROM live_gps_positions p
        INNER JOIN (
            SELECT vehicle_id, MAX(timestamp) as max_ts
            FROM live_gps_positions
            GROUP BY vehicle_id
        ) latest ON p.vehicle_id = latest.vehicle_id AND p.timestamp = latest.max_ts
        INNER JOIN vehicles v ON p.vehicle_id = v.vehicle_id
        WHERE v.current_route_id IN (
            SELECT DISTINCT route_id FROM waypoints WHERE waypoint_name = ?
        )
    """, (waypoint_name,))
    
    vehicles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return vehicles









@app.route('/')
def index():
    return render_template('index.html')

def background_location_emitter():
    tracked_locations = ["Ludhiana Bus Stand", "Phillaur", "Jalandhar Bus Stand"]
    while True:
        all_vehicles = {}
        for location in tracked_locations:
            vehicles_for_location = get_vehicles_data_by_waypoint(location)
            for vehicle in vehicles_for_location:
                all_vehicles[vehicle['vehicle_id']] = vehicle

        if all_vehicles:
            socketio.emit('live_location_update', {'vehicles': list(all_vehicles.values())})
        
        socketio.sleep(2)

@socketio.on('connect')
def handle_connect():
    print('Client connected to user server')

if __name__ == '__main__':
    socketio.start_background_task(target=background_location_emitter)
    socketio.run(app, debug=True, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)



    
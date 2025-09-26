import asyncio
import json
import math
import random
from datetime import datetime, timezone, timedelta
import sqlite3

from geopy.distance import geodesic
from geopy.point import Point
from get_routes import get_route




DB_PATH = 'tracking.db'





def get_vehicles_for_simulation():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicles WHERE region = 'Punjab'")
    vehicles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return vehicles





def get_mission_waypoints_for_route(route_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT waypoint_id, latitude, longitude, waypoint_type, is_major_stop, is_skippable
        FROM waypoints WHERE route_id = ? ORDER BY sequence ASC
    """, (route_id,))
    waypoints = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return waypoints





def update_live_position_in_db(packet, max_entries=1000):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO live_gps_positions (vehicle_id, timestamp, latitude, longitude, speed_kmh, heading, status, gps_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        packet['vehicle_id'], packet['timestamp'], packet['location']['lat'],
        packet['location']['lon'], packet['speed_kmh'], packet['heading'], 
        packet['status'], packet['gps_status']
    ))
    cursor.execute("""
        DELETE FROM live_gps_positions WHERE id IN (
            SELECT id FROM live_gps_positions WHERE vehicle_id = ?
            ORDER BY timestamp DESC LIMIT -1 OFFSET ?
        )
    """, (packet['vehicle_id'], max_entries))
    conn.commit()
    conn.close()





def save_vehicle_state(vehicle_id, lat, lon, segment_idx, direction):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE vehicles SET last_known_lat = ?, last_known_lon = ?,
        last_segment_index = ?, direction = ? WHERE vehicle_id = ?
    """, (lat, lon, segment_idx, direction, vehicle_id))
    conn.commit()
    conn.close()






def log_waypoint_arrival(vehicle_id, waypoint_id, timestamp):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO waypoint_history (vehicle_id, waypoint_id, arrival_timestamp)
        VALUES (?, ?, ?)
    """, (vehicle_id, waypoint_id, timestamp))
    conn.commit()
    conn.close()





def prune_waypoint_history(days=3):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    cursor.execute("DELETE FROM waypoint_history WHERE arrival_timestamp < ?", (cutoff_date,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted_count > 0:
        print(f"Pruned {deleted_count} old waypoint history records.")






class RouteManager:

    def __init__(self, max_requests_per_second=4):
        self.semaphore = asyncio.Semaphore(max_requests_per_second)


    def _format_waypoints_for_api(self, waypoint_list):
        return "|".join([f"{wp['latitude']},{wp['longitude']}" for wp in waypoint_list])
    


    async def build_full_route(self, mission_waypoints, vehicle_id):
        print(f"[{vehicle_id}] Building new detailed route...")
        waypoints_str = self._format_waypoints_for_api(mission_waypoints)

        async with self.semaphore:
            api_route_coords = await asyncio.to_thread(get_route, waypoints_str)

        if not api_route_coords: return [], {}
        full_route_coords = api_route_coords
        stop_indices = {}

        for wp in mission_waypoints:
            if wp.get('waypoint_type') != 'start':
                wp_lat, wp_lon = wp['latitude'], wp['longitude']
                closest_point_index = min(range(len(full_route_coords)),
                    key=lambda i: geodesic((wp_lat, wp_lon), (full_route_coords[i][1], full_route_coords[i][0])).m)
                stop_indices[closest_point_index] = {
                    "waypoint_id": wp['waypoint_id'],
                    "is_major": wp.get('is_major_stop', False),
                    "is_skippable": wp.get('is_skippable', False)
                }

        return full_route_coords, stop_indices





class VehicleSimulator:
    def __init__(self, vehicle_data, route_manager, speed_kmh=50, update_interval=1):
        self.vehicle_data = vehicle_data
        self.vehicle_id = vehicle_data['vehicle_id']
        self.route_manager = route_manager
        self.speed_mps = speed_kmh * 1000 / 3600
        self.update_interval = update_interval
        self.current_pos = None
        self.status = "initializing"
        self.gps_status = "functional"
        self.direction = vehicle_data['direction']
        self.current_segment_index = vehicle_data['last_segment_index']



    async def run(self):
        mission_waypoints = get_mission_waypoints_for_route(self.vehicle_data['current_route_id'])
        if self.direction == 'backward':
            mission_waypoints.reverse()


        while True:
            full_route_coords, stop_indices = await self.route_manager.build_full_route(mission_waypoints, self.vehicle_id)
            if not full_route_coords:
                await asyncio.sleep(60); continue

            #  FIXEd starting opints  off the mapp
            full_route_points = [Point(latitude=p[1], longitude=p[0]) for p in full_route_coords]

            if self.vehicle_data.get('last_known_lat') and self.vehicle_data.get('last_known_lon'):
               
                initial_pos_from_db = Point(
                    latitude=self.vehicle_data['last_known_lat'], 
                    longitude=self.vehicle_data['last_known_lon']
                )

                
                snapped_start_point = min(
                    full_route_points,
                    key=lambda p: geodesic(initial_pos_from_db, p).meters
                )
                
                self.current_pos = snapped_start_point
                
                self.current_segment_index = full_route_points.index(snapped_start_point)
                
                
                if self.current_segment_index >= len(full_route_points) - 1:
                    self.current_segment_index = len(full_route_points) - 2

                print(f"[{self.vehicle_id}] Snapped to route at index {self.current_segment_index}.")

            else:
                
                self.current_segment_index = 0
                self.current_pos = full_route_points[0]
            

            self.status = "moving"
            


            while self.current_segment_index < len(full_route_points) - 1:
                distance_to_travel = self.speed_mps * self.update_interval
                start_of_segment = self.current_pos
                
                
                end_of_segment = full_route_points[self.current_segment_index + 1]
                
                bearing = self._calculate_bearing(start_of_segment, end_of_segment)
                remaining_segment_distance = geodesic(start_of_segment, end_of_segment).meters

                if distance_to_travel >= remaining_segment_distance:
                    self.current_pos = end_of_segment
                    self.current_segment_index += 1
                else:
                    destination = geodesic(meters=distance_to_travel).destination(start_of_segment, bearing)
                    self.current_pos = destination
                
                packet = self.generate_gps_packet(bearing)
                update_live_position_in_db(packet)

                if self.current_segment_index in stop_indices:
                    stop_info = stop_indices[self.current_segment_index]
                    
                    should_stop = True
                    if stop_info['is_skippable'] and self.vehicle_data['service_type'] == 'Express':
                        should_stop = False

                    if should_stop:
                        self.status = "stopped"
                        stop_duration = 600 if stop_info["is_major"] else random.randint(240, 300)
                        packet = self.generate_gps_packet(bearing)
                        update_live_position_in_db(packet)
                        log_waypoint_arrival(self.vehicle_id, stop_info['waypoint_id'], packet['timestamp'])
                        await asyncio.sleep(stop_duration)
                        self.status = "moving"
                
                await asyncio.sleep(self.update_interval)

            self.status = "finished"
            end_stop_duration = random.randint(600, 900)
            packet = self.generate_gps_packet(0)
            update_live_position_in_db(packet)
            
            self.direction = 'backward' if self.direction == 'forward' else 'forward'
            mission_waypoints.reverse()
            
            save_vehicle_state(self.vehicle_id, self.current_pos.latitude, self.current_pos.longitude, 0, self.direction)
            await asyncio.sleep(end_stop_duration)
    



    def _calculate_bearing(self, a, b):
        lat1, lon1 = math.radians(a.latitude), math.radians(a.longitude)
        lat2, lon2 = math.radians(b.latitude), math.radians(b.longitude)
        d_lon = lon2 - lon1
        y = math.sin(d_lon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360




    def generate_gps_packet(self, heading):
        return {
            "vehicle_id": self.vehicle_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "location": {
                "lat": round(self.current_pos.latitude, 6),
                "lon": round(self.current_pos.longitude, 6)
            },
            "speed_kmh": round(self.speed_mps * 3.6 if self.status == "moving" else 0, 2),
            "heading": round(heading, 2),
            "status": self.status,
            "gps_status": self.gps_status
        }


    def start(self):
        return asyncio.create_task(self.run())




async def periodic_pruner():
    while True:
        await asyncio.sleep(3600)
        prune_waypoint_history()



async def main():
    route_manager = RouteManager()
    vehicles_to_simulate = get_vehicles_for_simulation()
    
    pruner_task = asyncio.create_task(periodic_pruner())
    

    simulators = []
    for vehicle_data in vehicles_to_simulate:
        speed = random.randint(35, 60)
        simulator = VehicleSimulator(vehicle_data, route_manager, speed_kmh=speed)
        simulators.append(simulator)
    


    tasks = [s.start() for s in simulators]
    tasks.append(pruner_task)
        
    await asyncio.gather(*tasks)



if __name__ == "__main__":
    asyncio.run(main())


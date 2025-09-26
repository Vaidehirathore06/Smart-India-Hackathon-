import requests
import json
from dotenv import  load_dotenv
import os
import folium

load_dotenv()
key = os.environ.get("ROUTE_API")

url = "https://api.geoapify.com/v1/routing"
# waypoints = "48.184731,11.547931|48.168254,11.581501|48.179391,11.612174"


def get_route(waypoints):
    querystring = {
        "waypoints": waypoints,
        "mode": "truck", # options: drive   light_truck	  medium_truck	 truck	 (22t)	  heavy_truck	 (40t)
        "apiKey": key
    }
    try:
        response = requests.get(url, params=querystring)
        response.raise_for_status()
        data = response.json()

        route_geometry = data["features"][0]["geometry"]["coordinates"]

        all_route_points = []
        for leg in route_geometry:
            all_route_points.extend(leg)
        return all_route_points


    except requests.exceptions.RequestException as e:
        print(f"An error occurred with the API request: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Could not find the coordinate data in the API response. Error: {e}")
        return None



# For testing ------------------------------------------------------------------------------------


# all_route_points = get_route(waypoints)
# if all_route_points:
#     file_name = "route.txt"
#     with open(file_name, "w") as f:
#         f.write("latitude,longitude\n")
#         for point in all_route_points:
#             f.write(f"{point[1]},{point[0]}\n")





# coords = []
# with open("route.txt", "r") as f:
#     next(f)  
#     for line in f:
#         lat, lon = map(float, line.strip().split(","))
#         coords.append([lat, lon]) 


# m = folium.Map(location=coords[0], zoom_start=18)

# folium.PolyLine(coords, color="blue", weight=5).add_to(m)


# # for i, point in enumerate(coords, 1):
# #     folium.Marker(point, popup=f"Point {i}").add_to(m)


# m.save("route.html")



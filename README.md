# SIH Transport System

## Project Overview
This project is a transportation tracking and simulation system that allows for real-time monitoring of vehicles along predefined routes. The system includes functionality for route planning, vehicle simulation, and data storage.

## Project Structure

```

└── new/            # Testing environment for simulator
    ├── get_routes.py          # Route fetching for tests
    ├── readme.md              # Test simulator documentation
    ├── server.py              # Test server implementation
    ├── simulator.py           # Test simulator implementation
    ├── templates/             # HTML templates for testing
    │   └── index.html         # Test UI template
    └── tracking.db            # Test database
```

## Data Flow

### 1. Route Planning Flow
1. **Route Data Acquisition**:
   - `get_routes.py` fetches route data from the Geoapify API
   - Routes are defined by waypoints (latitude/longitude coordinates)
   - The API returns detailed route geometry with coordinates

2. **Route Storage**:
   - Routes are stored in the database (`tracking.db`)
   - The database contains tables for routes and waypoints
   - Routes can be visualized using Folium (saved as `route.html`)

### 2. Vehicle Simulation Flow
1. **Simulation Initialization**:
   - `simulation_server.py` or `test_simulator/simulator.py` initializes vehicle simulations
   - Vehicles are loaded from the database with their assigned routes
   - The `RouteManager` class builds detailed routes from waypoints

2. **Vehicle Movement Simulation**:
   - `VehicleSimulator` class handles vehicle movement along routes
   - Vehicles move at specified speeds between waypoints
   - The simulator calculates positions, headings, and status updates

3. **Data Broadcasting**:
   - GPS position updates are emitted as events
   - Updates include vehicle ID, timestamp, location, speed, heading, and status
   - In the test environment, Socket.IO is used for real-time communication

### 3. Database Operations Flow
1. **Database Schema**:
   - `sim_database.py` defines the database schema
   - Tables include: vehicles, routes, waypoints, fares, and live_gps_positions

2. **Data Storage**:
   - Vehicle positions are stored in the `live_gps_positions` table
   - Vehicle state (last known position, segment index) is updated in the `vehicles` table
   - A limit is maintained on the number of position entries per vehicle

3. **Data Retrieval**:
   - Functions fetch vehicles for simulation based on region
   - Waypoints are retrieved for route planning
   - Live position data can be queried for tracking

## Key Components

### 1. Route Management
- Uses external API for route planning
- Handles waypoint formatting and route building
- Identifies stops along routes

### 2. Vehicle Simulation
- Simulates vehicle movement along routes
- Calculates positions based on speed and time
- Handles stops and status changes

### 3. Database Management
- Stores vehicle, route, and position data
- Maintains relationships between entities
- Provides functions for data operations

### 4. Server Implementation
- Manages multiple vehicle simulations
- Handles real-time data broadcasting
- Processes incoming and outgoing data

## Usage

1. **Database Setup**:
   - Run `sim_database.py` to create the database schema
   - Use `add_data.py` to populate the database with initial data

2. **Route Planning**:
   - Use `get_routes.py` to fetch and plan routes
   - Visualize routes using the generated HTML file

3. **Running Simulations**:
   - Execute `simulation_server.py` to start the main simulation
   - For testing, use the components in the `test_simulator` directory

4. **Development**:
   - The `new` directory contains updated implementations
   - Use these files for the latest features and improvements

## Dependencies
- Python 3.x
- SQLite
- Requests (for API calls)
- Geopy (for geographical calculations)
- Folium (for map visualization)
- Socket.IO (for real-time communication)
- dotenv (for environment variable management)
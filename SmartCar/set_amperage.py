# check_charge_status.py

import smartcar
import json
import os
from token_manager import TokenManager

client = smartcar.AuthClient(
    client_id='016a2cf0-2d2b-4644-900e-bff74c4824b6',
    client_secret='e84702b4-b42a-4420-841f-ba68e2696c69',
    redirect_uri='http://localhost:8000/callback',
    test_mode=False  # Set to False for production
)

# Instantiate TokenManager
token_manager = TokenManager(client)

# Get the access token, refreshing it if necessary
access_token = token_manager.get_or_refresh_access_token()

if not access_token:
    print("Authentication required")
    exit(1)

# Get the vehicle ID
vehicles = smartcar.get_vehicles(access_token)
vehicle_ids = vehicles.vehicles

if not vehicle_ids:
    print("No vehicles found")
    exit(1)


# Instantiate the vehicle
vehicle = smartcar.Vehicle(vehicle_ids[0], access_token)

# Request the charge status and SOC
try:
    print('in')
    ammeter = vehicle.request(
    "POST", 
    "tesla/charge/ammeter", 
    {"amperage": 4}
)    
    print(ammeter)
    
except smartcar.SmartcarException as e:
    print(f"Failed to set Amperage: {e}")

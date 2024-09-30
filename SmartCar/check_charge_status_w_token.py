# check_charge_status.py

import smartcar
import json
import os
from token_manager import TokenManager

client = smartcar.AuthClient(
    client_id='016a2cf0-2d2b-4644-900e-bff74c4824b6',
    client_secret='5fcd1830-9aeb-4fbe-bdeb-dd9265994ae3',
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
print(vehicles)

if not vehicle_ids:
    print("No vehicles found")
    exit(1)

# Instantiate the vehicle
vehicle = smartcar.Vehicle(vehicle_ids[0], access_token)

# Request the charge status and SOC
try:
    # Get the State of Charge (SOC)
    battery_status = vehicle.battery()
    soc = battery_status[0] * 100  # Convert to percentage
    print(soc)


    # ## This is all extra stuff @Ioan
    print(battery_status)
    vin_attributes = vehicle.attributes()
    print("Vin Attriubtes:", vin_attributes)
    # Get the Charger Plug in status
    plug_in_status = vehicle.charge().is_plugged_in
    charging_status = vehicle.charge().state
    print(f"Plug In Status: {plug_in_status}")
    print(f"Charging Status: {charging_status}")
    
except smartcar.SmartcarException as e:
    print(f"Failed to retrieve charge status or SOC: {e}")

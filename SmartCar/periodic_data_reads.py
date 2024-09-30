from flask import Flask, redirect, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import smartcar
import json
import os
import csv
import atexit
from datetime import datetime

app = Flask(__name__)

TOKEN_FILE = 'access_token.json'
CSV_FILE = 'vehicle_data.csv'

client = smartcar.AuthClient(
    client_id='016a2cf0-2d2b-4644-900e-bff74c4824b6',
    client_secret='e84702b4-b42a-4420-841f-ba68e2696c69',
    redirect_uri='http://localhost:8000/callback',
    test_mode=False  # Set to False for production
)

def load_token():
    print('inside load_token()')
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return None

def save_token(token):
    print('inside save_token()')
    token['expiration'] = token['expiration'].isoformat()
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token, f)

@app.route('/login', methods=['GET'])
def login():
    auth_url = client.get_auth_url(
        scope=[
            'read_vehicle_info',
            'read_location',
            'read_odometer',
            'read_battery',
            'read_charge',
            'read_speedometer',
            'read_thermometer',
            'read_tires',
            'read_user_profile',
            'read_vin',
            # 'control_charge'
        ]
    )
    return redirect(auth_url)

@app.route('/callback', methods=['GET'])
def callback():
    print('Inside callback()')
    code = request.args.get('code')
    access = client.exchange_code(code)
    save_token({
        'access_token': access.access_token,
        'refresh_token': access.refresh_token,
        'expiration': access.expiration
    })
    return redirect('/vehicle')

def refresh_token_if_needed():
    print('Inside refresh_token_if_needed()')
    token_data = load_token()
    if not token_data:
        print('inside not token_data')
        return None

    expiration_time = datetime.fromisoformat(token_data['expiration'])
    if datetime.now() >= expiration_time:
        print('Inside refresh if')
        new_access = client.exchange_refresh_token(token_data['refresh_token'])
        save_token({
            'access_token': new_access.access_token,
            'refresh_token': new_access.refresh_token,
            'expiration': new_access.expiration
        })
        return new_access.access_token
    print('Outside refresh if')
    return token_data['access_token']

def get_vehicle_data():
    print('Inside get_vehicle_data()')
    access_token = refresh_token_if_needed()
    if not access_token:
        return {"error": "No valid access token"}

    vehicles = smartcar.get_vehicles(access_token)
    vehicle_ids = vehicles.vehicles
    
    if not vehicle_ids:
        return {"error": "No vehicles found"}

    vehicle = smartcar.Vehicle(vehicle_ids[0], access_token)

    vehicle_data = {
        "timestamp": datetime.now().isoformat(),
        "make": vehicle.attributes().make,
        "model": vehicle.attributes().model,
        "year": vehicle.attributes().year,
        "total_battery_capacity": vehicle.battery_capacity().capacity,
        "current_battery_level": vehicle.battery().percent_remaining,
        "current_battery_range": vehicle.battery().range,
        "odometer": vehicle.odometer().distance,
        "location_lat": vehicle.location().latitude,
        "location_long": vehicle.location().longitude,
        "charge_plug_status": vehicle.charge().is_plugged_in,
        "charge_state": vehicle.charge().state,
        "vin": vehicle.vin().vin
    }

    return vehicle_data

def append_to_csv(data):
    print('Inside append_to_csv()')
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(data)

def poll_vehicle_data():
    print('Inside poll_vehile_data()')
    vehicle_data = get_vehicle_data()
    if "error" not in vehicle_data:
        append_to_csv(vehicle_data)
        print(f"Data appended to CSV: {vehicle_data}")
    else:
        print(f"Error: {vehicle_data['error']}")

@app.route('/vehicle', methods=['GET'])
def vehicle_endpoint():
    return jsonify(get_vehicle_data())

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=poll_vehicle_data, trigger="interval", minutes=5)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    app.run(port=8000)

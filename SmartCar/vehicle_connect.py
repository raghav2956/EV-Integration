from flask import Flask, redirect, request, jsonify
import atexit
import smartcar

app = Flask(__name__)
# Global variable to save our access_token
# access = None

client = smartcar.AuthClient(
    client_id='016a2cf0-2d2b-4644-900e-bff74c4824b6',
    client_secret='e84702b4-b42a-4420-841f-ba68e2696c69',
    redirect_uri='http://localhost:8000/callback',
    # scope=['read_vehicle_info'],
    test_mode=False  # Set to False for production
)

@app.route('/login', methods=['GET'])
def login():
    auth_url = client.get_auth_url(
        scope=[
            'read_vehicle_info',
            'read_location',
            'read_odometer',
            # 'read_alerts',
            'read_battery',
            'read_charge',
            # 'read_charge_locations',
            # 'read_charge_records',
            # 'read_charge_events',
            # 'read_climate',
            # 'read_compass',
            # 'read_extended_vehicle_info',
            # 'read_security',
            'read_speedometer',
            'read_thermometer',
            'read_tires',
            'read_user_profile',
            'read_vin',
            'control_charge'
        ]
    )
    return redirect(auth_url)

@app.route('/callback', methods=['GET'])
def callback():
    code = request.args.get('code')
    print(f"Authorization code: {code}")
    global access
    access = client.exchange_code(code)
    # print(f"Access token: {access['access_token']}")
    # access = client.exchange_code(code)
    return redirect('/vehicle')  

@app.route('/vehicle', methods=['GET'])
def get_vehicle():
    # Access our global variable to retrieve our access tokens
    global access
    
    # Get the smartcar vehicleIds associated with the access_token
    vehicles = smartcar.get_vehicles(access.access_token)
    vehicle_ids = vehicles.vehicles
    
    # Instantiate the first vehicle in the vehicle id list
    vehicle = smartcar.Vehicle(vehicle_ids[1], access.access_token)

    charge =  vehicle.request(
      "GET", 
      "tesla/charge"
    )
    print(charge)
    # Update vehicle data with Smartcar API responses
    vehicle_data = {
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
        # "charge_st": vehicle.charge().state,
        "vin": vehicle.vin().vin,
        "charge_state": charge 
    }
    # Stop a charge session
    try:
        vehicle.stop_charge()
        print("Charge session stopped.")
    except smartcar.SmartcarException as e:
        print(f"Error starting charge session: {e}")
    
    try:
        vehicle.start_charge()
        print("Charge session started.")
    except smartcar.SmartcarException as e:
        print(f"Error starting charge session: {e}")

    return jsonify(vehicle_data)

if __name__ == "__main__":
    app.run(port=8000)


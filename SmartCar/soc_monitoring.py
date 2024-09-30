import time
from token_manager import TokenManager
import smartcar

# Define the log file path
LOG_FILE = 'battery_status_log.txt'

# Function to log the battery status to a file
def log_battery_status(soc, plug_in_status, charging_status):
    with open(LOG_FILE, 'a') as file:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        file.write(f"{timestamp} - SOC: {soc}%, Plugged In: {plug_in_status}, Charging: {charging_status}\n")
    print(f"Logged: SOC: {soc}%, Plugged In: {plug_in_status}, Charging: {charging_status} at {timestamp}")

def monitor_battery_status(interval_minutes=5):
    client = smartcar.AuthClient(
        client_id='016a2cf0-2d2b-4644-900e-bff74c4824b6',
        client_secret='5fcd1830-9aeb-4fbe-bdeb-dd9265994ae3',
        redirect_uri='http://localhost:8000/callback',
        test_mode=False  # Set to True for sandbox testing
    )

    # Instantiate TokenManager
    token_manager = TokenManager(client)

    while True:
        try:
            # Get or refresh the access token
            access_token = token_manager.get_or_refresh_access_token()
            if not access_token:
                print("Authentication failed. Exiting...")
                break

            # Get the vehicle ID
            vehicles = smartcar.get_vehicles(access_token)
            vehicle_ids = vehicles.vehicles

            if not vehicle_ids:
                print("No vehicles found. Exiting...")
                break

            # Instantiate the vehicle with the first available ID
            vehicle = smartcar.Vehicle(vehicle_ids[0], access_token)

            # Request the charge status and SOC
            battery_status = vehicle.battery()
            soc = battery_status['percent_remaining'] * 100  # SOC in percentage

            # Get charging information
            charge_status = vehicle.charge()
            plug_in_status = charge_status['is_plugged_in']
            charging_status = charge_status['state']

            # Log the battery SOC and charging status
            log_battery_status(soc, plug_in_status, charging_status)

        except smartcar.SmartcarException as e:
            print(f"An error occurred while retrieving vehicle data: {e}")
        
        # Wait for the specified interval (in minutes) before the next check
        time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    monitor_battery_status(interval_minutes=5)  # Adjust interval as needed

import smartcar
from token_manager import TokenManager  # Importing TokenManager

client = smartcar.AuthClient(
    client_id='your_client_id',
    client_secret='your_client_secret',
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

# Get the vehicle IDs
vehicles = smartcar.get_vehicles(access_token)
vehicle_ids = vehicles.vehicles

if not vehicle_ids:
    print("No vehicles found")
    exit(1)

# Instantiate the vehicle (assuming vehicle ID 1 corresponds to the second vehicle in the list)
vehicle = smartcar.Vehicle(vehicle_ids[0], access_token)

# Start the charge session
try:
    vehicle.start_charge()
    print("Charge session started.")
except smartcar.SmartcarException as e:
    print(f"Error starting charge session: {e}")

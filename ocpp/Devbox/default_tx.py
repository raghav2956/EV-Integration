import asyncio
import logging
from datetime import datetime, timedelta

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)

from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call, call_result
from ocpp.v16.enums import Action, RegistrationStatus, ClearCacheStatus, ConfigurationStatus, ChargingProfilePurposeType, ChargingProfileKindType, RecurrencyKind

logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):
    @on(Action.BootNotification)
    async def on_boot_notification(
        self, charge_point_vendor: str, charge_point_model: str, **kwargs
    ):
        # await boot_notification_call(self, charge_point_model, charge_point_vendor)
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatus.accepted,
        )

    @on(Action.Heartbeat)
    def on_heartbeat(self):
        print("Got a Heartbeat!")
        return call_result.HeartbeatPayload(
            current_time=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        )


    @on(Action.StatusNotification)
    async def on_status_notification(self, connector_id: int, error_code: str, status: str, **kwargs):
        """
        Handle StatusNotification messages sent by the charger.
        
        Parameters:
        - connector_id (int): The connector for which the status is reported.
        - error_code (str): The error code, if any.
        - status (str): The current status of the connector.
        """
        logging.info(f"Received StatusNotification: connector_id={connector_id}, error_code={error_code}, status={status}")
        
        # You can add your logic here to handle different statuses
        if status == "Available":
            logging.info(f"Connector {connector_id} is available.")
        elif status == "Occupied":
            logging.info(f"Connector {connector_id} is occupied.")
        elif status == "Faulted":
            logging.warning(f"Connector {connector_id} has a fault: {error_code}")
        
        # Respond with an empty payload as per the OCPP 1.6 standard
        return call_result.StatusNotificationPayload()

config_status = {}
charge_points = {}

async def send_default_tx_profile(cp):

    # Define the charging profile
    charging_profile = {
        "chargingProfileId": 1,
        "transactionId": None,  # Apply to all future transactions
        "stackLevel": 0,  # Highest priority
        "chargingProfilePurpose": ChargingProfilePurposeType.tx_default_profile,
        "chargingProfileKind": ChargingProfileKindType.recurring,
        "recurrencyKind": RecurrencyKind.daily,
        "validFrom": None,
        "validTo": None,
        "chargingSchedule": {
            "duration": 86400,  # 24 hours in seconds
            "startSchedule": "2024-08-23T13:30:00Z",  # Start time in UTC (1:30 PM UK time)
            "chargingRateUnit": "A",  # Amperes
            "chargingSchedulePeriod": [
                { "startPeriod": 0, "limit": 8.7 },      # 1:30 PM - 3:30 PM (2 kW)
                { "startPeriod": 7200, "limit": 17.4 },  # 3:30 PM - 5:30 PM (4 kW)
                { "startPeriod": 14400, "limit": 21.7 }, # 5:30 PM - 7:30 PM (5 kW)
                { "startPeriod": 21600, "limit": 28.3 }, # 7:30 PM - 10:00 PM (6.5 kW)
                { "startPeriod": 30600, "limit": 0 },    # 10:00 PM - 1:30 PM next day (0 kW)
            ],
            "minChargingRate": None
        }
    }

    # Create the SetChargingProfile request
    request = call.SetChargingProfilePayload(
        connector_id=1,  # Assuming connector 1; adjust if necessary
        cs_charging_profiles=charging_profile
    )

    try:
        # Send the SetChargingProfile request and wait for the response
        timeout_seconds = 180
        response = await asyncio.wait_for(cp.call(request), timeout=timeout_seconds)

        # Check the result
        if response.status == "Accepted":
            logging.info("DefaultTx charging profile successfully set.")
        else:
            logging.error(f"Failed to set DefaultTx charging profile: {response.status}")
    except asyncio.TimeoutError:
        logging.error("Timed out waiting for the SetChargingProfile response.")


async def send_get_configuration_command(cp, keys=None):
    """
    Sends a GetConfiguration command to the given charge point.
    
    Parameters:
    cp (ChargePoint): An instance of the ChargePoint class representing the charger.
    keys (list): Optional list of configuration keys to retrieve. If None, all keys will be retrieved.
    """
    # Create the GetConfiguration request
    get_configuration_request = call.GetConfigurationPayload()
    
    try:
        # Send the GetConfiguration request and wait for the response
        timeout_seconds = 120
        response = await asyncio.wait_for(cp.call(get_configuration_request), timeout=timeout_seconds)
        
        # Now response is awaited, and we can handle the returned configuration data
        if response.configuration_key:
            logging.info("Received configuration keys:")
            for config in response.configuration_key:
                logging.info(f"Key: {config['key']}, Value: {config.get('value', 'Not set')}, Readonly: {config['readonly']}")
        else:
            logging.warning("No configuration keys were returned.")
            
        if response.unknown_key:
            logging.warning("The following keys were not recognized:")
            for key in response.unknown_key:
                logging.warning(f"Unknown key: {key}")
    except asyncio.TimeoutError:
        logging.error("Timed out waiting for the GetConfiguration response.")


async def wait_for_charger(charge_point_id, timeout=120):
    """ Wait for a specific charger to connect. """
    start_time = datetime.utcnow()
    while (datetime.utcnow() - start_time).total_seconds() < timeout:
        if charge_point_id in charge_points:
            return charge_points[charge_point_id]
        await asyncio.sleep(1)  # Wait 1 second before checking again
    raise TimeoutError(f"Charger {charge_point_id} did not connect within {timeout} seconds.")


async def on_connect(websocket, path):
    """For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.
    """
    try:
        requested_protocols = websocket.request_headers["Sec-WebSocket-Protocol"]
    except KeyError:
        logging.error("Client hasn't requested any Subprotocol. Closing Connection")
        return await websocket.close()
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        # In the websockets lib if no subprotocols are supported by the
        # client and the server, it proceeds without a subprotocol,
        # so we have to manually close the connection.
        logging.warning(
            "Protocols Mismatched | Expected Subprotocols: %s,"
            " but client supports  %s | Closing connection",
            websocket.available_subprotocols,
            requested_protocols,
        )
        return await websocket.close()

    charge_point_id = path.strip("/")
    print(charge_point_id)

    # # Check if the charge point is already connected
    # if charge_point_id in charge_points:
    #     logging.info(f"Charge point {charge_point_id} is already connected.")
    #     cp = ChargePoint(charge_point_id, websocket)
    #     await cp.start() 
    #     return

    cp = ChargePoint(charge_point_id, websocket)

    # Add the connected charge point to the dictionary
    charge_points[charge_point_id] = cp

    # Start the charge point logic in its own task
    start_task = asyncio.create_task(cp.start())

    if not config_status.get(charge_point_id, False):
        # Wait for the specific charger to connect before sending profile
        if charge_point_id == 'UKAGKHTV':
            print(charge_points)
            await send_default_tx_profile(charge_points['UKAGKHTV'])
            config_status[charge_point_id] = True

    # Wait for the start task to complete, which keeps the connection open
    try:
        await start_task
    except asyncio.CancelledError:
        logging.info(f"Connection closed for charge point: {charge_point_id}")

    # # Perform additional tasks (e.g., sending configuration commands)
    # if not config_status.get(charge_point_id, False):
    #     print(charge_points)
    #     await send_default_tx_profile(charge_points['UKF78PEM'])
    #     # await send_get_configuration_command(cp)
    #     config_status[charge_point_id] = True
    
    # # Wait for the start task to complete, which keeps the connection open
    # try:
    #     await start_task
    # except asyncio.CancelledError:
    #     logging.info(f"Connection closed for charge point: {charge_point_id}")
    
    # Remove from the dictionary when the connection closes
    charge_points.pop(charge_point_id, None)

    logging.info(f"Connection handler for {charge_point_id} is terminating")


async def main():
    server = await websockets.serve(
        on_connect, "0.0.0.0", 8080, subprotocols=["ocpp1.6"]
    )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())

import asyncio
import logging
from datetime import datetime

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
from ocpp.v16.enums import Action, RegistrationStatus, ClearCacheStatus, ConfigurationStatus

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

async def send_change_configuration_command(cp, key, value):
    """
    Sends a ChangeConfiguration command to the given charge point to change a configuration key.
    
    Parameters:
    cp (ChargePoint): An instance of the ChargePoint class representing the charger.
    key (str): The configuration key to change.
    value (str): The new value for the configuration key.
    """
    # Create the ChangeConfiguration request
    change_configuration_request = call.ChangeConfigurationPayload(key=key, value=value)
    
    try:
        # Send the ChangeConfiguration request and wait for the response
        response = await cp.call(change_configuration_request)
        
        # Handle the response based on the status returned
        if response.status == ConfigurationStatus.accepted:
            logging.info(f"Configuration key '{key}' changed to '{value}'.")
        elif response.status == ConfigurationStatus.rejected:
            logging.error(f"ChangeConfiguration request for key '{key}' was rejected.")
        elif response.status == ConfigurationStatus.reboot_required:
            logging.info(f"Configuration key '{key}' changed, but a reboot is required.")
        else:
            logging.warning(f"ChangeConfiguration request for key '{key}' returned unknown status: {response.status}.")
    except asyncio.TimeoutError:
        logging.error(f"Timed out waiting for the ChangeConfiguration response.")


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
        response = await cp.call(get_configuration_request)
        
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
        
async def safe_start(cp):
    # while True:
    try:
        await cp.start()
    except websockets.exceptions.ConnectionClosedOK:
        logging.info("Connection closed normally. Attempting to reconnect...")
        # await asyncio.sleep(5)  # Wait before trying to reconnect
    except websockets.exceptions.ConnectionClosedError as e:
        logging.error(f"Connection closed with an error: {e}. Attempting to reconnect...")
        # await asyncio.sleep(5)  # Wait before trying to reconnect
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        # break  # Exit the loop on an unexpected error

        
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

    # Start the charge point logic in its own task
    start_task = asyncio.create_task(cp.start())

    # Perform additional tasks (e.g., sending configuration commands)
    if not config_status.get(charge_point_id, False):
        await send_change_configuration_command(cp, key="HeartbeatInterval", value="30")
        await send_get_configuration_command(cp)
        config_status[charge_point_id] = True
    
    # Wait for the start task to complete, which keeps the connection open
    try:
        await start_task
    except asyncio.CancelledError:
        logging.info(f"Connection closed for charge point: {charge_point_id}")

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

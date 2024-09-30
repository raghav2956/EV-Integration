# import asyncio

# from ocpp.v201.enums import RegistrationStatusType
# import logging
# import websockets

# from ocpp.v201 import call
# from ocpp.v201 import ChargePoint as cp

# logging.basicConfig(level=logging.INFO)


# class ChargePoint(cp):

#     async def send_boot_notification(self):
#         request = call.BootNotification(
#             charging_station={
#                 'model': 'Wallbox XYZ',
#                 'vendor_name': 'anewone'
#             },
#             reason="PowerUp"
#         )
#         response = await self.call(request)

#         if response.status == RegistrationStatusType.accepted:
#             print("Connected to central system.")


# async def main():
#     async with websockets.connect(
#             'ws://localhost:9000/CP_1',
#             subprotocols=['ocpp2.0.1']
#     ) as ws:
#         cp = ChargePoint('CP_1', ws)

#         await asyncio.gather(cp.start(), cp.send_boot_notification())


# if __name__ == '__main__':
#     asyncio.run(main())

# from flask import Flask, request, jsonify

# app = Flask(__name__)

# @app.route('/api/ocpi/emsp/2.1.1/locations/NL/ECO/<location_id>/<evse_uid>', methods=['PATCH'])
# def update_location(location_id, evse_uid):
#     try:
#         print('inside')
#         data = request.get_json()
#         if data is None:
#             raise ValueError("No JSON data received")
#         # Process the update here
#         print(f"Received update for location_id: {location_id}, evse_uid: {evse_uid}")
#         print(f"Data: {data}")
#         return jsonify({"status": "success", "location_id": location_id, "evse_uid": evse_uid}), 200
#     except ValueError as e:
#         print(f"Error: {e}")
#         return jsonify({"status": "error", "message": str(e)}), 400
#     except Exception as e:
#         print(f"Unexpected error: {e}")
#         return jsonify({"status": "error", "message": "Unexpected error occurred"}), 500

# if __name__ == '__main__':
#     app.run(port=5000)


import asyncio
import logging

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)


from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call
from ocpp.v16.enums import RegistrationStatus

logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):
    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charge_point_model="Optimus", charge_point_vendor="The Mobility House"
        )

        response = await self.call(request)

        if response.status == RegistrationStatus.accepted:
            print("Connected to central system.")


async def main():
    async with websockets.connect(
        "ws://localhost:8080/CP_1", subprotocols=["ocpp1.6"]
    ) as ws:

        cp = ChargePoint("CP_1", ws)

        await asyncio.gather(cp.start(), cp.send_boot_notification())


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())


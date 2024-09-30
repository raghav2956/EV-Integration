# oauth_setup.py

from flask import Flask, redirect, request
from datetime import datetime
import smartcar
import json
import os

app = Flask(__name__)

TOKEN_FILE = 'tokens.json'

client = smartcar.AuthClient(
    client_id='016a2cf0-2d2b-4644-900e-bff74c4824b6',
    client_secret='5fcd1830-9aeb-4fbe-bdeb-dd9265994ae3',
    redirect_uri='http://localhost:8000/callback',
    test_mode=False  # Set to False for production
)


def save_tokens(tokens_response):
    tokens = {
        "access_token": tokens_response.access_token,
        "token_type": tokens_response.token_type,
        "expires_in": tokens_response.expires_in,
        "expiration": tokens_response.expiration.isoformat(),
        "refresh_token": tokens_response.refresh_token,
        "refresh_expiration": tokens_response.refresh_expiration.isoformat(),
    }

    with open(TOKEN_FILE, 'w') as file:
        json.dump(tokens, file)

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
            'control_charge',

        ]
    )
    return redirect(auth_url)

@app.route('/callback', methods=['GET'])
def callback():
    code = request.args.get('code')
    tokens = client.exchange_code(code)
    save_tokens(tokens)
    return "OAuth setup complete. Tokens have been saved."

if __name__ == "__main__":
    app.run(port=8000)

import json
import os
import smartcar
from datetime import datetime, timedelta

TOKEN_FILE = 'tokens.json'

class TokenManager:
    def __init__(self, client):
        self.client = client
        self.tokens = self.load_tokens()

    def load_tokens(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as file:
                return json.load(file)
        return None
    
    def save_tokens(self, tokens):
        # Convert all datetime objects in tokens to ISO 8601 string
        for key, value in tokens.items():
            if isinstance(value, datetime):
                tokens[key] = value.isoformat() + 'Z'  # Add 'Z' to indicate UTC time

        # Save the tokens dictionary to a file
        with open(TOKEN_FILE, 'w') as file:
            json.dump(tokens, file)

    def get_access_token(self):
        if self.tokens:
            # Check if the access token is expired
            expiration = datetime.fromisoformat(self.tokens['expiration'].replace('Z', ''))
            if datetime.utcnow() < expiration:
                return self.tokens['access_token']
        return None

    def refresh_tokens(self):
        if self.tokens and 'refresh_token' in self.tokens:
            try:
                self.tokens = self.client.exchange_refresh_token(self.tokens['refresh_token'])
                self.save_tokens(self.tokens)  # Ensure refreshed tokens are saved
                return self.tokens['access_token']
            except smartcar.SmartcarException as e:
                print(f"Failed to refresh tokens: {e}")
                return None
        return None

    def get_or_refresh_access_token(self):
        access_token = self.get_access_token()
        if access_token:
            return access_token
        return self.refresh_tokens()

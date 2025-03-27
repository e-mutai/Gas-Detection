import requests
import os
import logging

class ArduinoCloudAPI:
    def __init__(self, client_id, client_secret, thing_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.thing_id = thing_id
        self.token = None
        self.base_url = 'https://api2.arduino.cc/iot/v2'
        self.auth_url = 'https://api2.arduino.cc/iot/v1/clients/token'
        self.authenticate()

    def authenticate(self):
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'audience': 'https://api2.arduino.cc/iot'
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(self.auth_url, data=data, headers=headers)
        if response.status_code == 200:
            self.token = response.json().get('access_token')
        else:
            logging.error('Failed to authenticate with Arduino Cloud API.')

    def get_headers(self):
        return {'Authorization': f'Bearer {self.token}'}

    def get_latest_data(self):
        url = f'{self.base_url}/things/{self.thing_id}/properties'
        response = requests.get(url, headers=self.get_headers())
        if response.status_code == 200:
            properties = response.json()
            data = {prop['name']: prop['last_value'] for prop in properties}
            return data
        else:
            logging.error('Failed to retrieve data from Arduino Cloud.')
            return {}

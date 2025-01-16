import requests

class Response:
    '''Class used to get the response from a `POST` request.

    Parameters
    ----------
    `api_key`: The API key for the user account.


    `secret_key`: The scret key for the user account.
    '''
    def __init__(self, api_key: str, secret_key: str):
        self.api = api_key
        self.secret_key = secret_key
        self.url = 'https://apis-sandbox.fedex.com'

    def get_auth_token(self) -> str | int:
        auth_end = '/oauth/token'

        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.api,
            'client_secret': self.secret_key
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(self.url + auth_end, data=payload, headers=headers, verify=False)

        if response.status_code != 200:
            return response

        return response.json()['access_token']

    def get_response(self, token: str, payload: dict) -> dict:
        ship_end = '/ship/v1/shipments'

        headers = {
            'Content-Type': "application/json",
            'X-locale': "en_US",
            'Authorization': f"Bearer {token}"
        }
        
        response = requests.post(self.url + ship_end, data=payload, headers=headers, verify=False)

        return response.json()
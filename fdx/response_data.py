import requests
from .payload import get_metadata, get_payload
from .dict_utils import get_key_value, set_key_value

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

    def get_auth_token(self) -> str | list[int, str]:
        '''Returns a authentication token with the given credentials.

        If there is an error, a `list` is returned containing the status code `int` and the error message `str`.
        '''
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
            return [response.status_code, get_key_value(response.json(), 'message')]

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

    def get_fdx_payload(self, payload: dict, *, blacklist: set[str] = set()) -> dict:
        '''Used to format the payload into the proper FedEx json format.
        
        Parameters
        ----------
        '''
        contact = {
            "personName": payload['name'],
            "phoneNumber": 1234567890
        }

        street_lines = [get_key_value(payload, 'street_one')]

        st_2 = get_key_value(payload, 'street_two')
        if st_2:
            street_lines.append(st_2)

        postal = get_key_value(payload, 'postal')

        address = {
          "streetLines": street_lines,
          "city": get_key_value(payload, 'city'),
          "stateOrProvinceCode": get_key_value(payload, 'state'),
          "postalCode": int(postal) if postal.isdigit() else postal,
          # i'll do this properly in the future i guess.
          "countryCode": 'US' if postal.isdigit() else 'CA'
        }

        fdx_payload = get_payload()

        set_key_value(fdx_payload, 'address', address, blacklist=blacklist)
        set_key_value(fdx_payload, 'contact', contact, blacklist=blacklist)

        return fdx_payload

    def _get_fedex_service(self, need_by: str) -> str:
        '''Retrieve the FedEx service type by calculating the days with the `need_by` input.'''
    
    def _get_requested_packages(self, hardware_list: list) -> list:
        '''Retrieve the amount of packages that are being sent out. This creates X shipping/return labels.'''
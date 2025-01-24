from core.create_user import UserCreation
from core.scrape import ScrapeRITM
from components.links import Links
from selenium.webdriver.chrome.webdriver import WebDriver
from fdx.response_data import Response
from fdx.dict_utils import get_key_value
import webbrowser, json

from dotenv import load_dotenv
import os

load_dotenv()

def create_user(driver: WebDriver, scraper: ScrapeRITM, ritm: str) -> None:
    '''
    Creates the user to add into the database, and generates the label that goes with the user.
    '''
    print("\n   Obtaining information for user creation...")
    name = scraper.scrape_name()
    req, address = scraper.scrape_ritm()
    user_info = scraper.scrape_user_info()
    need_by = scraper.scrape_need_by_date()
    requested_item, add_items = scraper.scrape_hardware()
    requestor = scraper.scrape_requestor()

    new_user = UserCreation(driver, Links.user_create, user_info, name, requestor)
    print("\n   Starting user creation process.")
    new_user.create_user()
    print('\n   Label information:')
    print(f'\t   Ticket info: {" ".join(name)} {ritm} {req}')
    print(f'\t   Address: {address}')
    print(f'\t   Hardware: {requested_item} {" ".join(add_items)}')
    print(f'\t   Need by: {need_by}')

    label_data = {
        'name': " ".join(name),
        'ritm': ritm,
        'req': req,
        'address': address,
        'need_by_date': need_by,
        'hardware': [requested_item] + [add_items],
        'account_number': os.getenv('account')
    }

    ak = os.getenv('api')
    sk = os.getenv('secret')

    create_label(ak, sk, label_data)

def create_label(api: str, secret: str, label_info: dict):
    lab = Response(api, secret)

    payload = lab.get_fdx_payload(label_info, blacklist={'shipper'})
    payload = json.dumps(payload)

    token = lab.get_auth_token()
    
    if not isinstance(token, list):
        response = lab.get_response(token, payload)
        
        url = get_key_value(response, 'url')

        webbrowser.open(url)

        print('\n   Label generated.')
    else:
        raise TypeError(f'ERROR: {response[0]}. Message: {response[1]}')
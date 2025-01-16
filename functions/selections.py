from core.create_user import UserCreation
from core.scrape import ScrapeRITM
from components.links import Links
from tests.debug import debug_ritm_info
from selenium.webdriver.chrome.webdriver import WebDriver
import time

def create_user(driver: WebDriver, scraper: ScrapeRITM, ritm: str) -> None:
    '''
    Creates the user to add into the database.
    '''
    print("\n   Obtaining information for user creation...")
    name = scraper.scrape_name()
    req, address = scraper.scrape_ritm()
    user_info = scraper.scrape_user_info()
    need_by = scraper.scrape_need_by_date()
    requested_item, add_items = scraper.scrape_hardware()
    requestor = scraper.scrape_requestor()
    debug_ritm_info(user_info, name)

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
        'need_by_date': need_by
    }
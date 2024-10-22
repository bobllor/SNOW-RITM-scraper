from core.create_user import UserCreation
from core.scrape import ScrapeRITM
from core.vtb_scanner import VTBScanner
from components.links import Links
from selenium import webdriver
# remove later, used for debugging only
from tests.debug import debug_ritm_info
import re, os, time


'''
File containing all the main functions for the program to function.
'''

clear: None = lambda: os.system('cls') if os.name == 'nt' else 'clear'

def create_user(driver: webdriver, scraper: ScrapeRITM, ritm: str) -> None:
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

    new_user = UserCreation(driver, Links.new_user, user_info, name, requestor)
    print("\n   Starting user creation process.")
    time.sleep(3)
    new_user.create_user()
    print('\n   Label information:')
    print(f'\t   Ticket info: {" ".join(name)} {ritm} {req}')
    print(f'\t   Address: {address}')
    print(f'\t   Hardware: {requested_item} {" ".join(add_items)}')
    print(f'\t   Need by: {need_by}')

def manual_user_creation(driver: webdriver):
    '''
    Scans for user information from a given RITM ticket to add into the SNOW database.
    '''
    def get_ritm() -> str:
        '''
        Returns the RITM input from the user.
        '''
        print("\n   ENTER AN RITM NUMBER")
        print("   Enter 'QUIT' to exit out of the program.")
        print("\n   Valid inputs: RITM1234567 | 1234567")
        ritm = input("\n   Enter an RITM to search: ")

        return ritm

    while True:
        clear()
        ritm = get_ritm()

        if ritm.lower() == 'quit':
            break

        ritm_checker = re.compile(r'^([RITM]{4})([0-9]{7})\b')

        if ritm.isdigit():
            ritm = 'RITM' + ritm

        while not ritm_checker.match(ritm):
            clear()
            print("\n   RITM number format is wrong.")
            ritm = get_ritm()

            if ritm == 'QUIT':
                break

        print("\n   Searching for RITM...")
        scraper = ScrapeRITM(driver, ritm)
        scraper.search_ritm()

        create_user(driver, scraper, ritm)

        scanner = VTBScanner(driver, Links().vtb)

        if driver.current_url != Links().vtb:
            scanner.get_to_vtb()
        
        ritm_element = scanner.get_ritm_element(ritm)

        if ritm_element:
            scanner.drag_task(ritm_element, 'RITM')
        else:
            print(f'{ritm} is not found in the Requests lane.')
        
        input("\n   Press 'enter' to return back to menu.")
        clear()
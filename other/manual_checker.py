from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from core.login import Login
from core.scrape import ScrapeRITM
from core.create_user import UserCreation
from core.vtb_scanner import VTBScanner
from components.acc import get_accs
from components.links import Links
from selenium.common.exceptions import NoSuchFrameException, NoSuchElementException 
from selenium.common.exceptions import ElementClickInterceptedException
from misc.cust_except import AttemptsException
import os, time, traceback, re
from tests.debug import debug_ritm_info
from log import logger

'''
This is a test file that takes the RITM input instead of automatically scanning the VTB.

You should use this if you are attempting to test out errors from a specific RITM.
In case you want to ever go back to manual input, then this will remain here.
'''

def create_user(scraper: ScrapeRITM):
    print("\n   Obtaining information for user creation...")
    name = scraper.scrape_name()
    req, address = scraper.scrape_ritm()
    user_info = scraper.scrape_user_info()
    need_by = scraper.scrape_need_by_date()
    requested_item, add_items = scraper.scrape_hardware()
    requestor = scraper.scrape_requestor()
    debug_ritm_info(user_info, name)

    new_user = UserCreation(driver, new_user_link, user_info, name, requestor)
    print("\n   Starting user creation process.")
    time.sleep(3)
    new_user.create_user()
    print('\n   Label information:')
    print(f'\t   Ticket info: {" ".join(name)} {ritm} {req}')
    print(f'\t   Address: {address}')
    print(f'\t   Hardware: {requested_item} {" ".join(add_items)}')
    print(f'\t   Need by: {need_by}')

if __name__ == '__main__':
    options = Options()
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)
    
    user, pw = get_accs()
    login_link = "https://tek.service-now.com/navpage.do"
    login = Login(driver, login_link, user, pw)
    print("\n   Logging in...")
    login.login_sn()
    os.system('cls')

    # search for an RITM ticket and scrape the info on the ticket
    # xpath for global search in order to enter the RITM number
    new_user_link = 'https://tek.service-now.com/nav_to.do?uri=%2Fsys_user.do%3Fsys_id%3D-1%26sys_is_list%3Dtrue%26sys_target%3Dsys_user%26sysparm_checked_items%3D%26sysparm_fixed_query%3D%26sysparm_group_sort%3D%26sysparm_list_css%3D%26sysparm_query%3DGOTO123TEXTQUERY321%3DDavid%2BKvachev%26sysparm_referring_url%3Dsys_user_list.do%3Fsysparm_query%3DGOTO123TEXTQUERY321%253DDavid%2BKvachev@99@sysparm_first_row%3D1%26sysparm_target%3D%26sysparm_view%3D'
    
    while True:
        os.system('cls')
        print("\n   ENTER AN RITM NUMBER")
        print("   Enter 'QUIT' to exit out of the program.")
        print("\n   Valid inputs: RITM1234567 | 1234567")
        ritm = input("\n   Enter an RITM to search: ")

        if ritm.lower() == 'quit':
            break

        ritm_checker = re.compile(r'^([RITM]{4})([0-9]{7})\b')

        if ritm.isdigit():
            ritm = 'RITM' + ritm

        while not ritm_checker.match(ritm):
            os.system('cls')
            print("\n   RITM number format is wrong.")
            print("   Enter 'QUIT' to exit out of the program.")
            print("\n   Valid inputs: RITM1234567 | 1234567")
            ritm = input("\n   Enter an RITM number: ")

            if ritm == 'QUIT':
                break

        try:
            print("\n   Searching for RITM...")
            scraper = ScrapeRITM(driver, ritm)
            scraper.search_ritm()

            create_user(scraper)

            scanner = VTBScanner(driver, Links().vtb)

            if driver.current_url != Links().vtb:
                scanner.get_to_vtb()
            
            ritm_element = scanner.get_ritm_element(ritm)

            if ritm_element:
                scanner.drag_task(ritm_element, 'RITM')
            else:
                print(f'{ritm} is not found in the Requests lane.')
        # TODO: implement logging for exceptions
        except (NoSuchElementException, NoSuchFrameException):
            print('\n   CRITICAL ERROR: Something went wrong during the process. The error has been logged.')
            logger(traceback.format_exc())
        except AttemptsException:
            print('\n   ERROR: Too many attempts were repeated, the RITM is blacklisted.')
            # the error will be logged, this will be looked at.
            logger(traceback.format_exc())
        except ElementClickInterceptedException:
            print('\n   ERROR: Something went wrong during the process. Please try again.')
            
        input("\n   Press 'enter' to return back to menu.")
        os.system('cls')

    driver.quit()
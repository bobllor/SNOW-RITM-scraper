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
import os, time, traceback
from log import logger

def create_user(scraper: ScrapeRITM, links: Links):
    print("\n   Obtaining information for user creation...")
    name = scraper.scrape_name()
    req, address = scraper.scrape_ritm()
    user_info = scraper.scrape_user_info()
    need_by = scraper.scrape_need_by_date()
    requested_item, add_items = scraper.scrape_hardware()
    requestor = scraper.scrape_requestor()

    new_user = UserCreation(driver, links.new_user, user_info, name, requestor)
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
    links = Links()
    login = Login(driver, links.dashboard, user, pw)
    print("\n   Logging in...")
    login.login_sn()
    os.system('cls')

    # used to break out of the loop, this is a temp variable while i work out the stuff.
    stop = 0
    
    os.system('cls')
    print('\n   Getting to the Visual Task Board...')
    scanner = VTBScanner(driver, links.vtb)

    # bool used to stop going back to the VTB IF NO RITMS are found.
    found = True
    print('\n   Scanning the VTB for tasks...')
    time.sleep(2)

    while stop < 10:
        if found is True:
            found = False
            scanner.get_to_vtb()
        ritm_list, ritm_elements, inc_elements = scanner.get_ritms()
        
        try:
            if ritm_list:
                found = True
                for ritm in ritm_list:
                    print(f"\n   Searching for {ritm}...")
                    scraper = ScrapeRITM(driver, ritm)
                    scraper.search_ritm()

                    create_user(scraper, links)
            else:
                print('\n   No tasks were found.')
                print('   Please wait 3 minutes for the next scan.')
                time.sleep(1)
                
            # drag tasks to their respective lane.
            if ritm_elements:
                scanner.drag_task(ritm_elements, 'RITM')
            if inc_elements:
                scanner.drag_task(inc_elements, 'INC')
        except (NoSuchElementException, NoSuchFrameException):
            print('\n   CRITICAL ERROR: Something went wrong during the process. The error has been logged.')
            logger(traceback.format_exc())
        except ElementClickInterceptedException:
            print('\n   ERROR: Something went wrong during the process. Please try again.')

        stop += 1
            
    driver.quit()
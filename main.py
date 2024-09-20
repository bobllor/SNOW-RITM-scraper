from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from core.login import Login
from core.scrape import ScrapeRITM
from core.create_user import UserCreation
from core.vtb_scanner import VTBScanner
from components.acc import get_accs
from components.links import Links
import misc.text_formats, misc.timing
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
    clear = lambda: os.system('cls') if os.name == 'nt' else 'clear'
    options = Options()
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)

    user, pw = get_accs()
    links = Links()
    login = Login(driver, links.dashboard, user, pw)
    print("\n   Logging in...")
    login.login_sn()
    clear()

    # NOTE: this is a temp variable while i work out the stuff.
    stop = 0

    # if a RITM is added to the blacklist, the program will not use the RITM number if it is present on the board.
    # blacklisted RITMs will remain in the Request lane (assuming it hasn't moved), which requires manual interaction.
    # blacklisted RITMs only occur if an exception is raised.
    blacklisted_ritms = set()

    while stop < 50:
        if driver.current_url != links.vtb:
            print('\n   Getting to the Visual Task Board...')
        scanner = VTBScanner(driver, links.vtb, blacklisted_ritms)

        # used to open the VTB link, initialized to True to start the process.
        print('\n   Scanning the VTB for tasks...')
        time.sleep(2)

        # ensures that if there are no 
        if driver.current_url != links.vtb:
            scanner.get_to_vtb()
        ritm = scanner.get_ritm_number()

        # used to repeat the user creating process, if > 3 then the RITM will be added to the blacklist.
        # NOTE: this is only true to 2nd except block, if an exception is raised for the 1st except block
        # then it will blacklist it immediately and exit out of the loop regardless of the attempts count.
        attempts = 0
        
        while ritm:
            try:
                print(f"\n   Searching for {ritm}...")
                scraper = ScrapeRITM(driver, ritm)
                scraper.search_ritm()

                create_user(scraper, links)
                
                # going back to the vtb should always occur after creating a user.
                scanner.get_to_vtb()

                ritm_element = scanner.get_ritm_element(ritm)
                if ritm_element:
                    scanner.drag_task(ritm_element, 'RITM')

                break                
            except (NoSuchElementException, NoSuchFrameException):
                print('\n   CRITICAL ERROR: Something went wrong during the process. The error has been logged.')
                blacklisted_ritms.add(ritm)
                logger(traceback.format_exc())
                break
            except ElementClickInterceptedException:
                print('\n   ERROR: Something went wrong during the process. Trying again.')
                if attempts > 3:
                    blacklisted_ritms.add(ritm)
                    break
                attempts += 1
        else:
            print('\n   No tasks were found.')
            print('   Please wait 2 minutes for the next scan.')
            misc.timing.timer()

        inc_element = scanner.get_inc_element()
        if inc_element:
            scanner.drag_task(inc_element, 'INC')
        
        stop += 1

        # if the list is greater than X, then reset it back 0.
        if len(blacklisted_ritms) > 500:
            blacklisted_ritms.clear()
            
    driver.quit()
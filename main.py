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

# for some reason without this function i am getting errors with the original scanner class object.
def drag_elements(driver: webdriver, links: Links):
    mover = VTBScanner(driver, links)
    ritm_elements, inc_elements = mover.get_web_elements()

    if ritm_elements:
        mover.drag_task(ritm_elements, 'RITM')
    
    if inc_elements:
        mover.drag_task(inc_elements, 'INC')

if __name__ == '__main__':
    clear = lambda: os.system('cls')
    options = Options()
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)

    user, pw = get_accs()
    links = Links()
    login = Login(driver, links.dashboard, user, pw)
    print("\n   Logging in...")
    login.login_sn()
    clear()

    # used to break out of the loop, this is a temp variable while i work out the stuff.
    stop = 0
    
    clear()
    print('\n   Getting to the Visual Task Board...')
    scanner = VTBScanner(driver, links.vtb)

    # used to open the VTB link, initialized to True to start the process.
    found = True
    print('\n   Scanning the VTB for tasks...')
    time.sleep(2)

    while stop < 50:
        if found is True:
            # the driver will stay on the VTB if found is false- used for exceptions or if there are no tasks.
            found = False
            scanner.get_to_vtb()
        ritm_list = scanner.get_ritm_numbers()
        
        try:
            if ritm_list:
                found = True
                # NOTE: this is done in batches of four, any more than that the program breaks.
                for ritm in ritm_list:
                    print(f"\n   Searching for {ritm}...")
                    scraper = ScrapeRITM(driver, ritm)
                    scraper.search_ritm()

                    create_user(scraper, links)
                
                # drag tasks to their respective lane.
                scanner.get_to_vtb()
                drag_elements(driver, links)
            else:
                print('\n   No tasks were found.')
                print('   Please wait 2 minutes for the next scan.')
                misc.timing.timer()
        except (NoSuchElementException, NoSuchFrameException):
            print('\n   CRITICAL ERROR: Something went wrong during the process. The error has been logged.')
            logger(traceback.format_exc())
        except ElementClickInterceptedException:
            print('\n   ERROR: Something went wrong during the process. Trying again.')

        stop += 1
            
    driver.quit()
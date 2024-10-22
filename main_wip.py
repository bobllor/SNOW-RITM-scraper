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
from gui.table import TableGUI
from selections import manual_user_creation
import misc.text_formats, misc.timing
import os, time, traceback, random

from log import logger

if __name__ == '__main__':
    clear: None = lambda: os.system('cls') if os.name == 'nt' else 'clear'

    options = Options()
    options.add_experimental_option("detach", True)
    #options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Chrome(options=options)

    user, pw = get_accs()
    links = Links()
    login = Login(driver, links.dashboard, user, pw)
    print("\n   Logging in...")
    login.login_sn()
    clear()

    while True:
        try:
            manual_user_creation(driver)
        except (NoSuchElementException, NoSuchFrameException):
            print('\n   CRITICAL ERROR: Something went wrong during the process. The error has been logged.')
            logger(traceback.format_exc())
        except AttemptsException:
            print('\n   ERROR: Too many attempts were repeated, the RITM is blacklisted.')
            # the error will be logged, this will be looked at.
            logger(traceback.format_exc())
        except ElementClickInterceptedException:
            print('\n   ERROR: Something went wrong during the process. Please try again.')
        except KeyboardInterrupt:
            print('Operation canceled.')
            time.sleep(1.5)
        
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from core.login import Login
from components.acc import get_accs
from components.links import Links
from selenium.common.exceptions import NoSuchFrameException, NoSuchElementException 
from selenium.common.exceptions import ElementClickInterceptedException
from misc.cust_except import AttemptsException
from gui.table import TableGUI
from functions.manual import ManualRITM
import misc.text_formats, misc.timing
import misc.menu as menu
import os, traceback
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
            menu.display_main_menu()
            menu_choice = menu.main_menu_choice()

            if menu_choice.lower() == 'quit':
                break
            
            if menu_choice == 'a':
                print('WIP sorry!')

            if menu_choice == 'm':
                man = ManualRITM(driver)
                menu.display_manual_menu()
                manual_choice = menu.manual_choice()

                if manual_choice == 'm':
                    # single file input.
                    man.manual_input()
                if manual_choice == 'f':
                    # uses a csv/xlsx input to get a list of RITMs.
                    man.file_input()

            if menu_choice == 'c':
                print('WIP sorry!')

        except (NoSuchElementException, NoSuchFrameException):
            print('\n   CRITICAL ERROR: Something went wrong during the process. The error has been logged.')
            logger(traceback.format_exc())
        except AttemptsException:
            print('\n   ERROR: Too many attempts were repeated, the RITM is blacklisted.')
            logger(traceback.format_exc())
        except ElementClickInterceptedException:
            print('\n   ERROR: Something went wrong during the process. Please try again.')
        except TypeError as e:
            print(f'\n   {e}')
        except KeyboardInterrupt:
            print('   KEYBOARD INTERRUPTION. Closing operation.')
            break
    
    driver.quit()
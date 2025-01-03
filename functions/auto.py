from core.scrape import ScrapeRITM
from core.vtb_scanner import VTBScanner
from components.links import Links
from selenium.common.exceptions import NoSuchFrameException, NoSuchElementException 
from selenium.common.exceptions import ElementClickInterceptedException
from misc.cust_except import AttemptsException
from gui.table import TableGUI
from .selections import create_user
import misc.text_formats, misc.timing
import time, traceback, random
from log import logger

# TODO: WIP.

class AutoRITM:
    def __init__(self, driver):
        self.driver = driver
    
    def start(self):
        # NOTE: this is a temp variable while i work out the stuff.
        stop = 0

        # if a RITM is added to the blacklist, the program will not use the RITM number if it is present on the board.
        # blacklisted RITMs will remain in the Request lane (assuming it hasn't moved), which requires manual interaction.
        # blacklisted RITMs only occur if an exception is raised.
        blacklisted_ritms = set()

        while stop < 50:
            # used for displaying the table, state NC/C indicates the status of that particular task.
            # there are 4 main tasks, each one has sub tasks which the programs go through.
            # this gets modified during the program, and resets when it loops another RITM.
            tasks = {
                'vtb': ['Scanning the VTB', 'NC'],
                'ritm': ['Getting info for the RITM', 'NC'],
                'create user': ['Creating the user', 'NC'],
                'drag': ['Dragging task on the VTB', 'NC']
            }

            if self.driver.current_url != Links.vtb:
                print('\n   Getting to the Visual Task Board...')
            scanner = VTBScanner(self.driver, Links.vtb, blacklisted_ritms)

            self.__task_table(tasks)
            
            print('\n   Scanning the VTB for tasks...')
            time.sleep(2)

            if self.driver.current_url != Links.vtb:
                scanner.get_to_vtb()
            else:
                # if the driver is on the VTB, refresh on a random basis (due to VTB not updating).
                target = random.randint(1, 3)
                if target == 2:
                    self.driver.refresh()
            # inside this class method contains code that skips over blacklisted RITMs.
            ritm = scanner.get_ritm_number()

            # used to repeat the user creating process, if > 3 then the RITM will be added to the blacklist.
            # NOTE: this is only true to 2nd except block, if an exception is raised for the 1st except block
            # then it will blacklist it immediately and exit out of the loop regardless of the attempts count.
            attempts = 0
            
            while ritm:
                tasks['vtb'][1] = 'C'

                try:
                    self.__task_table(tasks)
                    print(f"\n   Searching for {ritm}...")
                    scraper = ScrapeRITM(self.driver, ritm)
                    scraper.search_ritm()

                    tasks['ritm'][1] = 'C'
                    self.__task_table(tasks)

                    create_user(self.driver, scraper, ritm)
                    tasks['create user'][1] = 'C'
                    self.__task_table(tasks)
                    
                    # going back to the vtb should always occur after creating a user.
                    scanner.get_to_vtb()

                    ritm_element = scanner.get_ritm_element(ritm)
                    if ritm_element:
                        scanner.drag_task(ritm_element, 'RITM')
                    tasks['drag'][1] = 'C'
                    self.__task_table(tasks)

                    break                
                except (NoSuchElementException, NoSuchFrameException, AttemptsException):
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
            if inc_element and inc_element not in blacklisted_ritms:
                scanner.drag_task(inc_element, 'INC')
            
            stop += 1

            # if the list is greater than X, then reset it back 0.
            if len(blacklisted_ritms) > 500:
                blacklisted_ritms.clear()

    def __task_table(self, tasks: dict[str, list[str]]) -> None:
        '''
        Function to create and print the table repeated throughout main.
        '''
        table = TableGUI(tasks)
        table.create_table()
        table.print_table()

from core.scrape import ScrapeRITM
from core.vtb_scanner import VTBScanner
from components.links import Links
from tkinter import filedialog
from pathlib import Path
from selenium.common.exceptions import JavascriptException, StaleElementReferenceException, NoSuchElementException
from . import selections as sel
from core.vtb_scanner import VTBScanner
from selenium.webdriver.chrome.webdriver import WebDriver
import re, os
import pandas as pd

clear: None = lambda: os.system('cls') if os.name == 'nt' else 'clear'

class ManualRITM:
    '''
    Manual interaction to add the user into the SNOW database.
    '''
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.scanner = VTBScanner(driver)

    def manual_input(self):
        # TODO: allow multiple RITMs in a string, as well as an option to read a csv/xlxs of RITMs.
        # tl;dr: return a list of RITMs which leads to a for loop of all RITMs.
        '''
        Create the user using a single RITM input.
        '''
        def get_ritm() -> str:
            '''
            '''
            print("\n   ENTER A RITM NUMBER")
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

            if ritm_checker.match(ritm):
                print("\n   Searching for RITM...")
                scraper = ScrapeRITM(self.driver)
                scraper.search_ritm(ritm)

                flag = scraper.is_ritm()

                if flag:
                    sel.create_user(self.driver, scraper, ritm)

                    if self.driver.current_url != Links.vtb:
                        self.driver.get(Links.vtb)
                    
                    ritm_element = self.scanner.get_ritm_element(ritm)

                    if ritm_element:
                        self.scanner.drag_task(ritm_element)
                    else:
                        print(f'{ritm} is not found in the Requests lane.')
                    
                    input("\n   Press 'enter' to return back to menu.")
                    clear()
                else:
                    print('\n   ERROR: Incorrect RITM read.')
                    input('   Press "enter" to return back to the menu.')

    def file_input(self) -> list:
        '''
        Creates users based on the CSV/XLSX input.

        NOTE: This requires a specific report generated from SNOW that contains the RITM number column as the first column.
        '''
        def get_ritms() -> list:
            downloads_path = str(Path.home() / 'Downloads')
            file = filedialog.askopenfilename(initialdir=downloads_path, filetypes=[('Files', '.csv .xlsx')])
            
            # TODO: make this raise an exception.
            if not file or Path(file).suffix not in ['.csv', '.xlsx']:
                return []
            
            # initialize it as an empty dataframe, if either the file initialization does not work then exit out back to the menu.
            df = pd.DataFrame([])
            is_csv = True if Path(file).suffix == '.csv' else False
            
            if is_csv:
                try:
                    df = pd.read_csv(file)
                except UnicodeDecodeError:
                    # ?
                    df = pd.read_csv(file, encoding='windows-1254')
            else:
                df = pd.read_excel(file)
            
            # invalid file is used, the correct file is generated from the reports tab in SNOW.
            if df.empty or list(df.columns)[0].lower() != 'number':
                return []

            return list(df.iloc[:,0])

        ritms = get_ritms()

        if not ritms:
            return []

        for ritm in ritms:
            try:
                print(f"\n   Searching for {ritm}...")
                scraper = ScrapeRITM(self.driver)
                scraper.search_ritm(ritm)

                # TODO: fix the frame switching part for ScrapeRITM.
                is_correct = scraper.is_ritm()

                if is_correct:
                    sel.create_user(self.driver, scraper, ritm)

                    if self.driver.current_url != Links.vtb:
                        self.driver.get(Links.vtb)
                    
                    ritm_element = self.scanner.get_ritm_element(ritm)

                    if ritm_element:
                        self.scanner.drag_task(ritm_element)
                    else:
                        print(f'   {ritm} is not found in the Requests lane.')
                else:
                    print('   \nA bad RITM was read, skipping the process.')
                
                clear()
            except JavascriptException:
                # unsure why this error happens. this is a "has no size and location" error.
                print('ERROR: Cannot drag task. Continuing the process.')
                flag = False
                self.driver.refresh()

                if not flag:
                    clear()
                    flag = True
                    continue
                
                # make a proper exception for this. hopefully this does not bite my ass.
                raise NoSuchElementException
            except StaleElementReferenceException:
                print('   ERROR: Element is stale. Contiuing the process.')
                flag = False

                if not flag:
                        clear()
                        flag = True
                        continue
                    
                # same thing as above. please save my ass.
                raise NoSuchElementException
    
    def scan_vtb(self):
        '''Scan the VTB for any current tickets.
        
        This creates users for all tickets (other than INC), including software.
        '''
        self.driver.get(Links.vtb)

        ritms = self.scanner.get_ritm_number()

        ritm_list = [ritm.text for ritm in ritms]
        # TODO: refactor the classes... please. or at least finish my custom library. 2/24/2025

        print(f'   Found {len(ritms)} {'RITMs'}.')

        if len(ritm_list) > 0:
            for ritm in ritm_list:
                scraper = ScrapeRITM(self.driver)
                scraper.search_ritm(ritm)

                if scraper.is_ritm():
                    sel.create_user(self.driver, scraper, ritm)
                    if self.driver.current_url != Links.vtb:
                        self.driver.get(Links.vtb)
                    ritm_ele = self.scanner.get_ritm_element(ritm)

                    if ritm_ele is None:
                        print(f'   Error with grabbing element, skipping the {ritm}.')
                        continue

                    self.scanner.drag_task(ritm_ele)
                else:
                    print(f'   Issue with search for {ritm}. Skipping the RITM.')
from core.scrape import ScrapeRITM
from core.vtb_scanner import VTBScanner
from components.links import Links
from tkinter import filedialog
from pathlib import Path
from . import selections as sel
import re, os
import pandas as pd

clear: None = lambda: os.system('cls') if os.name == 'nt' else 'clear'

class ManualRITM:
    '''
    Takes an input which is then used to scrape the ticket and creates the user into the SNOW database.

    Has two methods:
        1. `ManualRITM.manual_input` takes a single RITM input.
        2. `ManualRITM.file_input` takes a CSV or XLSX input using filedialog.
    '''
    def __init__(self, driver):
        self.driver = driver

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
                scraper = ScrapeRITM(self.driver, ritm)
                scraper.search_ritm()

                sel.create_user(self.driver, scraper, ritm)

                scanner = VTBScanner(self.driver, Links().vtb)

                if self.driver.current_url != Links().vtb:
                    scanner.get_to_vtb()
                
                ritm_element = scanner.get_ritm_element(ritm)

                if ritm_element:
                    scanner.drag_task(ritm_element, 'RITM')
                else:
                    print(f'{ritm} is not found in the Requests lane.')
                
                input("\n   Press 'enter' to return back to menu.")
                clear()

    def file_input(self) -> list:
        # tl;dr: return a list of RITMs which leads to a for loop of all RITMs.
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
            print(f"\n   Searching for {ritm}...")
            scraper = ScrapeRITM(self.driver, ritm)
            scraper.search_ritm()

            sel.create_user(self.driver, scraper, ritm)

            scanner = VTBScanner(self.driver, Links().vtb)

            if self.driver.current_url != Links().vtb:
                scanner.get_to_vtb()
            
            ritm_element = scanner.get_ritm_element(ritm)

            if ritm_element:
                scanner.drag_task(ritm_element, 'RITM')
            else:
                print(f'{ritm} is not found in the Requests lane.')
        
            clear()
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import JavascriptException
import time
'''
how the VTBScanner works:
1. the VTB and scans every 2 minutes for any new requests.
2. if new requests are found, then the VTB will grab the task number and begin the user
   creation process.
3. once the user creation is completed, the task with the RITM is moved over to the next lane.
    - INCs are the exception to this, it will automatically filter to the appropriate lane.
    - WIP: distinguish between software and hardware.
loop:
open to VTB > scan the VTB lane > grab task number(s) > insert task number into search bar > 
create the user > move task number(s) to the correct lane > repeat from beginning
'''

class VTBScanner():
    def __init__(self, driver, link, blacklist=None):
        self.driver = driver
        self.vtb_link = link
        self.blacklist = set() if blacklist is None else blacklist

        self.req_lane = '//li[@v-lane-index="0" and @h-lane-index="0"]'
    
    def get_to_vtb(self) -> None:
        '''
        Sends the driver to the VTB directly.
        '''
        self.driver.get(self.vtb_link)

    def __switch_frames(self):
        '''
        Switch iframes when going back to or currently on the VTB.
        '''
        self.driver.switch_to.default_content()
        try:
            WebDriverWait(self.driver, 15).until(
                EC.frame_to_be_available_and_switch_to_it(self.driver.find_element(By.XPATH, '//iframe[@id="gsft_main"]'))
            )
        except TimeoutException:
            # TODO: create a logging message here.
            print('   Something went wrong during the switching to the VTB frame.')
            pass

    def get_ritm_number(self):
        '''
        Scans the request lane for a RITM number.

        The scan starts from the top of the request lane.

        It only returns a single RITM number. If the list is empty, then None is returned.
        '''
        self.__switch_frames()

        ritm = None
        try:
            ritm_elements = WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, f'{self.req_lane}//a[contains(text(), "RITM")]'))
            )

            if len(ritm_elements) > 0:
                for element in ritm_elements:
                    if element.text not in self.blacklist:
                        ritm = element.text
                        break
        except TimeoutException:
            pass
        
        self.driver.switch_to.default_content()

        return ritm

    def get_ritm_element(self, ritm: str):
        '''
        Returns a RITM element.

        If a RITM element is not found, it returns None.
        '''
        # NOTE: this is going to be ran indefinitely as it will be scanning the VTB for any incoming tasks.
        # xpath to the lane which contains the items to look for.
        self.__switch_frames()
        
        try:
            ritm_elements = WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, f'{self.req_lane}//a[contains(text(), "{ritm}")]'))
            )
        except TimeoutException:
            return None
        
        self.driver.switch_to.default_content()
        
        if len(ritm_elements) > 0:
            return ritm_elements[0]

    def get_inc_element(self) -> list:
        '''
        Returns an INC element.

        If an INC element is not found, it returns None.
        '''
        self.__switch_frames()

        try:
            inc_elements = WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, f'{self.req_lane}//a[contains(text(), "INC")]'))
            )
        except TimeoutException:
            return None
        
        if len(inc_elements) > 0:
            return inc_elements[0]
    
    def drag_task(self, element, type: str):
        '''
        Drags the task over to their respective lane. This does it for both INCs and RITMs.

        INCs gets dragged to the ASAP/INC/Replace lane.

        Most RITMs will get dragged over to the User Created lane, some may be in the Software row instead.
        '''
        self.__switch_frames()

        lane = self.driver.find_element(By.XPATH, '//li[@v-lane-index="1" and @h-lane-index="0"]')

        # by default, the task will be dragged over to the user created lane.
        # if an INC is detected, then it will move it accordingly.
        if type == 'INC':
            inc_lane = self.driver.find_element(By.XPATH, '//li[@v-lane-index="2" and @h-lane-index="0"]')
            lane = inc_lane

        try:
            action = ActionChains(self.driver)
            action.click_and_hold(element)
            time.sleep(1)
            action.move_to_element(lane)
            time.sleep(1)
            action.release(lane).perform()

            print('   Task dragged.')
            time.sleep(1.5)
        except NoSuchElementException:
            raise NoSuchElementException
        
        self.driver.switch_to.default_content()
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, JavascriptException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
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

class VTBScanner:
    def __init__(self, driver, blacklist=None):
        self.driver = driver
        self.blacklist = set() if blacklist is None else blacklist

        self.req_lane = '//li[@v-lane-index="0" and @h-lane-index="0"]'

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
        except NoSuchElementException:
            self.driver.switch_to.default_content()

    def get_ritm_number(self):
        '''
        Scans the request lane for a RITM number.

        The scan starts from the top of the request lane.

        It only returns a single RITM number. If the list is empty, then None is returned.
        '''
        self.__switch_frames()

        ritm_elements = None
        try:
            ritm_elements = WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, f'{self.req_lane}//a[contains(text(), "RITM")]'))
            )
        except TimeoutException:
            pass
        
        self.driver.switch_to.default_content()

        return ritm_elements

    def get_ritm_element(self, ritm: str):
        '''
        Returns a RITM element.

        If a RITM element is not found, it returns None.
        '''
        #self.__switch_frames()
        
        try:
            ritm_elements = WebDriverWait(self.driver, 6).until(
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
    
    def drag_task(self, element, *, is_inc: bool = False):
        '''
        Drags a ticket in the Requests lane to their respective lane.

        RITMs gets moved to the User Created lane. INCs gets moved to the ASAP/INC/Replace lane. 

        Parameters
        ---------
        `is_inc`

        Indicates whether the element is an INC instead of a RITM.
        
        This parameter is only relevant to the automatic ticket detection, it can be ignored entirely.
        Default is `False`.
        '''
        self.__switch_frames()

        lane_path = '//li[@v-lane-index="1" and @h-lane-index="0"]' if is_inc is False else '//li[@v-lane-index="2" and @h-lane-index="0"]'
        try:
            lane = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, lane_path)))
        except TimeoutException:
            return
        

        # selects the parent of the element (div). prevents: 1. clicking on the href & 2. having a javascript no size error.
        element = element.find_element(By.XPATH, '..')

        try:
            action = ActionChains(self.driver)

            action.click_and_hold(element)

            time.sleep(1)

            action.move_to_element(lane)

            time.sleep(1)

            action.release(lane).perform()

            print('   Task dragged.')
        except StaleElementReferenceException:
            # hopefully this doesn't bite me back in the ass.
            pass
        except JavascriptException:
            # used to handle elements that are not in scroll view. should happen very rarely.
            body_element = self.driver.find_element(By.CSS_SELECTOR, 'body')
            body_element.click()
            body_element.send_keys(Keys.PAGE_DOWN)

            self.drag_task(element)
        
        self.driver.switch_to.default_content()
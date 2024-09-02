from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
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
    def __init__(self, driver, link):
        self.driver = driver
        self.vtb_link = link

    def get_to_vtb(self) -> None:
        self.driver.get(self.vtb_link)
        time.sleep(7)

    def get_ritms(self) -> list:
        # NOTE: this is going to be ran indefinitely as it will be scanning the VTB for any incoming tasks.
        # xpath to the lane which contains the items to look for.
        self.driver.switch_to.frame('gsft_main')
        
        req_lane = '//li[@v-lane-index="0" and @h-lane-index="0"]'
        ritm_elements = self.driver.find_elements(By.XPATH, f'{req_lane}//a[contains(text(), "RITM")]')
        inc_elements = self.driver.find_elements(By.XPATH, f'{req_lane}//a[contains(text(), "INC")]')
        
        # limit the list to a maximum of 4.
        # NOTE: i do not know why it breaks when it is > 4, i can't be bothered.
        if len(ritm_elements) > 4:
            ritm_elements = ritm_elements[:4]
        if len(inc_elements) > 4:
            inc_elements = inc_elements[:4]

        ritm_numbers = []
        if ritm_elements:
            for element in ritm_elements:
                ritm_numbers.append(element.text)

        self.driver.switch_to.default_content()
        
        return ritm_numbers, ritm_elements, inc_elements
    
    def drag_task(self, elements, type: str):
        self.driver.switch_to.frame('gsft_main')

        lane = self.driver.find_element(By.XPATH, '//li[@v-lane-index="1" and @h-lane-index="0"]')

        # by default, the task will be dragged over to the user created lane.
        # if an INC is detected, then it will move it accordingly.
        if type == 'INC':
            inc_lane = self.driver.find_element(By.XPATH, '//li[@v-lane-index="2" and @h-lane-index="0"]')
            lane = inc_lane

        for element in elements:
            # go back to select the parent container of the web element.
            element = element.find_element(By.XPATH, '../..')

            drag_task = ActionChains(self.driver).click_and_hold(element)
            time.sleep(1)
            drag_task.move_to_element(lane)
            time.sleep(1)
            drag_task.release(lane).perform()

            print('   Task dragged.')
            time.sleep(1.5)
        
        self.driver.switch_to.default_content()
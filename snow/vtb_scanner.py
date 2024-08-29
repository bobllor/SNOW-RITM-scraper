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
        time.sleep(10)
        self.driver.switch_to.frame('gsft_main')
        time.sleep(5)

    # NOTE: this is going to be ran indefinitely as it will be scanning the VTB for any incoming tasks.
    def get_ritms(self) -> list:
        # xpath to the lane which contains the items to look for.
        # NOTE: the lanes' tag is <li> with the attribute v-lane-index="i" and h-lane-index="i".
        # v-lane indicates where 
        # NOTE: the tickets' tag is <li> with the attribute role="listitem".
        # completed lane = 4 0, custom software email req = 5 1
        req_lane = '//li[@v-lane-index="0" and @h-lane-index="0"]'
        ritm_elements = self.driver.find_elements(By.XPATH, f'{req_lane}//a[contains(text(), "RITM")]')
        inc_elements = self.driver.find_elements(By.XPATH, f'{req_lane}//a[contains(text(), "INC")]')

        ritm_numbers = []
        if ritm_elements:
            for element in ritm_elements:
                ritm_numbers.append(element.text)

        if inc_elements:
            for element in inc_elements:
                self.drag_task(element, 'INC')

        return ritm_numbers
    
    def drag_task(self, source, type):
        # by default, the lane will always start in the requests lane.
        lane = self.driver.find_element(By.XPATH, '//li[@v-lane-index="1" and @h-lane-index="0"]')

        if type == 'INC':
            inc_lane = self.driver.find_element(By.XPATH, '//li[@v-lane-index="2" and @h-lane-index="0"]')
            lane = inc_lane

        drag_task = ActionChains(self.driver).click_and_hold(source)
        drag_task.move_to_element(lane)
        drag_task.release(lane).perform()

        print(f'   {type} task moved.')
        time.sleep(2)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import NoSuchElementException
import time

class TaskComplete:
    def __init__(self, driver):
        self.driver = driver

    def complete_task(self):
        self.driver.switch_to.frame("gsft_main")

        # NOTE: status cells, no matter if it's the first or the following two/three cells, will always
        # be tr[1]. HOWEVER, this is assuming that the filter is default view- new appearing tasks go from bottom
        # to top. keep it in mind if this ever breaks.
        catalog_task_container = '//div[@id="sc_req_item.sc_task.request_item_list"]'
        status_cell = '//tbody[@class="list2_body"]/tr[1]//td[4]'

        count = 0
        while count < 4:
            # when all status cells are cloesd complete (min 3 max 4) there will be no more elements
            # inside the container- an exception will be thrown indicating the operation is done.
            # NOTE: the count is used to ensure that if it is not >= 3, then an error occurred.
            try:
                # click on the status cell to open the selection menu.
                clickable = self.driver.find_element(By.XPATH, f'{catalog_task_container}{status_cell}')
                ActionChains(self.driver).double_click(clickable).perform()
                time.sleep(2)

                # click on the option to mark it as Closed Complete.
                status_list = Select(self.driver.find_element(By.XPATH, '//select[@id="cell_edit_value"]'))
                for option in status_list.options:
                    if option.text == 'Closed Complete':
                        option.click()
                        time.sleep(1)
                        self.driver.find_element(By.XPATH, '//a[@id="cell_edit_ok"]').click()
                        break
                time.sleep(3)
                
                # refresh the task bar to show the next status cell, it doesn't update automatically.
                catalog_task_bar = '//div[@class="navbar-header"]'
                task_bar = self.driver.find_element(By.XPATH, f'{catalog_task_container}{catalog_task_bar}')
                ActionChains(self.driver).context_click(task_bar).perform()
                time.sleep(2)
                refresh_xpath = '//div[@id="context_list_titlesc_req_item.sc_task.request_item"]//div[@item_id="216ac28a0a0a0bb200af43eb879c30ae"]'
                refresh = self.driver.find_element(By.XPATH, refresh_xpath)
                time.sleep(2)
                refresh.click()
                time.sleep(5.5)

                count += 1
            except NoSuchElementException:
                break

            # remove later, used for testing only.
            input('Press enter to continue (DEBUG)')
        
        if count >= 3:
            # fill in mandatory company field, not to be confused with consultant company field.
            field_xpath = '//input[@id="sys_display.sc_req_item.company"]'
            self.driver.find_element(By.XPATH, field_xpath).send_keys('TEKsystems')
            time.sleep(1.5)

            # save button at the top of the screen
            save_xpath = '//button[@class="form_action_button header  action_context btn btn-default"]'
            self.driver.find_element(By.XPATH, save_xpath).click()
            time.sleep(3)

            self.driver.switch_to.defaultcontent()
        else:
            print('\n   ERROR: Something went wrong with the task completion.')
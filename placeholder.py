from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

class Login:
    def __init__(self, driver, link, user, pw):
        self.driver = driver
        self.link = link
        self.user = user
        self.pw = pw
    
    def login_sn(self):
        self.driver.get(self.link)

        time.sleep(5)
        
        self.driver.switch_to.frame("gsft_main")

        self.driver.find_element(By.ID, "user_name").send_keys(self.user)
        time.sleep(3)
        self.driver.find_element(By.ID, "user_password").send_keys(self.pw)
        time.sleep(5)
        self.driver.find_element(By.ID, "sysverb_login").click()

    
        self.driver.switch_to.default_content()
        
        time.sleep(8)

class ScrapeRITM():
    def __init__(self, driver, ritm, search_xpath):
        self.driver = driver
        self.ritm = ritm
        self.search_xpath = search_xpath
    
    # main functionality, enter the RITM value into the global search
    # in order to grab the values
    def search_ritm(self):
        # search for global search bar and query the site for an RITM ticket
        global_search = self.driver.find_element(By.XPATH, self.search_xpath)
        global_search.send_keys(self.ritm)
        global_search.send_keys(Keys.ENTER)

        time.sleep(13)
        
        # reset search field to prepare it for future queries
        global_search.click()
        global_search.send_keys(Keys.CONTROL + "a")
        global_search.send_keys(Keys.DELETE)
    
    # main web scrape functionality, obtain info from RITM ticket
    # returns Full Name, Full Address, and ZIP code
    # the result of this function feeds into the label generator
    # TODO: link this file to my fedex label generator, eliminating
    # the need for manual input (except RITM ticket)
    def scrape_ritm(self):
        self.driver.switch_to.frame("gsft_main")

        # returns the REQ number
        req = self.scrape_req()

        # returns the full name of the consultant
        name = self.scrape_name()
        time.sleep(5)

        # returns the address of the consultant
        address = self.scrape_address()
        time.sleep(5)

        return req, name, address
    
    def scrape_name(self):
        # xpath of the container that holds all consultant info
        consultant_info_xpath = '//tr[@id="element.container_23caec60e17c4a00c2ab91d15440c5ee"]'
        # xpath of first and last name child containers
        fn_xpath = '//tr[1]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        ln_xpath = '//tr[2]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        name_xpaths = [f"{consultant_info_xpath}{fn_xpath}", 
                            f"{consultant_info_xpath}{ln_xpath}"]
        
        name = []
        # get the value from the xpath, strip any whitespace
        # and append to a list which then forms a string
        for xpath in name_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, xpath)
            part = element_xpath.get_attribute("value").strip()
            name.append(part)
        
        return " ".join(name)
    
    def scrape_address(self):
        # xpath of container that holds all address info
        address_info_xpath = '//tr[@id="element.container_66291a0ae1fc8a00c2ab91d15440c5c2"]'
        column_xpath1 = '//div[@class="section-content catalog-section-content"]/div[1]'
        column_xpath2 = '//div[@class="section-content catalog-section-content"]/div[2]'
        # xpath of street 1, street 2, and postal
        street_one_xpath = f'{column_xpath1}//tr[1]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        street_two_xpath = f'{column_xpath1}//tr[2]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        postal_xpath = f'{column_xpath2}//tr[1]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'

        # order: ADDRESS 1, ADDRESS 2, POSTAL
        address_xpaths = [f"{address_info_xpath}{street_one_xpath}",
                          f"{address_info_xpath}{street_two_xpath}",
                          f"{address_info_xpath}{postal_xpath}"]

        address = []

        for xpath in address_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, xpath)
            part = element_xpath.get_attribute("value")
            part = part.strip()
            if part != None or part == " ":
                address.append(part)
    
        return " ".join(address)
    
    def scrape_req(self):
        req_xpath = '//input[@id="sys_display.sc_req_item.request"]'
        
        element_xpath = self.driver.find_element(By.XPATH, req_xpath)
        req = element_xpath.get_attribute("value")

        return req
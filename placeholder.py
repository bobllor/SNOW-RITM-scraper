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
        print("Logging in...")
        
        self.driver.switch_to.frame("gsft_main")

        self.driver.find_element(By.ID, "user_name").send_keys(self.user)
        time.sleep(3)
        self.driver.find_element(By.ID, "user_password").send_keys(self.pw)
        time.sleep(5)
        self.driver.find_element(By.ID, "sysverb_login").click()

    
        self.driver.switch_to.default_content()
        
        time.sleep(8)

class ScrapeRITM():
    def __init__(self, driver, ritm):
        self.driver = driver
        self.ritm = ritm

        # global search xpath
        self.search_xpath = '//input[@name="sysparm_search"]'

        # xpath of RITM tickets
        # these are containers that hold other xpaths for form values
        self.consultant_info_xpath = '//tr[@id="element.container_23caec60e17c4a00c2ab91d15440c5ee"]'
        self.address_info_xpath = '//tr[@id="element.container_66291a0ae1fc8a00c2ab91d15440c5c2"]'
        self.company_info_xpath = '//tr[@id="element.container_84f76a0ee1fc8a00c2ab91d15440c50e"]'
        # normal xpaths inside a ticket
        self.req_xpath = '//input[@id="sys_display.sc_req_item.request"]'
    
    # main functionality, enter the RITM value into the global search
    # in order to grab the values
    def search_ritm(self):
        # ensure that driver is not in a frame before performing a search.
        self.driver.switch_to.default_content()
        
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
        # xpath of first and last name child containers
        fn_xpath = '//tr[1]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        ln_xpath = '//tr[2]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        name_xpaths = [f"{self.consultant_info_xpath}{fn_xpath}", 
                            f"{self.consultant_info_xpath}{ln_xpath}"]
        
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
        column_xpath1 = '//div[@class="section-content catalog-section-content"]/div[1]'
        column_xpath2 = '//div[@class="section-content catalog-section-content"]/div[2]'
        # xpath of street 1, street 2, and postal
        street_one_xpath = f'{column_xpath1}//tr[1]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        street_two_xpath = f'{column_xpath1}//tr[2]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        postal_xpath = f'{column_xpath2}//tr[1]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'

        # order: ADDRESS 1, ADDRESS 2, POSTAL
        address_xpaths = [f"{self.address_info_xpath}{street_one_xpath}",
                          f"{self.address_info_xpath}{street_two_xpath}",
                          f"{self.address_info_xpath}{postal_xpath}"]

        address = []

        for xpath in address_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, xpath)
            part = element_xpath.get_attribute("value").strip()

            if part != None or part != " " or part != "":
                address.append(part)
    
        return " ".join(address)
    
    def scrape_req(self):        
        element_xpath = self.driver.find_element(By.XPATH, self.req_xpath)
        req = element_xpath.get_attribute("value")

        return req
    
    def scrape_user_info(self):
        # consultant's company xpaths
        cid_xpath = '//tr[19]//input[@class="questionsetreference form-control element_reference_input"]'
        oid_xpath = '//tr[24]//input[@class="questionsetreference form-control element_reference_input"]'
        pid_xpath = '//tr[7]//input[@class="cat_item_option sc-content-pad form-control"]'
        # CHECKS IF "NEW CUSTOMER" IS A VALUE ON CID XPATH.
        # this is needed because if "New Customer" is selected then the company and CID xpaths
        # swap positions with each other and every value below it increments by one.
        customer_id_values = ["New Customer", "Not Listed"]
        if self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{cid_xpath}").get_attribute("value") in customer_id_values:
            company_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'
            cid_xpath = '//tr[22]//input[@class="cat_item_option sc-content-pad form-control"]'
        else:
            company_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'

        # consultant xpaths
        email_xpath = '//tr[3]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        eid_xpath = '//tr[4]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'

        consultant_xpaths = [email_xpath, eid_xpath]
        user_info = []

        for xpath in consultant_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.consultant_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")
            user_info.append(part)

        company_xpaths = [cid_xpath, company_xpath, oid_xpath, pid_xpath]

        for xpath in company_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")

            if part != None:
                user_info.append(part)
        
        # returns a list in order: email, employee ID, customer ID, company, office ID, project ID.
        return user_info
        
# fill in the user fields of a new user record
# NOTE: still requires manual input in saving and other missing information
# that requires interaction with the SNOW UI.
class UserCreation:
    def __init__(self, driver, link, user_info, name):
        self.driver = driver
        self.link = link
        self.name = name

        # company info, values are initialized from a list
        self.email = user_info[0]
        self.eid = user_info[1]
        self.cid = user_info[2]
        self.company = user_info[3]
        self.oid = user_info[4]
        self.pid = user_info[5]

    def create_user(self):
        self.driver.get(self.link)

    def format_office_id(self):
        full_oid = self.oid
        full_oid = full_oid.split("-")

        self.oid = full_oid[0]
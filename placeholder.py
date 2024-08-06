from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import re

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
        
        print("Login complete.")
        time.sleep(8)

class ScrapeRITM():
    def __init__(self, driver, ritm):
        self.driver = driver
        self.ritm = ritm

        # global search xpath
        self.search_xpath = '//input[@name="sysparm_search"]'

        # xpath of RITM tickets
        # these are containers that need to be accessed before being able to grab the values
        self.consultant_info_xpath = '//tr[@id="element.container_23caec60e17c4a00c2ab91d15440c5ee"]'
        self.address_info_xpath = '//tr[@id="element.container_66291a0ae1fc8a00c2ab91d15440c5c2"]'
        self.company_info_xpath = '//tr[@id="element.container_84f76a0ee1fc8a00c2ab91d15440c50e"]'
        self.org_info_xpath = '//tr[@id="element.container_dbc92e7fe1a44a00c2ab91d15440c51c"]'

        # xpath that does not require a container to access
        self.req_xpath = '//input[@id="sys_display.sc_req_item.request"]'
    
    def search_ritm(self):
        # ensure that driver is not in a frame before performing a search.
        self.driver.switch_to.default_content()
        
        # search for global search bar and query the site for an RITM ticket
        global_search = self.driver.find_element(By.XPATH, self.search_xpath)
        global_search.send_keys(self.ritm)
        global_search.send_keys(Keys.ENTER)

        time.sleep(10)

        print("RITM search complete.")
        # reset search field to prepare it for future queries
        global_search.click()
        global_search.send_keys(Keys.CONTROL + "a")
        global_search.send_keys(Keys.DELETE)
    
    # TODO: link this file to my fedex label generator, eliminating
    # the need for manual input (except RITM ticket)
    def scrape_ritm(self):
        self.driver.switch_to.frame("gsft_main")

        # returns the REQ number
        req = self.scrape_req()
        time.sleep(5)

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
        oid_xpath = '//tr[24]//input[@class="questionsetreference form-control element_reference_input"]'
        pid_xpath = '//tr[7]//input[@class="cat_item_option sc-content-pad form-control"]'

        # CHECKS IF CID CONTAINS ANYTHING OTHER THAN A NUMBER.
        # this is needed because if "New Customer/Not LIsted" is selected then multiple XPATHS are
        # positioned in different locations due to an additional field form appearing.
        cid_xpath = '//tr[19]//input[@class="questionsetreference form-control element_reference_input"]'
        customer_id_values = ["New Customer", "Not Listed"]
        if self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{cid_xpath}").get_attribute("value") in customer_id_values:
            company_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'
        else:
            company_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'

        # consultant info xpaths
        email_xpath = '//tr[3]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        eid_xpath = '//tr[4]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        org_xpath = '//option[contains(@selected, "SELECTED")]'

        consultant_xpaths = [email_xpath, eid_xpath]
        user_info = []

        for xpath in consultant_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.consultant_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")
            user_info.append(part)

        company_xpaths = [company_xpath, oid_xpath, pid_xpath, org_xpath]
        for xpath in company_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")

            if part != None:
                user_info.append(part)
        
        # returns a list in order: email, employee ID, company, office ID, project ID, and organization
        return user_info
        
# NOTE: still requires manual input in saving and other missing information
# that requires interaction with the SNOW UI.
class UserCreation:
    def __init__(self, driver, link, user_info, name):
        self.driver = driver
        self.link = link
        self.name = name

        # company info, instances are initialized from a list
        self.email = user_info[0]
        self.eid = user_info[1]
        self.company = user_info[2]
        self.oid = user_info[3]
        self.pid = user_info[4]
        self.org = user_info[5]

    def create_user(self):
        self.driver.get(self.link)

        time.sleep(5)

        self.driver.switch_to.frame("gsft_main")

        self.format_project_id()
        
        f_name, l_name = self.name_keys()

        # consultant information (name + employee ID)
        self.driver.find_element(By.ID, "sys_user.first_name").send_keys(f_name)
        time.sleep(1.5)
        self.driver.find_element(By.ID, "sys_user.last_name").send_keys(l_name)
        time.sleep(1.5)
        self.driver.find_element(By.ID, "sys_user.employee_number").send_keys(self.eid)

        time.sleep(1.5)

        user_name = self.user_name_keys()
        # email information
        # user_name is the "FIRST.LAST@teksystemsgs.com"
        self.driver.find_element(By.ID, "sys_user.user_name").send_keys(user_name)
        time.sleep(1.5)
        self.driver.find_element(By.ID, "sys_user.email").send_keys(self.email)
        time.sleep(1.5)
        self.driver.find_element(By.ID, "sys_user.u_personal_e_mail").send_keys(self.email)

        time.sleep(2)
        # NOTE: the company names in aerotek_list deviates from the standard
        # user creation, look for conditionals and aerotek_list.
        # TODO: set up aerotek organizations requirements.
        aerotek_list = ["Aerotek", "Aston Carter", "Actalent"]
        # check what the selected organization is, GS requires "0000xxxxx" and other selections
        # uses unique project IDs related to their name, i.e. Staffing = TEKSTAFFING.
        if self.org != "GS":
            if self.org == "Staffing":
                self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys("TEKSTAFFING")
        else:
            self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys(self.pid)
        time.sleep(1.5)
        self.driver.find_element(By.ID, "sys_display.sys_user.company").send_keys(self.company)
        time.sleep(1.5)
        self.driver.find_element(By.ID, "sys_user.u_office_id").send_keys(self.oid)
        
        print("User created. Please review the information then hit save.")
        time.sleep(5)

    # extract only the number ID of the oid instance
    def format_office_id(self):
        full_oid = self.oid
        full_oid = full_oid.split("-")

        self.oid = full_oid[0]
    
    # modify the name into the correct format
    def name_keys(self):
        name = self.name

        name = name.title()

        if "-" in name:
            name = name.replace("-", " ")

        name = name.split()

        return name[0], name[-1]

    # format user name (first + last name) with the domain @teksystemsgs.com.
    def user_name_keys(self):
        f_name, l_name = self.name_keys()

        return f"{f_name}.{l_name}@teksystemsgs.com"
    
    # format the project ID to the correct length, only runs if the project ID
    # is incorrect to begin with.
    def format_project_id(self):
        pid = self.pid
        # 000011111, 9 digits long and first 4 digits must be 0.
        pid_format = re.compile(r'^(0{4})([0-9]{5})$')
        counter = 0

        if pid_format.match(pid):
            self.pid = pid
        else:
            if pid[:4] != "0000":
                for char in pid:
                    if char == "0":
                        counter += 1

                        # break out of loop, only the first four characters matter
                        if counter == 4:
                            break

                zeroes = 4 - counter
                prefix = "0" * zeroes
                pid = prefix + pid

            if len(pid) > 9 or len(pid) < 9:
                print("WARNING: The project ID in the ticket is incorrect.")
                print("Please email the CSA for the correct ID.")
            
            input("Enter 'enter' to continue.")

                    
            
                    

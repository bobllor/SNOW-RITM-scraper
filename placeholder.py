from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
import time, re

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
        
        print("\n   Login complete.")
        time.sleep(8)

class ScrapeRITM():
    def __init__(self, driver, ritm):
        self.driver = driver
        self.ritm = ritm

        self.global_search_xpath = '//input[@name="sysparm_search"]'

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
        global_search = self.driver.find_element(By.XPATH, self.global_search_xpath)
        global_search.send_keys(self.ritm)
        global_search.send_keys(Keys.ENTER)

        time.sleep(10)

        print("   RITM search complete.")
        # reset search field to prepare it for future queries
        global_search.click()
        global_search.send_keys(Keys.CONTROL + "a")
        global_search.send_keys(Keys.DELETE)
    
    # NOTE: this function alone can be used to generate a label with my FedEx label program.
    def scrape_ritm(self):
        self.driver.switch_to.frame("gsft_main")

        # returns the REQ number
        req = self.scrape_req()
        time.sleep(2.5)

        # returns the full name of the consultant
        name = self.scrape_name()
        time.sleep(2.5)

        # returns the address of the consultant
        address = self.scrape_address()
        time.sleep(2.5)

        return req, name, address
    
    def scrape_name(self):
        self.driver.switch_to.frame("gsft_main")

        # xpath of first and last name child containers
        fn_xpath = '//tr[1]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        ln_xpath = '//tr[2]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        name_xpaths = [f"{self.consultant_info_xpath}{fn_xpath}", 
                            f"{self.consultant_info_xpath}{ln_xpath}"]
        
        names = []
        for xpath in name_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, xpath)
            part = element_xpath.get_attribute("value")
            names.append(part)
        
        for index, name in enumerate(names):
            names[index] = name.strip().title()
        
        return names
    
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
        # organization container, contains global services, staffing, or aerotek orgs
        org_xpath = '//option[contains(@selected, "SELECTED")]'
        org_ele_xpath = self.driver.find_element(By.XPATH, f"{self.org_info_xpath}{org_xpath}")
        org = org_ele_xpath.get_attribute("value")

        # special aerotek orgs that creates additional fields inside the ticket
        # pushing down certain xpaths for fields.
        aerotek_list = ["Aerotek", "Aston Carter", "Actalent"]

        # consultant's company xpaths.
        if org in aerotek_list :
            oid_xpath = '//tr[25]//input[@class="cat_item_option sc-content-pad form-control"]'
        else:
            oid_xpath = '//tr[24]//input[@class="questionsetreference form-control element_reference_input"]'
        pid_xpath = '//tr[7]//input[@class="cat_item_option sc-content-pad form-control"]'

        # CHECKS IF CID CONTAINS ANYTHING OTHER THAN A NUMBER.
        # this is needed because if "New Customer/Not Listed" is selected then multiple XPATHS are
        # positioned in different locations due to an additional field form appearing.
        cid_xpath = '//tr[19]//input[@class="questionsetreference form-control element_reference_input"]'
        customer_id_values = ["New Customer", "Not Listed", "Not Listed - Not Listed"]
        if self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{cid_xpath}").get_attribute("value") in customer_id_values:
            cid_xpath = '//tr[22]//input[@class="cat_item_option sc-content-pad form-control"]'
            company_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'
        else:
            company_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'

        # consultant info xpaths
        email_xpath = '//tr[3]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        eid_xpath = '//tr[4]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        div_xpath = '//option[contains(@selected, "SELECTED")]'

        consultant_xpaths = [email_xpath, eid_xpath, div_xpath]
        user_info = []

        # consultant container, contains employee ID and email address
        for xpath in consultant_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.consultant_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")

            user_info.append(part)

        # company container, contains company information (company name, project ID, office ID)
        company_xpaths = [cid_xpath, company_xpath, oid_xpath, pid_xpath]
        for xpath in company_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")

            user_info.append(part)

        # append organzation last to the list
        user_info.append(org)

        if org in aerotek_list:
            if org == "Actalent":
                org = "ACTALENT"
            user_info[2] = org
            user_info[3] = org
            user_info[4] = org
        
        # returns a list: email, employee ID, division, customer ID, company, office ID, project ID, and organization
        return user_info
        
# NOTE: still requires manual input in certain aspects of the program.
class UserCreation:
    def __init__(self, driver, link, user_info, name):
        self.driver = driver
        self.link = link
        self.name = name

        # company info, instances are initialized from a list
        # in order: email, employee ID, division #, company ID, company name, office ID, project ID, and organization
        self.email = user_info[0]
        self.eid = user_info[1]
        self.div = user_info[2]
        self.cid = user_info[3]
        self.company = user_info[4]
        self.oid = user_info[5]
        self.pid = user_info[6]
        self.org = user_info[7]

        # initialized in a future function call
        self.oid_location = ""
        self.user_name = ""

        # used for duplicate keys, increments by 1 if the new user is unique.
        # NOTE: the first duplicate user starts at 2.
        self.user_name_unique_id = 1

    # MAIN FUNCTION
    def create_user(self):
        self.driver.get(self.link)

        time.sleep(5)

        self.driver.switch_to.frame("gsft_main")

        self.send_consultant_keys()

        # email keys
        f_name, l_name = self.name_keys()
        # if unique id is equal to 1, then it is a unique, non-duplicate username.
        if self.user_name_unique_id >= 1:
            self.user_name = f"{f_name}.{l_name}@teksystemsgs.com"
        else:
            self.user_name = f'{f_name}.{l_name}{str(self.user_name_unique_id)}@teksystemsgs.com'
        self.send_email_keys()

        # NOTE: these companies does not adhere to the standard user creation process.
        aerotek_list = ["Aerotek", "Aston Carter", "Actalent"]
        self.send_org_keys(aerotek_list)

        errors = self.save_user()
        if errors == False:
            self.search_user_list(20)
            self.fill_user(False)
            print("   User created. Please double check the information before continuing.")
        else:
            print("   User updated. Please double check the information before continuing.")
        
    # fills in consultant first name, last name, and their employee ID.
    def send_consultant_keys(self):
        self.driver.find_element(By.ID, "sys_user.first_name").send_keys(self.name[0])
        time.sleep(1.5)
        self.driver.find_element(By.ID, "sys_user.last_name").send_keys(self.name[1])
        time.sleep(1.5)

        # determine if employee ID needs to fill in TBD
        if self.eid.islower():
            self.eid = self.eid.upper()
        elif self.eid == '' or self.eid.strip('0') == '':
            self.eid = 'TBD'

        self.driver.find_element(By.ID, "sys_user.employee_number").send_keys(self.eid)
        time.sleep(3)
    
    # fills in username (first.last@teksystemsgs.com), and their personal email.
    def send_email_keys(self):
        self.driver.find_element(By.ID, "sys_user.user_name").send_keys(self.user_name)
        time.sleep(1.5)
        
        # mutable variables in case of a bad email input.
        email_key = self.email
        personal_key = self.email
        
        if self.email.upper() == 'TBD' or self.email == '':
            email_key = self.user_name
            personal_key = ''

        self.driver.find_element(By.ID, "sys_user.email").send_keys(email_key)
        time.sleep(1.5)
        self.driver.find_element(By.ID, "sys_user.u_personal_e_mail").send_keys(personal_key)
        time.sleep(2)

    # fills in project ID, company name, and office ID.
    def send_org_keys(self, aerotek_list):
        # check what the selected organization is, GS requires "0000xxxxx" and other selections
        # uses unique project IDs related to their name, i.e. Staffing = TEKSTAFFING.
        if self.org != "GS":
                if self.org == "Staffing":
                    self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys("TEKSTAFFING")

                if self.org in aerotek_list:
                    self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys(self.org)
        else:
            self.format_project_id()
            self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys(self.pid)
        time.sleep(1.5)

        self.driver.find_element(By.ID, "sys_display.sys_user.company").send_keys(self.company)
        time.sleep(1.5)

        self.format_office_id()
        self.driver.find_element(By.ID, "sys_user.u_office_id").send_keys(self.oid)
    
    # MAIN FUNCTION - saves the user and checks for errors during the process.
    def save_user(self):
        # TODO: check for errors during user creation: incorrect PID, incorrect company, duplicate username, incorrect email
        save_btn_xpath = '//button[@id="sysverb_insert_and_stay"]'
        time.sleep(5)

        self.driver.find_element(By.XPATH, save_btn_xpath).click()

        time.sleep(3)

        errors = self.user_error_msg_check()

        print(f"\n   DEBUG (Class UserCreation: errors @ save_user(self)): {errors}")
        print("   TO DO: do stuff with error checking. yeah!")

        time.sleep(3)

        # returns T/F if there was an error found during the user creation process.
        if errors == []:
            return False
        elif 'Unique Key violation' in errors[0]:
            print('\n   Duplicate user detected! WIP')
            input("   Press 'enter' to continue.")
            time.sleep(3)
            self.error_duplicate_key()

            return True
        elif 'The following mandatory fields' in errors[0]:
            # TODO: open the company list and check if the company name exists inside the list.
            # NOTE: if the company does not exist, then create a new company with the same name.
            print("\n   WARNING: An error has occurred with creating a new user. WIP")
            
            return True
        else:
            print("\n   WARNING: An error has occurred with creating a new user.")
            print("   The automatation will stop here, manual input to finish the user is required.")
            print("   A search of the user will occur in the Users List.")
            input("   Press 'enter' to continue.")

            return True
    
    def search_user_list(self, time_to_wait):
        user_link = 'https://tek.service-now.com/nav_to.do?uri=%2Fsys_user_list.do%3Fsysparm_clear_stack%3Dtrue%26sysparm_userpref_module%3D62354a4fc0a801941509bc63f8c4b979'

        print("\n   Searching for user...")
        
        self.driver.get(user_link)
        time.sleep(5)
        self.driver.switch_to.frame("gsft_main")

        search = '//input[@type="search"]'

        # long wait time due to SNOW's slow updating, can't do anything about it.
        time.sleep(time_to_wait)
        user_search = self.driver.find_element(By.XPATH, search)
        user_search.send_keys(self.user_name)
        user_search.send_keys(Keys.ENTER)

    def fill_user(self, duplicate_error):
        # duplicate is a bool, which indicates to update an existing user rather work on a new user.
        print("\n   User search completed.")
        # to access each cell: /td[X]
        # start on the 6th cell and end on the 11th
        # 6th = CID, 7th = office number (OID), 9th = office location, 10th = division
        user_cell_xpath = '//tbody[@class="list2_body"]'
        user_cells = []
        if duplicate_error is False:
            for i in range(6, 11):
                # 8th cell contains office ID, which is filled from the user creation process.
                if i != 8:
                    user_cell = f'{user_cell_xpath}//td[{i}]'
        
                user_cells.append(user_cell)
        else:
            for i in range(5, 11):
                # update all values of an existing user, only executes if a Unique Key error is found.
                user_cell = f'{user_cell_xpath}//td[{i}]'
        
                user_cells.append(user_cell)
        
        elements = []
        for path in user_cells:
            element_xpath = self.driver.find_element(By.XPATH, path)
            elements.append(element_xpath)

        time.sleep(5)
        print("\n   Inserting in consultant values...")

        # ORDER: customer ID, office number, office location, division
        keys_to_send = [self.cid, self.oid, self.oid_location, self.div]

        if duplicate_error:
            keys_to_send.insert(0, self.pid)
            keys_to_send.insert(3, self.oid)

        try:
            count = 0
            for key in keys_to_send:
                ActionChains(self.driver).double_click(elements[count]).perform()
                time.sleep(2.5)

                cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="cell_edit_value"]')

                # if an entry exists, remove it (NOTE: ONLY USED FOR UPDATING USERS).
                if cell_edit_value.text:
                    cell_edit_value.send_keys(Keys.CONTROL + "a")
                    time.sleep(2)
                    cell_edit_value.send_keys(Keys.DELETE)

                cell_edit_value.send_keys(key)
                time.sleep(2.5)
                cell_edit_value.send_keys(Keys.ENTER)
                time.sleep(3)

                count += 1
        except:
            raise NoSuchElementException
        
        print("\n   Task completed.")
        time.sleep(5)

    def user_error_msg_check(self):
        error_list = ['The following mandatory fields are not filled in: Company',
                      'Unique Key violation detected by database']
        errors = []
        
        # if an error message exists, return the object type.
        # error_hide returns a list of objects if found
        for error in error_list:
            element_xpath = self.driver.find_elements(By.XPATH, f'//span[contains(text(), "{error}")]')
            if element_xpath:
                error_msg = element_xpath[0].text
                errors.append(error_msg)
                break
        
        # ignore
        # //div[@class="outputmsg_container outputmsg_hide"]

        return errors

    # DUPLICATE KEY ERROR, checks info from existing user and the user inside the RITM ticket.
    def error_duplicate_key(self):
        self.search_user_list(5)
        
        # bool to check if the items matches
        eid_check = False
        email_check = False

        eid_xpath = self.driver.find_element(By.XPATH, f'//tbody[@class="list2_body"]//td[11]')
        email_xpath = self.driver.find_element(By.XPATH, f'//tbody[@class="list2_body"]//td[15]')
        print('\n   Comparing information of the existing user and the ticket.')

        # if employee ID or all digits but the last matches.
        if eid_xpath.text == self.eid or eid_xpath.text[0:-1] == self.eid:
            eid_check = True
            print(f'\n   Employee ID matched! {self.eid}')
            time.sleep(2)

        if email_xpath.text == self.email:
            email_check = True
            print(f'\n   Email address matched! {self.email}')
            time.sleep(2)

        # fill in the new info on the existing user based on if employee ID and email matches.
        if eid_check is True or email_check is True:
            print('\n   Existing user matches the RITM user, updating information.')
            time.sleep(3)
            self.fill_user(True)
        else:
            # if none matches, then this user is a new user.
            # adjust the user_name by adding in first.name{1 + i}@... depending on how many exists.
            # NOTE: there is a 99% chance that a third same-name user won't be needed, but keep it in mind!
            # TODO: create new user but with first.name{1 + i}@...
            print('\n   Existing user is unique, creating new user with updated username.')
            self.user_name_unique_id += 1
            self.create_user()
            time.sleep(3)

    def format_office_id(self):
        full_oid = self.oid
        full_oid = full_oid.split("-", 1)

        self.oid = full_oid[0].strip()
        self.oid_location = full_oid[-1].strip()
    
    def name_keys(self):
        name = self.name
        name = " ".join(name)

        if "-" in name:
            name = name.replace("-", " ")

        name = name.split()

        # name keys will always be the first and last name, regardless of X middle names.
        return name[0], name[-1]
    
    def format_project_id(self):
        pid = self.pid
        # 000011111(1), 9-10 digits long and first 4 digits must be 0.
        pid_format = re.compile(r'^(0{4})([0-9]{5,6})$')
        counter = 0

        if pid_format.match(pid):
            self.pid = pid
        else:
            if pid.startswith("0000") is False:
                for char in pid[:4]:
                    if char == "0":
                        counter += 1

                zeroes = 4 - counter
                prefix = "0" * zeroes
                self.pid = prefix + pid
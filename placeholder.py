from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, NoSuchFrameException
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

class ScrapeRITM:
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
        try:
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
        except NoSuchElementException:
            raise NoSuchElementException
        except NoSuchFrameException:
            raise NoSuchFrameException
    
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
        user_info = []

        # organization container, contains global services, staffing, or aerotek orgs
        org_xpath = '//option[contains(@selected, "SELECTED")]'
        org_ele_xpath = self.driver.find_element(By.XPATH, f"{self.org_info_xpath}{org_xpath}")
        org = org_ele_xpath.get_attribute("value")

        # allegis child orgs that creates additional fields inside the ticket
        # changing the xpaths of a typical RITM ticket.
        allegis_list = ["Aerotek", "Aston Carter", "Actalent"]

        if org in allegis_list:
            oid_xpath = '//tr[24]//input[@class="cat_item_option sc-content-pad form-control"]'
        else:
            oid_xpath = '//tr[24]//input[@class="questionsetreference form-control element_reference_input"]'

        cid_xpath = '//tr[19]//input[@class="questionsetreference form-control element_reference_input"]'

        # CHECKS IF CID CONTAINS ANYTHING OTHER THAN A NUMBER.
        # this is needed because if customer ID is not a number, then additional forms will appear
        # which pushes down the customer IDs and other values.
        customer_id_values = ["New Customer", "Not Listed"]
        if self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{cid_xpath}").get_attribute("value") in customer_id_values:
            cid_xpath = '//tr[22]//input[@class="cat_item_option sc-content-pad form-control"]'
            
        company_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'

        # consultant info xpaths
        email_xpath = '//tr[3]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        eid_xpath = '//tr[4]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        div_xpath = '//table[@class="container_table"]/tbody/tr[2]//option[@selected="SELECTED"]'
        
        # consultant container, contains employee ID and email address
        consultant_xpaths = [email_xpath, eid_xpath, div_xpath]
        for xpath in consultant_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.consultant_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")

            user_info.append(part)

        # company container, contains company information (customer ID, company name, office ID)
        company_xpaths = [cid_xpath, company_xpath, oid_xpath]
        
        # append project ID if xpath if org is GS, other orgs removes the project ID field.
        if org == 'GS':
            pid_xpath = '//tr[7]//input[@class="cat_item_option sc-content-pad form-control"]'
            company_xpaths.append(pid_xpath)
        
        for xpath in company_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")

            user_info.append(part.strip())

        # changes the project ID if org is not GS
        if org in allegis_list:
            if org == "Actalent":
                org = "ACTALENT"
            # modifies division and project ID
            user_info[2] = org
            user_info.append(org)
        if org == 'Staffing':
            user_info.append('TEKSTAFFING')
        
        # append organzation last to the list
        user_info.append(org)
        
        # returns a list: email, employee ID, division, customer ID, company, office ID, project ID, and organization
        return user_info

# NOTE: still requires manual input if something goes wrong.
class UserCreation:
    def __init__(self, driver, link, user_info, name):
        self.driver = driver
        self.link = link
        self.name = name

        # company info, instances are initialized from a list from ScrapeRITM
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

        # used to indicate if a user already exists, and not to initiate
        # the fill_user() process in the UserCreation class.
        # by default it is False- meaning that it should attempt to create a new user every time.
        self.existing_user = False

    def create_user(self):
        self.driver.get(self.link)

        time.sleep(5)

        self.driver.switch_to.frame("gsft_main")

        self.send_consultant_keys()

        f_name, l_name = self.name_keys()
        # if unique id is equal to 1, then it is a unique, non-duplicate username.
        # the line of code that is used to increment this count is found in error_duplicate_key().
        if self.user_name_unique_id >= 1:
            self.user_name = f"{f_name}.{l_name}@teksystemsgs.com"
        else:
            self.user_name = f'{f_name}.{l_name}{str(self.user_name_unique_id)}@teksystemsgs.com'
        self.send_email_keys()

        self.send_org_keys()

        errors = self.save_user()
        if errors is False and self.existing_user is False:
            self.search_user_list(15)
            self.fill_user()
            print("\n   User created. Please check the information before continuing.")
        else:
            # check save_users(), if errors is True and existing_user is False then execute
            # the new user creation. to be honest, i could just make new user creation into a function.
            # TODO: make it into a function. maybe.
            print("\n   Error handled, user updated accordingly. Please check the information before continuing.")
    
    def save_user(self):
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('gsft_main')
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
            # either a new user will be created or the existing user is updated, both of which
            # are determined inside the function call below. uses create_user() and fill_user().
            print('\n   WARNING: User already exists in the database!')
            print('   Checking the existing user\'s information.')
            time.sleep(3)
            self.error_duplicate_key()
        elif 'The following mandatory fields' in errors[0]:
            print("\n   WARNING: The company name does not exist.")
            print('   Checking the company lookup list for the company name.')
            time.sleep(2)
            self.error_invalid_company()
        elif 'Invalid email address' in errors[0]:
            print('\n   WARNING: An invalid email address was detected!')
            print('   Replacing the email with the username.')
            time.sleep(3)
            self.error_invalid_email()
            time.sleep(3)
        elif 'Invalid update' in errors[0]:
            print('\n   WARNING: The project ID is invalid!')
            self.error_project_id()
        else:
            print("\n   WARNING: An error has occurred with creating a new user.")
            print("   The automatation will stop here, manual input to finish the user is required.")
            print("   A search of the user will occur in the Users List.")
            input("   Press 'enter' to continue.")

        if errors:
            if self.existing_user is False:
                self.save_user()
                self.search_user_list(15)
                self.fill_user()

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
        time.sleep(3)
        user_search.send_keys(Keys.ENTER)

        time.sleep(1)
        print("   User search completed.")

    def fill_user(self):
        keys_to_send = [self.cid, self.oid, self.oid, self.oid_location, self.div]
        user_cells = []
        user_cell_xpath = '//tbody[@class="list2_body"]'
        
        if self.existing_user:
            user_cells.append(f'{user_cell_xpath}//td[4]')
            keys_to_send.insert(0, self.pid)

        # start on the 6th cell and end on the 10th
        # 6th = CID, 7th = office number (OID), 9th = office location, 10th = division
        for i in range(6, 11):
            user_cell = f'{user_cell_xpath}//td[{i}]'
           
            user_cells.append(user_cell)
    
        elements = []
        for path in user_cells:
            element_xpath = self.driver.find_element(By.XPATH, path)
            elements.append(element_xpath)

        time.sleep(5)
        print("\n   Inserting in consultant values...")

        count = 0
        for key in keys_to_send:
            if key == self.pid:
                # this code works around the issue with the href link located in the project ID cell.
                # long story short, if it works it ain't stupid!
                ActionChains(self.driver).click(elements[count]).perform()
                time.sleep(1.5)
                ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()
                time.sleep(1.5)
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                time.sleep(1.5)
                cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="sys_display.LIST_EDIT_sys_user.u_project_id"]')
            else:
                ActionChains(self.driver).double_click(elements[count]).perform()
                time.sleep(1.5)
                cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="cell_edit_value"]')

            time.sleep(1.5)

            # normally opening the cell already highlights the entire text,
            # but just to be safe this will remove it also.
            if cell_edit_value.text:
                cell_edit_value.send_keys(Keys.CONTROL + "a")
                time.sleep(1.5)
                cell_edit_value.send_keys(Keys.DELETE)

            cell_edit_value.send_keys(key)
            time.sleep(1.5)
            cell_edit_value.send_keys(Keys.ENTER)
            time.sleep(1.5)
            
            count += 1
        
        print("   Task completed.")
        time.sleep(5)

    def user_error_msg_check(self):
        '''
        following mandatory fields: bad company name, either it does not exist or SNOW is being bad.
        unique key violation: a user already exists with the newly created username.
        invalid email: bad email, not sure why this happens.
        invalid update: bad project ID, either it does not exist or SNOW is being bad.
        '''
        error_list = ['The following mandatory fields are not filled in: Company',
                      'Unique Key violation detected by database',
                      'Invalid email address',
                      'Invalid update']
        errors = []
        
        # search for if the error exists
        for error in error_list:
            if error != error_list[2]:
                element_xpath = self.driver.find_elements(By.XPATH, f'//span[contains(text(), "{error}")]')
            else:
                element_xpath = self.driver.find_elements(By.XPATH, f'//div[contains(text(), "{error}")]')

            if element_xpath:
                error_msg = element_xpath[0].text
                errors.append(error_msg)
                break

        return errors

    # DUPLICATE KEY ERROR, compares the existing user with the info inside the RITM ticket.
    # NOTE: don't bother refactoring this, i can tell this is a lot of unnecessary work - Tri | 8/15/2024.
    def error_duplicate_key(self):
        self.search_user_list(5)
        
        # bool to check if the items matches
        eid_check = False
        email_check = False

        eid_xpath = self.driver.find_element(By.XPATH, f'//tbody[@class="list2_body"]//td[11]')
        email_xpath = self.driver.find_element(By.XPATH, f'//tbody[@class="list2_body"]//td[14]')
        personal_email_xpath = self.driver.find_element(By.XPATH, f'//tbody[@class="list2_body"]//td[15]')
        email_texts = [email_xpath.text, personal_email_xpath.text]
        print('\n   Comparing information of the existing user and the ticket.\n')

        if self.eid != 'TBD':
            if eid_xpath.text == self.eid or eid_xpath.text[0:-1] == self.eid:
                eid_check = True
                print(f'   Employee ID matched! {self.eid}')
                time.sleep(2)
        
        # takes into account of if the CSA is stupid and puts down
        # the consultant's username instead of the personal email.
        for email in email_texts:
            if self.email == email or self.user_name == email:
                email_check = True
                print(f'   Email address matched! {self.email}')
                time.sleep(2)
                break

        if eid_check is True or email_check is True:
            print('   Existing user is the same from the RITM ticket, updating information.')
            time.sleep(3)
            # triggers that the existing user needs to be modified
            self.existing_user = True
            self.fill_user()
        else:
            # adjust the username by adding in first.name{1 + i}@... depending on how many exists.
            # NOTE: there is a 99% chance that a third same-name user won't be needed, but keep it in mind!
            print('   Existing user is a different user, creating new user with updated username.')
            self.user_name_unique_id += 1
            self.create_user()
            time.sleep(3)

    # INVALID COMPANY/COMPANY DOESN'T EXIST, select the company from the list or create a new one.
    def error_invalid_company(self):
        default_window = self.driver.current_window_handle

        time.sleep(2)
        self.driver.find_element(By.XPATH, '//button[@name="lookup.sys_user.company"]').click()
        time.sleep(5)

        for window_handle in self.driver.window_handles:
            if window_handle != default_window:
                self.driver.switch_to.window(window_handle)
                time.sleep(3)
                break
        
        company_table = '//tbody[@class="list2_body"]'
        company_name = '//a[@tabindex="0"]'

        self.driver.switch_to.default_content()

        company_list = self.driver.find_elements(By.XPATH, f'{company_table}{company_name}[contains(text(), "{self.company}")]')

        # look for the exact match of company name and element value.
        if company_list:
            for company_name in company_list:
                if self.company == company_name.text:
                    found = True
                    company_name.click()
                    time.sleep(1.5)
                    self.driver.switch_to.window(default_window)
                    break
                else:
                    found = False

        if company_list == [] or found is False:
            # apparently this crashes the program, i am unsure why since there are
            # rarely any tickets that requires a new company to be made.
            print('\n   Company is not found in the list. Creating a new company name.')
            time.sleep(1.5)

            new_company_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
            new_company_button.click()
            time.sleep(3)

            name_field = self.driver.find_element(By.XPATH, '//input[@name="core_company.name"]')
            name_field.send_keys(self.company)
            time.sleep(1.5)
            save_button = self.driver.find_element(By.XPATH, '//button[@value="sysverb_insert_and_stay"]')
            save_button.click()
            time.sleep(1.5)

            self.driver.close()
            time.sleep(1.5)
            self.driver.switch_to.window(default_window)
            self.driver.switch_to.default_content()

            # call function again to select the company name.
            self.error_invalid_company()
    
    # INVALID PROJECT ID, select the project ID from the list or create a new one.
    def error_project_id(self):
        default_window = self.driver.current_window_handle

        time.sleep(2)
        self.driver.find_element(By.XPATH, '//button[@name="lookup.sys_user.u_project_id"]').click()
        time.sleep(5)

        for window_handle in self.driver.window_handles:
            if window_handle != default_window:
                self.driver.switch_to.window(window_handle)
                time.sleep(3)
                break
        
        project_table = '//tbody[@class="list2_body"]'
        project_id = '//a[@role="button"]'

        project_list = self.driver.find_elements(By.XPATH, f'{project_table}{project_id}[contains(text(), "{self.pid}")]')

        if project_list:
            for project in project_list:
                if self.pid == project.text:
                    found = True
                    project.click()
                    time.sleep(1.5)
                    self.driver.switch_to.window(default_window)
                    break
                else:
                    found = False
        
        if project_list == [] or found is False:
            print('   WIP')
            new_button = self.driver.find_element(By.XPATH, '//button[@value="sysverb_new"]')
            # TODO: fill in project ID, primary POC (CSA), division, allocation (GS/STAFFING).
            # TODO: fill in the date, this requires extra steps (open calender, select today, hit enter/save)
            time.sleep(1.5)

    # INVALID EMAIL ERROR, replaces email address with username instead.
    def error_invalid_email(self):
        # change the user's email to the username instead.
        self.email = self.user_name

        email_field = self.driver.find_element(By.ID, "sys_user.email")
        email_field.send_keys(Keys.CONTROL + 'a')
        time.sleep(2)
        email_field.send_keys(Keys.DELETE)
        time.sleep(2)
        email_field.send_keys(self.email)
        time.sleep(2)

        self.save_user()
    
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
    def send_org_keys(self):
        if self.org == 'GS':
            self.format_project_id()
            self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys(self.pid)
        else:
            self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys(self.pid)
      
        time.sleep(1.5)

        self.driver.find_element(By.ID, "sys_display.sys_user.company").send_keys(self.company)
        time.sleep(1.5)

        self.format_office_id()
        self.driver.find_element(By.ID, "sys_user.u_office_id").send_keys(self.oid)

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

# used for companies that have blanket admin rights.
class AdminRights:
    # microsoft, apple, pet smart, american airlines, altice, church of christ, disney, 
    pass
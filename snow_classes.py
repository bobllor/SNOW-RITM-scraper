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

        time.sleep(15)

        print("   RITM search complete.")
        # reset search field to prepare it for future queries
        global_search.click()
        global_search.send_keys(Keys.CONTROL + "a")
        global_search.send_keys(Keys.DELETE)

    # NOTE: this function alone can be used to generate a label with my FedEx label program.
    def scrape_ritm(self):
        #self.driver.switch_to.frame("gsft_main")

        req = self.scrape_req()
        time.sleep(2.5)

        # returns the address of the consultant
        address = self.scrape_address()
        time.sleep(2.5)

        return req, address
    
    def scrape_need_by_date(self) -> str:
        input_xpath = '//input[@id="sc_req_item.u_need_by_"]'
        date = self.driver.find_element(By.XPATH, input_xpath).get_attribute("value")

        return date

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

            # checks if the name field has something else other than
            # the name itself, such as C/O XX XX. should rarely be true.
            if len(part.split()) > 3:
                split_part = part.split()
                part = split_part[0]

            names.append(part)
        
        for index, name in enumerate(names):
            names[index] = name.strip().title()
        
        return names
    
    def scrape_address(self):
        # column xpath which divides the address container.
        column_xpath1 = '//div[@class="section-content catalog-section-content"]/div[1]'
        column_xpath2 = '//div[@class="section-content catalog-section-content"]/div[2]'

        street_one_xpath = f'{column_xpath1}//tr[1]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        street_two_xpath = f'{column_xpath1}//tr[2]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        postal_xpath = f'{column_xpath2}//tr[1]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        city_xpath = f'{column_xpath1}//tr[3]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[2]'
        state_xpath = f'{column_xpath2}//tr[4]//option[@selected="SELECTED"]'

        # ORDER: ADDRESS 1, ADDRESS 2, POSTAL, CITY, STATE.
        address_xpaths = [f"{self.address_info_xpath}{street_one_xpath}",
                          f"{self.address_info_xpath}{street_two_xpath}",
                          f"{self.address_info_xpath}{postal_xpath}",
                          f"{self.address_info_xpath}{city_xpath}",
                          f"{self.address_info_xpath}{state_xpath}"]

        address = []

        for xpath in address_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, xpath)
            part = element_xpath.get_attribute("value").strip()

            address.append(part)
        
        for add_part in address:
            if add_part == '' or add_part == ' ':
                address.remove(add_part)
    
        return " ".join(address)
    
    def scrape_req(self):        
        element_xpath = self.driver.find_element(By.XPATH, self.req_xpath)
        req = element_xpath.get_attribute("value")

        return req
    
    # hardware options that the requestor checked, in addition to the main item.
    def scrape_hardware(self):
        hardware_container = '//span[@id="question_container_d7af38e4e17c4a00c2ab91d15440c571"]'
        checked_xpath = f'{hardware_container}/div[2]/div[1]//input[@checked="checked"]'
        checked_obj_list = self.driver.find_elements(By.XPATH, checked_xpath)

        # the main item that is being requested/wanted.
        requested_item_xpath = '//input[@id="sys_display.sc_req_item.cat_item"]'
        requested_item = self.driver.find_element(By.XPATH, requested_item_xpath).get_attribute("value")

        time.sleep(2)

        items = []
        if checked_obj_list:
            text_xpath = f'{checked_xpath}/following-sibling::label'
            text_obj_list = self.driver.find_elements(By.XPATH, text_xpath)

            time.sleep(2)

            if text_obj_list:
                for obj in text_obj_list:
                    items.append(obj.text)

        if items:
            for index, item in enumerate(items):
                if 'Add' in item:
                    items[index] = item.replace('Add', '').lstrip()
        
        return requested_item, items
    
    def scrape_user_info(self):
        # list for these pieces of shit, they change the xpaths of normal builds.
        allegis_list = ["Aerotek", "Aston Carter", "Actalent"]

        user_info = []

        # organization container, contains global services, staffing, or allegis orgs
        org_xpath = '//option[contains(@selected, "SELECTED")]'
        org_ele_xpath = self.driver.find_element(By.XPATH, f"{self.org_info_xpath}{org_xpath}")
        org = org_ele_xpath.get_attribute("value")

        try:
            oid_xpath = '//tr[24]//input[@class="questionsetreference form-control element_reference_input"]'
        except NoSuchElementException:
            # in case of an exception- this shouldn't happen often except for fucking allegis.
            oid_xpath = '//tr[24]//input[@class="cat_item_option sc-content-pad form-control"]'

        cid_xpath = '//tr[19]//input[@class="questionsetreference form-control element_reference_input"]'
        # if CID is not a number, then a new field will appear below the company name.
        # this pushes the CID from [19] to [22]
        customer_id_values = ["New Customer", "Not Listed"]
        if self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{cid_xpath}").get_attribute("value") in customer_id_values:
            cid_xpath = '//tr[22]//input[@class="cat_item_option sc-content-pad form-control"]'
        company_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'

        email_xpath = '//tr[3]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        eid_xpath = '//tr[4]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'

        # consultant container, contains employee ID and email address
        consultant_xpaths = [email_xpath, eid_xpath]
        for xpath in consultant_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.consultant_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")

            user_info.append(part)
        
        div_xpath = '//table[@class="container_table"]/tbody/tr[2]//option[@selected="SELECTED"]'
        div_value = self.driver.find_element(By.XPATH, f'{self.consultant_info_xpath}{div_xpath}').get_attribute("value")
        # depending on the selected division #, the xpath can either be tr[1] or tr[2].
        # if the value is empty, then try the other xpath instead.
        if div_value == '':
            div_xpath = '//table[@class="container_table"]/tbody/tr[1]//option[@selected="SELECTED"]'
            div_value = self.driver.find_element(By.XPATH, f'{self.consultant_info_xpath}{div_xpath}').get_attribute("value")
        user_info.append(div_value)

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
        
        # Not Listed creates two new fields for the office ID and location/name. 
        if 'Not Listed' in user_info[5]:
            oid_xpath = '//tr[25]//input[@class="cat_item_option sc-content-pad form-control"]'
            olocation_xpath = '//tr[26]//input[@class="cat_item_option sc-content-pad form-control"]'

            oid = self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{oid_xpath}').get_attribute('value')
            olocation = self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{olocation_xpath}').get_attribute('value')

            user_info[5] = f'{oid} - {olocation}'

        # changes the project ID if org is not GS
        if org in allegis_list:
            if org == "Actalent":
                org = "ACTALENT"
            # modifies division, company, PID
            user_info[2] = org
            user_info[4] = org
            user_info.append(org)
        if org == 'Staffing':
            user_info.append('TEKSTAFFING')
        
        # append organzation last to the list
        user_info.append(org)
        
        # NOTE: bad employee IDs gets converted to TBD in class UserCreation.
        # returns: email, employee ID, division, customer ID, company, office ID, project ID, and organization
        return user_info

# NOTE: still requires manual input if something goes wrong.
class UserCreation:
    def __init__(self, driver, link, user_info, name):
        self.driver = driver
        self.link = link
        self.name = name

        # company info, instances are initialized from a list from ScrapeRITM
        # in order: email, employee ID, division #, company ID, company name, office ID, project ID, and organization
        self.email = user_info[0].strip()
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

        # bool to check if a user already exists, if true it does not intiiate
        # the fill_user() process below.
        # by default it is False- meaning that it should attempt to create a new user every time.
        self.existing_user = False

    def create_user(self):
        self.driver.get(self.link)

        time.sleep(5)

        self.driver.switch_to.frame("gsft_main")

        self.send_consultant_keys()

        f_name, l_name = self.name_keys()
        
        if self.user_name_unique_id == 1:
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

        time.sleep(3)

        # returns T/F if there was an error found during the user creation process.
        if errors == [] and self.existing_user is False:
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

    # used for both filling and checking the user information.
    def fill_user(self):
        keys_to_send = [self.cid, self.oid, self.oid, self.oid_location, self.div]
        user_cells_obj = []
        user_cell_xpath = '//tbody[@class="list2_body"]'

        # cell positions: 5* 6 7 8 9 10
        # PID*, CID, OID, OID, office location, division
        # *only used if duplicate user is true.
        for i in range(6, 11):
            user_cell = f'{user_cell_xpath}//td[{i}]'
           
            user_cells_obj.append(user_cell)
        
        if self.existing_user:
            # PID cell, this will get changed later- for now it is used
            # to check the value of the cell.
            user_cells_obj.insert(0, f'{user_cell_xpath}//td[5]')
            keys_to_send.insert(0, self.pid)
        else:
            # remove oid/3rd element as it is filled during the user creation.
            keys_to_send.pop(2)
            user_cells_obj.pop(2)
    
        elements_obj = []
        for path in user_cells_obj:
            element_xpath = self.driver.find_element(By.XPATH, path)
            elements_obj.append(element_xpath)

        # checks if the cell values are the same as the ticket info.
        # if True, then remove the web object from the list to not fill.
        if self.existing_user:
            index_remover = []
            cell_names = ['Project ID', 'Customer ID', 'Office Number',
                          'Office ID', 'Office Location', 'Division']
            for index, web_obj in enumerate(elements_obj):
                if web_obj.text == keys_to_send[index]:
                    print(f'   {cell_names[index]} {web_obj.text} matches.')
                    index_remover.append(index)
                else:
                    print(f'   {cell_names[index]} {web_obj.text} does not match.')
            
            for index in sorted(index_remover, reverse=True):
                del elements_obj[index]
                del keys_to_send[index]
            
            if keys_to_send:
                # changes the PID cell (//td[5]) to the name cell (//td[4]).
                # this is done to work around the href link found in //td[5].
                # check while loop below, TL;DR: Right Arrow -> Enter (bypasses the link).
                if keys_to_send[0] == self.pid:
                    elements_obj[0] = self.driver.find_element(By.XPATH, f'{user_cell_xpath}//td[4]')

        time.sleep(5)
        print("\n   Inserting in consultant values...")

        count = 0
        repeat_attempts = 0
        while count < len(keys_to_send) and repeat_attempts != 3:
            # try block is used to keep trying in case an error occurs 
            # during the attempt to fill a status cell in, max 3 repeats.
            try:
                print(f'   Inserting {keys_to_send[count]}...')
                if keys_to_send[count] == self.pid:
                    # workaround the issue with the href link located in the PID cell.
                    # if it works it ain't stupid!
                    ActionChains(self.driver).click(elements_obj[count]).perform()
                    time.sleep(1)
                    ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()
                    time.sleep(1)
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    time.sleep(1)
                    cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="sys_display.LIST_EDIT_sys_user.u_project_id"]')
                else:
                    ActionChains(self.driver).double_click(elements_obj[count]).perform()
                    time.sleep(1)
                    cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="cell_edit_value"]')

                time.sleep(1)

                # normally opening the cell already highlights the entire text,
                # but just to be safe this will remove it also.
                if cell_edit_value.text:
                    cell_edit_value.send_keys(Keys.CONTROL + "a")
                    time.sleep(1)
                    cell_edit_value.send_keys(Keys.DELETE)
                    time.sleep(1)

                cell_edit_value.send_keys(keys_to_send[count])
                time.sleep(1)
                cell_edit_value.send_keys(Keys.ENTER)
                time.sleep(1)
                
                count += 1
                # if successful, reset repeat_attempts to 0.
                repeat_attempts = 0
                time.sleep(2)
            except NoSuchElementException:
                repeat_attempts += 1
                if 3 - repeat_attempts <= 1:
                    text_times = 'time'
                else:
                    text_times = 'times'
                print(f'   Failed inserting {keys_to_send[count]}. Repeating {3 - repeat_attempts} {text_times}.')
                time.sleep(2)
        
        if repeat_attempts != 3:
            print("   User filling completed.")
        else:
            # TODO: use an actual exception here, maybe a custom one?
            raise NoSuchElementException
        time.sleep(5)

    def user_error_msg_check(self):
        '''
        following mandatory fields: bad company name, either it does not exist or SNOW is being bad.
        unique key violation: a user already exists with the username.
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
        # TODO: check if all cells match, then don't do anything.
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
            if self.email.lower() == email.lower() or self.user_name.lower() == email.lower():
                email_check = True
                print(f'   Email address matched! {self.email}')
                time.sleep(2)
                break

        if eid_check is True or email_check is True:
            print('   Existing user is the same from the RITM ticket, updating relevant information.')
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
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame("gsft_main")
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
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame("gsft_main")
        self.driver.find_element(By.XPATH, '//button[@name="lookup.sys_user.u_project_id"]').click()
        time.sleep(5)

        for window_handle in self.driver.window_handles:
            if window_handle != default_window:
                self.driver.switch_to.window(window_handle)
                time.sleep(3)
                break
        
        self.driver.switch_to.default_content()
        
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

class AdminRights:
    # blanket admin rights:
    # american airlines, microsoft, t-mobile, LSD saints/church of christ
    # church mutual (staffing ONLY), do it best, frontier, altice
    # apple, petsmart
    def __init__(self, company):
        self.company = company

        self.blanket_dict = {
            'Microsoft': ['MSFT'],
            'American Airlines': ['AA'],
        }
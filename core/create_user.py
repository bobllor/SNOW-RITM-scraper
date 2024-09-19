from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from components.blanket_admin import AdminRights
import time, re

# NOTE: still requires manual input if something goes wrong.
class UserCreation:
    def __init__(self, driver, link: str, user_info: dict, name: list, requestor: str, admin=None):
        self.driver = driver
        self.link = link
        self.name = name
        self.requestor = requestor

        # company info, 8 instances are initialized from a list from ScrapeRITM.
        # keys: email, e_id, division, c_id, company, o_id, p_id, org
        self.email = user_info['email']
        self.eid = user_info['e_id']
        self.div = user_info['division']
        self.cid = user_info['c_id']
        self.company = user_info['company']
        self.oid = user_info['o_id']
        self.pid = user_info['p_id']
        self.org = user_info['org']

        self.admin = AdminRights(self.company).check_blanket() if admin is None else admin

        # initialized in a future function call
        self.oid_location = ""
        self.user_name = ""

        # used for duplicate keys, increments by 1 if the new user is unique.
        # NOTE: the first duplicate user starts at 1.
        self.user_name_unique_id = 0

        # bool to check if a user already exists, then modify the user instead of creating a new one.
        # by default it is False- meaning that it should attempt to create a new user every time.
        self.existing_user = False
        # used to stop a recursion issue, this only applies in one very specific circumstance.
        self.loop_once = False
        # prevent multiple companies creation, which is either temp or permanent-
        # depending on if i want to find a solution. for now, it will raise an exception.
        self.company_created = False
        # issue with the company field inside the creation of a new pid, this triggers a new step in the process.
        self.pid_error = False

    def create_user(self):
        self.driver.get(self.link)

        time.sleep(3)

        self.driver.switch_to.frame("gsft_main")

        self.__send_consultant_keys()

        f_name, l_name = self.__name_keys()
        
        self.user_name = f"{f_name}.{l_name}@teksystemsgs.com"
        # if the unique ID is > 0, then this is a different user with the same name as an existing one.
        if self.user_name_unique_id > 0:
            self.user_name = f'{f_name}.{l_name}{str(self.user_name_unique_id)}@teksystemsgs.com'
        self.__send_email_keys()

        self.__send_org_keys()

        errors = self.save_user()
        if errors is False and self.existing_user is False:
            self.search_user_list(15)
            self.fill_user()
            print("\n   User created. Please check the information before continuing.")
        else:
            print("\n   Error handled, user updated accordingly. Please check the information before continuing.")
        
        self.driver.switch_to.default_content()
    
    def save_user(self) -> bool:
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('gsft_main')
        save_btn_xpath = '//button[@id="sysverb_insert_and_stay"]'
        time.sleep(3)

        self.driver.find_element(By.XPATH, save_btn_xpath).click()

        time.sleep(5)

        errors = self.user_error_msg_check()
        
        # returns T/F if there was an error found during the user creation process.
        if not errors and self.existing_user is False:
            return False
        elif 'Unique Key violation' in errors[0]:
            # either a new user will be created or the existing user is updated, both of which
            # are determined inside the function call below. uses create_user() and fill_user().
            print('\n   WARNING: User already exists in the database!')
            print('   Checking the existing user\'s information.')
            self.error_duplicate_key()
            time.sleep(2)
        elif 'The following mandatory fields' in errors[0]:
            print("\n   WARNING: An error ocurred with the company field!")
            print('   Searching the company name list.')
            self.error_invalid_company()
            time.sleep(2)
        elif 'Invalid email address' in errors[0]:
            print('\n   WARNING: An error ocurred with the email address!')
            print('   Replacing the email with the username.')
            self.error_invalid_email()
        elif 'Invalid update' in errors[0]:
            print('\n   WARNING: An error ocurred with the project ID field!')
            print('   Searching the project ID list.')
            self.error_project_id()

        if errors:
            if self.existing_user is False:
                self.save_user()
                self.search_user_list(15)
                self.fill_user()

        return True

    def search_user_list(self, time_to_wait):
        if self.loop_once is False:
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
        # prevent a double-loop for user creation.
        if self.loop_once is False:
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame('gsft_main')
            # indicate to stop this function from executing its main loop, 
            # condition is only True if existing values of a cell are all matching.
            stop = False

            keys_to_send = [self.cid, self.oid, self.oid, self.oid_location, self.div]
            user_cells_obj = []
            user_cell_xpath = '//tbody[@class="list2_body"]'

            # cell positions: 5* 6 7 8 9 10
            # PID*, CID, OID, OID, office location, division
            # *only used if duplicate user is true- it gets inserted later.
            for i in range(6, 11):
                user_cell = f'{user_cell_xpath}//td[{i}]'
            
                user_cells_obj.append(user_cell)

            elements_obj = []
            for path in user_cells_obj:
                elements_obj.append(self.driver.find_element(By.XPATH, path))

            # initialized below, defined here to prevent an exception in a later loop if a condition isn't met.
            pid_cell_element = ''
            # checks if the cell values are the same as the ticket info.
            # if True, then remove the web object from the list to not fill.
            if self.existing_user:
                # if it is an existing user, insert PID to the beginning to modify it (if not matching).
                # NOTE: elements_obj[0] will be changed later if the PID cell doesn't match.
                pid_cell_element = self.driver.find_element(By.XPATH, f'{user_cell_xpath}//td[5]')

                elements_obj.insert(0, pid_cell_element)
                keys_to_send.insert(0, self.pid)

                index_remover = []
                cell_names = ['Project ID', 'Customer ID', 'Office Number',
                            'Office ID', 'Office Location', 'Division']
                match_count = 0

                # if a cell matches to the key, track the index number.
                for index, web_obj in enumerate(elements_obj):
                    if web_obj.text.lower() == keys_to_send[index].lower():
                        print(f'   {cell_names[index]} {web_obj.text} matches.')
                        index_remover.append(index)
                        time.sleep(.5)
                        match_count += 1
                    else:
                        print(f'   {cell_names[index]} {web_obj.text} does not match.')
                
                if match_count == 6:
                    print('   No values need to be updated.')
                    stop = True

                for index in sorted(index_remover, reverse=True):
                    del elements_obj[index]
                    del keys_to_send[index]
                
                if keys_to_send:
                    # changes the xpath "//td[5]" to the name cell "//td[4]".
                    # this is done to work around the href link found in "//td[5]"- check the while loop below.
                    if elements_obj[0] == pid_cell_element:
                        elements_obj[0] = self.driver.find_element(By.XPATH, f'{user_cell_xpath}//td[4]')
            else:
                # remove oid/3rd element as it is filled during the user creation.
                # only applicable if this is not an existing user.
                del keys_to_send[2]
                del elements_obj[2]
            
            print("\n   Inserting in consultant values...")
            time.sleep(3)

            count = 0
            repeat_attempts = 0
            while count < len(keys_to_send) and repeat_attempts != 3 and not stop:
                # try block is used to keep trying in case an error occurs 
                # during the attempt to fill a status cell in, max 3 repeats.
                try:
                    print(f'   Inserting {keys_to_send[count]}...')
                    # used only for duplicate users due to changing the PID cell.
                    if elements_obj[0] == pid_cell_element:
                        ActionChains(self.driver).click(elements_obj[count]).perform()
                        time.sleep(.5)
                        ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()
                        time.sleep(.5)
                        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                        time.sleep(1.5)
                        cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="sys_display.LIST_EDIT_sys_user.u_project_id"]')
                    else:
                        ActionChains(self.driver).double_click(elements_obj[count]).perform()
                        time.sleep(.5)
                        cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="cell_edit_value"]')

                    # normally opening the cell already highlights the entire text,
                    # but just to be safe this will remove it also.
                    if cell_edit_value.text:
                        cell_edit_value.send_keys(Keys.CONTROL + "a")
                        time.sleep(.5)
                        cell_edit_value.send_keys(Keys.DELETE)
                        time.sleep(1)

                    cell_edit_value.send_keys(keys_to_send[count])
                    time.sleep(.5)
                    cell_edit_value.send_keys(Keys.ENTER)
                    time.sleep(.5)
                    
                    # if successful, reset repeat_attempts to 0.
                    repeat_attempts = 0
                    count += 1
                    time.sleep(1)
                except NoSuchElementException:
                    repeat_attempts += 1
                    print(f'   Failed inserting {keys_to_send[count]}. Attempting to fill again.')
                    time.sleep(1)
                
            # initialized by the constructor, checks if the company is a blanket admin.
            # NOTE: this does not check for manually approved ones. it will maybe be implemented.
            if self.admin:
                admin_cell = self.driver.find_element(By.XPATH, f'{user_cell_xpath}//td[12]')
                admin_cell_val = admin_cell.text

                if admin_cell_val != 'true':
                    ActionChains(self.driver).double_click(admin_cell).perform()
                    time.sleep(1.5)

                    admin_cell_edit = self.driver.find_element(By.XPATH, '//select[@class="form-control list-edit-input"]')
                    ActionChains(self.driver).click(admin_cell_edit).perform()
                    time.sleep(.5)
                    ActionChains(self.driver).send_keys(Keys.ARROW_UP).perform()
                    time.sleep(.5)
                    ActionChains(self.driver).send_keys(Keys.ENTER).send_keys(Keys.ENTER).perform()
                    time.sleep(.5)
            
            if repeat_attempts != 3:
                print("   User filling completed.")
            else:
                # TODO: use an actual exception here, maybe a custom one?
                raise NoSuchElementException
        
            self.driver.switch_to.default_content()

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
            element_xpath = self.driver.find_elements(By.XPATH, f'//span[contains(text(), "{error}")]')

            # invalid email address and invalid update use the same tag.
            if error == error_list[2] or error == error_list[3]:
                element_xpath = self.driver.find_elements(By.XPATH, f'//div[contains(text(), "{error}")]')

            if element_xpath:
                error_msg = element_xpath[0].text
                errors.append(error_msg)
                break
        
        return errors

    # DUPLICATE KEY ERROR, compares the existing user with the info inside the RITM ticket.
    # NOTE: don't bother refactoring this.
    def error_duplicate_key(self):
        self.search_user_list(5)
        
        # bool to check if the items matches
        eid_check = False
        email_check = False

        # these xpaths can be found by searching for the user in the users list.
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
            if self.email.lower() == email.lower():
                email_check = True
                print(f'   Email address matched! {self.email}')
                time.sleep(2)
                break

        if eid_check is True or email_check is True:
            print('   Existing user is the same from the RITM ticket, updating relevant information.')
            time.sleep(3)
            # triggers that the existing user needs to be modified.
            if self.existing_user is False:
                self.existing_user = True
                self.fill_user()
                # stops a recursion, i do not know why this happens but this fixes it.
                self.loop_once = True
        else:
            # adjust the username by adding in first.name{1 + i}@... depending on how many exists.
            # NOTE: there is a 99% chance that a third same-name user won't be needed, but keep it in mind!
            print('   Existing user is a different user, creating new user with updated username.')
            self.user_name_unique_id += 1
            self.create_user()

    # INVALID COMPANY/COMPANY DOESN'T EXIST, select the company from the list or create a new one.
    def error_invalid_company(self):
        default_window = self.driver.current_window_handle

        time.sleep(2)
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame("gsft_main")
        self.driver.find_element(By.XPATH, '//button[@name="lookup.sys_user.company"]').click()
        time.sleep(3)

        for window_handle in self.driver.window_handles:
            if window_handle != default_window:
                self.driver.switch_to.window(window_handle)
                time.sleep(.5)
                break
        
        company_table = '//tbody[@class="list2_body"]'
        company_name = '//a[@tabindex="0"]'

        self.driver.switch_to.default_content()

        company_search_button = self.driver.find_element(By.XPATH, '//span[@id="core_company_hide_search"]//input[@type="search"]')
        
        # search the company name in the search bar
        company_search_button.send_keys(Keys.CONTROL + 'a')
        time.sleep(.5)
        company_search_button.send_keys(Keys.DELETE)
        time.sleep(.5)
        company_search_button.send_keys(self.company.lower())
        time.sleep(.5)
        company_search_button.send_keys(Keys.ENTER)
        time.sleep(3)

        company_list = self.driver.find_elements(By.XPATH, f'{company_table}{company_name}')

        # look for the exact match of company name and element value.
        if company_list:
            for company_name in company_list:
                if self.company.lower() == company_name.text.lower() or self.company.lower() in company_name.text.lower():
                    found = True
                    company_name.click()
                    time.sleep(1.5)
                    self.driver.switch_to.window(default_window)
                    break
                else:
                    found = False
        
        if self.company_created is False:
            if company_list == [] or found is False:
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

                # prevent an infinite loop.
                self.company_created = True

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

        search_container = '//div[@role="search"]'
        search_xpath = f'{search_container}/input[@type="search"]'

        search = self.driver.find_element(By.XPATH, search_xpath)
        search.send_keys(self.pid)
        time.sleep(.5)
        search.send_keys(Keys.ENTER)
        time.sleep(2)

        project_list = self.driver.find_elements(By.XPATH, f'{project_table}{project_id}[contains(text(), "{self.pid}")]')
        
        found = False
        if project_list:
            for project in project_list:
                if self.pid == project.text:
                    found = True
                    project.click()
                    time.sleep(1.5)
                    self.driver.switch_to.window(default_window)
                    break
        
        # create a new project ID.
        if project_list == [] or found is False:
            new_button = self.driver.find_element(By.XPATH, '//button[@value="sysverb_new"]')
            new_button.click()
            time.sleep(1.5)

            # pid field.
            pid_field = self.driver.find_element(By.XPATH, '//input[@id="u_projects.u_project_number"]')
            pid_field.send_keys(self.pid)
            time.sleep(.5)

            # primary point of contact- the requestor.
            ppoc_field = self.driver.find_element(By.XPATH, '//input[@id="sys_display.u_projects.u_primary_poc"]')
            ppoc_field.send_keys(self.requestor)
            time.sleep(.5)

            # company field, if pid_error is true then the steps to create the pid is changed.
            company_field = self.driver.find_element(By.XPATH, '//input[@id="sys_display.u_projects.u_company"]')
            if not self.pid_error:
                company_field.send_keys(self.company)
                time.sleep(.5)
            else:
                company_field.send_keys(self.company)
                time.sleep(.5)
                company_field.click()
                time.sleep(.5)
                ActionChains(self.driver).send_keys(Keys.ARROW_DOWN).send_keys(Keys.ENTER).perform()
                time.sleep(.5)

            allocation_field_xpath = '//select[@id="u_projects.u_allocation"]'
            if self.org == 'GS':
                allocation_select = self.driver.find_element(By.XPATH, f'{allocation_field_xpath}/option[@value="Global Services"]')
            elif self.org == 'TEKSTAFFING':
                allocation_select = self.driver.find_element(By.XPATH, f'{allocation_field_xpath}/option[@value="Staffing"]')
            allocation_select.click()
            time.sleep(2)

            div_field = self.driver.find_element(By.XPATH, '//input[@id="u_projects.u_division"]')
            div_field.send_keys(self.div)
            time.sleep(1)

            # select the date for the creation of the new PID.
            created_on_btn = self.driver.find_element(By.XPATH, '//button[@class="btn btn-default btn-ref date_time_trigger"]')
            created_on_btn.click()
            time.sleep(3)
            go_to_today = self.driver.find_element(By.XPATH, '//td[@class="calText calTodayText pointerhand"]')
            go_to_today.click()
            time.sleep(1)
            save_today = self.driver.find_element(By.XPATH, '//button[@id="GwtDateTimePicker_ok"]')
            save_today.click()
            time.sleep(2)

            save_btn = self.driver.find_element(By.XPATH, '//button[@value="sysverb_insert_and_stay"]')
            save_btn.click()
            time.sleep(2)

            # company name errors can occur when creating a new project ID.
            # if the error appears, then redo the process but with an additional step.
            invalid_company = 'Invalid update'
            error_element = self.driver.find_elements(By.XPATH, f'//div[contains(text(), "{invalid_company}")]')
            if error_element:
                self.pid_error = True

            self.driver.close()
            time.sleep(1)
            self.driver.switch_to.window(default_window)
            self.driver.switch_to.default_content()

            self.error_project_id()
    
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
    def __send_consultant_keys(self):
        self.driver.find_element(By.ID, "sys_user.first_name").send_keys(self.name[0])
        time.sleep(1)
        self.driver.find_element(By.ID, "sys_user.last_name").send_keys(self.name[1])
        time.sleep(1)

        # determine if employee ID needs to fill in TBD
        if self.eid.islower():
            self.eid = self.eid.upper()
        elif self.eid == '' or self.eid.strip('0') == '':
            self.eid = 'TBD'

        self.driver.find_element(By.ID, "sys_user.employee_number").send_keys(self.eid)
        time.sleep(3)
    
    # fills in username (first.last@teksystemsgs.com), and their personal email.
    def __send_email_keys(self):
        email_check = re.compile(r'(^[A-Za-z0-9_.-]{1,320})@([A-Za-z]{1,253}).([A-Za-z]*)$')
        self.driver.find_element(By.ID, "sys_user.user_name").send_keys(self.user_name)
        time.sleep(1)
        
        # mutable variables in case of a bad email input.
        email_key = self.email
        personal_key = self.email
        
        if self.email.upper() == 'TBD' or self.email == '':
            email_key = self.user_name
            personal_key = ''
        
        # used for very bad email addresses.
        if email_check.match(self.email) is None:
            email_key = self.user_name
            personal_key = ''

        self.driver.find_element(By.ID, "sys_user.email").send_keys(email_key)
        time.sleep(1)
        self.driver.find_element(By.ID, "sys_user.u_personal_e_mail").send_keys(personal_key)
        time.sleep(1)

    # fills in project ID, company name, and office ID.
    def __send_org_keys(self):
        if self.org == 'GS':
            self.__format_project_id()
        self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys(self.pid)
      
        time.sleep(1)

        self.__format_office_id()
        self.driver.find_element(By.ID, "sys_user.u_office_id").send_keys(self.oid)
        
        time.sleep(1)

        self.driver.find_element(By.ID, 'sys_display.sys_user.company').send_keys(self.company)
 
    def __format_office_id(self):
        full_oid = self.oid
        full_oid = full_oid.split("-", 1)

        self.oid = full_oid[0].strip()
        self.oid_location = full_oid[-1].strip()
    
    def __name_keys(self):
        name = self.name
        name = " ".join(name)

        if "-" in name:
            name = name.replace("-", " ")

        name = name.split()

        # name keys will always be the first and last name, regardless of X middle names.
        return name[0], name[-1]
    
    def __format_project_id(self):
        pid = self.pid
        # first 4 digits must be '0' / the remaining digits must be between 5 to 6 characters in length.
        pid_prefix = re.compile(r'^([0]{4})$')
        pid_suffix = re.compile(r'^([0-9]{5,6})$')
        counter = 0

        # if length of the pid is 11, highly likely it is 5 zeroes and 6 digits, remove an extra 0.
        if len(pid) == 11:
            five_zero_count = 0

            for char in pid:
                if char == '0':
                    five_zero_count += 1
                    if five_zero_count == 5:
                        self.pid = pid.replace('0', '', 1)
                        break
                else:
                    break

        if pid_prefix.match(pid[:4]):
            if pid_suffix.match(pid[4:]):
                self.pid = pid
            else:
                # TODO: ADD A CUSTOM EXCEPTION.
                raise NoSuchElementException
        else:
        # counts how many 0s are in the beginning, when a different character is read, break out the loop.
            if pid_prefix.match(pid[:4]) is None:
                for char in pid:
                    if char == '0':
                        counter += 1
                        if counter == 4:
                            break
                    else:
                        break
                        
                # append X zeroes to the beginning if they are missing.
                difference = 4 - counter
                text = 'zeroes'
                if difference <= 1:
                    text = 'zero'
                zeroes = '0' * difference
                pid = zeroes + pid

                print(f'   Project ID is incorrect, added in {difference} {text}.')

                # check if the last 5-6 digits are correct.
                if pid_suffix.match(pid[4:]):
                    self.pid = pid
                else:
                    # TODO: ADD A CUSTOM EXCEPTION.
                    raise NoSuchElementException
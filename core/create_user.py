from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from components.blanket_admin import AdminRights
from misc.cust_except import AttemptsException
import time, re

# NOTE: still requires manual input if something goes wrong.
class UserCreation:
    '''
    Create the user and add them into the Service NOW database.

    Checks and handles for any errors that can occur during the process.

    If 3 exceptions are raised during the process, then it will be canceled and the RITM will be blacklisted.
    '''
    def __init__(self, driver, link: str, user_info: dict, name: list, requestor: str, admin=None):
        self.driver = driver
        self.link = link
        self.name = name
        self.requestor = requestor

        # company info, 8 instances are initialized from a list from ScrapeRITM.
        # keys: email, e_id, division, c_id, company, o_id, p_id, org, o_id_loc
        self.email = user_info['email'].strip()
        self.eid = user_info['e_id']
        self.div = user_info['division']
        self.cid = user_info['c_id']
        self.company = user_info['company']
        self.oid = user_info['o_id']
        self.pid = user_info['p_id']
        self.org = user_info['org']
        self.oid_location = user_info['o_id_loc']

        self.admin = AdminRights(self.company).check_blanket() if admin is None else admin

        # initialized in a future function call, this is necessary because of potential duplicate users.
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
        # used to prevent an infinite loop inside the new user creation. if two errors show up at the same time,
        # the error message at the top of the page will not go away and cause an infinite loop.
        # when > 3, an exception will be thrown and blacklist the RITM.
        self.error_counter = 0
        # this is set to true when fill_user is executed, due to a recursion issue after creating a unique
        # user, the program goes back to save_user and breaks the program. this prevents the issue from occuring.
        self.prevent_save_user = False
        # used for `fill_user` to stop the process of filling in the user if all existing values match the RITM values.
        self.stop = False

    def __switch_frames(self):
        self.driver.switch_to.default_content()
        try:
            WebDriverWait(self.driver, 15).until(
                EC.frame_to_be_available_and_switch_to_it(self.driver.find_element(By.XPATH, '//iframe[@id="gsft_main"]'))
            )
        except TimeoutException:
            # TODO: create a logging message here.
            print('   Something went wrong during the switching to the VTB frame.')
            raise TimeoutException

    def create_user(self):
        '''
        Creates the user to add in SNOW's database.

        Checks if the user exists first by searching by their email address. 
        
        If an email address does not exist, then a new user will be created. 
        Otherwise, the user will be edited in the database table.
        '''
        # check_user_list returns true/false, existing user/new user.
        if self.__check_user_list() and not self.existing_user:
            self.existing_user = True
            self.fill_user()
        else:
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

            self.driver.find_element(By.XPATH, '//input[@id="sys_user.first_name"]').click()

            time.sleep(2)

            errors = self.save_user()
        
            if not errors and not self.existing_user:
                self.search_user_list(20)
                self.fill_user()
        
        print("\n   User created. Please check the information before continuing.")
        self.driver.switch_to.default_content()

    def save_user(self) -> bool:
        '''
        Saves the user on the user creation page.

        This checks for any errors that pop up during the user creation process.

        Uses a class method to obtain the list of errors to check.
        '''
        # used to prevent a recursion issue, check __init__ for more details.
        if not self.prevent_save_user:
            self.__switch_frames()

            # check for initial errors (company and pid errors).
            time.sleep(1)
            errors = self.user_error_msg_check()
            time.sleep(1)
            if errors:
                self.__check_errors(errors)

            save_btn_xpath = '//button[@id="sysverb_insert_and_stay"]'
            self.__switch_frames()
            save_btn = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, save_btn_xpath))
            )
            save_btn.click()
            time.sleep(1.5)

            # check for additional errors after hitting save (duplicate user and bad email).
            errors = self.user_error_msg_check()
            time.sleep(1)
            
            # if errors exist, then do method X to fix error Y.
            if errors:
                self.__check_errors(errors)

                # non-duplicate users will go through the process as normal.
                if self.existing_user is False:
                    self.save_user()
                    self.search_user_list(20)
                    self.fill_user()
            
            if not errors and self.existing_user is False:
                return False

        return True

    def __check_errors(self, errors: list):
        for error in errors:
                if 'Unique Key violation detected by database' in error:
                    # either a new user will be created or the existing user is updated, both of which
                    # are determined inside the function call below. uses create_user() and fill_user().
                    print('\n   WARNING: User already exists in the database!')
                    print('   Checking the existing user\'s information.')
                    self.error_duplicate_key()
                elif 'The following mandatory fields are not filled in: Company' in error:
                    print("\n   WARNING: An error ocurred with the company field!")
                    print('   Searching the company name list.')
                    self.error_invalid_company()
                elif 'Invalid email address' in error:
                    print('\n   WARNING: An error ocurred with the email address!')
                    print('   Replacing the email with the username.')
                    self.error_invalid_email()
                elif 'Invalid update' in error:
                    print('\n   WARNING: An error ocurred with the project ID field!')
                    print('   Searching the project ID list.')
                    self.error_project_id()

    def search_user_list(self, time_to_wait: int):
        '''
        Search for the user using their unique username.

        Takes an int as a parameter for how much time to wait.
        '''
        # this is used to prevent some recursion issue.
        if self.loop_once is False:
            user_link = 'https://tek.service-now.com/nav_to.do?uri=%2Fsys_user_list.do%3Fsysparm_clear_stack%3Dtrue%26sysparm_userpref_module%3D62354a4fc0a801941509bc63f8c4b979'

            print("\n   Searching for user...")
            
            self.driver.get(user_link)
            self.__switch_frames()

            search = '//input[@type="search"]'

            # long wait time due to SNOW's slow updating, can't do anything about it.
            time.sleep(time_to_wait)
            user_search = self.driver.find_element(By.XPATH, search)
            user_search.send_keys(self.email)
            time.sleep(1)
            user_search.send_keys(Keys.ENTER)

            time.sleep(1)
            print("   User search completed.")

    # used for both filling and checking the user information.        
    def fill_user(self):
        '''
        Fills in the user cells after searching up the user in the database.

        If any exception is raised during the process, it will attempt the process 3 times before blacklisting the RITM.
        '''
        # this is used to prevent some recursion issue.
        if self.loop_once is False:
            #self.prevent_save_user = True
            
            self.__switch_frames()
            # indicate to stop this function from executing its main loop, 
            # condition is only True if existing values of a cell are all matching.
            stop = False

            keys_to_send = [self.cid, self.oid, self.oid, self.oid_location, self.div]
            user_cells_obj = []
            user_cell_xpath = '//tbody[@class="list2_body -sticky-group-headers"]'

            # cell positions: 5* 6 7 8 9 10
            # PID*, CID, OID, OID, office location, division
            # *only used if duplicate user is true- it gets inserted later.
            for i in range(6, 11):
                user_cell = f'{user_cell_xpath}//td[{i}]'
            
                user_cells_obj.append(user_cell)

            elements_obj = []
            for path in user_cells_obj:
                # wait for the element to appear and select it, if a timeout exception occurs then refresh the page.
                # if it happens a second time, then the RITM will be blacklisted.
                attempts = 0
                while True:
                    try:
                        element = WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.XPATH, path)))
                        break
                    except TimeoutException:
                        self.driver.refresh()

                        if attempts == 2:
                            raise AttemptsException
                        attempts += 1
                        
                elements_obj.append(element)

            # initialized below, defined here to prevent an exception in a later loop if a condition isn't met.
            pid_cell_element = ''
            # checks if the cell values are the same as the ticket info.
            # if True, then remove the web object from the list to not fill.
            if self.existing_user:
                self.__check_cell_values(keys_to_send, elements_obj)
            else:
                # remove oid/3rd element as it is filled during the user creation.
                # only applicable if this is not an existing user.
                del keys_to_send[2]
                del elements_obj[2]
            
            if not self.stop:
                print("\n   Inserting in consultant values...")
                time.sleep(1.5)

            count = 0
            repeat_attempts = 0
            while count < len(keys_to_send) and repeat_attempts != 3 and not self.stop:
                # try block is used to keep trying in case an error occurs 
                # during the attempt to fill a status cell in, max 3 repeats.
                try:
                    print(f'   Inserting {keys_to_send[count]}...')
                    # used only for duplicate users due to changing the PID cell.
                    if elements_obj[count] == pid_cell_element:
                        ActionChains(self.driver).click(elements_obj[count]).perform()
                        time.sleep(.5)
                        ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()
                        time.sleep(.5)
                        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                        time.sleep(1.5)
                        cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="sys_display.LIST_EDIT_sys_user.u_project_id"]')
                    else:
                        # normal fill operation.
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
                self.loop_once = True
            else:
                # TODO: create a custom exception here.
                raise NoSuchElementException
        
            self.driver.switch_to.default_content()

    def __check_cell_values(self, keys_to_send, elements_obj) -> None:
        '''
        Checks the user cell values in the database table for any mismatching values.
        
        Has two parameters:
            1. `keys_to_send` is a list of keys that are the values entered to the cells.
            2. `elements_obj` is a list of elements object xpaths of the cell in the table.

        It modifies the list `keys_to_send` and `elements_obj` to add and remove cells based on matching values.
        Passes by reference for the two arguments.

        This only applies on duplicate users or if a user exists in the database already.
        '''
        # xpath for where the child user cells are located.
        user_cell_xpath = '//tbody[@class="list2_body -sticky-group-headers"]'
        # initialized below, defined here to prevent an exception in a later loop if a condition isn't met.
        pid_cell_element = ''
        # if it is an existing user, insert PID to the beginning to modify it (if not matching).
        # NOTE: elements_obj[0] will be changed later if the PID cell doesn't match.
        pid_cell_element = self.driver.find_element(By.XPATH, f'{user_cell_xpath}//td[5]')

        # insert these two elements to the front for both checking and modifying.
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
            self.stop = True

        for index in sorted(index_remover, reverse=True):
            del elements_obj[index]
            del keys_to_send[index]
        
        if keys_to_send:
            # changes the xpath "//td[5]" to the name cell "//td[4]".
            # this is done to work around the href link found in "//td[5]"- check the while loop below.
            if elements_obj[0] == pid_cell_element:
                pid_cell_element = self.driver.find_element(By.XPATH, f'{user_cell_xpath}//td[4]')
                elements_obj[0] = pid_cell_element

    def user_error_msg_check(self):
        '''
        Looks for any error messages that pop up due to a bad input when creating the user.

        Following mandatory fields: bad company name, either it does not exist or SNOW is being bad.
        Unique key violation: a user already exists with the username.
        Invalid email: bad email, not sure why this happens.
        Invalid update: bad project ID, either it does not exist or SNOW is being bad.
        '''
        error_list = ['The following mandatory fields are not filled in: Company',
                      'Unique Key violation detected by database',
                      'Invalid email address',
                      'Invalid update']
        errors = []

        # check if an invalid message is below the company fields.
        try:
            comp_err_ele = self.driver.find_element(By.XPATH, '//div[@data-fieldmsg-key="sys_user.company_fieldmsg_invalid_reference"]')

            if comp_err_ele:
                errors.append(error_list[0])
        except NoSuchElementException:
            pass

        # check if an invalid message is below the project ID.
        try:
            pid_err_ele = self.driver.find_element(By.XPATH, '//div[@data-fieldmsg-key="sys_user.u_project_id_fieldmsg_invalid_reference"]')

            if pid_err_ele:
                errors.append(error_list[-1])
        except NoSuchElementException:
            pass
        
        elements = []
        for count, error in enumerate(error_list):
            try:
                if count == 0:
                    error_ele = self.driver.find_element(By.XPATH, f'//span[contains(text(), "{error}")]')
                else:
                    error_ele = self.driver.find_element(By.XPATH, f'//div[contains(text(), "{error}")]')
                elements.append(error_ele)
            except NoSuchElementException:
                pass

        for element in elements:
            for error in error_list:
                if error in element.text:
                    errors.append(element.text)

        self.error_counter += 1
        return errors

    def error_duplicate_key(self):
        '''
        Unique key violation, this error is a warning that a user already exists with the current username.

        This checks if either the personal email address or employee ID matches with the existing user.

        If a match is found, then the class method to fill the user cells is called and will update the user.
        This also will update the class attribute existing_user to True, which indicates that this instance is an 
        existing user and will not execute certain steps regarding user creation.

        If no matches are found, then a number (n + 1) is attached to the end of the username (before the @) to
        distinguish the new user from the existing user(s).
        The number is incremented by 1 depending on how many unique users exist.
        '''
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame("gsft_main")
        self.search_user_list(5)
        
        # bool to check if the items matches
        eid_check = False
        email_check = False

        # these xpaths can be found by searching for the user in the users list.
        table_body_xpath = '//tbody[@class="list2_body -sticky-group-headers"]'
        eid_xpath = self.driver.find_element(By.XPATH, f'{table_body_xpath}//td[11]')
        email_xpath = self.driver.find_element(By.XPATH, f'{table_body_xpath}//td[14]')
        personal_email_xpath = self.driver.find_element(By.XPATH, f'{table_body_xpath}//td[15]')
        email_texts = [email_xpath.text, personal_email_xpath.text]
        print('\n   Comparing information of the existing user and the ticket.\n')

        count = 0
        if self.eid != 'TBD':
            if eid_xpath.text == self.eid or eid_xpath.text[0:-1] == self.eid or eid_xpath.text[1:] == self.eid:
                eid_check = True
                print(f'   Employee ID matched! {self.eid}')
                time.sleep(1)
        
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

    def error_invalid_company(self):
        '''
        Invalid company error that occurs during the user creation process.

        There are two reasons why this issue occurs:
            1. The company name does not exist inside the database.
            2. There is some issue with the autofilling of the company name.
        
        In any case, the list of company names is opened and a matching name will be selected
        if it is matching- otherwise select any company that at least contains the company name.

        If the company name does not exist, then a new company name will be created, then the same method
        is called to repeat the process.
        '''
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
        
        company_table = '//tbody[@class="list2_body -sticky-group-headers"]'
        company_name = '//a[@tabindex="0"]'

        # begin the process of searching, selecting, and create (if applicable) the company.
        self.driver.switch_to.default_content()

        '''company_search_button = self.driver.find_element(By.XPATH, '//span[@id="core_company_hide_search"]//input[@type="search"]')
        
        # search the company name in the search bar
        company_search_button.send_keys(Keys.CONTROL + 'a')
        time.sleep(.5)
        company_search_button.send_keys(Keys.DELETE)
        time.sleep(.5)
        company_search_button.send_keys(self.company.lower())
        time.sleep(.5)
        company_search_button.send_keys(Keys.ENTER)
        time.sleep(3)'''

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
                #self.company_created = True

                # call function again to select the company name.
                self.error_invalid_company()
    
    # INVALID PROJECT ID, select the project ID from the list or create a new one.
    def error_project_id(self):
        '''
        Invalid project ID error that occurs during the user creation process.

        There are three reasons why this issue occurs:
            1. The project ID does not exist inside the database.
            2. There is some issue with the autofilling of the project ID.

        Incorrect project IDs are corrected using a class method. If the project ID is very bad, as in the length
        of the ID is over 11 or if there is no project ID, then an exception is raised and the RITM is blacklisted.
        
        In any case, the list of project IDs is opened and a matching ID will be selected if it is an exact match.

        If the project ID does not exist, then a new project ID will be created. This process requires additional
        steps, which requires 6 inputs: project ID, requestor, date created, company name, division, and allocation.
        
        Afterwards, the same method will be called to select the correct project ID.
        '''
        default_window = self.driver.current_window_handle

        time.sleep(2)
        self.__switch_frames()
        self.driver.find_element(By.XPATH, '//button[@name="lookup.sys_user.u_project_id"]').click()
        time.sleep(5)

        for window_handle in self.driver.window_handles:
            if window_handle != default_window:
                self.driver.switch_to.window(window_handle)
                time.sleep(3)
                break
        
        self.driver.switch_to.default_content()
        
        project_table = '//tbody[@class="list2_body -sticky-group-headers"]'
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
            # in case an infinite loop occurs during this process, exit out immediately for blacklisting.
            if self.error_counter == 3:
                raise AttemptsException
            
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
            ppoc_field.send_keys(Keys.ARROW_DOWN)
            time.sleep(.5)
            ppoc_field.send_keys(Keys.ENTER)

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

            # used to stop an infinite loop, this is necessary because (at the time of writing this)
            # it is impossible to check for bad company name errors inside the PID creation window.
            self.error_counter += 1

            self.error_project_id()
    
    def error_invalid_email(self):
        '''
        Bad email address error during the user creation process.

        This will occur due to a bad input from the requestor inside the RITM ticket.

        If this is detected, then the user's unique username is used instead.
        '''
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
    
    def __send_consultant_keys(self):
        '''
        Fills in the first name, last name, and employee ID to the fields during user creation.
        '''
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
    
    def __check_user_list(self) -> bool:
        '''
        Returns `True` if one of these matches: Employee ID and Email. 
        
        Returns `False` if this is a new user.

        This is used to check if the user in the RITM is a duplicate or a new user. The function searches the
        database and compares the values above to the user in the table, if one exists.

        If any matches, then the user in the table will be edited. If it isn't a match or if `NoSuchElementException` 
        is thrown, then a new user will be created accordingly.
        '''
        self.__switch_frames()
        self.search_user_list(10)
        
        table_body_xpath = '//tbody[@class="list2_body -sticky-group-headers"]'

        try:
            eid_xpath = self.driver.find_element(By.XPATH, f'{table_body_xpath}//td[11]')

            # ensure that this is a valid employee ID to check. 
            # often times the ID isn't given and is either 'TBD' or a bunch of '0's.
            if self.eid != 'TBD' or self.eid.strip('0') != '':
                if eid_xpath.text == self.eid or eid_xpath.text[0:-1] == self.eid or eid_xpath.text[1:] == self.eid:
                        print(f'   Employee ID matched! {self.eid}')
                        time.sleep(1)
                        return True
                
            email_xpath = self.driver.find_element(By.XPATH, f'{table_body_xpath}//td[14]')
            personal_email_xpath = self.driver.find_element(By.XPATH, f'{table_body_xpath}//td[15]')
            email_texts = [email_xpath.text, personal_email_xpath.text]

            # ensures this is a valid email before checking it. the email address is
            # often there 95% of the time. most of the error checking occurs in scrape.py.
            if self.email != 'TBD' or '@' not in self.email:
                for email in email_texts:
                    if self.email.lower() == email.lower():
                        print(f'   Email address matched! {self.email}')
                        time.sleep(1)
                        return True
            
            # indicates that the user is a duplicate if the email ID or employee ID are no matches.
            self.user_name_unique_id += 1
        except NoSuchElementException:
            # indicates that there is no existing user in the database.
            pass
    
        return False

    # fills in username (first.last@teksystemsgs.com), and their personal email.
    def __send_email_keys(self):
        '''
        Fills in the username (first.last@teksystemsgs.com) and the personal email address 
        to the fields during user creation.

        In case of a bad email input, such as TBD or an empty input, then the username is used
        in place of the personal email address.
        '''
        self.driver.find_element(By.ID, "sys_user.user_name").send_keys(self.user_name)
        time.sleep(.5)
        
        # mutable variables in case of a bad email input.
        email_key = self.email
        personal_key = self.email
        
        # honestly it could work with just checking for @, but i don't want to test it.
        if self.email.upper() == 'TBD' or self.email == '' or '@' not in self.email:
            email_key = self.user_name
            personal_key = ''

        self.driver.find_element(By.ID, "sys_user.email").send_keys(email_key)
        time.sleep(.5)
        self.driver.find_element(By.ID, "sys_user.u_personal_e_mail").send_keys(personal_key)
        time.sleep(.5)

    def __send_org_keys(self):
        '''
        Fills in the project ID, office ID, and company name to the fields during user creation.
        '''
        self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys(self.pid)
      
        time.sleep(.5)

        self.driver.find_element(By.ID, "sys_user.u_office_id").send_keys(self.oid)
        
        time.sleep(.5)

        self.driver.find_element(By.ID, 'sys_display.sys_user.company').send_keys(self.company)
    
    def __name_keys(self):
        '''
        Method used to ensure the first and last name will always be the first and last name
        if the user contains multiple names (i.e. John Doe Smith).

        Dashes ("-") are accounted for any removed to properly parse the name.
        '''
        name = self.name
        name = " ".join(name)

        if "-" in name:
            name = name.replace("-", " ")

        name = name.split()
        
        last_name = name[-1]

        # checks if the last value in the name is a suffix
        suffixes = {'jr', 'sr', '1st', '2nd', '3rd', '4th', 'I', 'II', 'III', 'IV'}
        if name[-1].lower().strip('.') in suffixes:
            last_name = name[-2]

        # name keys will always be the first and last name, regardless of X middle names.
        return name[0], last_name
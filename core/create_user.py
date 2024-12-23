from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoSuchFrameException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from components.blanket_admin import AdminRights
from misc.cust_except import AttemptsException
import time, re

# NOTE: still requires manual input if something goes wrong.
class UserCreation:
    '''Create the user and add them into the Service NOW database.

    Checks and handles for any errors that can occur during the process.

    If 3 exceptions are raised during the process, then it will be canceled and the RITM will be blacklisted.

    IMPORTANT
    -------
    The order of the cells of the table in the database matters. 
    It must follow this order (cell name / SNOW name):
        1. User ID / User ID
        2. Name / Name
        3. Project ID / Project ID(u_project_id)
        4. Customer ID / Customer ID
        5. Office Number / Office Number
        6. Office ID / Office ID(u_office_id)
        7. Office Location / Office Location (u_office_location)
        8. Division / Divison
        9. Employee Number / Employee Number
        10. Local Admin / Local Admin
        11. Company / Company
        12. Email / Email
        13. Personal Email / Personal Email
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
        self.user_name = ''
        
        # initialized in create_user method.
        self.f_name = ''
        self.l_name = ''

        # used for duplicate keys, increments by 1 if the new user is unique.
        # NOTE: the first duplicate user starts at 1.
        self.user_name_unique_id = 0

        # bool to check if a user already exists, then modify the user instead of creating a new one.
        # by default it is False- meaning that it should attempt to create a new user every time.
        self.existing_user = False

        # if True, then the user is a unique duplicate user (user with the name of another existing in the database, but isn't the same person).
        # by default it is False, assuming that every user created does not exist in the database.
        # used to handle duplicate users if the unique ID > 0. it is set to true when an exception is thrown inside check_user_list.
        self.duplicate_user = False

        # used to stop a recursion issue, this only applies in one very specific circumstance.
        self.loop_once = False

        # issue with the company field inside the creation of a new pid, this triggers a new step in the process.
        self.pid_error = False

        # used to prevent an infinite loop inside the new user creation. if two errors show up at the same time,
        # the error message at the top of the page will not go away and cause an infinite loop.
        self.error_counter = 0

        # used for `fill_user` to stop the process of filling in the user if all existing values match the RITM values.
        self.stop = False

        # prevent eid_search from repeating twice. this is a workaround to the new code i created, and it's easier than to overhaul my code.
        # this is False initially, becomes True in search_user_list, then False again after email or username search is executed.
        self.eid_search = False

    def __switch_frames(self):
        '''Switches to the *iframe* of the page.

        If no iframes exist on the current page, a `TimeoutException` is thrown, which is handled
        and keeps the driver on the default frame.
        '''
        self.driver.switch_to.default_content()
        try:
            WebDriverWait(self.driver, 6).until(
                EC.frame_to_be_available_and_switch_to_it(self.driver.find_element(By.XPATH, '//iframe[@id="gsft_main"]'))
            )
        except TimeoutException or NoSuchFrameException:
            self.driver.switch_to.default_content()
        except NoSuchElementException:
            self.driver.switch_to.default_content()

    def create_user(self):
        '''Creates the user from the RITM and adds them in the SNOW's database.

        Checks if the user exists first by searching by their email address. 
        
        If an email address does not exist, then a new user will be created. 
        Otherwise, the user will be edited in the table directly.
        '''
        self.f_name, self.l_name = self.__name_keys()
        # changed later below if the user is a duplicate.
        self.user_name = f'{self.f_name}.{self.l_name}@teksystemsgs.com'

        # used to loop through the user search list for loop below. maximum of 3 times.
        loop_max = 1
        if self.eid != 'TBD':
            loop_max += 1
        if self.email != 'TBD':
            loop_max += 1

        # if checker_user_list is true, then break out after editing the user. if all loops finish, then this is a new user.
        # this is used to ensure that all 3 types of checks are done (EID, email, username).
        # the most important variable is self.existing_user = True, which indicates that 1. it is an existing user and 2. prevents the next statement.
        b = False
        for i in range(loop_max):
            if i == loop_max - 1:
                b = True

            if self.__check_user_list(search_user_name=b):
                self.fill_user()
                break
        
        # this increments inside check_user_list. the conditions: 1. no exception is thrown & 2. a user with the name exists but isn't a match.
        if self.user_name_unique_id > 0:
            c = 0
            while True:
                self.user_name = f'{self.f_name}.{self.l_name}{str(self.user_name_unique_id)}@teksystemsgs.com'

                if self.__check_user_list(search_user_name=True):
                    self.fill_user()
                    break

                if self.duplicate_user:
                    break
                
                # this condition shouldn't ever be met, but just in case a cosmic ray hits the the computer.
                if c > 7:
                    raise AttemptsException
                c += 1

        if not self.existing_user or self.duplicate_user:
            self.__create_user_fill_info()

            errors = self.save_user()

            if not errors:
                self.search_user_list(time_to_wait=18, search_by_user=False)
                self.fill_user()
        
        print("\n   User created. Please check the information before continuing.")
        self.driver.switch_to.default_content()

    def __create_user_fill_info(self):
            '''Fills the required fields during the creation of a new user on the New User page.'''

            self.driver.get(self.link)
            time.sleep(1)
            self.__switch_frames()

            self.__send_consultant_keys()
            
            self.__send_email_keys()

            self.__send_org_keys()

            self.driver.find_element(By.XPATH, '//input[@id="sys_user.first_name"]').click()

    def save_user(self) -> bool:
        '''Saves the new user on the New User page.

        This checks for any errors that pop up during the user creation process.

        Uses a class method to obtain the list of errors to check.
        '''
        self.__switch_frames()

        # check for initial errors (company and pid errors).
        time.sleep(1)
        errors = self.__user_error_msg_company_pid()
        time.sleep(1)
        if errors:
            self.__check_errors(errors)

        self.__save_user_save_btn()
        time.sleep(1.5)

        # check for additional errors after hitting save (duplicate user and bad email).
        errors = self.__user_error_msg_check()
        time.sleep(1)
        
        # if errors exist, then do method X to fix error Y.
        if errors:
            self.__check_errors(errors)

            # non-duplicate users will go through the process as normal.
            if self.existing_user is False:
                self.save_user()
                self.search_user_list(time_to_wait=18)
                self.fill_user()
        
        if not errors and self.existing_user is False:
            return False

        return True
    
    def __save_user_save_btn(self) -> None:
        '''Clicks on the save button inside the New User page.'''

        save_btn_xpath = '//button[@id="sysverb_insert_and_stay"]'
        self.__switch_frames()

        save_btn = WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.XPATH, save_btn_xpath))
        )
        save_btn.click()

    def __check_errors(self, errors: list):
        '''Used to check for any errors in the New User page, and calls the relevant method to handle the error.'''

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

    def search_user_list(self, *, time_to_wait: int = 20, search_by_user: bool = False):
        """Searches for the user in the database.

        Parameters
        ----------

        ``time_to_wait``: int

        (optional) The number of seconds before attempting to search for the user. Default is 20.

        ``search_by_user``: bool

        (optional) A flag to search for the user by username (True). Default is False.
        """
        if not isinstance(time_to_wait, int):
            raise TypeError(f'Expected an integer for time_to_wait, but got {type(time_to_wait).__name__}.')
        if not isinstance(search_by_user, bool):
            raise TypeError(f'Expected a bool for search_by_user, but got {type(search_by_user).__name__}.')

        # this is used to prevent some recursion issue. i don't remember why and where it happened.
        if self.loop_once is False:
            #user_link = 'https://tek.service-now.com/nav_to.do?uri=%2Fsys_user_list.do%3Fsysparm_clear_stack%3Dtrue%26sysparm_userpref_module%3D62354a4fc0a801941509bc63f8c4b979'
            user_link = 'https://tek.service-now.com/sys_user_list.do?sysparm_clear_stack=true&sysparm_userpref_module=62354a4fc0a801941509bc63f8c4b979'

            print("\n   Searching for user...")
            
            self.driver.get(user_link)
            self.__switch_frames()

            search = '//input[@type="search"]'

            # long wait time due to SNOW's slow updating, can't do anything about it.
            time.sleep(time_to_wait)
            user_search = self.driver.find_element(By.XPATH, search)

            if not search_by_user:
                if self.eid != 'TBD' and not self.eid_search:
                    user_search.send_keys(self.eid)
                    self.eid_search = True
                else:
                    self.eid_search = False
                    if self.email != 'TBD':
                        user_search.send_keys(self.email)
                    else:
                        user_search.send_keys(self.user_name)
            else:
                user_search.send_keys(self.user_name)

            time.sleep(1)
            user_search.send_keys(Keys.ENTER)

            time.sleep(1)
            print("   User search completed.")

    # used for both filling and checking the user information.        
    def fill_user(self):
        '''Edits the table cells for the current user once a search is completed.'''
        # this is used to prevent some recursion issue.
        if self.loop_once is False:
            self.__switch_frames()

            keys_to_send = [self.cid, self.oid, self.oid, self.oid_location, self.div]
            user_cell_xpath = '//tr[@record_class="sys_user"]'

            # cell positions: 5* 6 7 8 9 10
            # PID*, CID, OID, OID, office location, division
            # *only used if duplicate user is true- it gets inserted later.
            user_cells_obj = [f'{user_cell_xpath}//td[{i}]' for i in range(6, 11)]

            elements_obj = []
            for path in user_cells_obj:
                # wait for the element to appear and select it, if a timeout exception occurs then refresh the page.
                # if it happens 5 times, then the RITM will be blacklisted.
                attempts = 0
                while True:
                    try:
                        element = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, path)))
                        break
                    except TimeoutException:
                        self.search_user_list(time_to_wait=8)

                        if attempts > 5:
                            raise AttemptsException
                        attempts += 1
                        
                elements_obj.append(element)

            cell_names = ['Customer ID', 'Office Number',
            'Office ID', 'Office Location', 'Division']
            # checks if the cell values are the same as the ticket info.
            # if True, then remove the web object from the list to not fill.
            if self.existing_user:
                self.__check_cell_values(keys_to_send, elements_obj, cell_names)
            else:
                # remove oid/3rd element due to the existing user already having this value.
                del keys_to_send[2]
                del elements_obj[2]
            
            if not self.stop:
                print("\n   Inserting in consultant values...")
                time.sleep(1.5)

            count = 0
            repeat_attempts = 0
            while count < len(keys_to_send) and repeat_attempts != 3 and not self.stop:
                try:
                    print(f'   Inserting {keys_to_send[count]}...')
                    # used only for duplicate users, they have an additional PID to potentially modify.
                    if cell_names[0] == 'Project ID':
                        ActionChains(self.driver).click(elements_obj[count]).perform()
                        time.sleep(.5)
                        ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()
                        time.sleep(.5)
                        ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                        time.sleep(1.5)
                        cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="sys_display.LIST_EDIT_sys_user.u_project_id"]')
                        del cell_names[0]
                    else:
                        ActionChains(self.driver).double_click(elements_obj[count]).perform()
                        time.sleep(.5)
                        cell_edit_value = self.driver.find_element(By.XPATH, '//input[@id="cell_edit_value"]')

                    if cell_edit_value.text:
                        cell_edit_value.send_keys(Keys.CONTROL + "a")
                        time.sleep(.5)
                        cell_edit_value.send_keys(Keys.DELETE)
                        time.sleep(1)

                    cell_edit_value.send_keys(keys_to_send[count])
                    time.sleep(.5)
                    cell_edit_value.send_keys(Keys.ENTER)
                    time.sleep(.5)
                    
                    repeat_attempts = 0
                    count += 1
                    time.sleep(1)
                except NoSuchElementException:
                    repeat_attempts += 1
                    print(f'   Failed inserting {keys_to_send[count]}. Attempting to fill again.')
                    
                    self.search_user_list(time_to_wait=5)
                
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

    def __check_cell_values(self, keys_to_send: list, elements_obj: list, cell_names: list) -> None:
        '''Checks the user cell values in the database table for any mismatching values.
        
        Has two parameters:
            1. `keys_to_send` is a list of keys that are the values entered to the cells.
            2. `elements_obj` is a list of elements object xpaths of the cell in the table.

        It modifies the list `keys_to_send` and `elements_obj` to add and remove cells based on matching values.
        Returns None, as it uses pass by reference to modify the two lists.

        This only method is only called if a duplicate user error appears.
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
        cell_names.insert(0, 'Project ID')

        index_remover = []
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
            del cell_names[index]
        
        if keys_to_send:
            # changes the xpath "//td[5]" to the name cell "//td[4]".
            # this is done to work around the href link found in "//td[5]"- check the while loop below.
            if elements_obj[0] == pid_cell_element:
                pid_cell_element = self.driver.find_element(By.XPATH, f'{user_cell_xpath}//td[4]')
                elements_obj[0] = pid_cell_element

    def __user_error_msg_company_pid(self) -> list:
        '''Checks for *Company* and *Project ID* error messages on the New User page.

        Errors
        ------

        These errors appear before saving the user.

        Two ways both the messages can occur:
            1. The company/project ID does not exist in the system.
            2. An issue with SNOW's database, sometimes it cannot recognize the input.
        
        Methods `error_invalid_company` and `error_project_id` handle the errors respectively.
        
        Returns
        -------

        Returns an empty `list` if no errors were found or a `list` with the error messages attached.
        '''
        error_list = ('The following mandatory fields are not filled in: Company',
                      'Invalid update')
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

        return errors

    def __user_error_msg_check(self) -> list:
        '''Checks for *Duplicate User* and *Invalid Email Address* that appear on the New User page.
        
        Errors
        ------

        Both the errors only appear after saving the user once.

        \"Duplicate user\": A user with the same username already exists inside the database.

        \"Invalid email\": Unable to validate the email address, this is handled by SNOW and cannot be changed.

        Methods `error_duplicate_key` and `error_invalid_email` handle the errors respectively.

        Returns
        -------

        Returns an empty `list` if no errors were found or a `list` with the error messages attached.
        '''
        error_list = ['Unique Key violation detected by database',
                      'Invalid email address',]
        errors = []
        
        elements = []
        for error in error_list:
            try:
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
        '''Unique key violation, this error is a warning that a user already exists with the current username.

        Continuing on the previous method of creating the user, which searches the database for the personal email address of the user.
        It will increment the username unique ID, refresh the user creation page, and repeat the process.

        If it fails, it will keep going until the error is no longer seen or if max attempts are reached.
        '''
        self.__switch_frames()
        max_attempts = 0

        while True:
            if max_attempts > 7:
                raise AttemptsException
            
            self.user_name_unique_id += 1
            self.__create_user_fill_info()

            if 'Unique key violation' not in self.__user_error_msg_check():
                break

            max_attempts += 1

    def error_invalid_company(self):
        '''Invalid company error that occurs during the user creation process.

        There are two reasons why this issue occurs:
            1. The company name does not exist inside the database.
            2. There is some issue with the autofilling of the company name.
        
        In any case, the list of company names is opened and a matching name will be selected
        if it is matching- otherwise select any company that at least contains the company name.

        If the company name does not exist, then a new company name will be created, then the same method
        is called to repeat the process.
        '''
        default_window = self.driver.current_window_handle

        self.driver.switch_to.default_content()
        self.driver.switch_to.frame("gsft_main")
        self.driver.find_element(By.XPATH, '//button[@name="lookup.sys_user.company"]').click()
        time.sleep(1)

        for window_handle in self.driver.window_handles:
            if window_handle != default_window:
                self.driver.switch_to.window(window_handle)
                time.sleep(.5)
                break
        
        company_table = '//tbody[@class="list2_body -sticky-group-headers"]'
        company_name = '//a[@tabindex="0"]'

        # begin the process of searching, selecting, and create (if applicable) the company.
        self.driver.switch_to.default_content()

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
        
        if company_list == [] or found is False:
            print('\n   Company is not found in the list. Creating a new company name.')
            time.sleep(1.5)

            new_company_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
            new_company_button.click()
            time.sleep(1.5)

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
        '''An invalid project ID error message is detected.

        There are two errors that cause the message:
            1. The project ID does not exist inside the database.
            2. There is some issue with the autofilling of the project ID, which is a problem with SNOW's servers.

        In order to correct the error a new window is opened that consists of a table of project IDs only.
        A search is performed on the table to find the correct project ID, or create a new one if it doesn't exist.
        
        The fix is broken into two parts:
            1. If the project ID is found in the table, then the project ID is selected.
            2. If the project ID is not found, a series of steps are taken to create a new project ID.
            These steps require the *project ID*, *requestor/CSA email address*, *organization*, and *division number* from the RITM.
            After creation, the method calls itself to select the created project ID.
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
        
        # process of creating a new project ID.
        if project_list == [] or found is False:
            # in case an infinite loop occurs during this process.
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
        '''Bad email address error during the user creation process.

        If this error is found, then the user's unique username is used instead.
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
        '''Used to fill in the fields for first name, last name, and employee ID during user creation.'''

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
    
    def __check_user_list(self, *, search_user_name: bool = False) -> bool:
        '''Checks if the user in the table, if they exist, is a duplicate or new user.

        If any matches, then the user in the table will be edited with `fill_user`.
        
        If a user exists but there are no matches, then the unique ID will increment by one when creating a new user.

        If a `NoSuchElementException` is thrown, then a new user will be created accordingly.

        Parameters
        -------
        `search_user_name`

        (OPTIONAL) Default `False`. Searches by username instead of by email or employee ID if `True`.
        
        Returns
        -------
        `True` if either identifiers matches the user in the table: Employee ID and Email. 
        
        `False` if `NoSuchElementException` is thrown, the user does not exist in the database.
        '''
        self.__switch_frames()

        if not search_user_name:
            self.search_user_list(time_to_wait=5)
        else:
            self.search_user_list(time_to_wait=5, search_by_user=True)
        
        table_body_xpath = '//tr[@record_class="sys_user"]'
        found = False

        #obj = self.__get_user()

        # an exception is thrown if the table is empty.
        try:
            eid_xpath = self.driver.find_element(By.XPATH, f'{table_body_xpath}//td[11]')

            # ensure that this is a valid employee ID to check. 
            # often times the ID isn't given and is either 'TBD' or a repeating number.
            if self.eid != 'TBD' or self.eid.strip(self.eid[0]) != '':
                if eid_xpath.text == self.eid or eid_xpath.text[0:-1] == self.eid or eid_xpath.text[1:] == self.eid:
                        print(f'   Employee ID matched! {self.eid}')
                        found = True
                        time.sleep(1)
                
            email_xpath = self.driver.find_element(By.XPATH, f'{table_body_xpath}//td[14]')
            personal_email_xpath = self.driver.find_element(By.XPATH, f'{table_body_xpath}//td[15]')
            email_texts = [email_xpath.text, personal_email_xpath.text]

            # ensures this is a valid email before checking it. the email address is
            # often there 95% of the time. most of the error checking occurs in scrape.py.
            if self.email != 'TBD' or '@' not in self.email:
                for email in email_texts:
                    if self.email.lower() == email.lower():
                        print(f'   Email address matched! {self.email}')
                        found = True
                        time.sleep(1)
                        break
            
            if found:
                self.existing_user = True
                return True
            else:
                # if the user exists but the values do not match, increment the unique ID because this is a new unique user.
                print('   A different user exists in the database, incrementing the unique ID by one.')
                self.user_name_unique_id += 1
        except NoSuchElementException:
            # IF the unqiue ID was incremented, and an exception was thrown because the current username does not exist
            # in the database (meaning that the incremented ID is completely unique), then break out of the loop above and
            # create the new unique user with the new incremented ID.
            if self.user_name_unique_id > 0:
                self.duplicate_user = True
    
        return False

    def __get_user(self):
        '''Returns the web object of the correct use in the table.
        '''
        try:
            self.driver.find_element(By.CLASS_NAME, 'list2_no_records')

            return None
        except NoSuchElementException:
            list_row_odds = self.driver.find_elements(By.CSS_SELECTOR, '.list_row.list_odd')
            list_row_evens = self.driver.find_elements(By.CSS_SELECTOR, '.list_row.list_even')

            table_objs = list_row_evens + list_row_odds

            for obj in table_objs:
                full_text = obj.text

                if self.eid in full_text or self.email in full_text:
                    return obj

    def __send_email_keys(self):
        '''Fills in the username and personal email address fields during user creation.

        The username follows the format first.last@teksystemsgs.com. In case of a duplicate user, the `self.user_name_unique_id`
        is incremented and appended to the last name to differentiate multiple users with the same name.

        If the username is a bad email input (before the error is detected), if the input does not contain an email with an \"@\",
        then the username is used in place of the personal email address.
        '''
        # if the unique ID is > 0, then this is a different user with the same name as an existing one.
        if self.user_name_unique_id > 0:
            self.user_name = f'{self.f_name}.{self.l_name}{str(self.user_name_unique_id)}@teksystemsgs.com'

        user_name_obj = self.driver.find_element(By.ID, "sys_user.user_name")

        user_name_obj.send_keys(self.user_name)
        time.sleep(.5)
        
        # the email + personal email are the same, unless it is a bad email, in which case see below.
        email_key = self.email
        personal_key = self.email

        if '@' not in self.email:
            email_key = self.user_name
            personal_key = ''

        self.driver.find_element(By.ID, "sys_user.email").send_keys(email_key)
        time.sleep(.5)
        self.driver.find_element(By.ID, "sys_user.u_personal_e_mail").send_keys(personal_key)
        time.sleep(.5)

    def __send_org_keys(self):
        '''Fills in the fields for project ID, office ID, and company name during user creation.
        '''
        self.driver.find_element(By.ID, "sys_display.sys_user.u_project_id").send_keys(self.pid)
      
        time.sleep(.5)

        self.driver.find_element(By.ID, "sys_user.u_office_id").send_keys(self.oid)
        
        time.sleep(.5)

        self.driver.find_element(By.ID, 'sys_display.sys_user.company').send_keys(self.company)
    
    def __name_keys(self):
        '''Formats the first and last name in case of multiple names, or if a suffix is found in the last name.

        Dashes ("-") are accounted for to properly parse the name.
        '''
        name = self.name
        name = " ".join(name)
        
        if '-' in name:
            name = name.replace('-', ' ')

        name = name.split()

        # checks if the last value in the name is a suffix
        suffixes = {'jr', 'sr', '1st', '2nd', '3rd', '4th', 'i', 'ii', 'iii', 'iv'}
        if name[-1].lower().strip('.') not in suffixes:
            last_name = name[-1]
        else:
            last_name = name[-2]

        # name keys will always be the first and last name, regardless of X middle names.
        return name[0], last_name
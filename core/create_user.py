from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoSuchFrameException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from components.blanket_admin import AdminRights
from misc.cust_except import AttemptsException
from components.links import Links
import time

# NOTE: still requires manual input if something goes wrong.
class UserCreation:
    '''Create the user and add them into the Service NOW database.

    Checks and handles for any errors that can occur during the process.

    If 3 exceptions are raised during the process, then it will be canceled and the RITM will be blacklisted.

    Parameters
    -------
    `driver`

    The `WebDriver`.

    `link`
    
    Link to the new user creation URL.

    `user_info`

    `dict` containing information about the ticket. This requires 8 values:
    
        1. email
        2. e_id (employee ID)
        3. division
        4. c_id (customer ID)
        5. company
        6. o_id (office ID)
        7. p_id (project ID)
        8. org (organization)
        9. o_id_loc (office ID location)

    `name`

    A `list` that contains the first and last name of the user.

    `requestor`

    The email address of the person who requested the ticket.

    `admin`

    Determines if the user is an admin or not. By default `False`.
    '''
    
    def __init__(self, driver, link: str, user_info: dict, name: list[str], requestor: str, admin=False):
        self.driver: WebDriver = driver
        self.link = link
        self.name: list[str] = name
        self.requestor: str = requestor
        self.actions: ActionChains = ActionChains(driver)

        self.email: str = user_info['email'].strip()
        self.eid: str = user_info['e_id']
        self.div: str = user_info['division']
        self.cid: str = user_info['c_id']
        self.company: str = user_info['company']
        self.oid: str = user_info['o_id']
        self.pid: str = user_info['p_id']
        self.org: str = user_info['org']
        self.oid_location: str = user_info['o_id_loc']

        self.admin = AdminRights(self.company).check_blanket() if not admin else admin

        # initialized in a future function call, this is necessary because of potential duplicate users.
        self.user_name = ''
        
        # NOTE: i am sorry for the properties below. 

        # used for duplicate keys, increments by 1 if the new user is unique.
        self.user_name_unique_id = 0

        # bool to check if the current user has an existing profile. this can be the exact user or a different user with the same name.
        self.existing_user = False

        # issue with the company field inside the creation of a new pid, this triggers a new step in the process.
        self.pid_error = False

        # used to prevent an infinite loop inside the new user creation. if two errors show up at the same time,
        # the error message at the top of the page will not go away and cause an infinite loop.
        self.error_counter = 0

        # prevent eid_search from repeating twice. this is a workaround to the new code i created, and it's easier than to overhaul my code.
        # this is False initially, becomes True in search_user_list, then False again after email or username search is executed.
        self.eid_search = False

    def __switch_frames(self):
        '''Switches to the iframe of the page.

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
        f_name, l_name = self.__name_keys()
        # changed later below if the user is a duplicate.
        self.user_name = f'{f_name}.{l_name}@teksystemsgs.com'

        # used to loop through the user search list for loop below. maximum of 3 times.
        loop_max = 1
        if self.eid != 'TBD':
            loop_max += 1
        if self.email != 'TBD':
            loop_max += 1

        # if all loops finish, then this is a new user. this loops check EID, email, and username, if applicable.
        b = False
        for i in range(loop_max):
            if i == loop_max - 1:
                b = True
            
            if self._user_exists(search_user_name=b):
                obj = self._get_user()
                self._modify_table_data(obj, existing=True)

                break
        
        # username_uid increments inside check_user_list.
        # if a user entry exists with the same name, but is not the same user.
        duplicate_user = False
        if self.user_name_unique_id > 0:
            self.user_name = f'{f_name}.{l_name}{str(self.user_name_unique_id)}@teksystemsgs.com'

            found_user: bool = self._user_exists(search_user_name=True)
            obj = self._get_user()

            if found_user:
                self._modify_table_data(obj, True)
            else:
                duplicate_user = True

        # indicates that this is a new user- no entry in the database.
        if not self.existing_user or duplicate_user:
            self._create_user_fill_info()

            errors = self.save_user()

            if not errors:
                self.search_user_list(time_to_wait=18, search_by_user=False)
                
                # occasionally the database doesn't update, and needs a refresh to display the user.
                for _ in range(4):
                    try:
                        obj = self._get_user()
                        self._modify_table_data(obj)
                    except AttributeError:
                        self.driver.refresh()
                        time.sleep(4)
                
                # maybe change this to a proper exception? this shouldn't occur with the loop above.
                if obj is None:
                    raise NoSuchElementException
        
        print("\n   User created. Please check the information before continuing.")
        self.driver.switch_to.default_content()
    
    def _modify_table_data(self, obj: WebElement, existing = False):
        '''Corrects any incorrect data from a provided WebElement object in the user table. Returns None.
        
        Parameters
        ----------
            obj: WebElement
                `WebElement` object that represents the row in the user search table. The method creates
                a list of `WebElement` objects obtained from finding "td" tag elements.
                These represents the cell `WebElement`, and is required to interact with the data.
            
            
            existing: bool
                Used to indicate if the user has an entry in the database or is a new user.
                The method automatically assumes every user is a new user. By default it is `False`.
        '''
        obj_elements: list[WebElement] = obj.find_elements(By.CSS_SELECTOR, 'td')

        if len(obj_elements) < 1:
            raise ValueError(f'Got an empty {list}')
                
        check_elements = {
            'p_id': obj_elements[4], 'c_id': obj_elements[5],
            'off_num': obj_elements[6], 'off_id': obj_elements[7], 
            'off_loc': obj_elements[8], 'division': obj_elements[9]
        }

        curr_values = [self.pid, self.cid, self.oid, 
                        self.oid, self.oid_location, self.div]

        # used only for new users- OID and PID are filled during the user creation process
        if not existing:
            del check_elements['p_id']
            del check_elements['off_id']

            del curr_values[0]
            del curr_values[2]
        
        for i, web_ele in enumerate(check_elements.values()):
            if web_ele.text != curr_values[i]:
                text: str = web_ele.text if web_ele.text != '' else 'Empty entry'
                print(f'   {text} does not match {curr_values[i]}.')

                # the pause time is slightly longer due to additional checks from SNOW's backend.
                t = 2 if i == 0 and existing else .6
                if existing and i == 0:
                    # this is a cheeky trick to avoid clicking on the link found in the PID cell.
                    self.actions.click(obj_elements[3]).send_keys(
                        Keys.ARROW_RIGHT).pause(1).send_keys(Keys.ENTER).pause(.7).perform()
                else:
                    self.actions.double_click(web_ele).pause(t).perform()

                self.actions.send_keys(curr_values[i]).pause(t).send_keys(Keys.ENTER).perform()

    def _create_user_fill_info(self):
            '''Fills the required fields during the creation of a new user on the New User page.'''

            self.driver.get(self.link)
            self.__switch_frames()

            self.__send_consultant_keys()
            
            self.__send_email_keys()

            self.__send_org_keys()

            # ? i don't know why this is here. i'll leave it alone for now. 2/26/2025
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

                # TODO: i am not sure if this is needed? needs further testing.
                self.search_user_list(time_to_wait=18)

                obj = self._get_user()
                self._modify_table_data(obj)
        
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

        user_link = Links.user_list

        print("\n   Searching for user...")
        
        self.driver.get(user_link)
        self.__switch_frames()

        search = '//input[@type="search"]'

        # long wait time due to SNOW's slow updating, can't do anything about it.
        time.sleep(time_to_wait)
        user_search = self.driver.find_element(By.XPATH, search)

        # HACK: very terrible edge case regarding an idiot named PML.
        if self.email == self.requestor:
            self.email = self.user_name

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
            self._create_user_fill_info()

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

        self.__switch_frames()
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
            self.actions.send_keys(Keys.ARROW_DOWN).send_keys(Keys.ENTER).perform()
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
        self.driver.find_element(By.ID, "sys_user.last_name").send_keys(self.name[1])

        # determine if employee ID needs to fill in TBD
        if self.eid.islower():
            self.eid = self.eid.upper()
        elif self.eid == '' or self.eid.strip('0') == '':
            self.eid = 'TBD'

        self.driver.find_element(By.ID, "sys_user.employee_number").send_keys(self.eid)
    
    def _user_exists(self, *, search_user_name: bool = False) -> bool:
        '''Checks if the user is in the search table. Returns `True` if it a user exists and is the correct
        user, else returns `False`.

        Parameters
        ----------
        `search_user_name`: bool
            Searches by username instead of by email or employee ID if `True`. Default `False`.
        '''
        self.__switch_frames()

        if not search_user_name:
            self.search_user_list(time_to_wait=5)
        else:
            self.search_user_list(time_to_wait=5, search_by_user=True)

        obj = self._get_user()

        if not obj:
            return False
        
        self.existing_user = True
        return True

    def _get_user(self) -> WebElement | None:
        '''Returns the `WebElement` of the matching user in the table. Returns `None` if not found.
        
        self.username_unique_id is incremented in this method.
        This method assumes that the driver is on the page after a user search.
        '''
        info_check: list[str] = []

        if self.email.lower() != 'tbd' or '@' in self.email.lower():
            if len(self.email) > 40:
                # insane edge case. if len > 40, it truncates all characters past 40.
                info_check.append(self.email[:41])
            else:
                info_check.append(self.email)

        if self.eid.lower() != 'tbd':
            info_check.append(self.eid)

        if len(info_check) < 1:
            info_check.append(self.user_name)

        try:
            self.driver.find_element(By.CLASS_NAME, 'list2_no_records')
        except NoSuchElementException:
            list_row_odds = self.driver.find_elements(By.CSS_SELECTOR, '.list_row.list_odd')
            list_row_evens = self.driver.find_elements(By.CSS_SELECTOR, '.list_row.list_even')

            table_objs: list[WebElement] = list_row_odds + list_row_evens

            for i, obj in enumerate(table_objs, start=1):
                text_lowered: str = obj.text.lower()

                # used to handle multiple users with the same EID/email.
                name_found = self.name[0].lower() in text_lowered and self.name[1].lower() in text_lowered
                
                if name_found:
                    for info in info_check:
                        if info.lower() in text_lowered:
                            print(f'\n   {info} matches user entry {i}.\n')
                            
                            # reset is required because a future condition uses this value.
                            if self.user_name_unique_id > 0:
                                self.user_name_unique_id = 0

                            return obj
                
                # increments uid by 1 if EID/email doesn't match but the name does.
                if (self.user_name.lower() in text_lowered or name_found):
                    print(f'\n   User entry {i} does not match. Incrementing the unique ID by one.\n')
                    self.user_name_unique_id += 1
            
            return None

    def __send_email_keys(self):
        '''Fills in the username and personal email address fields during user creation.

        The username follows the format first.last@teksystemsgs.com. In case of a duplicate user, the `self.user_name_unique_id`
        is incremented and appended to the last name to differentiate multiple users with the same name.

        If the username is a bad email input (before the error is detected), if the input does not contain an email with an \"@\",
        then the username is used in place of the personal email address.
        '''
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
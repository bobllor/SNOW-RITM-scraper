from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, NoSuchFrameException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, re, string

class ScrapeRITM:
    def __init__(self, driver, ritm: str):
        self.driver = driver
        self.ritm = ritm

        # these are containers that need to be accessed before being able to grab the values
        self.consultant_info_xpath = '//tr[@id="element.container_23caec60e17c4a00c2ab91d15440c5ee"]'
        self.address_info_xpath = '//tr[@id="element.container_66291a0ae1fc8a00c2ab91d15440c5c2"]'
        self.company_info_xpath = '//tr[@id="element.container_84f76a0ee1fc8a00c2ab91d15440c50e"]'
        self.org_info_xpath = '//tr[@id="element.container_dbc92e7fe1a44a00c2ab91d15440c51c"]'

        # xpath that does not require a container to access
        self.req_xpath = '//input[@id="sys_display.sc_req_item.request"]'

        self.allegis_orgs = ["Aerotek", "Aston Carter", "Actalent", "MLA"]

    def search_ritm(self):
        # ensure that driver is not in a frame before performing a search.
        self.driver.switch_to.default_content()

        # let's fix this later...
        if self.driver.current_url != 'https://tek.service-now.com/now/nav/ui/classic/params/target/%24pa_dashboard.do':
            self.driver.get('https://tek.service-now.com/now/nav/ui/classic/params/target/%24pa_dashboard.do')
        
        try:
            # search for global search bar and query the site for an RITM ticket
            try:
                global_search_xpath = '//input[@name="sysparm_search"]'
                global_search = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, global_search_xpath)))

                global_search.send_keys(self.ritm)
            except TimeoutException:
                # used on the new SNOW, i do not know if this will be permanent or a temporary change.
                # as of 10/8/2024, this seems temporary but putting this here for future proofing.
                sr1 = self.driver.find_element(By.CSS_SELECTOR, 'macroponent-f51912f4c700201072b211d4d8c26010').shadow_root
                sr2 = sr1.find_element(By.CSS_SELECTOR, 'sn-polaris-layout').shadow_root
                sr3 = sr2.find_element(By.CSS_SELECTOR, 'sn-polaris-header').shadow_root
                sr4 = sr3.find_element(By.CSS_SELECTOR, 'sn-search-input-wrapper').shadow_root
                sr5 = sr4.find_element(By.CSS_SELECTOR, 'sn-component-workspace-global-search-typeahead').shadow_root

                global_search = sr5.find_element(By.CSS_SELECTOR, '.sn-global-typeahead').find_element(By.TAG_NAME, 'input')

                global_search.send_keys(self.ritm)
                time.sleep(1)
                global_search.send_keys(Keys.ARROW_DOWN)
                time.sleep(.2)

            global_search.send_keys(Keys.ENTER)

            time.sleep(15)

            print("   RITM search complete.")
            # reset search field to prepare it for future queries
            global_search.click()
            global_search.send_keys(Keys.CONTROL + "a" + Keys.DELETE)
        except ElementClickInterceptedException:
            # some issue with clicking the element, so instead reset back to the dashboard to repeat the process.
            print('   ERROR: Something went wrong with the search. Trying the process again.')
            self.driver.get('https://tek.service-now.com/nav_to.do?uri=%2F$pa_dashboard.do')
            time.sleep(5)
            self.search_ritm()

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

    def scrape_name(self) -> list:
        try:
            self.driver.switch_to.frame('gsft_main')
        except NoSuchFrameException:
            # only related to new SNOW
            sr1 = self.driver.find_element(By.TAG_NAME, 'macroponent-f51912f4c700201072b211d4d8c26010').shadow_root
            sr2 = sr1.find_element(By.CSS_SELECTOR, 'sn-canvas-appshell-root')
            iframe = sr2.find_element(By.CSS_SELECTOR, 'iframe')
            self.driver.switch_to.frame(iframe)


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
            # the name itself, such as C/O XX XX. should rarely occur.
            if len(part.split()) > 3:
                split_part = part.split()
                part = split_part[0]

            names.append(part)
        
        bad_chars = {'<', '>', '`', '\'', ';', ','}
        for index, name in enumerate(names):
            names[index] = name.strip().title()
            for char in bad_chars:
                if char in name:
                    names[index] = name.replace(char, '')

        return names

    def scrape_address(self) -> list:
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
    
    def scrape_req(self) -> str:        
        element_xpath = self.driver.find_element(By.XPATH, self.req_xpath)
        req = element_xpath.get_attribute("value")

        return req

    def scrape_requestor(self) -> str:
        '''
        Returns the requestor's email address, this is used for creating new project IDs when an error shows up.
        '''
        self.driver.find_element(By.XPATH, '//button[@name="viewr.sc_req_item.request.requested_for"]').click()
        time.sleep(1)
        req_element = self.driver.find_element(By.XPATH, '//input[@id="sys_readonly.sys_user.user_name"]')

        return req_element.get_attribute("value")

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
    
    def scrape_user_info(self) -> dict:
        '''
        Returns a dict that contains information from the ticket to create them in the database.

        The dict contains:
            1. email
            2. employee ID
            3. division
            4. customer ID
            5. company name
            6. office ID
            7. project ID
            8. office ID location
            9. organization
        '''
        # orgs: allegis groups (see above), STAFFING, and GS
        org = self.__scrape_org()

        pid = self.__scrape_project_id(org)

        oid, oid_location = self.__format_office_id(self.__scrape_office_id())

        cid = self.__scrape_customer_id()
        company = self.__scrape_company(org)

        email = self.__scrape_email()
        eid = self.__scrape_employee_id()

        divison = self.__scrape_division(org)

        return {'email': email, 'e_id': eid, 'division': divison, 'c_id': cid,
                'company': company, 'o_id': oid, 'p_id': pid, 'o_id_loc': oid_location,
                'org': org}
    
    def __scrape_org(self) -> str:
        '''
        Returns the organization value on the RITM.

        This value is either GS, Staffing, or Allegis companies (Actalent, Aerotek, Aston Carter, MLA).
        
        If the org is an Allegis company, then the following will be changed:
            1. Project ID
            2. Company
            3. Division
        '''
        # organization container, contains global services, staffing, or allegis orgs
        org_xpath = '//option[contains(@selected, "SELECTED")]'
        org_ele_xpath = self.driver.find_element(By.XPATH, f"{self.org_info_xpath}{org_xpath}")
        org = org_ele_xpath.get_attribute("value")

        return org
    
    def __scrape_project_id(self, org: str) -> str:
        '''
        Returns the PID for the RITM. Requires an `org` argument in order to return the correct
        PID value.

        The PID value is dependent on the type of organization the consultant belongs to.
            'GS': 10 digit number- example: 0000123456
            'Staffing': TEKSTAFFING
            'Any Allegis Orgs': ALLEGIS_ORO (the PID is the same as the org)
        '''
        if org == 'GS':
            pid_xpath = '//tr[7]//input[@class="cat_item_option sc-content-pad form-control"]'
        
            pid = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{pid_xpath}").get_attribute("value").strip()
            pid = self.__format_project_id(pid)
    
        if org ==  'Staffing':
            pid = 'TEKSTAFFING'

        # allegis organizations are missing the PID field, but the PID for these are the orgs itself.
        if org in self.allegis_orgs:
            # formatting the name? i actually don't remember what this is used for.
            if org == 'Actalent':
                org = 'ACTALENT'

            return org
        
        return pid

    def __scrape_customer_id(self) -> str:
        '''
        Scrape the customer ID. Takes into account of new HTML fields if a company doesn't exist.
        '''
        # these two are options that when chosen, will change the xpath of the CID, from [19] to [22].
        customer_id_values = ["New Customer", "Not Listed"]

        # by default [19] will be the value of CID, assuming that this is an existing company.
        cid_xpath = '//tr[19]//input[@class="questionsetreference form-control element_reference_input"]'
        cid = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{cid_xpath}").get_attribute("value").strip()

        # used to remove any invisible escape characters in a customer ID by casting it into an int and back to a str.
        # an exception is thrown on non-digit values, in which case check for the issue in the catch, otherwise return cid.
        try:
            if str(int(cid)).isdigit():
                pass
        except ValueError:
            # related to above, 
            if cid in customer_id_values:
                cid_xpath = '//tr[22]//input[@class="cat_item_option sc-content-pad form-control"]'
                cid = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{cid_xpath}").get_attribute("value")
            # this is a major issue in regards to NM idiots, who decide to put N/A for the CID and still provide the CID. (i.e. 'company - 111111').
            elif cid == 'N/A':
                # if CID is N/A, there is only one field, and (so far) the requestors put both the company name and customer ID in this field.
                temp_cid_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'
                temp_cid = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{temp_cid_xpath}").get_attribute("value")

                pos = 0
                for i, c in enumerate(temp_cid):
                    if c.isdigit():
                        pos = i
                        break
                
                # condition should always be true if cid is N/A, but this is used for future proofing.
                if pos != 0:
                    cid = temp_cid[pos:]
            # takes into account of idiots (like JW) who put the company name in the CID field.
            # this should very rarely ever be seen, but more idiot-proof code is better.
            elif not cid.isdigit():
                cid_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'
                cid = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{cid_xpath}").get_attribute("value")
            
        return cid
    
    def __scrape_office_id(self) -> str:
        '''Handles both the office ID and office location, returns a `str`.
        
        `_format_office_id` is used to split the two to the proper office ID and office location assignments.

        Returns
        -------
        `string` formatted "ID - LOCATION". Default return if no issues in the default field.

        `string` formatted "ID||LOCATION". This return is if there is one of two issues in the default field.
        '''
        try:
            oid_xpath = '//tr[24]//input[@class="questionsetreference form-control element_reference_input"]'
        except NoSuchElementException:
            # in case of an exception- this shouldn't happen often except for fucking aerotek.
            oid_xpath = '//tr[24]//input[@class="cat_item_option sc-content-pad form-control"]'

        oid = self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{oid_xpath}').get_attribute('value')

        # Not Listed and New Office in the oid field will change the xpaths for the office ID and location/name.
        # on certain RITMs the oid_xpath is 23 instead of 24 (e.g. RITM0092364), in which case it ends up as an empty string.
        if 'Not Listed' in oid or 'New Office - New Office' in oid or oid == '':
            oid_xpath = '//tr[25]//input[@class="cat_item_option sc-content-pad form-control"]'
            olocation_xpath = '//tr[26]//input[@class="cat_item_option sc-content-pad form-control"]'

            oid = self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{oid_xpath}').get_attribute('value')
            o_location = self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{olocation_xpath}').get_attribute('value')

            # modified oid string, due to the two fields being separate from each other.
            # a new block of code will be used in format_office_id due to the double pipe.
            oid = f'{oid}||{o_location}'

        return oid

    def __scrape_company(self, org: str) -> str:
        # the company field is missing, but it is the same as the org for allegis orgs.
        if org in self.allegis_orgs:
            return org
        
        # by default it company field is [21], however some circumstances may drop it down to [22]- see below.
        company_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'
        company = self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{company_xpath}').get_attribute('value')
        # takes into account of idiots (like JW) who put the CID in the company field.
        # this should very rarely ever be seen, but more idiot-proof code is better.
        if company.isdigit():
            company_xpath = company_xpath = '//tr[22]//input[@class="cat_item_option sc-content-pad form-control"]'
            company = self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{company_xpath}')

        # another validation in case idiots (specifically NM requestors) put in the wrong company format again...
        # this takes into account of bad format like "COMPANY-123456" or "COMPANY 123456" or similar strings.
        if not company[0].isdigit() and ':' not in company:
            num_pos = 0
            
            for i, char in enumerate(company):
                if char.isdigit():
                    num_pos = i
                    break
            
            if num_pos != 0:
                company = company[:num_pos]
        # in case that a colon is used in the company, the company string will start on col_index + 1.
        elif ':' in company:
            col_index = company.find(':')
            company = company[col_index + 1:].strip().strip('.')

        return company.strip()
    
    def __scrape_email(self) -> str:
        email_xpath = '//tr[3]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        email = self.driver.find_element(By.XPATH, f"{self.consultant_info_xpath}{email_xpath}").get_attribute("value")
        
        # if for whatever reason the email address does not have an @- indicator that this is a bad input.
        if '@' not in email:
            return 'TBD'
        
        return self.__validate_email(email)
    
    def __scrape_employee_id(self) -> str:
        eid_xpath = '//tr[4]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        eid = self.driver.find_element(By.XPATH, f"{self.consultant_info_xpath}{eid_xpath}").get_attribute("value").strip()

        # if EID is not a valid input then leave it as TBD.
        if not eid.isdigit() or eid.strip(eid[0]) == '':
            eid = 'TBD'

        return eid

    def __scrape_division(self, org: str) -> str:
        # division for these fields are the same as their orgs.
        if org in self.allegis_orgs:
            return org
        
        div_xpath = '//table[@class="container_table"]/tbody/tr[2]//option[@selected="SELECTED"]'
        div = self.driver.find_element(By.XPATH, f'{self.consultant_info_xpath}{div_xpath}').get_attribute("value")
        
        # depending on the selected division #, the xpath can either be tr[1] or tr[2].
        # if the value is empty, then try the other xpath instead.
        if div == '':
            div_xpath = '//table[@class="container_table"]/tbody/tr[1]//option[@selected="SELECTED"]'
            div = self.driver.find_element(By.XPATH, f'{self.consultant_info_xpath}{div_xpath}').get_attribute("value")

        return div
    
    def __format_office_id(self, oid: str) -> str:
        '''
        Formats the office ID by splitting the "-" inside the original office ID string.

        Returns the formated attributes, office ID and office location.
        '''
        # double pipes '||' indicate an issue with the office ID.
        if '||' in oid:
            full_oid = oid.split('||')

            # the following code checks very, very bad office ID inputs.
            # replaces non-digit characters in the office ID if it isn't a digit.
            if not full_oid[0].isdigit():
                for c in full_oid[0]:
                    if not c.isdigit():
                        full_oid[0] = full_oid[0].replace(c, '').strip('-')

            # looks for the dash '-' if it is within the first 2 characters of the string, if it is then replace it.
            loc_dash_pos = full_oid[1].find('-')
            if loc_dash_pos != -1 and not loc_dash_pos > 2:
                full_oid[1] = full_oid[1].replace('-', '', 1).strip('-')
        elif '-' in oid:
            full_oid = oid.split('-')
            
        oid = full_oid[0].strip()
        oid_location = full_oid[-1].strip()

        return oid, oid_location

    def __validate_email(self, email: str) -> str:
        try:
            tup = re.search('@', email).span()

            bad_chars = {'<', '>', '/', '\\', ']', '[', ':', ';', ' ', ':', '|', '?', '\t'}

            lp, rp = tup[0], tup[1]

            # hack fix. i cba.
            while email[lp] not in bad_chars and lp > 0:
                lp -= 1

            while email[rp] not in bad_chars and rp < len(email) - 1:
                rp += 1

        except AttributeError:
            email = 'TBD'
            
        return email[lp + 1 if email[lp] in bad_chars else lp:rp if email[rp] in bad_chars else rp + 1]
    
    def __format_project_id(self, pid):
        '''
        Checks the project ID and converts it to the correct format.

        Project IDs must be 10-11 characters long and must contain four 0s at the front of the project ID.

        In case of very bad errors, such as length > 11 or no project ID, then the RITM will be blacklisted.
        '''
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
                        pid = pid.replace('0', '', 1)
                        break
                else:
                    break

        if pid_prefix.match(pid[:4]):
            if pid_suffix.match(pid[4:]):
                return pid
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
                    return pid
                
    def validate_RITM(self) -> bool:
        '''Method used to check if the RITM is a valid RITM.

        If an incorrect RITM is inputted, an empty search page is found instead of the actual ticket page.
        
        Returns `False` if the RITM is valid.
        '''
        pass
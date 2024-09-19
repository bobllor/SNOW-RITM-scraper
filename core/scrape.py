from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.support.wait import WebDriverWait
import time

class ScrapeRITM:
    def __init__(self, driver, ritm: str):
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
        
        try:
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
        except ElementClickInterceptedException:
            # some issue with clicking the element, so instead reset back to the dashboard.
            print('   ERROR: Something went wrong with the search. Trying the process again.')
            self.driver.get('https://tek.service-now.com/nav_to.do?uri=%2F$pa_dashboard.do')
            time.sleep(5)
            self.search_ritm()

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

    def scrape_name(self) -> list:
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
        self.driver.find_element(By.XPATH, '//button[@name="viewr.sc_req_item.request.requested_for"]').click()
        time.sleep(2.5)
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
    
    # returns keys: email, e_id, division, c_id, company, o_id, p_id, org
    def scrape_user_info(self) -> dict:
        # list for these pieces of shit, they change the xpaths of normal builds.
        allegis_list = ["Aerotek", "Aston Carter", "Actalent"]

        temp = {}

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
        # what if a new customer puts the cid in the company name field instead?
        # this takes into account of idiots like JW who puts in the wrong input in the field.
        if self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{company_xpath}').get_attribute('value').isdigit():
            company_xpath = '//tr[22]//input[@class="cat_item_option sc-content-pad form-control"]'
            cid_xpath = '//tr[21]//input[@class="cat_item_option sc-content-pad form-control"]'

        email_xpath = '//tr[3]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'
        eid_xpath = '//tr[4]//div[@class="col-xs-12 form-field input_controls sc-form-field "]/input[1]'

        # consultant container, contains employee ID and email address
        consultant_xpaths = [('email', email_xpath), ('e_id', eid_xpath)]
        for key, xpath in consultant_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.consultant_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")

            temp[key] = part
        
        div_xpath = '//table[@class="container_table"]/tbody/tr[2]//option[@selected="SELECTED"]'
        div_value = self.driver.find_element(By.XPATH, f'{self.consultant_info_xpath}{div_xpath}').get_attribute("value")
        # depending on the selected division #, the xpath can either be tr[1] or tr[2].
        # if the value is empty, then try the other xpath instead.
        if div_value == '':
            div_xpath = '//table[@class="container_table"]/tbody/tr[1]//option[@selected="SELECTED"]'
            div_value = self.driver.find_element(By.XPATH, f'{self.consultant_info_xpath}{div_xpath}').get_attribute("value")
        temp['division'] = div_value

        # company container, contains company information (customer ID, company name, office ID)
        company_xpaths = [('c_id', cid_xpath), ('company', company_xpath), ('o_id', oid_xpath)]
        # append project ID if xpath if org is GS, other orgs removes the project ID field.
        if org == 'GS':
            pid_xpath = '//tr[7]//input[@class="cat_item_option sc-content-pad form-control"]'
            company_xpaths.append(('p_id', pid_xpath))
        
        for key, xpath in company_xpaths:
            element_xpath = self.driver.find_element(By.XPATH, f"{self.company_info_xpath}{xpath}")
            part = element_xpath.get_attribute("value")
            temp[key] = part.strip()
        
        # Not Listed creates two new fields for the office ID and location/name. 
        # user_info[5] is oid.
        if 'Not Listed' in self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{oid_xpath}').get_attribute('value'):
            oid_xpath = '//tr[25]//input[@class="cat_item_option sc-content-pad form-control"]'
            olocation_xpath = '//tr[26]//input[@class="cat_item_option sc-content-pad form-control"]'

            oid = self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{oid_xpath}').get_attribute('value')
            olocation = self.driver.find_element(By.XPATH, f'{self.company_info_xpath}{olocation_xpath}').get_attribute('value')

            temp['oid'] = f'{oid} - {olocation}'

        # changes the project ID if org is not GS
        if org in allegis_list:
            if org == "Actalent":
                org = "ACTALENT"
            # modifies division, company, PID
            temp['division'] = org
            temp['company'] = org
            temp['p_id'] = org
        elif org == 'Staffing':
            temp['p_id'] = 'TEKSTAFFING'

        temp['org'] = org
        
        # NOTE: bad employee IDs gets converted to TBD in class UserCreation.
        return temp
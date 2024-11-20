from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class Login:
    def __init__(self, driver, link, user, pw):
        self.driver = driver
        self.link = link
        self.user = user
        self.pw = pw
    
    def login_sn(self):
        '''
        Login into SNOW.
        '''
        self.driver.get(self.link)
        wait = WebDriverWait(self.driver, 10)
        time.sleep(5)
        
        # used in case login page is changed due to new SNOW instance.
        try:
            self.driver.switch_to.frame("gsft_main")
        except:
            pass

        wait.until(EC.presence_of_element_located((By.ID, "user_name"))).send_keys(self.user)
        wait.until(EC.presence_of_element_located((By.ID, "user_password"))).send_keys(self.pw)
        wait.until(EC.presence_of_element_located((By.ID, "sysverb_login"))).click()

        self.driver.switch_to.default_content()
        
        print("   Login complete.")
        time.sleep(8)
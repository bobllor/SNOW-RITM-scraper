from selenium.webdriver.common.by import By
import time

class Login:
    def __init__(self, driver, link, user, pw):
        self.driver = driver
        self.link = link
        self.user = user
        self.pw = pw
    
    def login_sn(self):
        self.driver.get(self.link)

        time.sleep(5)
        
        # used in case login page is changed due to new SNOW instance.
        try:
            self.driver.switch_to.frame("gsft_main")
        except:
            pass

        self.driver.find_element(By.ID, "user_name").send_keys(self.user)
        time.sleep(3)
        self.driver.find_element(By.ID, "user_password").send_keys(self.pw)
        time.sleep(5)
        self.driver.find_element(By.ID, "sysverb_login").click()

        self.driver.switch_to.default_content()
        
        print("   Login complete.")
        time.sleep(8)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from placeholder import Login, ScrapeRITM, UserCreation
from selenium.common.exceptions import NoSuchFrameException, NoSuchElementException
import menu, os, time, re
from acc import get_accs

if __name__ == '__main__':
    options = Options()
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)

    user, pw = get_accs()
    login_link = "https://tek.service-now.com/navpage.do"
    login = Login(driver, login_link, user, pw)
    print("\n   Logging in...")
    login.login_sn()
    os.system('cls')

    # search for an RITM ticket and scrape the info on the ticket
    # xpath for global search in order to enter the RITM number
    new_user_link = 'https://tek.service-now.com/nav_to.do?uri=%2Fsys_user.do%3Fsys_id%3D-1%26sys_is_list%3Dtrue%26sys_target%3Dsys_user%26sysparm_checked_items%3D%26sysparm_fixed_query%3D%26sysparm_group_sort%3D%26sysparm_list_css%3D%26sysparm_query%3DGOTO123TEXTQUERY321%3DDavid%2BKvachev%26sysparm_referring_url%3Dsys_user_list.do%3Fsysparm_query%3DGOTO123TEXTQUERY321%253DDavid%2BKvachev@99@sysparm_first_row%3D1%26sysparm_target%3D%26sysparm_view%3D'
    
    while True:
        choice = menu.main_menu()

        if choice == 'c':
            break
        
        os.system('cls')
        print("\n   ENTER AN RITM NUMBER")
        print("\n   Valid inputs: RITM1234567 | 1234567")
        ritm = input("\n   Enter an RITM to search: ")
        ritm_checker = re.compile(r'^([RITM]{4})([0-9]{7})\b')

        if ritm.isdigit():
            ritm = 'RITM' + ritm

        while True:
            os.system('cls')
            if ritm_checker.match(ritm):
                break
            else:
                print("\n   RITM number format is wrong.")
                print("\n   Valid inputs: RITM1234567 | 1234567")
                ritm = input("\n   Enter an RITM number: ")

        # TODO: make a try-except catch for bad RITM input
        print("\n   Searching for RITM...")
        scraper = ScrapeRITM(driver, ritm)

        # TODO: tie in with my fedex label maker
        # FedEx requirements: RITM, REQ, address, and name.
        if choice == 'a':
            print("\n   Work in progress")
            time.sleep(4)

            #print("Obtaining information for label creation...")
        
            '''req, name, address = scraper.scrape_ritm()
            # remove this later, used for debugging purposes
            print(f"{ritm} {req} {name} {address}")'''
        
        if choice == 'b':
            scraper.search_ritm()
            # TODO: implement logging for exceptions
            try:
                print("\n   Obtaining information for user creation...")
                name = scraper.scrape_name()
                user_info = scraper.scrape_user_info()
                # remove this later, used for debugging purposes
                print("   DEBUG:", user_info, name)
                time.sleep(2)
                print('   Complete.')
                    
                new_user = UserCreation(driver, new_user_link, user_info, name)
                print("\n   Starting user creation process.")
                time.sleep(3)
                new_user.create_user()
            except NoSuchElementException as nsee:
                print('\n   CRITICAL ERROR: An element cannot be found associated with the RITM ticket.')
                print(f'   {nsee}')
            except NoSuchFrameException as nsfe:
                print('\n   CRITICAL ERROR: No frame was found.')
                print(f'   {nsfe}')

        print ('   Returning back to menu.')
        input("\n   Press 'enter' to continue.")
        os.system('cls')

    # while loop exit
    driver.quit()
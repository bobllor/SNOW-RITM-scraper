from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from placeholder import Login, ScrapeRITM, UserCreation
from acc import get_accs

if __name__ == '__main__':
    # keep browser open until program terminates
    options = Options()
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)

    # main login logic to access SNOW
    user, pw = get_accs()
    login_link = "https://tek.service-now.com/navpage.do"
    login = Login(driver, login_link, user, pw)
    print("Logging in...")
    login.login_sn()

    # TODO: create a while loop
    # TODO: input to choose either user creation or label generation (WIP)
    # search for an RITM ticket and scrape the info on the ticket
    # xpath for global search in order to enter the RITM number
    new_user_link = 'https://tek.service-now.com/nav_to.do?uri=%2Fsys_user.do%3Fsys_id%3D-1%26sys_is_list%3Dtrue%26sys_target%3Dsys_user%26sysparm_checked_items%3D%26sysparm_fixed_query%3D%26sysparm_group_sort%3D%26sysparm_list_css%3D%26sysparm_query%3DGOTO123TEXTQUERY321%3DDavid%2BKvachev%26sysparm_referring_url%3Dsys_user_list.do%3Fsysparm_query%3DGOTO123TEXTQUERY321%253DDavid%2BKvachev@99@sysparm_first_row%3D1%26sysparm_target%3D%26sysparm_view%3D'
    
    while True:
        ritm = input("Enter an RITM number: ")
        print("Searching for RITM...")
        scraper = ScrapeRITM(driver, ritm)
        scraper.search_ritm()

        req, name, address = scraper.scrape_ritm()
        print("Obtaining information for label creation...")
        # remove this later, used for debugging purposes
        print(f"{ritm} {req} {name} {address}")

        user_info = scraper.scrape_user_info()
        print("Obtaining information for user creation...")
        # remove this later, used for debugging purposes
        print(user_info)

        input("Enter 'enter' to continue")
        
        new_user = UserCreation(driver, new_user_link, user_info, name)
        print("Creating new user...")
        new_user.format_office_id()
        new_user.create_user()

        input("Enter 'enter' to continue.")

    driver.quit()
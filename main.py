from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from placeholder import Login, ScrapeRITM
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
    login.login_sn()

    # search for an RITM ticket and scrape the info on the ticket
    # TODO: create a proper loop, for now keep break
    # xpath for global search in order to enter the RITM number
    search_xpath = '//input[@name="sysparm_search"]'
    while True:
        ritm = input("Enter an RITM number: ")
        scraper = ScrapeRITM(driver, ritm, search_xpath)
        scraper.search_ritm()

        req, name, address = scraper.scrape_ritm()

        # remove this later, used for debugging purposes
        print(f"{ritm} {req} {name} {address}")

        input("Enter any key to continue")
        break

    driver.quit()

# About the Project

SNOW RITM scraper which takes an RITM ticket number and scrapes the information from the ticket, returning back information that the user can use through Selenium.

<font color="red">***WARNING:***</font> This is tested on a company-specific instance of Service Now. It is currently unknown if other instances will work the same way.

## Features:
Automatically scrapes RITM tickets for information, which include name, address, organization information, and more.

Automatically generates a user with the scraped information (however it requires manual interaction to complete).

WIP: Automatically generate a FedEx label based on the RITM chosen.

## Getting Started

Requires selenium and dotenv.

pip install:
```
pip install selenium
pip install python-dotenv
```

If there are issues regarding Windows OS:
```
python -m pip install selenium
python -m pip install python-dotenv
```



1. Replace the values inside .env_sample.txt
2. Rename .env_sample.txt to .env
3. WIP


## 

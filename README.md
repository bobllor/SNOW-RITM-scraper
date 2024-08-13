# About the Project

SNOW RITM scraper which takes an RITM ticket number and scrapes the information from the ticket, returning back information that the user can use through Selenium.

<font color="#AA4A44">***WARNING:***</font> This is tested on a company-specific instance of Service Now. It is currently unknown if other instances will work the same way.

## Features:
Automatically scrapes RITM tickets for information, which include name, address, organization information, and more.

Automatically generates a user with the scraped information (however it requires manual interaction to complete).

WIP: Automatically generate a FedEx label based on the RITM chosen.

## Getting Started

Requires selenium and dotenv.

### Prerequisites

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

### Installation

1. Clone the repo
   ```
   git clone https://github.com/bobllor/SNOW-RITM-scraper
   ```
2. Install required libraries
3. Enter the username and password in .env_sample.txt.
   ```
   sn_u = "ENTER_USERNAME_HERE"
   sn_p = "ENTER_PASSWORD_HERE"
   ```
4. Remove _sample.txt from .env_sample.txt
5. Run main.py

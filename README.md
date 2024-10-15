# About the Project

SNOW user creation automation uses Selenium to automate the creation of users to add into the TEKSystem's database.

It scans the taskboard for any tickets that is added to the board, scrape the user information of the ticket, and then fills in the fields required to create the user.

<font color="#AA4A44">***WARNING:***</font> This is tested on a company-specific instance of Service Now- TEKSystem's. It is currently unknown if other instances will work the same way.

# Features

Automatically scrapes RITM tickets for information, which include name, address, organization information, and more- by scanning the taskboard of which the tickets arrive on.

Automatically creates a user with the information obtained from the ticket.

It handles any errors that occur during user creation, which includes existing users, invalid email address, invalid company name, and invalid project ID.

In case of a critical failure due to a bad input (thanks to the people who fill out the information to begin with...) then the ticket will be blacklisted- which requires manual interaction to fix.

## Upcoming Features

1. Link the FedEx label generator to automatically create the label without needing any manual input.
2. Add manual RITM input, if automatic is not your mojo.
3. Close out RITMs with a manual input.

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

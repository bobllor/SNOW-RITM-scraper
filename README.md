# About the Project

SNOW user creation automation uses Selenium to automate the creation of users to add into the ServiceNow database.

It scans the taskboard for any tickets that is added to the board, scrape the user information of the ticket, and then fills in the fields required to create the user.

<font color="#AA4A44">***WARNING:***</font> This is tested on a company-specific instance of ServiceNow. It is currently unknown if other instances will work the same way.

# Features

Automatically scrapes RITM tickets for information, which include name, address, organization information, and more- by scanning the taskboard of which the tickets arrive on.

Automatically creates a user with the information obtained from the ticket.

It handles any errors that occur during user creation, which includes existing users, invalid email address, invalid company name, and invalid project ID.

In case of a critical failure due to a bad input (thanks to the people who fill out the information to begin with...) then the ticket will be blacklisted- which requires manual interaction to fix.

## Upcoming Features

1. Link the FedEx label generator to automatically create the label without needing any manual input.
2. Close out RITMs with a manual input.
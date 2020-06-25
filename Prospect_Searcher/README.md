# Prospect Searcher
The purpose of this tool is to be able to efficiently gain information on businesses such as social media status
and contact information. This is done by using a google search with multiple fetches and scraping the results.

## Getting Started
Instructions on how to setup and use this tool.

1. Install [Python 3](https://www.python.org/downloads/)
1. Download this repository from [GitHub](https://github.com/bacon1097/WebSpred_Tools)
1. Obtain the ```creds.json``` file from Benjamin Brunyee
1. Unzip file if you're on Windows
1. Open a terminal
    * Mac ```terminal (bash)```
    * Windows ```cmd```
1. Verify you have Python 3 with:
    * Mac ```python3 --version```
    * Windows ```python --version```
1. ```cd``` into the directory of your downloaded version of this project.
    * Mac & Windows ```cd Downloads/WebSpred_Tools-master/Tools``` (default directory)
    * Mac & Windows ```cd Downloads/WebSpred_Tools/Tools``` (default directory)
1. Install all python dependencies
    * Mac & Windows ```pip3 install xlwt beautifulsoup4 gspread oauth2client requests```
1. Run your application by double clicking on ```Prospect_Searcher.pyw```

## Options
* ```Search Term``` = The search query you want to throw to Google.
* ```Number of results``` = The number of results you want to return. The higher the number, the longer it will take.
* ```Timeframe``` = Valid options are: day, week or month. This will only get results of websites that have been
uploaded to google in the recent time-frame. This is good for finding new businesses.
* ```Get social information``` = Whether to get social information such as Facebook & Instagram.
* ```Save information``` = Saves to Google sheet. Saves to excel sheet.

## Additional Information
Logs are saved in a file called ```./logs/Prospect_Searcher.log```. If the program fails. Do not delete this log as it will
be useful for debugging and providing fixes.

This repository contains a file called ```test.js```, ignore this file for the moment as it is not fully
functioning.

## Author
**Ben Brunyee** - [bacon1097](https://github.com/bacon1097)
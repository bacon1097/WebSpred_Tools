# Prospect Searcher
The purpose of this tool is to be able to efficiently gain information on businesses such as social media status
and contact information. This is done by using a google search with multiple fetches and scraping the results.

## Getting Started
Instructions on how to setup and use this tool.

1. Install [Python3](https://www.python.org/downloads/)
1. Download this repository from [GitHub](https://github.com/bacon1097/WebSpred_Tools)
1. Unzip file
1. Open a terminal
    * Mac ```terminal (bash)```
    * Windows ```cmd```
1. ```cd``` into the directory of your downloaded version of this project.
    * Mac & Windows ```cd Downloads/WebSpred_Tools/Tools``` (default directory)
1. Install all python dependencies
    * Mac & Windows ```pip3 install xlwt beautifulsoup4```
1. Run your application with appropriate options
    * Mac & Windows ```python Prospect_Searcher.py --searchTerm gym --results 10 --socials True --time m```

## Command Line Options
* ```--searchTerm | -s``` = The search query you want to throw to Google.
* ```--results | -r``` = The number of results you want to return (The higher the number, the longer it will take).
* ```--time | -t``` = Valid options are:"d", "w", "m" for day, week, month. This will only get results of websites
that have been uploaded to google in the recent time-frame. (Good for finding new businesses).
* ``` --socials | -o``` = Whether to get social information such as Facebook & Instagram.

## Additional Information
Logs are saved in a file called ```Prospect_Searcher.log```. If the script fails. Do not delete this log as it will
be useful for debugging and providing fixes.

This repository contains a file called ```test.js```, ignore this file for the moment as it is not fully
functioning.

## Author
**Ben Brunyee** - [bacon1097](https://github.com/bacon1097)
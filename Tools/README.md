# Prospect Searcher
The purpose of this tool is to be able to efficiently gain information on businesses such as social media status
and contact information. This is done by using a google search with multiple fetches and scraping the results.

## Getting Started
Instructions on how to setup and use this tool.

1. Install [NodeJS](https://nodejs.org/en/)
1. Download this repository from [GitHub]()
1. Open a terminal
    * Mac ```terminal (bash)```
    * Windows ```cmd```
1. ```cd``` into the directory of your downloaded version of this project.
    * Mac & Windows ```cd Downloads/WebSpred_Tools/Tools``` (default directory)
1. Install all dependencies
    * Mac & Windows ```npm install```
1. Run your application with appropriate options
    * Mac & Windows ```node Prospect_Searcher.js --seachTerm gym --results 10```

## Command Line Options

* ```--searchTerm``` = The search query you want to throw to Google.
* ```--results``` = The number of results you want to return (The higher the number, the longer it will take).
* ```--time``` = Valid options are:"d", "w", "m" for day, week, month. This will only get results of websites
that have been uploaded to google in the recent time-frame. (Good for finding new businesses).

## Author

**Ben Brunyee** - [bacon1097](https://github.com/bacon1097)
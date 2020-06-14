#------------------------------------------------------------------------------------#
# Modules
#------------------------------------------------------------------------------------#

import requests, argparse, re, json, xlwt, os
import logging as log
from bs4 import BeautifulSoup
from googlesearch import search
from googleapiclient.discovery import build

#------------------------------------------------------------------------------------#
# Variables & Config
#------------------------------------------------------------------------------------#

log.basicConfig(level=log.DEBUG, format="%(levelname)s : %(asctime)s : %(message)s", datefmt="%I:%M:%S %p")
parser = argparse.ArgumentParser()
parser.add_argument("--search", "-s", metavar="STRING", required=True, help="Enter a search term")
parser.add_argument("--results", "-r", metavar="INT", required=False, type=int, default=4, help="How " +\
  "many results do you want. Up to 100")
parser.add_argument("--time", "-t", metavar="STRING", required=False, help="Returns google indexes " +\
  "a certain perdiod. d = past day, w = past week, m = past month")
parser.add_argument("--socials", "-o", metavar="BOOLEAN", required=False, help="Whether to return social " +\
  "information or not (True/False)", default="True")
args = parser.parse_args()

if (args.results is not None):
  if (int(args.results) > 100):
    log.info("Cannot get more than 100 results, will return the max")
    args.results = 100
else:
  log.info("No number of results specified, will retrieve 10")
  args.results = 10

searchString = args.search
results = args.results
time = args.time
socialsFlag = args.socials

#------------------------------------------------------------------------------------#
# Process list for the script
#------------------------------------------------------------------------------------#

def Main():
  log.info(f"Getting google search results for {searchString}")
  links = GetGoogleResults(searchString, results, time)
  links = GetUnique(links)[:results]    # Only use the number of results requested
  infoArray = []
  for link in links:
    log.info(f"Getting information on {link}")
    info = GetInfo(link)
    log.debug("Appending to array: " + str(info))
    infoArray.append(info)
  log.info(json.dumps(infoArray, indent=4))
  while True:
    response = int(input("What would you like to do with this information?\n" +
      "1. Save to .xls file\n" +
      "2. Save to .txt file\n" +
      "3. Send emails\n" +
      "4. Exit\n"))
    if (response == 1):
      ExportXls(infoArray)
      break
    elif (response == 2):
      break
    elif (response == 3):
      break
    elif (response == 4):
      break
    else:   # If response is not a valid response
      continue

#------------------------------------------------------------------------------------#
# Export information to xls file
#------------------------------------------------------------------------------------#

def ExportXls(data, fileName="Prospects.xls"):
  bold = xlwt.easyxf("font: bold on")

  book = xlwt.Workbook()
  sheet = book.add_sheet("Prospects")

  # Titles
  titles = [
    "Prospect",
    "Website",
    "Contact Page",
    "Contact Email",
    "Contact Number",
    "Facebook Page Link",
    "Facebook Page Name",
    "Facebook Likes",
    "Facebook Followers",
    "Instagram Page Link",
    "Instagram Username",
    "Instagram Followers",
    "Instagram Following"
  ]

  # Write titles to file
  counter = 0
  for title in titles:
    sheet.write(0, counter, title, bold)
    sheet.col(counter).width = 6000
    counter += 1

  rowCounter = 1
  na = "N/A"    # Identifier for empty data values
  for prospect in data:   # Every loop = next row
    companyName = list(prospect.keys())[0]
    sheet.write(rowCounter, 0, companyName)

    prospectData = prospect[companyName]
    if (prospectData["result"] == "success"):
      for key in prospectData:    # Every loop = different column
        if (key == "website"):
          sheet.write(rowCounter, 1, prospectData[key])
        elif (key == "Contact Info"):
          if (prospectData[key]["result"] == "success"):
            if (prospectData[key]["link"]):
              sheet.write(rowCounter, 2, prospectData[key]["link"])
            else:
              sheet.write(rowCounter, 2, na)

            if (prospectData[key]["email"]):
              sheet.write(rowCounter, 3, prospectData[key]["email"])
            else:
              sheet.write(rowCounter, 3, na)

            if (prospectData[key]["number"]):
              sheet.write(rowCounter, 4, prospectData[key]["number"])
            else:
              sheet.write(rowCounter, 4, na)
          else:
            for i in range(3):
              counter = i + 2
              sheet.write(rowCounter, counter, na)
        elif (key == "Facebook Page"):
          if (prospectData[key]["result"] == "success"):
            if (prospectData[key]["link"]):
              sheet.write(rowCounter, 5, prospectData[key]["link"])
            else:
              sheet.write(rowCounter, 5, na)

            if (prospectData[key]["page name"]):
              sheet.write(rowCounter, 6, prospectData[key]["page name"])
            else:
              sheet.write(rowCounter, 6, na)

            if (prospectData[key]["likes"]):
              sheet.write(rowCounter, 7, prospectData[key]["likes"])
            else:
              sheet.write(rowCounter, 7, na)

            if (prospectData[key]["followers"]):
              sheet.write(rowCounter, 8, prospectData[key]["followers"])
            else:
              sheet.write(rowCounter, 8, na)
          else:
            for i in range(4):
              counter = i + 5
              sheet.write(rowCounter, counter, na)
        elif (key == "Instagram Page"):
          if (prospectData[key]["result"] == "success"):
            if (prospectData[key]["link"]):
              sheet.write(rowCounter, 9, prospectData[key]["link"])
            else:
              sheet.write(rowCounter, 9, na)

            if (prospectData[key]["username"]):
              sheet.write(rowCounter, 10, prospectData[key]["username"])
            else:
              sheet.write(rowCounter, 10, na)

            if (prospectData[key]["followers"]):
              sheet.write(rowCounter, 11, prospectData[key]["followers"])
            else:
              sheet.write(rowCounter, 11, na)

            if (prospectData[key]["following"]):
              sheet.write(rowCounter, 12, prospectData[key]["following"])
            else:
              sheet.write(rowCounter, 12, na)
          else:
            for i in range(4):
              counter = i + 9
              sheet.write(rowCounter, counter, na)

    else:
      for i in range(13):
        sheet.write(rowCounter, i, na)
    rowCounter += 1

  # Save file
  try:
    book.save(fileName)
    log.info(f"{fileName} has been saved")
  except Exception as e:
    log.error(e)

#------------------------------------------------------------------------------------#
# Get websites from google
#------------------------------------------------------------------------------------#

def GetGoogleResults(searchString, results=10, time=""):
  googleUrl = f"https://www.google.com/search?q={searchString}&num=100"
  if (time == "d" or time == "w" or time == "m"):
    googleUrl += f"&as_qdr={time}"
  r = requests.get(googleUrl)
  soup = BeautifulSoup(r.text, "html.parser")

  websites = []
  for site in soup.select("a > h3"):
    log.debug(site.parent["href"])
    site = re.sub(r"^/url\?q=", "", site.parent["href"])
    site = re.sub(r"((\.com)|(\.co\.uk)|(\.org(\.uk)?)|(\.uk)).*", r"\1", site)
    log.debug(site)
    if (re.search(r"^http", site)):
      websites.append(site)
  log.debug("List of websites from Google: " + str(websites))
  return websites

#------------------------------------------------------------------------------------#
# Get unique links
#------------------------------------------------------------------------------------#

def GetUnique(links):
  correctedArray = []
  for link in links:
    link = re.sub(r"((\.com)|(\.co\.uk)|(\.org(\.uk)?)|(\.uk)|(\.co)).*", r"\1", link)
    correctedArray.append(link)
  correctedArray = list(dict.fromkeys(correctedArray))    # Parse to a dict and then make another array
  return correctedArray

#------------------------------------------------------------------------------------#
# Get standard information from the webpage (Contact Info, Social media accounts)
#------------------------------------------------------------------------------------#

def GetInfo(link):
  info = {        # Set basic info for each website
    "Facebook Page": {},
    # "Twitter Page": {}, Disabling Twitter as it has problems
    "Instagram Page": {},
    "Contact Info": {},
    "website": link,
    "result": "failed"
  }
  soup = ""
  try:
    soup = BeautifulSoup(requests.get(info["website"]).text, "html.parser")
    info["result"] = "success"
  except Exception as e:
    log.error(e)
    return info

  if (socialsFlag.lower() != "false"):
    # Find facebook webpage
    facebook = soup.find_all('a', href=re.compile(r"facebook\.com\/(?!sharer)"))
    if (facebook):
      info["Facebook Page"] = CheckFacebook(str(facebook[0]["href"]))
    else:
      info["Facebook Page"]["msg"] = "Could not find page"
      info["Facebook Page"]["result"] = "failed"

    # Disabling Twitter as it has run into problems
    # Find twitter webpage
    # twitter = soup.find_all('a', href=re.compile(r"twitter\.com\/(?!intent)"))
    # if (twitter):
    #   info["Twitter Page"] = CheckTwitter(str(twitter[0]["href"]))
    # else:
    #   info["Twitter Page"]["msg"] = "Could not find page"
    #   info["Twitter Page"]["result"] = "failed"

    # Find instagram webpage
    instagram = soup.find_all('a', href=re.compile(r"instagram\.com\/.*"))
    if (instagram):
      info["Instagram Page"] = CheckInsta(str(instagram[0]["href"]))
    else:
      info["Instagram Page"]["msg"] = "Could not find page"
      info["Instagram Page"]["result"] = "failed"

  # Find contact page
  contactPage = soup.find_all('a', text=re.compile(r"contact", re.IGNORECASE))
  if (contactPage):
    try:
      contactLink = info["website"] + "/" + re.sub(r"((.*?)\/\/(.*?)\/)|^\/", r"", str(contactPage[0]["href"]))       # Obtain contact link
      info["Contact Info"] = GetContactInfo(contactLink)
    except Exception as e:
      info["Contact Info"] = "failed"
      log.error(e)
      pass
  else:
    info["Contact Info"] = "failed"
  companyName = re.sub(r"^.*?//", "", link)
  companyName = re.sub(r"^.*?www\.", "", companyName)
  companyName = re.sub(r"\..*$", "", companyName)
  info = {companyName: info}    # Assign the object the company name as an identifier
  return info

#------------------------------------------------------------------------------------#
# Get details from their facebook account
#------------------------------------------------------------------------------------#

def CheckFacebook(link):
  info = {
    "result": "failed",
    "link": "",
    "likes": 0,
    "followers": 0,
    "page name": "",
  }
  soup = ""

  try:
    soup = BeautifulSoup(requests.get(link).text, "html.parser")
    info["link"] = link
    info["result"] = "success"
  except Exception as e:
    info["result"] = "failed"
    log.error(e)
    return info

  # Get likes of facebook page
  likes = soup.find(text=re.compile(r"people like this"))
  if (likes):
    likes = re.sub(r"(\d)\s.*", r"\1", likes)        # Remove the characters after the last digit
    info["likes"] = int(re.sub(r"\D", "", likes))

  # Get followers of facebook page
  followers = soup.find(text=re.compile(r"people follow this"))
  if (followers):
    followers = re.sub(r"(\d)\s.*", r"\1", followers)       # Remove the characters after the last digit
    info["followers"] = int(re.sub(r"\D", "", followers))

  try:
    pageName = soup.find("h1").find("span")
    if (pageName):
      info["page name"] = pageName.text
  except Exception:
    pass
  return info

#------------------------------------------------------------------------------------#
# Get details from their twitter account
#------------------------------------------------------------------------------------#

def CheckTwitter(link):
  info = {
    "result": "failed",
    "followers": 0,
    "following": 0,
    "link": "",
    "username": ""
  }
  soup = ""

  try:
    soup = BeautifulSoup(requests.get(link).text, "html.parser")
    info["result"] = "success"
  except Exception as e:
    info["result"] = "failed"
    log.error(e)
    return info

  print(requests.get(link).text)

  try:
    pageName = soup.find_all("h2")[2].find("b")
    if (pageName):
      info["username"] = pageName.text
  except Exception:
    pass

  try:
    following = soup.find("a", href=re.compile(r"following")).find("span", {"data-count": re.compile(r".*")})
    if (following):
        info["following"] = int(re.sub(r"\D", "", following["data-count"]))
  except Exception:
    pass

  try:
    followers = soup.find("a", href=re.compile(r"followers")).find("span", {"data-count": re.compile(r".*")})
    if (followers):
        info["followers"] = int(re.sub(r"\D", "", followers["data-count"]))
  except Exception:
    pass
  return info

#------------------------------------------------------------------------------------#
# Get details from their instagram account
#------------------------------------------------------------------------------------#

def CheckInsta(link):
  info = {
    "result": "failed",
    "followers": 0,
    "following": 0,
    "link": "",
    "username": ""
  }
  soup = ""

  try:
    soup = BeautifulSoup(requests.get(link).text, "html.parser")
    info["link"] = link
    info["result"] = "success"
  except Exception as e:
    info["result"] = "failed"
    log.error(e)
    return info

  # Check if page exists
  exists = soup.find("h2", text=re.compile(r"Sorry, this page isn't available."))
  if (exists):
    info["result"] = "failed"
    log.error("Page does not exist")
    return info

  # Get username of account
  username = soup.find("title")
  if (username):
    username = re.sub(r"^.*@", "", username.text.strip())        # Regex out everything except identifier
    username = re.sub(r"\).*$", "", username)
    info["username"] = username

  following = 0
  followers = 0
  try:
    followData = soup.find_all("script", {"type": "text/javascript"})[3]
    followData = re.sub(r";$", "", followData.text)
    followData = re.sub(r"^.*?=\s", "", followData)
    followData = json.loads(followData)
    followers = followData["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_followed_by"]["count"]
    following = followData["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_follow"]["count"]

    if (following):
      info["following"] = int(re.sub(r"\D", "", str(following)))

    if (followers):
      info["followers"] = int(re.sub(r"\D", "", str(followers)))
  except Exception:
    pass
  return info

#------------------------------------------------------------------------------------#
# Get contact details such as phone number and email address
#------------------------------------------------------------------------------------#

def GetContactInfo(contactLink):
  info = {
    "number": 0,
    "email": "",
    "link": "",
    "result": "failed"
  }

  # Get link html data
  r = requests.get(contactLink)
  soup = ""
  try:
    soup = BeautifulSoup(r.text, "html.parser")
    info["link"] = contactLink
    info["result"] = "success"
  except Exception as e:
    log.error(e)
    return info

  # Example number 01202 123456 | 01202 123 456 | 01202123456
  contactNumbers = soup.find_all(text=re.compile(r".*\d[\d\s]{10,12}.*"))

  # Try to get a contact number
  if (contactNumbers):
    for number in contactNumbers:
      number = re.sub(r"\D", "", number.strip())
      if (len(number) == 11):
        info["number"] = number[:5] + " " + number[5:]

  # Get email
  for elem in soup.select("body > *"):
    if (elem.text):
      match = re.search(r"\s(\w+@\w+[\.\w]+)\s", elem.text)
      if (match):
        info["email"] = match.group(1)
  return info

Main()
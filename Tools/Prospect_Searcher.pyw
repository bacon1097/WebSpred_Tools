#------------------------------------------------------------------------------------#
# Modules
#------------------------------------------------------------------------------------#

import requests, argparse, re, json, xlwt, os, threading, logging, gspread, time
import tkinter as tk
from bs4 import BeautifulSoup
from queue import Queue
from oauth2client.service_account import ServiceAccountCredentials
from gspread.models import Cell
from Application import Application

#------------------------------------------------------------------------------------#
# Variables & Config
#------------------------------------------------------------------------------------#

sh = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s : %(asctime)s : %(message)s", datefmt="%I:%M:%S %p")
sh.setFormatter(formatter)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(sh)

try:
  os.mkdir("./log")
  log.info("Created directory")
except FileExistsError:
  log.error("Directory already exists")
  pass
except Exception as err:
  log.critical("Could not create log directory")
  raise err

fh = logging.FileHandler("./log/Prospect_Searcher.log", "w")
fh.setFormatter(formatter)
log.addHandler(fh)

searchString = results = timeframe = socialsFlag = followUpOption = None

#------------------------------------------------------------------------------------#
# Get values from GUI
#------------------------------------------------------------------------------------#

def Init(reqSearchString=None, reqSocials=None, reqResults=None, reqTimeframe=None, reqSave=None):
  """Gets values from GUI and validates them and then runs program"""

  global results, searchString, timeframe, socialsFlag, followUpOption

  try:
    int(reqResults)
    reqResults = int(reqResults)
  except Exception:
    log.critical("Could not parse results to get as an integer")
    raise Exception

  try:
    int(reqSave)
    reqSave = int(reqSave)
  except Exception:
    log.critical("Could not parse save input as an integer")
    raise Exception

  try:
    ConvertToBool(reqSocials)
    socialsFlag = ConvertToBool(reqSocials)
  except Exception:
    log.critical("Save to socials option is not a boolean")
    raise Exception

  if (reqResults > 100):
    reqResults = 100
  elif (reqResults < 1):
    log.critical("Results requested is less that 1")
    raise Exception
  results = reqResults

  if (not (reqTimeframe == "d" or reqTimeframe == "w" or reqTimeframe == "m" or reqTimeframe == "anytime")):
    log.critical("Invalid timeframe option")
    raise Exception
  else:
    timeframe = reqTimeframe

  if (not (reqSave >= 1 and reqSave <= 3)):
    log.critical("Invalid save option")
    raise Exception
  else:
    followUpOption = reqSave

  searchString = reqSearchString

  Main()

#------------------------------------------------------------------------------------#
# Process list for the script
#------------------------------------------------------------------------------------#

def Main():
  """Execute Main() to run the program"""

  log.info(f"Getting google search results for {searchString}")
  links = GetGoogleResults(searchString, results, timeframe)
  links = GetUnique(links)[:results]    # Only use the number of results requested
  infoArray = []
  threadArray = []
  que = Queue()

  for link in links:
    log.info(f"Getting information on {link}")
    # info = GetInfo(link)
    thread = threading.Thread(target=lambda q, arg1: q.put(GetInfo(arg1)),   # Create a thread and put the result to a queue
      args=(que, link), daemon=True)
    log.debug("Added new thread for: " + link)
    thread.start()
    threadArray.append(thread)
    log.debug("Number of active threads: " + str(threading.activeCount()))

  for thread in threadArray:    # Wait for all threads to complete
    thread.join()
    log.debug("Thread joined. New number of active threads: " + str(threading.active_count()))

  log.debug("All threads complete")
  log.debug("New number of active threads: " + str(threading.active_count()))

  while not que.empty():    # Append all information gathered by threads to an array
    info = que.get()
    log.debug("Appending to array: " + str(info))
    infoArray.append(info)

  log.info(json.dumps(infoArray, indent=4))

  response = 0
  if (not followUpOption):
    while True:
        try:
          response = int(input("What would you like to do with this information?\n" +
            "1. Save to .xls file\n" +
            "2. Save to Google Drive sheets (Master Prospects)\n" +
            "3. Exit\n"))
          break
        except Exception:
          log.error("Invalid response entered: " + str(response))
  else:
    response = followUpOption
  log.debug("Using response: " + str(response))
  if (response == 1):
    fileName = ""
    if (not followUpOption):
      fileName = input("Enter name of file to be saved (Default = 'Prospects.xls')\n")
    if (fileName):
      fileName = re.sub(r"\.xls$", "", fileName.strip())
      fileName += ".xls"
    else:
      fileName = "Prospects.xls"
    log.debug(f"Saving information to {fileName}")
    ExportXls(infoArray, fileName)
    log.info(f"{fileName} has been saved")
  elif (response == 2):
    log.debug("Saving information to Google")
    SaveToGoogle(infoArray)
    log.info("Saved info to Google Sheets")
  elif (response == 3):
    pass
  else:   # If response is not a valid response
    pass

#------------------------------------------------------------------------------------#
# Converts a string to bool
#------------------------------------------------------------------------------------#

def ConvertToBool(val):
  if (val.lower() == "true"):
    val = 1
  elif (val.lower() == "false"):
    val = 0
  else:
    log.critical("Could not convert string to bool: " + str(val))
    raise Exception
  return bool(val)

#------------------------------------------------------------------------------------#
# Save to Google Sheets
#------------------------------------------------------------------------------------#

def SaveToGoogle(data):
  """Saves data to Google Sheets"""

  # Configure
  scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
  creds = None

  try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)   # Ensure that creds.json file exists
  except FileNotFoundError as err:
    log.critical("Could not find 'creds.json' file for connecting to Google")
    raise err
  except Exception as err:
    log.critical("Could not authorize with 'creds.json' file")
    raise err

  client = gspread.authorize(creds)   # Authorize with credentials

  masterSheet = client.open("Master Prospects").sheet1    # Get sheet to input values into
  usedSheet = client.open("Master Sent Emails").sheet1 # Get sheet of email addresses that have been used

  # Read all data
  savedEmails = masterSheet.get_all_records()
  usedEmails = usedSheet.get_all_records()

  invalidEmails = []
  invalidProspects = []
  for row in savedEmails:
    email = ""
    prospect = ""
    try:
      email = row["Contact Email"]
    except KeyError:
      log.error("'Contact Email' does not exist in 'Master Prospects'")
    try:
      prospect = row["Prospect"]
    except KeyError:
      log.error("'Prospect' does not exist in 'Master Prospects'")
    if (email and email != "N/A"):
      invalidEmails.append(email)
    if (prospect and prospect != "N/A"):
      invalidProspects.append(prospect)

  # Format and write data to Google Sheets
  for row in usedEmails:
    email = ""
    prospect = ""
    try:
      email = row["Email"]
    except KeyError:
      log.error("'Email' does not exist in 'Master Sent Emails'")
    try:
      prospect = row["Prospect"]
    except KeyError:
      log.error("'Prospect' does not exist in 'Master Prospects'")
    if (email and email != "N/A"):
      invalidEmails.append(email)
    if (prospect and prospect != "N/A"):
      invalidProspects.append(prospect)

  # Weed out duplicates by getting every element in data gathered and checking if the email is not in
  # array of invalid emails
  filteredData = [e for e in data if ("email" in e[list(e.keys())[0]]["Contact Info"] and \
    e[list(e.keys())[0]]["Contact Info"]["email"] not in invalidEmails)]    # Filter out by email
  filteredData = [e for e in data if (list(e.keys())[0] not in invalidProspects)]   # Filter out by prospect name

  availableRow = len(list(filter(None, masterSheet.col_values(1)))) + 1   # Get first empty row in sheet
  masterSheet.resize(rows=masterSheet.row_count + 100)   # Add 100 rows on every script run

  # Write data
  na = "N/A"    # Identifier for empty data values
  cells = []    # Put all data in an array to make 1 write call
  for elem in filteredData:
    prospect = list(elem.keys())[0]
    log.debug("Next available row: " + str(availableRow))
    log.debug(f"Saving: {prospect} to Google Sheets")

    cells.append(Cell(availableRow, 1, prospect))
    prospectData = elem[prospect]
    if (prospectData["result"] == "success"):
      cells.append(Cell(availableRow, 2, prospectData["website"]))
      if (prospectData["Contact Info"]["result"] == "success"):
        link = prospectData["Contact Info"]["link"] if (prospectData["Contact Info"]["link"]) else na
        cells.append(Cell(availableRow, 3, link))

        email = prospectData["Contact Info"]["email"] if (prospectData["Contact Info"]["email"]) else na
        cells.append(Cell(availableRow, 4, email))

        number = prospectData["Contact Info"]["number"] if (prospectData["Contact Info"]["number"]) else na
        cells.append(Cell(availableRow, 5, number))
      else:
        for i in range(3):
          cells.append(Cell(availableRow, i + 3, na))

      if (socialsFlag):
        if (prospectData["Facebook Page"]["result"] == "success"):
          link = prospectData["Facebook Page"]["link"] if (prospectData["Facebook Page"]["link"]) else na
          cells.append(Cell(availableRow, 6, link))

          pageName = prospectData["Facebook Page"]["page name"] if (prospectData["Facebook Page"]["page name"]) else na
          cells.append(Cell(availableRow, 7, pageName))

          likes = prospectData["Facebook Page"]["likes"] if (prospectData["Facebook Page"]["likes"]) else na
          cells.append(Cell(availableRow, 8, likes))

          followers = prospectData["Facebook Page"]["followers"] if (prospectData["Facebook Page"]["followers"]) else na
          cells.append(Cell(availableRow, 9, followers))
        else:
          for i in range(4):
            cells.append(Cell(availableRow, i + 6, na))

        if (prospectData["Instagram Page"]["result"] == "success"):
          link = prospectData["Instagram Page"]["link"] if (prospectData["Instagram Page"]["link"]) else na
          cells.append(Cell(availableRow, 10, link))

          username = prospectData["Instagram Page"]["username"] if (prospectData["Instagram Page"]["username"]) else na
          cells.append(Cell(availableRow, 11, username))

          followers = prospectData["Instagram Page"]["followers"] if (prospectData["Instagram Page"]["followers"]) else na
          cells.append(Cell(availableRow, 12, followers))

          following = prospectData["Instagram Page"]["following"] if (prospectData["Instagram Page"]["following"]) else na
          cells.append(Cell(availableRow, 13, following))
        else:
          for i in range(4):
            cells.append(Cell(availableRow, i + 10, na))
      else:
        for i in range(8):
          cells.append(Cell(availableRow, i + 6, na))
    else:
      for i in range(12):
        cells.append(Cell(availableRow, i + 2, na))
    availableRow += 1

  if (len(cells) != 0):
    while True:
        try:
          masterSheet.update_cells(cells)    # Write the data to the next available row
          break
        except gspread.exceptions.APIError as err:   # Error when API quota max has been reached
          log.error(err)
          log.error("Error occurred, waiting 10 seconds")
          time.sleep(10)
        except Exception as err:
          log.critical(err)
          log.critical("Undefined error, speak to Ben Brunyee")
          raise err
  else:
    log.info("Cells are empty: " + str(cells))

#------------------------------------------------------------------------------------#
# Update a cell in google sheets
#------------------------------------------------------------------------------------#

def update_cell(sheet, row, column, data):
  """Will update a cell in a Google Sheets document"""

  while True:
    try:
      sheet.update_cell(row, column, data)
      break
    except gspread.exceptions.APIError as err:
      log.error(err)
      log.error("Error occurred, waiting 10 seconds")
      time.sleep(10)

#------------------------------------------------------------------------------------#
# Export information to xls file
#------------------------------------------------------------------------------------#

def ExportXls(data, fileName="Prospects.xls"):
  """Saves data to an Excel sheet"""

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
          if (socialsFlag):
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
          if (socialsFlag):
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
        sheet.write(rowCounter, i + 1, na)
    rowCounter += 1

  # Save file
  while True:
    try:
      book.save(fileName)
      break
    except Exception as e:
      log.error(e)
      input("An error occurred when trying to save the file, press enter to try again?\n")

#------------------------------------------------------------------------------------#
# Get websites from google
#------------------------------------------------------------------------------------#

def GetGoogleResults(searchString, results=10, timeframe=""):
  """Gets links from Google"""

  googleUrl = f"https://www.google.com/search?q={searchString}&num=100"
  if (timeframe == "d" or timeframe == "w" or timeframe == "m"):
    googleUrl += f"&as_qdr={timeframe}"
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
  """Weeds out duplicate links"""
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
  """Gets information on a link"""

  # Get company name from link
  companyName = re.sub(r"^.*?//", "", link)
  companyName = re.sub(r"^.*?www\.", "", companyName)
  companyName = re.sub(r"\..*$", "", companyName)

  dataObject = {
    companyName: {        # Set basic info for each website
      "Facebook Page": {},
      # "Twitter Page": {}, Disabling Twitter as it has problems
      "Instagram Page": {},
      "Contact Info": {},
      "website": link,
      "result": "failed"
    }
  }

  info = dataObject[companyName]    # For easier modifications

  soup = ""
  try:
    soup = BeautifulSoup(requests.get(info["website"], timeout=5).text, "html.parser")
    info["result"] = "success"
  except Exception as e:
    log.error(e)
    return dataObject

  if (socialsFlag):
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
      info["Contact Info"]["result"] = "failed"
      log.error(e)
      pass
  else:
    info["Contact Info"]["result"] = "failed"
  return dataObject

#------------------------------------------------------------------------------------#
# Get details from their facebook account
#------------------------------------------------------------------------------------#

def CheckFacebook(link):
  """Gathers Facebook information on a facebook link"""

  info = {
    "result": "failed",
    "link": "",
    "likes": 0,
    "followers": 0,
    "page name": "",
  }
  soup = ""

  try:
    link = re.sub(r"^\/\/", "", link)   # Sometimes the link may have a "//" at the beginning
    soup = BeautifulSoup(requests.get(link, timeout=5).text, "html.parser")
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
  """Gathers Twitter information on a Twitter link"""

  info = {
    "result": "failed",
    "followers": 0,
    "following": 0,
    "link": "",
    "username": ""
  }
  soup = ""

  try:
    link = re.sub(r"^\/\/", "", link)   # Sometimes the link may have a "//" at the beginning
    soup = BeautifulSoup(requests.get(link, timeout=5).text, "html.parser")
    info["result"] = "success"
  except Exception as e:
    info["result"] = "failed"
    log.error(e)
    return info

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
  """Gets Instagram information from an Instagram link"""

  info = {
    "result": "failed",
    "followers": 0,
    "following": 0,
    "link": "",
    "username": ""
  }
  soup = ""

  try:
    soup = BeautifulSoup(requests.get(link, timeout=5).text, "html.parser")
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
    if (re.search(r"", username.text.strip())):
      info["result"] = "failed"
      log.error("Bot Detection for Instagram")
      return info
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
  """Gets contact information from a website"""

  info = {
    "number": 0,
    "email": "",
    "link": "",
    "result": "failed"
  }

  # Get link html data
  soup = ""
  try:
    soup = BeautifulSoup(requests.get(contactLink, timeout=5).text, "html.parser")
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
      match = re.search(r"\s(\w+@\w+\.[\.\w]+)\s", elem.text)
      if (match):
        info["email"] = match.group(1)
  return info

# Create the application GUI

app = Application(callback=Init)
app.mainloop()
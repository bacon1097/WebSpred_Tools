#------------------------------------------------------------------------------------#
# Modules
#------------------------------------------------------------------------------------#

import requests, argparse, re, json
from bs4 import BeautifulSoup
from googlesearch import search
from googleapiclient.discovery import build

#------------------------------------------------------------------------------------#
# Variables
#------------------------------------------------------------------------------------#

parser = argparse.ArgumentParser()
parser.add_argument("--search", "-s", metavar="STRING", required=True, help="Enter a search term")
parser.add_argument("--load", "-l", metavar="INT", required=False, type=int, default=4, help="How many loads per search")
args = parser.parse_args()
searchString = args.search
loadRequest = int(args.load)

#------------------------------------------------------------------------------------#
# Get websites from google
#------------------------------------------------------------------------------------#

def GoogleQuery(query, **kwargs):
  query_service = build("customsearch", "v1", developerKey="AIzaSyCej-LooM_bgPV45cFJzd5H3nGPfl02wRY")
  query_results = query_service.cse().list(q=query, cx="009310718199288639788:ykjb2j69tts", **kwargs).execute()
  return query_results['items']

#------------------------------------------------------------------------------------#
# Get websites from query
#------------------------------------------------------------------------------------#

def GetSites():
    collection = {}
    websites = GoogleQuery(searchString, num=2)
    otherWebsites = []
    for site in search(searchString, tld='co.uk', lang='en', num=10, start=0, stop=2, pause=2.0):
        otherWebsites.append(site)
    # print(otherWebsites)
    for site in otherWebsites:
        site = re.sub(r"((\.com)|(\.co\.uk)|(\.org(\.uk)?)|(\.uk)).*", r"\1", site)     # Regex out last part of site to get homepage
        try:
            requests.get(site)
            companyName = re.sub(r"^.*?//", "", site)
            companyName = re.sub(r"^.*?www\.", "", companyName)
            companyName = re.sub(r"\..*$", "", companyName)
            collection[companyName] = site
        except Exception:
            pass
    return collection

#------------------------------------------------------------------------------------#
# Get standard information from the webpage (Contact Info, Social media accounts)
#------------------------------------------------------------------------------------#

def GetInfo(collection):
    for website in collection:
        info = {        # Set basic info for each website
            "Facebook Page": {"result": "failed"},
            "Twitter Page": {"result": "failed"},
            "Instagram Page": {"result": "failed"},
            "Contact Number": {"result": "failed"},
            "website": collection[website]
        }
        soup = BeautifulSoup(requests.get(info["website"]).text, "html.parser")

        # Find facebook webpage
        facebook = soup.find_all('a', href=re.compile(r"facebook\.com\/(?!sharer)"))
        if (facebook):
            info["Facebook Page"]["link"] = str(facebook[0]["href"])
            info["Facebook Page"]["result"] = "success"
        else:
            info["Facebook Page"]["msg"] = "Could not find page"

        # Find twitter webpage
        twitter = soup.find_all('a', href=re.compile(r"twitter\.com\/(?!intent)"))
        if (twitter):
            info["Twitter Page"]["link"] = str(twitter[0]["href"])
            info["Twitter Page"]["result"] = "success"
        else:
            info["Twitter Page"]["msg"] = "Could not find page"

        # Find instagram webpage
        instagram = soup.find_all('a', href=re.compile(r"instagram\.com\/.*"))
        if (instagram):
            info["Instagram Page"]["link"] = str(instagram[0]["href"])
            info["Instagram Page"]["result"] = "success"
        else:
            info["Instagram Page"]["msg"] = "Could not find page"

        # Find contact page
        contactPage = soup.find_all('a', text=re.compile(r"contact", re.IGNORECASE))
        if (contactPage):
            try:
                contactLink = info["website"] + "/" + re.sub(r"((.*?)\/\/(.*?)\/)|^\/", r"", str(contactPage[0]["href"]))       # Obtain contact link
                info["Contact Number"]["link"] = contactLink
                r = requests.get(contactLink)
                contactSoup = BeautifulSoup(r.text, "html.parser")

                # Example number 01202 123456 | 01202 123 456 | 01202123456
                contactNumbers = contactSoup.find_all(text=re.compile(r".*\d[\d\s]{10,12}.*"))

                # Try to get a contact number
                if (contactNumbers):
                    for number in contactNumbers:
                        number = re.sub(r"\D", "", number.strip())
                        if (len(number) == 11):
                            info["Contact Number"]["contact number"] = number[:5] + " " + number[5:]
                            info["Contact Number"]["result"] = "success"
            except Exception:
                pass
        info = CheckFacebook(info)
        info = CheckTwitter(info)
        info = CheckInsta(info)
        collection[website] = info
    print(json.dumps(collection, indent=4))

#------------------------------------------------------------------------------------#
# Get details from their facebook account
#------------------------------------------------------------------------------------#

def CheckFacebook(info):
    if (info["Facebook Page"]["result"] == "success"):
        soup = ""
        try:
            soup = BeautifulSoup(requests.get(info["Facebook Page"]["link"]).text, "html.parser")
        except Exception:
            info["Facebook Page"]["result"] = "failed"
            return info

        # Get likes of facebook page
        likes = soup.find(text=re.compile(r"people like this"))
        if (likes):
            likes = re.sub(r"(\d)\s.*", r"\1", likes)        # Remove the characters after the last digit
            info["Facebook Page"]["likes"] = int(re.sub(r"\D", "", likes))

        # Get followers of facebook page
        followers = soup.find(text=re.compile(r"people follow this"))
        if (followers):
            followers = re.sub(r"(\d)\s.*", r"\1", followers)       # Remove the characters after the last digit
            info["Facebook Page"]["followers"] = int(re.sub(r"\D", "", followers))

        try:
            pageName = soup.find("h1").find("span")
            if (pageName):
                info["Facebook Page"]["page name"] = pageName.text
        except Exception:
            pass
    return info

#------------------------------------------------------------------------------------#
# Get details from their twitter account
#------------------------------------------------------------------------------------#

def CheckTwitter(info):
    if (info["Twitter Page"]["result"] == "success"):
        soup = ""
        try:
            soup = BeautifulSoup(requests.get(info["Twitter Page"]["link"]).text, "html.parser")
        except Exception:
            info["Twitter Page"]["result"] = "failed"
            return info

        try:
            pageName = soup.find_all("h2")[2].find("b")
            if (pageName):
                info["Twitter Page"]["username"] = pageName.text
        except Exception:
            pass

        try:
            following = soup.find("a", href=re.compile(r"following")).find("span", {"data-count": re.compile(r".*")})
            if (following):
                info["Twitter Page"]["following"] = int(re.sub(r"\D", "", following["data-count"]))
        except Exception:
            pass

        try:
            followers = soup.find("a", href=re.compile(r"followers")).find("span", {"data-count": re.compile(r".*")})
            if (followers):
                info["Twitter Page"]["followers"] = int(re.sub(r"\D", "", followers["data-count"]))
        except Exception:
            pass
    return info

#------------------------------------------------------------------------------------#
# Get details from their instagram account
#------------------------------------------------------------------------------------#

def CheckInsta(info):
    if (info["Instagram Page"]["result"] == "success"):
        soup = ""
        try:
            soup = BeautifulSoup(requests.get(info["Instagram Page"]["link"]).text, "html.parser", allow_redirects=True)
        except Exception as e:
            info["Instagram Page"]["result"] = "failed"
            print(e)
            return info

        # Check if page exists
        exists = soup.find("h2", text=re.compile(r"Sorry, this page isn't available."))
        if (not exists):
            info["Instagram Page"]["result"] = "failed"
            info["Instagram Page"]["msg"] = "Instagram page is not available"
            return info

        # Get username of account
        username = soup.find("title")
        if (username):
            username = re.sub(r"^.*@", "", username.text.strip())        # Regex out everything except identifier
            username = re.sub(r"\).*$", "", username)
            info["Instagram Page"]["username"] = username

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
                info["Instagram Page"]["following"] = int(re.sub(r"\D", "", str(following)))

            if (followers):
                info["Instagram Page"]["followers"] = int(re.sub(r"\D", "", str(followers)))
        except Exception:
            pass
    return info

#------------------------------------------------------------------------------------#
# Call stack
#------------------------------------------------------------------------------------#

GetInfo(GetSites())
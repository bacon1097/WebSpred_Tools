#------------------------------------------------------------------------------------#
# Modules
#------------------------------------------------------------------------------------#

import requests, argparse, re, json
from bs4 import BeautifulSoup
from googlesearch import search

#------------------------------------------------------------------------------------#
# Variables
#------------------------------------------------------------------------------------#

parser = argparse.ArgumentParser()
parser.add_argument("--search", "-s", metavar="STRING", required=True, help="Enter a search term")
parser.add_argument("--load", "-l", metavar="INT", required=False, type=int, default=5, help="How many loads per search")
args = parser.parse_args()
searchString = args.search
loadRequest = int(args.load)

#------------------------------------------------------------------------------------#
# Main Code
#------------------------------------------------------------------------------------#

def GetSites():
    collection = {}
    for site in search(searchString, tld="co.uk", lang='en', num=1, start=1, stop=1, pause=2):
        site = re.sub(r"((\.com)|(\.co\.uk)|(\.org(\.uk)?)|(\.uk)).*", r"\1", site)     # Regex out last part of site to get homepage
        try:
            requests.get(site)
            companyName = re.sub(r"^.*www\.", "", site)
            companyName = re.sub(r"\..*$", "", companyName)
            collection[companyName] = site
        except Exception:
            pass
    return collection

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
                        else:
                            print(website + " - Contact number is not 11 digits: " + number[:12] + "...")
                else:
                    print(website + " - Could not find contact number")
            except Exception as e:
                print(e)
                print(website + " - Could not return contact page")
        else:
            print(website + " - Could find contact page")
        info = CheckFacebook(info)
        info = CheckTwitter(info)
        info = CheckInsta(info)
        collection[website] = info
    print(json.dumps(collection, indent=4))

def CheckFacebook(info):
    if (info["Facebook Page"]["result"] == "success"):
        soup = ""
        try:
            soup = BeautifulSoup(requests.get(info["Facebook Page"]["link"]).text, "html.parser")
        except Exception:
            info["Facebook Page"]["result"] = "failed"
            print(info["website"] + " - Facebook Page could not be retrieved (" + info["Facebook Page"]["link"] + ")")
            return info

        # Get likes of facebook page
        likes = soup.find(text=re.compile(r"people like this"))
        if (likes):
            likes = re.sub(r"(\d)\s.*", r"\1", likes)        # Remove the characters after the last digit
            info["Facebook Page"]["likes"] = int(re.sub(r"\D", "", likes))
        else:
            print(info["website]" + " - Could not find Facebook likes"])

        # Get followers of facebook page
        followers = soup.find(text=re.compile(r"people follow this"))
        if (followers):
            followers = re.sub(r"(\d)\s.*", r"\1", followers)       # Remove the characters after the last digit
            info["Facebook Page"]["followers"] = int(re.sub(r"\D", "", followers))
        else:
            print(info["website]" + " - Could not find Facebook followers"])

        try:
            pageName = soup.find("h1").find("span")
            if (pageName):
                info["Facebook Page"]["page name"] = pageName.text
            else:
                print(info["website]" + " - Could not find Facebook Page name"])
        except Exception:
            print(info["website]" + " - Could not find Facebook Page name"])
    return info

def CheckTwitter(info):
    if (info["Twitter Page"]["result"] == "success"):
        soup = ""
        try:
            soup = BeautifulSoup(requests.get(info["Twitter Page"]["link"]).text, "html.parser")
        except Exception:
            info["Twitter Page"]["result"] = "failed"
            print(info["website"] + " - Twitter page could not be retrieved (" + info["Twitter Page"]["link"] + ")")
            return info

        try:
            pageName = soup.find_all("h2")[2].find("b")
            if (pageName):
                info["Twitter Page"]["username"] = pageName.text
            else:
                print(info["website"] + " - Could not find Twitter Page name")
        except Exception:
            print(info["website"] + " - Could not find Twitter Page name")

        try:
            following = soup.find("a", href=re.compile(r"following")).find("span", {"data-count": re.compile(r".*")})
            if (following):
                info["Twitter Page"]["following"] = int(re.sub(r"\D", "", following["data-count"]))
            else:
                print(info["website"] + " - Could not find Twitter following")
        except Exception:
            print(info["website"] + " - Could not find Twitter following")

        try:
            followers = soup.find("a", href=re.compile(r"followers")).find("span", {"data-count": re.compile(r".*")})
            if (followers):
                info["Twitter Page"]["followers"] = int(re.sub(r"\D", "", followers["data-count"]))
            else:
                print(info["website"] + " - Could not find Twitter followers")
        except Exception:
            print(info["website"] + " - Could not find Twitter followers")
    return info

def CheckInsta(info):
    if (info["Instagram Page"]["result"] == "success"):
        soup = ""
        try:
            soup = BeautifulSoup(requests.get(info["Instagram Page"]["link"]).text, "html.parser")
        except Exception:
            info["Instagram Page"]["result"] = "failed"
            print(info["website"] + " - Instagram page could not be retrieved (" + info["Instagram Page"]["link"] + ")")
            return info

        # Get username of account
        username = soup.find("title")
        if (username):
            username = re.sub(r"^.*@", "", username.text.strip())        # Regex out everything except identifier
            username = re.sub(r"\).*$", "", username)
            info["Instagram Page"]["username"] = username
        else:
            print(info["website]" + " - Could not find Instagram username"])

        following = 0
        followers = 0
        try:
            followData = soup.find_all("script", {"type": "text/javascript"})[3]
            followData = re.sub(r";$", "", followData.text)
            followData = re.sub(r"^.*?=\s", "", followData)
            followData = json.loads(followData)
            following = followData["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_followed_by"]["count"]
            followers = followData["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_follow"]["count"]

            if (following):
                info["Instagram Page"]["following"] = int(re.sub(r"\D", "", str(following)))
            else:
                print(info["website"] + " - Could not find Instagram following")

            if (followers):
                info["Instagram Page"]["followers"] = int(re.sub(r"\D", "", str(followers)))
            else:
                print(info["website"] + " - Could not find Instagram followers")
        except Exception:
            print(info["website"] + " - Could not find Instagram data")
    return info

GetInfo(GetSites())
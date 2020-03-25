#------------------------------------------------------------------------------------#
# Modules
#------------------------------------------------------------------------------------#

import requests, argparse, re
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
# Main
#------------------------------------------------------------------------------------#

def Main():
    websites = {}
    for site in search(searchString, tld="co.uk", lang='en', num=1, start=1, stop=1, pause=2):
        site = re.sub(r"((\.com)|(\.co\.uk)|(\.org(\.uk)?)|(\.uk)).*", r"\1", site)     # Regex out last part of site to get homepage
        r = ""
        try:
            r = requests.get(site)
            websites[site] = {"text": r.text}
        except Exception:       # Thrown if website doesn't exist
            pass
    CheckWebsite(websites)

def CheckWebsite(websites):
    for website in websites:
        info = {        # Set basic info for each website
            "Facebook Page": {"result": False},
            "Twitter Page": {"result": False},
            "Instagram Page": {"result": False},
            "Contact Number": {"result": False}
        }
        soup = BeautifulSoup(websites[website]["text"], "html.parser")

        # Find facebook webpage
        facebook = soup.find_all('a', href=re.compile(r"facebook\.com\/(?!sharer)"))
        if (facebook):
            info["Facebook Page"]["value"] = str(facebook[0]["href"])
            info["Facebook Page"]["result"] = True
        else:
            info["Facebook Page"]["value"] = "Could not find page"

        # Find twitter webpage
        twitter = soup.find_all('a', href=re.compile(r"twitter\.com\/(?!intent)"))
        if (twitter):
            info["Twitter Page"]["value"] = str(twitter[0]["href"])
            info["Twitter Page"]["result"] = True
        else:
            info["Twitter Page"]["value"] = "Could not find page"

        # Find instagram webpage
        instagram = soup.find_all('a', href=re.compile(r"instagram\.com\/.*"))
        if (instagram):
            info["Instagram Page"]["value"] = str(instagram[0]["href"])
            info["Instagram Page"]["result"] = True
        else:
            info["Instagram Page"]["value"] = "Could not find page"

        # Find contact page
        contactPage = soup.find_all('a', text=re.compile(r"contact", re.IGNORECASE))
        if (contactPage):
            try:
                contactLink = website + "/" + re.sub(r"((.*?)\/\/(.*?)\/)|^\/", r"", str(contactPage[0]["href"]))       # Obtain contact link
                r = requests.get(contactLink)
                contactSoup = BeautifulSoup(r.text, "html.parser")

                # Example number 01202 123456 | 01202 123 456 | 01202123456
                contactNumbers = contactSoup.find_all(text=re.compile(r".*\d[\d\s]{10,12}.*"))

                # Try to get a contact number
                if (contactNumbers):
                    for number in contactNumbers:
                        number = re.sub(r"\D", "", number.strip())
                        if (len(number) == 11):
                            info["Contact Number"]["value"] = number[:5] + " " + number[5:]
                            info["Contact Number"]["result"] = True
                        else:
                            info["Contact Number"]["value"] = "Number is not 11 digits - " + number[:15]
                            if (len(number) >= 15):
                                info["Contact Number"]["value"] += "..."
                else:
                    info["Contact Number"]["value"] = "Could not find contact numbers"
            except Exception as e:
                print(e)
                info["Contact Number"]["value"] = "Could not return contact page - " + contactLink
        else:
            info["Contact Number"]["value"] = "Could not find contact page"
        info = CheckFacebook(info)
        # info = CheckTwitter(info)
        websites[website] = info
    PrintOutput(websites)

def CheckFacebook(info):
    if (info["Facebook Page"]["result"]):
        soup = ""
        try:
            soup = BeautifulSoup(requests.get(info["Facebook Page"]["value"]).text, "html.parser")
        except Exception:
            info["Facebook Page"]["result"] = False
            info["Facebook Page"]["value"] = "Facebook Page does not exist - " + info["Facebook Page"]["value"]
            return info

        # Get likes of facebook page
        likes = soup.find(text=re.compile(r"people like this"))
        if (likes):
            likes = re.sub(r"(\d)\s.*", r"\1", likes)        # Remove the characters after the last digit
            info["Facebook Page"]["value"] += " " + likes + " likes"

        # Get followers of facebook page
        followers = soup.find(text=re.compile(r"people follow this"))
        if (followers):
            followers = re.sub(r"(\d)\s.*", r"\1", followers)       # Remove the characters after the last digit
            info["Facebook Page"]["value"] += " " + followers + " followers"
    return info

# def CheckTwitter(info):
#     if (info["Twitter Page"]["result"]):
#         soup = ""
#         try:
#             soup = BeautifulSoup(requests.get(info["Twitter Page"]["value"]).text, "html.parser")
#         except Exception:
#             info["Twitter Page"]["result"] = False
#             info["Twitter Page"]["value"] = "Twitter Page does not exist"
#             return info
#     return info

def PrintOutput(websites):
    for website in websites:
        for elem in websites[website]:
            if (elem != "text"):
                string = (elem + "  ")[:14] + ": "     # :14 for equal spacing when printing
                if (not websites[website][elem]["result"]):
                    string += "X "
                else:
                    string += "/ "
                string += website + " (" + websites[website][elem]["value"] + ")"
                print(string)
        print()     # Print new line

Main()
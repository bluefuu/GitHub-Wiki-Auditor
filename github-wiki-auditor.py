import argparse
import requests
import json
import sys
import time
import os
from getpass import getpass
from datetime import datetime
from bs4 import BeautifulSoup


def main():
  parser = argparse.ArgumentParser(description='Find world-editable GitHub repository wikis.')
  parser.add_argument('--accounts_file', type=str, required=True, help='Text file. Newline for each GitHub accounts')
  parser.add_argument('--username', type=str, required=True, help='GitHub username used for authentication.')
  args = parser.parse_args()

  accountsFile = args.accounts_file
  if not os.path.isfile(accountsFile):
    print("[*] Exiting - {0} is not a valid accounts input file.".format(accountsFile))
    sys.exit(1)

  accounts = getAccounts(accountsFile)
  gitHubUsername = args.username
  gitHubPassword = getpass()
  
  #create a session
  gitHubSession = requests.Session()
  
  wikiListFile = open("publicwiki.txt","w+")
  login(gitHubSession, gitHubUsername, gitHubPassword)
  
  wikiListFile.write("Date: {}\n".format(datetime.today().strftime("%d-%m-%Y")))
  for account in accounts:
    print("---Scanning {} GitHub account".format(account))
    repolist = getRepo(account, gitHubSession)
    wikiListFile.write("GitHub account {} [{}] repositories.\n \t Public wiki found: \n".format(account,len(repolist)))

    try:
      for repo in repolist:
        url = repo + "/wiki/_new"
        wikiResponse = gitHubSession.get(url)

        if wikiResponse.status_code == 429:
          print("\n[*] 429 Too Many Requests response received - sleeping 15 seconds.\n")
          time.sleep(15)
        
        wiki = BeautifulSoup(wikiResponse.text, "html.parser")

        try:
          print("--------Scanning: {}".format(repo))
          wikiTitle = wiki.find('title').string
          print("The wiki title is {}.".format(wikiTitle))
          if "Create New Page" in wikiTitle:
            print("\t Public wiki found!")
            wikiListFile.write("\t\t {}\n".format(repo))
        except:
          print("\t No title found on repo")
        
    except Exception as e:
      rateLimitRequest = gitHubSession.get("https://api.github.com/rate_limit")
      rateLimit = json.loads(rateLimitRequest.content)["rate"]["remaining"]
      print("[*]Exiting - Rate limit remaining {}.\n".format(rateLimit))
      sys.exit(1)

  wikiListFile.close()
  print("Scan finished. Wiki list @ publicwiki.txt")

def getRepo(account, gitHubSession):
  repos = []

  try: 
    repoRequest = gitHubSession.get(("https://api.github.com/users/{0}/repos?per_page=100&page=1").format(account))
    repoJSON = json.loads(repoRequest.content)
    
    # Itereate through multiple pages to ensure all repo wikis are checked.
    while repoRequest:
      if "next" in repoRequest.links.keys():
        repoRequest = gitHubSession.get(repoRequest.links["next"]["url"])
        repoJSON.extend(json.loads(repoRequest.content))
      else:
        break

    repoTotal = len(repoJSON)

    print("------Repositories total: ", repoTotal)
    for repoNum in range(repoTotal):
        repoURL = repoJSON[repoNum]["html_url"]
        repos.append(repoURL)

  except Exception as e:
    rateLimitRequest = gitHubSession.get("https://api.github.com/rate_limit")
    rateLimit = json.loads(rateLimitRequest.content)["rate"]["remaining"]
    print("Error: ", rateLimit)
    sys.exit(1)
  
  return repos

def getAccounts(accountsFile):
  accountfile = open(accountsFile, 'r')
  accountURLs = accountfile.read().splitlines()
  accounts = []

  for url in accountURLs:
    accounts.append(url.strip().split("https://github.com/",1)[1])
  
  accountfile.close()
  
  return accounts
    
def login(gitHubSession, username, password):     
  loginData = {
    'login': username,
    'password': password, 'js-webauthn-support': 'supported', 'js-webauthn-iuvpaa-support': 'unsupported',
    'commit': 'Sign in'
  }
  gitHubLogin = gitHubSession.get("https://www.github.com/login")
  html = BeautifulSoup(gitHubLogin.text, "html.parser")
  loginData.update(timestamp_secret = html.find("input", {'name':'timestamp_secret'}).get('value'))
  loginData.update(authenticity_token= html.find("input", {'name':'authenticity_token'}).get('value'))
  loginData.update(timestamp = html.find("input", {'name':'timestamp'}).get('value'))

  loginResponse = gitHubSession.post("https://github.com/session", data=loginData)

  if "Incorrect username or password" in loginResponse.text:
    print("[*]Exiting - Login failed.")
    sys.exit(1)
  else:
    print("Logged in.")

if __name__ == "__main__":
  main()
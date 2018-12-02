from bs4 import BeautifulSoup

import requests

url = "news.ycombinator.com"

r = requests.get("http://" + url)

data = r.text

soup = BeautifulSoup(data, features="html.parser")

for link in soup.find_all('a'):
    print(link.get('href'))

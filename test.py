import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

r = requests.get("https://mtgtop8.com/format?f=PAU", headers=HEADERS)
print(r.status_code)
soup = BeautifulSoup(r.content, 'lxml')
links = soup.find_all('a', href=lambda x: x and '/archetype?' in x)
print(len(links), "archetype links found")
for l in links[:3]:
    print(l.get('href'), l.get_text(strip=True))
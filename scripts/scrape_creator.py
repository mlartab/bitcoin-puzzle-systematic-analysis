#!/usr/bin/env python3
"""
Scrape all posts by saatoshi_rising from the main puzzle thread.
Outputs one cleaned line per sentence fragment.
"""

import requests, re, time, sys
from bs4 import BeautifulSoup

THREAD_URL = "https://bitcointalk.org/index.php?topic=5112311"
USERNAME = "saatoshi_rising"

def clean_text(text):
    # Remove quotes, signatures, excessive whitespace
    text = re.sub(r'\[quote.*?\]|\[/quote\]', '', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<.*?>', ' ', text)           # HTML tags
    text = re.sub(r'https?://\S+', ' ', text)    # URLs
    text = re.sub(r'[^a-zA-Z0-9\s:;\-\'\.\,\!\?]', ' ', text)  # Keep basic punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    # Split long messages into phrases of 2‑10 words
    words = text.split()
    phrases = []
    for length in range(2, min(11, len(words)+1)):
        for i in range(len(words)-length+1):
            phrase = ' '.join(words[i:i+length])
            phrases.append(phrase)
    return phrases

all_phrases = set()
page = 0
while True:
    url = f"{THREAD_URL}.{page*20}" if page > 0 else THREAD_URL
    print(f"Scraping page {page+1}...", end=' ', flush=True)
    try:
        r = requests.get(url, timeout=10)
    except Exception as e:
        print(f"Error: {e}")
        break
    if r.status_code != 200:
        print(f"Done (page {page+1} returned {r.status_code})")
        break
    soup = BeautifulSoup(r.text, 'html.parser')
    posts = soup.find_all('div', class_='post')
    found_author = False
    for post in posts:
        author_div = post.find('div', class_='smalltext')
        if not author_div:
            continue
        author_text = author_div.get_text()
        if USERNAME.lower() in author_text.lower():
            found_author = True
            body = post.find('div', class_='post')
            if body:
                text = body.get_text(separator=' ', strip=True)
                phrases = clean_text(text)
                all_phrases.update(phrases)
    print(f"found {len(all_phrases)} unique phrases so far")
    if not found_author:
        # No more posts by the author on this page; check next page anyway
        pass
    page += 1
    time.sleep(1)  # be polite

# Also add the username itself and common variations
all_phrases.add(USERNAME)
all_phrases.add(USERNAME.replace('_',''))
all_phrases.add(''.join(word.capitalize() for word in USERNAME.split('_')))

with open('creator_phrases.txt', 'w', encoding='utf-8') as f:
    for phrase in sorted(all_phrases):
        f.write(phrase + '\n')
print(f"\nDone. Total unique phrases: {len(all_phrases)} saved to creator_phrases.txt")
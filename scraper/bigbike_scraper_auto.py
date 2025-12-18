#!/usr/bin/env python3
"""
BigBike FAQ Auto Scraper - Get all articles from main FAQ page
"""

import json
import time
import requests
from bs4 import BeautifulSoup

def get_faq_urls():
    """Get all FAQ article URLs from main page"""
    try:
        print("📋 Getting FAQ URLs from main page...")
        
        url = 'https://www.bigbikeinfo.com/bigbike-faq'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all article links
        urls = []
        articles = soup.find_all('article', class_='post')
        
        for article in articles:
            link = article.find('a', href=True)
            if link:
                href = link['href']
                if 'bigbike-faq' in href and href not in urls:
                    urls.append(href)
        
        print(f"✓ Found {len(urls)} article URLs\n")
        return urls
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def scrape_article(url):
    """Scrape single article with full content"""
    try:
        print(f"  Accessing: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"  ❌ HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get title
        title_elem = soup.find('h1', class_='entry-title')
        title = title_elem.get_text(strip=True) if title_elem else "No Title"
        
        # Get content
        article = soup.find('article')
        if not article:
            print(f"  ❌ No article element")
            return None
        
        content_div = article.find('div', class_='entry-content')
        if not content_div:
            print(f"  ❌ No content div")
            return None
        
        # Extract all text
        paragraphs = []
        for elem in content_div.find_all(['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'li']):
            text = elem.get_text(strip=True)
            if text and len(text) > 10:
                paragraphs.append(text)
        
        content = '\n\n'.join(paragraphs)
        
        if not content or len(content) < 100:
            print(f"  ⚠️  Content too short: {len(content)} chars")
            return None
        
        return {
            'url': url,
            'title': title,
            'content': content
        }
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def main():
    print("=" * 80)
    print("BigBike FAQ Auto Scraper")
    print("=" * 80)
    
    # Get URLs from main page
    urls = get_faq_urls()
    
    if not urls:
        print("❌ No URLs found")
        return
    
    articles = []
    
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}]")
        article = scrape_article(url)
        
        if article:
            articles.append(article)
            print(f"  ✅ {article['title'][:60]}")
            print(f"  📝 {len(article['content'])} chars\n")
        else:
            print(f"  ⚠️  Skipped\n")
        
        time.sleep(1)
    
    # Save results
    output_file = 'scraper/bigbike_faq_complete.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    print("=" * 80)
    print(f"✅ Complete: {len(articles)} articles saved")
    print("=" * 80)
    
    if articles:
        total_chars = sum(len(a['content']) for a in articles)
        avg_chars = total_chars // len(articles)
        print(f"Total characters: {total_chars:,}")
        print(f"Average per article: {avg_chars:,}")
        print(f"Output: {output_file}")

if __name__ == "__main__":
    main()

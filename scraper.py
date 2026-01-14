"""
Generic Web Scraper - Scrapes public websites, blogs, and articles based on topic.
"""

import requests
from bs4 import BeautifulSoup
from newspaper import Article
from googlesearch import search
import pandas as pd
import json
import time
from datetime import datetime
from typing import Optional
import re


class WebScraper:
    """A generic web scraper for extracting content from public websites."""

    def __init__(self, delay: float = 1.0):
        """
        Initialize the scraper.
        
        Args:
            delay: Delay between requests in seconds (be respectful to servers)
        """
        self.delay = delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.results = []

    def search_topic(self, topic: str, num_results: int = 10) -> list[str]:
        """
        Search for URLs related to a topic using Google.
        
        Args:
            topic: The topic to search for
            num_results: Number of URLs to retrieve
            
        Returns:
            List of URLs
        """
        print(f"Searching for: {topic}")
        urls = []
        try:
            for url in search(topic, num_results=num_results):
                urls.append(url)
                time.sleep(self.delay)
        except Exception as e:
            print(f"Search error: {e}")
        return urls

    def scrape_article(self, url: str) -> Optional[dict]:
        """
        Scrape content from a single article/webpage using newspaper3k.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dictionary with article data or None if failed
        """
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            return {
                'url': url,
                'title': article.title,
                'authors': article.authors,
                'publish_date': str(article.publish_date) if article.publish_date else None,
                'text': article.text,
                'summary': article.text[:500] + '...' if len(article.text) > 500 else article.text,
                'top_image': article.top_image,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            return None

    def scrape_with_beautifulsoup(self, url: str) -> Optional[dict]:
        """
        Alternative scraping method using BeautifulSoup for more control.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dictionary with page data or None if failed
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            title = soup.find('title')
            title_text = title.get_text().strip() if title else 'No title'
            
            # Try to find main content
            main_content = soup.find('article') or soup.find('main') or soup.find('body')
            text = main_content.get_text(separator='\n', strip=True) if main_content else ''
            
            # Clean up text
            text = re.sub(r'\n+', '\n', text)
            
            return {
                'url': url,
                'title': title_text,
                'text': text,
                'summary': text[:500] + '...' if len(text) > 500 else text,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            return None


    def scrape_topic(self, topic: str, num_results: int = 10, method: str = 'article') -> list[dict]:
        """
        Search and scrape content for a given topic.
        
        Args:
            topic: The topic to search and scrape
            num_results: Number of results to scrape
            method: 'article' for newspaper3k or 'bs4' for BeautifulSoup
            
        Returns:
            List of scraped content dictionaries
        """
        urls = self.search_topic(topic, num_results)
        self.results = []
        
        for i, url in enumerate(urls, 1):
            print(f"Scraping ({i}/{len(urls)}): {url}")
            
            if method == 'article':
                data = self.scrape_article(url)
            else:
                data = self.scrape_with_beautifulsoup(url)
            
            if data:
                data['topic'] = topic
                self.results.append(data)
            
            time.sleep(self.delay)
        
        print(f"\nSuccessfully scraped {len(self.results)} pages")
        return self.results

    def save_to_json(self, filename: str = 'scraped_data.json'):
        """Save results to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"Saved to {filename}")

    def save_to_csv(self, filename: str = 'scraped_data.csv'):
        """Save results to CSV file."""
        if self.results:
            df = pd.DataFrame(self.results)
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"Saved to {filename}")

    def get_dataframe(self) -> pd.DataFrame:
        """Return results as a pandas DataFrame."""
        return pd.DataFrame(self.results)


def main():
    """Example usage of the web scraper."""
    scraper = WebScraper(delay=1.5)
    
    # Get topic from user
    topic = input("Enter topic to scrape: ").strip()
    if not topic:
        topic = "artificial intelligence trends 2024"
    
    num_results = input("Number of results (default 5): ").strip()
    num_results = int(num_results) if num_results.isdigit() else 5
    
    # Scrape the topic
    results = scraper.scrape_topic(topic, num_results=num_results)
    
    # Display results
    if results:
        print("\n" + "="*60)
        for i, item in enumerate(results, 1):
            print(f"\n[{i}] {item['title']}")
            print(f"    URL: {item['url']}")
            print(f"    Summary: {item['summary'][:200]}...")
        
        # Save options
        save = input("\nSave results? (json/csv/supabase/both/no): ").strip().lower()
        if save in ['json', 'both']:
            scraper.save_to_json(f"{topic.replace(' ', '_')}_data.json")
        if save in ['csv', 'both']:
            scraper.save_to_csv(f"{topic.replace(' ', '_')}_data.csv")
        if save == 'supabase':
            try:
                from supabase_client import SupabaseUploader
                uploader = SupabaseUploader()
                uploader.upload_new_only(results)
            except Exception as e:
                print(f"Supabase upload failed: {e}")
                print("Make sure SUPABASE_URL and SUPABASE_KEY are set in .env")


if __name__ == '__main__':
    main()

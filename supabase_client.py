"""
Supabase integration for WebDataScraper.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class SupabaseUploader:
    """Handles uploading scraped data to Supabase."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize Supabase client.
        
        Args:
            url: Supabase project URL (or set SUPABASE_URL env var)
            key: Supabase anon/service key (or set SUPABASE_KEY env var)
        """
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError(
                "Supabase credentials required. Set SUPABASE_URL and SUPABASE_KEY "
                "environment variables or pass them to the constructor."
            )
        
        self.client: Client = create_client(self.url, self.key)

    def upload_articles(self, articles: list[dict], table_name: str = 'scraped_articles') -> dict:
        """
        Upload scraped articles to Supabase.
        
        Args:
            articles: List of article dictionaries from the scraper
            table_name: Name of the Supabase table
            
        Returns:
            Response from Supabase
        """
        if not articles:
            return {'error': 'No articles to upload'}
        
        # Clean data for Supabase (convert lists to strings, handle None values)
        cleaned_articles = []
        for article in articles:
            cleaned = {
                'url': article.get('url'),
                'title': article.get('title'),
                'authors': ', '.join(article.get('authors', [])) if isinstance(article.get('authors'), list) else article.get('authors'),
                'publish_date': article.get('publish_date'),
                'text': article.get('text'),
                'summary': article.get('summary'),
                'top_image': article.get('top_image'),
                'topic': article.get('topic'),
                'scraped_at': article.get('scraped_at')
            }
            cleaned_articles.append(cleaned)
        
        try:
            response = self.client.table(table_name).insert(cleaned_articles).execute()
            print(f"Successfully uploaded {len(cleaned_articles)} articles to '{table_name}'")
            return {'success': True, 'count': len(cleaned_articles), 'data': response.data}
        except Exception as e:
            print(f"Upload failed: {e}")
            return {'success': False, 'error': str(e)}

    def upload_single(self, article: dict, table_name: str = 'scraped_articles') -> dict:
        """Upload a single article to Supabase."""
        return self.upload_articles([article], table_name)

    def get_existing_urls(self, table_name: str = 'scraped_articles') -> set:
        """Get all existing URLs to avoid duplicates."""
        try:
            response = self.client.table(table_name).select('url').execute()
            return {item['url'] for item in response.data}
        except Exception as e:
            print(f"Failed to fetch existing URLs: {e}")
            return set()

    def upload_new_only(self, articles: list[dict], table_name: str = 'scraped_articles') -> dict:
        """Upload only articles that don't already exist in the database."""
        existing_urls = self.get_existing_urls(table_name)
        new_articles = [a for a in articles if a.get('url') not in existing_urls]
        
        if not new_articles:
            print("No new articles to upload (all already exist)")
            return {'success': True, 'count': 0, 'skipped': len(articles)}
        
        print(f"Uploading {len(new_articles)} new articles (skipping {len(articles) - len(new_articles)} duplicates)")
        return self.upload_articles(new_articles, table_name)

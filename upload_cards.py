"""
Upload existing cards.json to Supabase database.
Non-interactive script for automated uploads.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from credit_card_scraper import CreditCardScraper
from credit_card_uploader import CreditCardUploader


def main():
    # Path to the existing cards.json
    json_path = "../fintech-idea/rewards-optimizer/src/data/cards.json"
    
    print("=" * 60)
    print("Credit Card Database Uploader")
    print("=" * 60)
    
    # Load cards from JSON
    scraper = CreditCardScraper()
    try:
        cards = scraper.load_from_json(json_path)
        scraper.cards = cards
    except FileNotFoundError:
        print(f"Error: Could not find {json_path}")
        print("Make sure you're running from the WebDataScraper directory")
        return
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return
    
    if not cards:
        print("No cards found in JSON file")
        return
    
    # Display summary
    print(f"\nLoaded {len(cards)} cards")
    print("\nCards by issuer:")
    issuers = {}
    for card in cards:
        issuers[card.issuer] = issuers.get(card.issuer, 0) + 1
    for issuer, count in sorted(issuers.items(), key=lambda x: -x[1]):
        print(f"  {issuer}: {count}")
    
    # Upload to Supabase
    print("\nUploading to Supabase...")
    try:
        uploader = CreditCardUploader()
        result = uploader.upload_cards(cards)
        
        print("\n" + "=" * 60)
        print("Upload Results:")
        print(f"  Cards inserted: {result['cards_inserted']}")
        print(f"  Cards updated: {result['cards_updated']}")
        print(f"  Category rewards: {result['category_rewards_inserted']}")
        print(f"  Signup bonuses: {result['signup_bonuses_inserted']}")
        
        if result['errors']:
            print(f"\nErrors ({len(result['errors'])}):")
            for err in result['errors'][:5]:
                print(f"  - {err['card']}: {err['error']}")
        else:
            print("\nAll cards uploaded successfully!")
            
    except ValueError as e:
        print(f"\nError: {e}")
        print("Make sure SUPABASE_URL and SUPABASE_KEY are set in .env")
    except Exception as e:
        print(f"\nUpload failed: {e}")


if __name__ == '__main__':
    main()

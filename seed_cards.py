"""
Seed Cards - Upload curated credit card data to Supabase.

This script loads card data from data/curated_cards.json and uploads it
to the Supabase database with full category rewards and signup bonuses.

Usage:
    python seed_cards.py
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from logger_config import setup_logger

load_dotenv(override=True)

logger = setup_logger("seed_cards", level="INFO")

# Path to curated cards data
DATA_FILE = Path(__file__).parent / "data" / "curated_cards.json"


def load_curated_cards() -> list:
    """Load curated cards from JSON file."""
    if not DATA_FILE.exists():
        logger.error(f"Data file not found: {DATA_FILE}")
        return []
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get('cards', [])


def upload_cards(cards: list) -> dict:
    """Upload cards with category rewards to Supabase."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    
    client = create_client(url, key)
    results = {'inserted': 0, 'updated': 0, 'category_rewards': 0, 'signup_bonuses': 0, 'errors': []}
    
    for card in cards:
        try:
            card_data = {
                'card_key': card['card_key'],
                'name': card['name'],
                'issuer': card['issuer'],
                'reward_program': card['reward_program'],
                'reward_currency': card['reward_currency'],
                'point_valuation': card['point_valuation'],
                'annual_fee': card['annual_fee'],
                'base_reward_rate': card['base_reward_rate'],
                'base_reward_unit': card['base_reward_unit'],
                'is_active': True,
            }
            
            existing = client.table('cards').select('id').eq('card_key', card['card_key']).execute()
            
            if existing.data:
                card_id = existing.data[0]['id']
                client.table('cards').update(card_data).eq('id', card_id).execute()
                results['updated'] += 1
            else:
                result = client.table('cards').insert(card_data).execute()
                card_id = result.data[0]['id'] if result.data else None
                results['inserted'] += 1
            
            if not card_id:
                continue
            
            # Delete and re-insert category rewards
            client.table('category_rewards').delete().eq('card_id', card_id).execute()
            for cr in card.get('category_rewards', []):
                cr_data = {
                    'card_id': card_id,
                    'category': cr['category'],
                    'multiplier': cr['multiplier'],
                    'reward_unit': cr['reward_unit'],
                    'description': cr['description'],
                }
                client.table('category_rewards').insert(cr_data).execute()
                results['category_rewards'] += 1
            
            # Delete and re-insert signup bonus
            client.table('signup_bonuses').delete().eq('card_id', card_id).execute()
            if card.get('signup_bonus'):
                sb = card['signup_bonus']
                sb_data = {
                    'card_id': card_id,
                    'bonus_amount': sb['bonus_amount'],
                    'bonus_currency': sb['bonus_currency'],
                    'spend_requirement': sb['spend_requirement'],
                    'timeframe_days': sb['timeframe_days'],
                    'is_active': True,
                }
                client.table('signup_bonuses').insert(sb_data).execute()
                results['signup_bonuses'] += 1
                
        except Exception as e:
            results['errors'].append({'card': card.get('card_key', 'unknown'), 'error': str(e)})
    
    return results


def main():
    logger.info("=" * 60)
    logger.info("Seeding Curated Cards")
    logger.info("=" * 60)
    
    cards = load_curated_cards()
    if not cards:
        logger.error("No cards to seed. Check data/curated_cards.json")
        return
    
    logger.info(f"Loading {len(cards)} curated cards...")
    result = upload_cards(cards)
    
    logger.info(f"\nResults:")
    logger.info(f"  Cards inserted: {result['inserted']}")
    logger.info(f"  Cards updated: {result['updated']}")
    logger.info(f"  Category rewards: {result['category_rewards']}")
    logger.info(f"  Signup bonuses: {result['signup_bonuses']}")
    
    if result['errors']:
        logger.error(f"\nErrors ({len(result['errors'])}):")
        for err in result['errors']:
            logger.error(f"  - {err['card']}: {err['error']}")
    
    logger.info("\nDone!")


if __name__ == '__main__':
    main()

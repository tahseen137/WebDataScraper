"""
Credit Card Uploader - Uploads credit card data to Supabase for the Rewards Optimizer.
Handles the cards, category_rewards, and signup_bonuses tables.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime

load_dotenv()


class CreditCardUploader:
    """Handles uploading credit card data to Supabase."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize Supabase client.
        
        Args:
            url: Supabase project URL (or set SUPABASE_URL env var)
            key: Supabase service role key (or set SUPABASE_KEY env var)
        """
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError(
                "Supabase credentials required. Set SUPABASE_URL and SUPABASE_KEY "
                "environment variables or pass them to the constructor."
            )
        
        self.client: Client = create_client(self.url, self.key)

    def upload_cards(self, cards: list) -> dict:
        """
        Upload credit cards to Supabase.
        Handles cards, category_rewards, and signup_bonuses tables.
        
        Args:
            cards: List of CreditCard objects from the scraper
            
        Returns:
            Summary of upload results
        """
        results = {
            'cards_inserted': 0,
            'cards_updated': 0,
            'category_rewards_inserted': 0,
            'signup_bonuses_inserted': 0,
            'errors': []
        }
        
        for card in cards:
            try:
                card_result = self._upsert_card(card)
                if card_result.get('inserted'):
                    results['cards_inserted'] += 1
                else:
                    results['cards_updated'] += 1
                
                card_id = card_result.get('id')
                if card_id:
                    # Upload category rewards
                    cr_count = self._upsert_category_rewards(card_id, card.category_rewards)
                    results['category_rewards_inserted'] += cr_count
                    
                    # Upload signup bonus
                    if card.signup_bonus:
                        sb_result = self._upsert_signup_bonus(card_id, card.signup_bonus)
                        if sb_result:
                            results['signup_bonuses_inserted'] += 1
                            
            except Exception as e:
                results['errors'].append({
                    'card': card.card_key,
                    'error': str(e)
                })
        
        return results


    def _upsert_card(self, card) -> dict:
        """Insert or update a single card."""
        card_data = {
            'card_key': card.card_key,
            'name': card.name,
            'name_fr': card.name_fr,
            'issuer': card.issuer,
            'reward_program': card.reward_program,
            'reward_currency': card.reward_currency,
            'point_valuation': card.point_valuation,
            'annual_fee': card.annual_fee,
            'base_reward_rate': card.base_reward_rate,
            'base_reward_unit': card.base_reward_unit,
            'image_url': card.image_url,
            'apply_url': card.apply_url,
            'is_active': True,
            'updated_at': datetime.now().isoformat(),
        }
        
        # Check if card exists
        existing = self.client.table('cards').select('id').eq('card_key', card.card_key).execute()
        
        if existing.data:
            # Update existing card
            card_id = existing.data[0]['id']
            self.client.table('cards').update(card_data).eq('id', card_id).execute()
            return {'id': card_id, 'inserted': False}
        else:
            # Insert new card
            result = self.client.table('cards').insert(card_data).execute()
            card_id = result.data[0]['id'] if result.data else None
            return {'id': card_id, 'inserted': True}

    def _upsert_category_rewards(self, card_id: str, category_rewards: list) -> int:
        """Insert or update category rewards for a card."""
        if not category_rewards:
            return 0
        
        # Delete existing category rewards for this card
        self.client.table('category_rewards').delete().eq('card_id', card_id).execute()
        
        # Insert new category rewards
        rewards_data = []
        for cr in category_rewards:
            rewards_data.append({
                'card_id': card_id,
                'category': cr.category,
                'multiplier': cr.multiplier,
                'reward_unit': cr.reward_unit,
                'description': cr.description,
                'description_fr': cr.description_fr,
                'has_spend_limit': cr.has_spend_limit,
                'spend_limit': cr.spend_limit,
                'spend_limit_period': cr.spend_limit_period,
            })
        
        if rewards_data:
            self.client.table('category_rewards').insert(rewards_data).execute()
        
        return len(rewards_data)

    def _upsert_signup_bonus(self, card_id: str, signup_bonus) -> bool:
        """Insert or update signup bonus for a card."""
        if not signup_bonus:
            return False
        
        # Delete existing signup bonus for this card
        self.client.table('signup_bonuses').delete().eq('card_id', card_id).execute()
        
        # Insert new signup bonus
        bonus_data = {
            'card_id': card_id,
            'bonus_amount': signup_bonus.bonus_amount,
            'bonus_currency': signup_bonus.bonus_currency,
            'spend_requirement': signup_bonus.spend_requirement,
            'timeframe_days': signup_bonus.timeframe_days,
            'valid_until': signup_bonus.valid_until,
            'is_active': True,
        }
        
        self.client.table('signup_bonuses').insert(bonus_data).execute()
        return True

    def get_all_cards(self) -> list:
        """Fetch all cards from Supabase."""
        result = self.client.table('cards').select('*').eq('is_active', True).execute()
        return result.data

    def get_card_with_rewards(self, card_key: str) -> dict:
        """Fetch a card with its category rewards and signup bonus."""
        # Get card
        card_result = self.client.table('cards').select('*').eq('card_key', card_key).execute()
        if not card_result.data:
            return None
        
        card = card_result.data[0]
        card_id = card['id']
        
        # Get category rewards
        cr_result = self.client.table('category_rewards').select('*').eq('card_id', card_id).execute()
        card['category_rewards'] = cr_result.data
        
        # Get signup bonus
        sb_result = self.client.table('signup_bonuses').select('*').eq('card_id', card_id).eq('is_active', True).execute()
        card['signup_bonus'] = sb_result.data[0] if sb_result.data else None
        
        return card

    def delete_card(self, card_key: str) -> bool:
        """Soft delete a card by setting is_active to False."""
        result = self.client.table('cards').update({'is_active': False}).eq('card_key', card_key).execute()
        return len(result.data) > 0

    def get_cards_by_issuer(self, issuer: str) -> list:
        """Fetch all cards from a specific issuer."""
        result = self.client.table('cards').select('*').eq('issuer', issuer).eq('is_active', True).execute()
        return result.data

    def get_cards_by_category(self, category: str) -> list:
        """Fetch all cards that have bonus rewards for a category."""
        # Get card IDs with this category
        cr_result = self.client.table('category_rewards').select('card_id').eq('category', category).execute()
        card_ids = [cr['card_id'] for cr in cr_result.data]
        
        if not card_ids:
            return []
        
        # Get cards
        result = self.client.table('cards').select('*').in_('id', card_ids).eq('is_active', True).execute()
        return result.data

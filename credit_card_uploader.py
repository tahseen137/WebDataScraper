"""
Credit Card Uploader - Uploads credit card data to Supabase for the Rewards Optimizer.
Handles the cards, category_rewards, and signup_bonuses tables.

Enhanced with duplicate prevention system:
- Automatic fingerprint generation
- Fuzzy duplicate detection
- Smart merging of duplicate data
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional, List, Dict
from datetime import datetime

from logger_config import get_logger
from card_identity_manager import (
    CardFingerprintGenerator,
    SmartDuplicateDetector,
    log_duplicate_detection
)

load_dotenv()

logger = get_logger(__name__)


class CreditCardUploader:
    """Handles uploading credit card data to Supabase with duplicate prevention."""

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

        # Initialize duplicate detection components
        self.generator = CardFingerprintGenerator()
        self.detector = SmartDuplicateDetector(self.client)

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
        """
        Insert or update a single card with duplicate detection.

        Process:
        1. Generate fingerprint
        2. Check for duplicates (exact + fuzzy)
        3. If duplicate found, merge data
        4. Otherwise, insert/update card
        """
        # Step 1: Generate fingerprint
        try:
            fingerprint, components = self.generator.generate_semantic_fingerprint(
                card.issuer,
                card.name,
                card.reward_program,
                card.annual_fee
            )
        except Exception as e:
            logger.error(f"Failed to generate fingerprint for {card.name}: {e}")
            # Fallback to old behavior if fingerprint generation fails
            fingerprint = None
            components = {}

        # Step 2: Check for duplicates using multi-level detection
        duplicates = []
        if fingerprint:
            try:
                duplicates = self.detector.find_duplicates_multilevel(card)
            except Exception as e:
                logger.error(f"Duplicate detection failed for {card.name}: {e}")

        # Prepare card data
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

        # Add duplicate prevention fields if fingerprint generated
        if fingerprint:
            card_data['fingerprint'] = fingerprint
            card_data['normalized_name'] = components.get('name', '')

        # Step 3: Handle duplicates
        if duplicates:
            best_match, similarity, match_type = duplicates[0]
            logger.info(f"Duplicate detected: {card.name} matches {best_match['name']} "
                       f"(similarity: {similarity:.2f}, type: {match_type})")

            if match_type in ['auto_merge', 'exact_fingerprint']:
                # Merge into existing card
                card_id = best_match['id']
                card_data = self._merge_card_data(card, best_match, card_data)
                self.client.table('cards').update(card_data).eq('id', card_id).execute()

                # Log the merge
                if fingerprint:
                    log_duplicate_detection(
                        self.client,
                        card_key_1=card.card_key,
                        card_key_2=best_match.get('card_key', ''),
                        fingerprint=fingerprint,
                        similarity_score=similarity,
                        action_taken='auto_merged',
                        merged_into_id=card_id,
                        metadata={
                            'match_type': match_type,
                            'source': card.source if hasattr(card, 'source') else 'unknown'
                        }
                    )

                logger.info(f"Merged {card.name} into existing card ID {card_id}")
                return {'id': card_id, 'inserted': False}
            else:
                # Manual review needed - log but still insert
                logger.warning(f"Manual review needed for {card.name} vs {best_match['name']}")
                if fingerprint:
                    log_duplicate_detection(
                        self.client,
                        card_key_1=card.card_key,
                        card_key_2=best_match.get('card_key', ''),
                        fingerprint=fingerprint,
                        similarity_score=similarity,
                        action_taken='flagged_manual_review',
                        metadata={'match_type': match_type}
                    )

        # Step 4: Insert or update card (no duplicates found or manual review)
        # Check if card exists by card_key
        existing = self.client.table('cards').select('id').eq('card_key', card.card_key).execute()

        if existing.data:
            # Update existing card
            card_id = existing.data[0]['id']
            self.client.table('cards').update(card_data).eq('id', card_id).execute()
            logger.info(f"Updated card: {card.name} (ID: {card_id})")
            return {'id': card_id, 'inserted': False}
        else:
            # Insert new card
            result = self.client.table('cards').insert(card_data).execute()
            card_id = result.data[0]['id'] if result.data else None
            logger.info(f"Inserted new card: {card.name} (ID: {card_id})")
            return {'id': card_id, 'inserted': True}

    def _merge_card_data(self, new_card, existing_card: Dict, new_card_data: Dict) -> Dict:
        """
        Merge new card data into existing card.

        Strategy:
        - Add new source to sources array
        - Merge highlights if available
        - Update confidence score based on source count
        - Keep most recent/complete data
        """
        merged_data = new_card_data.copy()

        # Merge sources
        existing_sources = existing_card.get('sources', []) or []
        new_source = new_card.source if hasattr(new_card, 'source') else None
        if new_source and new_source not in existing_sources:
            merged_data['sources'] = existing_sources + [new_source]
        else:
            merged_data['sources'] = existing_sources

        # Merge highlights if available
        if hasattr(new_card, 'highlights'):
            existing_highlights = existing_card.get('highlights', []) or []
            new_highlights = [h for h in new_card.highlights if h not in existing_highlights]
            if new_highlights:
                merged_data['highlights'] = existing_highlights + new_highlights

        # Update confidence score
        source_count = len(merged_data.get('sources', []))
        merged_data['confidence_score'] = min(1.0, 0.5 + (source_count * 0.1))

        return merged_data

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

"""
Scrape Workflow Orchestrator
Coordinates the complete scraping pipeline.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Any

from supabase import create_client, Client

from card_master_manager import CardMasterManager, MasterCard
from card_matcher import CardMatcher
from targeted_scraper import TargetedScraper, ScrapedCardData
from data_merger import DataMerger, MergedCardData
from card_identity_manager import SmartDuplicateDetector, CardFingerprintGenerator
from credit_card_uploader import CreditCardUploader
from config import load_config
from logger_config import get_logger

logger = get_logger(__name__)


class ScrapeWorkflow:
    """Orchestrates the complete scraping workflow."""

    def __init__(self, delay: float = 2.0):
        """Initialize workflow components."""
        self.config = load_config()

        # Initialize components
        self.master_manager = CardMasterManager()
        self.scraper = TargetedScraper(delay=delay)
        self.merger = DataMerger()
        self.uploader = CreditCardUploader()
        self.fingerprint_gen = CardFingerprintGenerator()

        # Supabase client for scraped_card_data
        url = self.config.get('supabase_url')
        key = self.config.get('supabase_key')
        self.db: Client = create_client(url, key)

        logger.info("ScrapeWorkflow initialized")

    def run(self, limit: Optional[int] = None,
            skip_scrape: bool = False,
            skip_upload: bool = False) -> Dict[str, Any]:
        """
        Execute complete scrape workflow.

        Args:
            limit: Optional limit on number of cards to process
            skip_scrape: Skip scraping (use existing scraped_card_data)
            skip_upload: Skip final upload to cards table

        Returns:
            Summary statistics
        """
        stats = {
            'started_at': datetime.now().isoformat(),
            'cards_processed': 0,
            'cards_found': 0,
            'cards_not_found': 0,
            'cards_uploaded': 0,
            'errors': []
        }

        try:
            # Step 1: Load master cards
            logger.info("Step 1: Loading master cards from database")
            master_cards = self.master_manager.get_all_active_cards()
            if limit:
                master_cards = master_cards[:limit]
            logger.info(f"  Loaded {len(master_cards)} master cards")

            # Step 2: Scrape each card
            if not skip_scrape:
                logger.info("Step 2: Scraping cards from web sources")
                for i, card in enumerate(master_cards, 1):
                    logger.info(f"  [{i}/{len(master_cards)}] {card.canonical_name}")
                    try:
                        scraped_data = self.scraper.scrape_card(card)
                        self._store_scraped_data(card, scraped_data)

                        if scraped_data:
                            stats['cards_found'] += 1
                        else:
                            stats['cards_not_found'] += 1

                        stats['cards_processed'] += 1

                    except Exception as e:
                        logger.error(f"Error scraping {card.canonical_name}: {e}")
                        stats['errors'].append({
                            'card': card.canonical_name,
                            'phase': 'scrape',
                            'error': str(e)
                        })
            else:
                logger.info("Step 2: Skipping scrape (using existing data)")
                stats['cards_processed'] = len(master_cards)

            # Step 3: Merge data for each card
            logger.info("Step 3: Merging data from multiple sources")
            merged_cards = []
            for card in master_cards:
                try:
                    scraped_records = self._get_scraped_data(card.id)
                    if scraped_records:
                        merged = self.merger.merge_card_data(
                            card.id,
                            scraped_records,
                            card.canonical_name,
                            card.canonical_issuer
                        )
                        merged_cards.append(merged)
                except Exception as e:
                    logger.error(f"Error merging {card.canonical_name}: {e}")
                    stats['errors'].append({
                        'card': card.canonical_name,
                        'phase': 'merge',
                        'error': str(e)
                    })

            logger.info(f"  Merged {len(merged_cards)} cards")

            # Step 4: Deduplicate
            logger.info("Step 4: Deduplicating merged data")
            deduplicated = self._deduplicate(merged_cards)
            logger.info(f"  {len(deduplicated)} cards after deduplication")

            # Step 5: Upload to database
            if not skip_upload:
                logger.info("Step 5: Uploading to cards table")
                upload_result = self._upload_cards(deduplicated)
                stats['cards_uploaded'] = upload_result.get('cards_inserted', 0) + upload_result.get('cards_updated', 0)
                logger.info(f"  Uploaded {stats['cards_uploaded']} cards")
            else:
                logger.info("Step 5: Skipping upload")

            stats['completed_at'] = datetime.now().isoformat()
            logger.info(f"Workflow complete: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            stats['errors'].append({'phase': 'workflow', 'error': str(e)})
            stats['completed_at'] = datetime.now().isoformat()
            return stats

    def _store_scraped_data(self, card: MasterCard, scraped_list: List[ScrapedCardData]):
        """Store scraped data to scraped_card_data table."""
        for scraped in scraped_list:
            try:
                data = {
                    'master_card_id': card.id,
                    'match_confidence': scraped.match_confidence,
                    'source_name': scraped.source_name,
                    'source_url': scraped.source_url,
                    'raw_data': scraped.raw_data,
                    'annual_fee': scraped.annual_fee,
                    'base_reward_rate': scraped.base_reward_rate,
                    'category_rewards': scraped.category_rewards,
                    'signup_bonus': scraped.signup_bonus,
                    'is_processed': False
                }

                self.db.table('scraped_card_data').insert(data).execute()

            except Exception as e:
                # Likely duplicate, skip
                logger.debug(f"Could not store scraped data: {e}")

    def _get_scraped_data(self, master_card_id: str) -> List[ScrapedCardData]:
        """Get scraped data for a master card (most recent per source)."""
        response = self.db.table('scraped_card_data') \
            .select('*') \
            .eq('master_card_id', master_card_id) \
            .order('scraped_at', desc=True) \
            .execute()

        # Dedupe by source (keep most recent)
        by_source = {}
        for row in response.data:
            source = row['source_name']
            if source not in by_source:
                by_source[source] = ScrapedCardData(
                    master_card_id=row['master_card_id'],
                    source_name=row['source_name'],
                    source_url=row.get('source_url', ''),
                    match_confidence=row.get('match_confidence', 0.0),
                    raw_data=row.get('raw_data', {}),
                    annual_fee=row.get('annual_fee'),
                    base_reward_rate=row.get('base_reward_rate'),
                    category_rewards=row.get('category_rewards', []),
                    signup_bonus=row.get('signup_bonus')
                )

        return list(by_source.values())

    def _deduplicate(self, merged_cards: List[MergedCardData]) -> List[MergedCardData]:
        """Deduplicate merged cards using fingerprinting."""
        seen_fingerprints = set()
        deduplicated = []

        for card in merged_cards:
            fingerprint, _ = self.fingerprint_gen.generate_semantic_fingerprint(
                card.issuer,
                card.name,
                card.reward_program or '',
                card.annual_fee or 0.0
            )

            if fingerprint not in seen_fingerprints:
                seen_fingerprints.add(fingerprint)
                deduplicated.append(card)
            else:
                logger.debug(f"Duplicate removed: {card.name}")

        return deduplicated

    def _upload_cards(self, merged_cards: List[MergedCardData]) -> Dict[str, Any]:
        """Upload merged cards to database."""
        # Convert MergedCardData to dict format expected by uploader
        cards_data = []
        for mc in merged_cards:
            card_dict = {
                'card_key': mc.card_key,
                'name': mc.name,
                'issuer': mc.issuer,
                'annual_fee': mc.annual_fee,
                'base_reward_rate': mc.base_reward_rate,
                'base_reward_unit': mc.base_reward_unit,
                'reward_program': mc.reward_program,
                'reward_currency': mc.reward_currency,
                'point_valuation': mc.point_valuation,
                'image_url': mc.image_url,
                'apply_url': mc.apply_url,
                'master_card_id': mc.master_card_id,
                'category_rewards': mc.category_rewards,
                'signup_bonus': mc.signup_bonus,
                'sources': mc.sources,
                'confidence_score': mc.confidence_score
            }
            cards_data.append(card_dict)

        return self.uploader.upload_cards_from_dicts(cards_data)


# CLI
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Scrape Workflow')
    parser.add_argument('--limit', type=int, help='Limit cards to process')
    parser.add_argument('--skip-scrape', action='store_true', help='Skip scraping')
    parser.add_argument('--skip-upload', action='store_true', help='Skip upload')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests')
    args = parser.parse_args()

    workflow = ScrapeWorkflow(delay=args.delay)
    result = workflow.run(
        limit=args.limit,
        skip_scrape=args.skip_scrape,
        skip_upload=args.skip_upload
    )

    print("\n=== Workflow Results ===")
    print(f"Cards processed: {result['cards_processed']}")
    print(f"Cards found: {result['cards_found']}")
    print(f"Cards not found: {result['cards_not_found']}")
    print(f"Cards uploaded: {result['cards_uploaded']}")
    print(f"Errors: {len(result['errors'])}")

    if result['errors']:
        print("\nErrors:")
        for err in result['errors']:
            print(f"  - {err}")

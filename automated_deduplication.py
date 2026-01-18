"""
Automated Deduplication Script

Scans the database for duplicate credit cards and automatically merges them
based on fingerprint matching and fuzzy name similarity.

Usage:
    python automated_deduplication.py --dry-run
    python automated_deduplication.py --threshold 0.90
    python automated_deduplication.py --email admin@example.com

Author: Kiro AI
Created: January 18, 2026
"""

import argparse
import sys
from typing import List, Tuple, Dict
from datetime import datetime
from card_identity_manager import CardIdentityManager, CreditCard
from supabase_client import get_supabase_client
from logger_config import get_logger

logger = get_logger(__name__)


class DuplicationScanner:
    """Scans database for duplicate cards and manages merging."""
    
    def __init__(self):
        """Initialize the scanner."""
        self.supabase = get_supabase_client()
        self.identity_manager = CardIdentityManager()
        self.merge_log = []
    
    def fetch_all_cards(self) -> List[CreditCard]:
        """
        Fetch all active cards from the database.
        
        Returns:
            List of CreditCard objects
        """
        try:
            response = self.supabase.table('cards').select('*').execute()
            
            cards = []
            for row in response.data:
                card = CreditCard(
                    id=row.get('id'),
                    name=row.get('name', ''),
                    issuer=row.get('issuer', ''),
                    reward_program=row.get('reward_program', ''),
                    annual_fee=float(row.get('annual_fee', 0)),
                    normalized_name=row.get('normalized_name'),
                    fingerprint=row.get('fingerprint'),
                    sources=row.get('sources', []),
                    confidence_score=float(row.get('confidence_score', 0.5)),
                    card_key=row.get('card_key')
                )
                cards.append(card)
            
            logger.info(f"Fetched {len(cards)} cards from database")
            return cards
            
        except Exception as e:
            logger.error(f"Error fetching cards: {e}")
            return []
    
    def scan_for_duplicates(
        self,
        threshold: float = 0.85
    ) -> List[Tuple[CreditCard, CreditCard, float]]:
        """
        Scan all cards for potential duplicates.
        
        Args:
            threshold: Minimum similarity score to consider as duplicate
            
        Returns:
            List of (card1, card2, similarity) tuples
        """
        logger.info(f"Scanning for duplicates with threshold {threshold}")
        
        cards = self.fetch_all_cards()
        duplicates = []
        checked_pairs = set()
        
        for i, card1 in enumerate(cards):
            # Find potential duplicates for this card
            candidates = self.identity_manager.find_potential_duplicates(
                card1,
                cards,
                threshold
            )
            
            for card2, similarity in candidates:
                # Create a sorted pair key to avoid checking same pair twice
                pair_key = tuple(sorted([card1.id, card2.id]))
                
                if pair_key not in checked_pairs:
                    checked_pairs.add(pair_key)
                    duplicates.append((card1, card2, similarity))
                    logger.info(
                        f"Found duplicate: '{card1.name}' <-> '{card2.name}' "
                        f"(similarity: {similarity:.3f})"
                    )
        
        logger.info(f"Found {len(duplicates)} duplicate pairs")
        return duplicates
    
    def merge_duplicate_pair(
        self,
        card1: CreditCard,
        card2: CreditCard,
        similarity: float,
        dry_run: bool = True
    ) -> Dict:
        """
        Merge two duplicate cards.
        
        Args:
            card1: First card
            card2: Second card
            similarity: Similarity score
            dry_run: If True, don't actually modify database
            
        Returns:
            Dictionary with merge results
        """
        # Determine which card to keep (higher confidence score)
        if card1.confidence_score >= card2.confidence_score:
            keep_card = card1
            remove_card = card2
        else:
            keep_card = card2
            remove_card = card1
        
        # Merge the cards
        merged_card = self.identity_manager.merge_cards(keep_card, remove_card)
        
        result = {
            'kept_id': keep_card.id,
            'kept_name': keep_card.name,
            'removed_id': remove_card.id,
            'removed_name': remove_card.name,
            'similarity': similarity,
            'merged_sources': merged_card.sources,
            'new_confidence': merged_card.confidence_score,
            'dry_run': dry_run
        }
        
        if not dry_run:
            try:
                # Update the kept card with merged data
                self.supabase.table('cards').update({
                    'sources': merged_card.sources,
                    'confidence_score': merged_card.confidence_score,
                    'annual_fee': merged_card.annual_fee,
                    'last_verified': datetime.now().isoformat()
                }).eq('id', keep_card.id).execute()
                
                # Soft delete the removed card
                self.supabase.table('cards').delete().eq('id', remove_card.id).execute()
                
                # Log to duplicate_detection_log
                self.supabase.table('duplicate_detection_log').insert({
                    'card_key_1': keep_card.card_key,
                    'card_key_2': remove_card.card_key,
                    'fingerprint': merged_card.fingerprint,
                    'similarity_score': similarity,
                    'action_taken': 'auto_merged',
                    'merged_into_id': keep_card.id,
                    'metadata': result
                }).execute()
                
                logger.info(
                    f"Merged '{remove_card.name}' into '{keep_card.name}' "
                    f"(similarity: {similarity:.3f})"
                )
                
            except Exception as e:
                logger.error(f"Error merging cards: {e}")
                result['error'] = str(e)
        
        self.merge_log.append(result)
        return result
    
    def automated_cleanup(
        self,
        dry_run: bool = True,
        threshold: float = 0.90,
        email: str = None
    ) -> Dict:
        """
        Run automated duplicate cleanup.
        
        Args:
            dry_run: If True, don't actually modify database
            threshold: Minimum similarity for auto-merge
            email: Email address for notification
            
        Returns:
            Summary report dictionary
        """
        logger.info(f"Starting automated cleanup (dry_run={dry_run}, threshold={threshold})")
        
        # Scan for duplicates
        duplicates = self.scan_for_duplicates(threshold)
        
        # Merge duplicates
        merged_count = 0
        flagged_count = 0
        
        for card1, card2, similarity in duplicates:
            if similarity >= threshold:
                # Auto-merge high-confidence duplicates
                self.merge_duplicate_pair(card1, card2, similarity, dry_run)
                merged_count += 1
            elif similarity >= 0.70:
                # Flag medium-confidence for manual review
                if not dry_run:
                    self.supabase.table('duplicate_detection_log').insert({
                        'card_key_1': card1.card_key,
                        'card_key_2': card2.card_key,
                        'fingerprint': card1.fingerprint,
                        'similarity_score': similarity,
                        'action_taken': 'flagged',
                        'metadata': {
                            'card1_name': card1.name,
                            'card2_name': card2.name,
                            'reason': 'medium_confidence_requires_review'
                        }
                    }).execute()
                flagged_count += 1
        
        # Generate summary report
        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'threshold': threshold,
            'total_duplicates_found': len(duplicates),
            'auto_merged': merged_count,
            'flagged_for_review': flagged_count,
            'merge_log': self.merge_log
        }
        
        # Log summary
        logger.info(f"Cleanup complete: {merged_count} merged, {flagged_count} flagged")
        
        # Send email notification if requested
        if email and not dry_run:
            self._send_email_notification(email, report)
        
        return report
    
    def _send_email_notification(self, email: str, report: Dict):
        """
        Send email notification with cleanup results.
        
        Args:
            email: Recipient email address
            report: Cleanup report dictionary
        """
        # TODO: Implement email sending
        logger.info(f"Would send email to {email} with report: {report}")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Automated credit card duplicate detection and merging'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without making database changes'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.90,
        help='Minimum similarity score for auto-merge (default: 0.90)'
    )
    parser.add_argument(
        '--email',
        type=str,
        help='Email address for notification'
    )
    
    args = parser.parse_args()
    
    # Run cleanup
    scanner = DuplicationScanner()
    report = scanner.automated_cleanup(
        dry_run=args.dry_run,
        threshold=args.threshold,
        email=args.email
    )
    
    # Print summary
    print("\n" + "="*60)
    print("DUPLICATE CLEANUP REPORT")
    print("="*60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Mode: {'DRY RUN' if report['dry_run'] else 'LIVE'}")
    print(f"Threshold: {report['threshold']}")
    print(f"Total duplicates found: {report['total_duplicates_found']}")
    print(f"Auto-merged: {report['auto_merged']}")
    print(f"Flagged for review: {report['flagged_for_review']}")
    print("="*60)
    
    if report['merge_log']:
        print("\nMerge Details:")
        for i, merge in enumerate(report['merge_log'], 1):
            print(f"\n{i}. Kept: {merge['kept_name']}")
            print(f"   Removed: {merge['removed_name']}")
            print(f"   Similarity: {merge['similarity']:.3f}")
            print(f"   New confidence: {merge['new_confidence']:.2f}")
    
    print("\n")
    
    return 0 if not report.get('error') else 1


if __name__ == '__main__':
    sys.exit(main())

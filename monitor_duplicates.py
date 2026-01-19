"""
Duplicate Detection Monitoring Script

Monitor and report on duplicate detection activities.
Provides insights into duplicate patterns, merge success rates, and data quality.

Usage:
    python monitor_duplicates.py --days 7        # Last 7 days
    python monitor_duplicates.py --action auto_merged  # Specific action
    python monitor_duplicates.py --export report.json  # Export to file

Author: WebDataScraper Team
Created: January 18, 2026
"""

import argparse
import sys
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from supabase import create_client
from logger_config import setup_logger, get_logger
from config import load_config


class DuplicateMonitor:
    """Monitor duplicate detection activities and generate reports."""

    def __init__(self, db_client):
        """
        Initialize monitor.

        Args:
            db_client: Supabase client
        """
        self.db = db_client
        self.logger = get_logger(__name__)

    def get_activity_summary(self, days: int = 7) -> Dict:
        """
        Get summary of duplicate detection activity.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            Dictionary with activity statistics
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        try:
            # Fetch all logs since cutoff
            response = self.db.table('duplicate_detection_log').select('*').gte('created_at', cutoff_date).execute()
            logs = response.data if response.data else []

            # Calculate statistics
            stats = {
                'period_days': days,
                'total_detections': len(logs),
                'by_action': defaultdict(int),
                'by_similarity': {
                    'exact_match': 0,
                    'high_similarity': 0,
                    'medium_similarity': 0
                },
                'avg_similarity': 0.0,
                'unique_cards_involved': set()
            }

            total_similarity = 0

            for log in logs:
                # Count by action
                action = log.get('action_taken', 'unknown')
                stats['by_action'][action] += 1

                # Track unique cards
                stats['unique_cards_involved'].add(log.get('card_key_1'))
                stats['unique_cards_involved'].add(log.get('card_key_2'))

                # Categorize by similarity
                similarity = float(log.get('similarity_score', 0))
                total_similarity += similarity

                if similarity >= 0.95:
                    stats['by_similarity']['exact_match'] += 1
                elif similarity >= 0.85:
                    stats['by_similarity']['high_similarity'] += 1
                else:
                    stats['by_similarity']['medium_similarity'] += 1

            # Calculate average similarity
            if logs:
                stats['avg_similarity'] = total_similarity / len(logs)

            # Convert sets to counts
            stats['unique_cards_involved'] = len(stats['unique_cards_involved'])
            stats['by_action'] = dict(stats['by_action'])

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get activity summary: {e}")
            return {}

    def get_manual_review_queue(self) -> List[Dict]:
        """
        Get list of cards flagged for manual review.

        Returns:
            List of card pairs needing manual review, sorted by similarity
        """
        try:
            response = self.db.table('duplicate_detection_log').select('*').eq('action_taken', 'flagged_manual_review').order('similarity_score', desc=True).execute()

            return response.data if response.data else []

        except Exception as e:
            self.logger.error(f"Failed to get manual review queue: {e}")
            return []

    def get_merge_statistics(self, days: int = 30) -> Dict:
        """
        Get statistics on merge operations.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with merge statistics
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        try:
            response = self.db.table('duplicate_detection_log').select('*').eq('action_taken', 'auto_merged').gte('created_at', cutoff_date).execute()

            merges = response.data if response.data else []

            stats = {
                'total_merges': len(merges),
                'by_day': defaultdict(int),
                'similarity_distribution': {
                    '0.95-1.00': 0,
                    '0.90-0.95': 0,
                    '0.85-0.90': 0
                }
            }

            for merge in merges:
                # Count by day
                date = merge.get('created_at', '')[:10]
                stats['by_day'][date] += 1

                # Distribute by similarity
                similarity = float(merge.get('similarity_score', 0))
                if similarity >= 0.95:
                    stats['similarity_distribution']['0.95-1.00'] += 1
                elif similarity >= 0.90:
                    stats['similarity_distribution']['0.90-0.95'] += 1
                else:
                    stats['similarity_distribution']['0.85-0.90'] += 1

            stats['by_day'] = dict(sorted(stats['by_day'].items()))

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get merge statistics: {e}")
            return {}

    def get_duplicate_patterns(self, limit: int = 10) -> List[Dict]:
        """
        Identify common duplicate patterns.

        Args:
            limit: Maximum number of patterns to return

        Returns:
            List of common duplicate patterns
        """
        try:
            # Get recent duplicates
            response = self.db.table('duplicate_detection_log').select('*').order('created_at', desc=True).limit(100).execute()

            logs = response.data if response.data else []

            # Analyze patterns
            patterns = defaultdict(int)

            for log in logs:
                metadata = log.get('metadata', {})
                match_type = metadata.get('match_type', 'unknown')
                patterns[match_type] += 1

            # Sort by frequency
            sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:limit]

            return [
                {'pattern': pattern, 'count': count}
                for pattern, count in sorted_patterns
            ]

        except Exception as e:
            self.logger.error(f"Failed to get duplicate patterns: {e}")
            return []

    def print_summary_report(self, days: int = 7) -> None:
        """
        Print a formatted summary report to console.

        Args:
            days: Number of days to analyze
        """
        print("\n" + "=" * 70)
        print(f"DUPLICATE DETECTION SUMMARY - Last {days} Days")
        print("=" * 70)

        # Activity summary
        stats = self.get_activity_summary(days)
        print(f"\n📊 Activity Overview:")
        print(f"   Total Detections: {stats.get('total_detections', 0)}")
        print(f"   Unique Cards Involved: {stats.get('unique_cards_involved', 0)}")
        print(f"   Average Similarity: {stats.get('avg_similarity', 0):.2f}")

        print(f"\n🔀 Actions Taken:")
        for action, count in stats.get('by_action', {}).items():
            print(f"   {action}: {count}")

        print(f"\n📈 Similarity Distribution:")
        sim_dist = stats.get('by_similarity', {})
        print(f"   Exact Match (≥0.95): {sim_dist.get('exact_match', 0)}")
        print(f"   High Similarity (0.85-0.95): {sim_dist.get('high_similarity', 0)}")
        print(f"   Medium Similarity (<0.85): {sim_dist.get('medium_similarity', 0)}")

        # Manual review queue
        queue = self.get_manual_review_queue()
        print(f"\n⚠️  Manual Review Queue: {len(queue)} items")
        if queue:
            print("   Top 5 items:")
            for i, item in enumerate(queue[:5], 1):
                print(f"   {i}. {item.get('card_key_1')} vs {item.get('card_key_2')} "
                      f"(similarity: {item.get('similarity_score', 0):.2f})")

        # Merge statistics
        merge_stats = self.get_merge_statistics(days)
        print(f"\n✅ Merge Statistics:")
        print(f"   Total Merges: {merge_stats.get('total_merges', 0)}")
        print(f"   Distribution:")
        for range_label, count in merge_stats.get('similarity_distribution', {}).items():
            print(f"      {range_label}: {count}")

        # Patterns
        patterns = self.get_duplicate_patterns(5)
        print(f"\n🔍 Common Patterns:")
        for pattern in patterns:
            print(f"   {pattern['pattern']}: {pattern['count']} occurrences")

        print("\n" + "=" * 70)

    def export_report(self, filepath: str, days: int = 7) -> None:
        """
        Export detailed report to JSON file.

        Args:
            filepath: Output file path
            days: Number of days to analyze
        """
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'period_days': days,
            'activity_summary': self.get_activity_summary(days),
            'manual_review_queue': self.get_manual_review_queue(),
            'merge_statistics': self.get_merge_statistics(days),
            'duplicate_patterns': self.get_duplicate_patterns(10)
        }

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n✅ Report exported to: {filepath}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Monitor duplicate detection activity')
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )
    parser.add_argument(
        '--action',
        type=str,
        choices=['auto_merged', 'flagged_manual_review', 'ignored'],
        help='Filter by specific action type'
    )
    parser.add_argument(
        '--export',
        type=str,
        help='Export report to JSON file'
    )
    args = parser.parse_args()

    # Setup logging
    logger = setup_logger()
    logger.info("Starting duplicate detection monitoring")

    # Load config
    try:
        config = load_config()
        supabase_url = config.get('supabase_url')
        supabase_key = config.get('supabase_key')

        if not supabase_url or not supabase_key:
            logger.error("Missing Supabase credentials in config")
            sys.exit(1)

        # Create database client
        db = create_client(supabase_url, supabase_key)

    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        sys.exit(1)

    # Create monitor
    monitor = DuplicateMonitor(db)

    # Print summary report
    monitor.print_summary_report(days=args.days)

    # Export if requested
    if args.export:
        monitor.export_report(args.export, days=args.days)


if __name__ == '__main__':
    main()

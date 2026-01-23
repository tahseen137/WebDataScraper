"""
Targeted Credit Card Scraper
Scrapes specific cards from master list instead of discovering cards.
"""

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup

from card_master_manager import MasterCard, CardMasterManager
from card_matcher import CardMatcher, MatchResult
from logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class ScrapedCardData:
    """Raw scraped data from a single source."""
    master_card_id: str
    source_name: str
    source_url: str
    match_confidence: float
    scraped_at: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # Extracted fields
    annual_fee: Optional[float] = None
    base_reward_rate: Optional[float] = None
    base_reward_unit: str = ""
    category_rewards: List[Dict] = field(default_factory=list)
    signup_bonus: Optional[Dict] = None
    image_url: Optional[str] = None
    apply_url: Optional[str] = None


class TargetedScraper:
    """Scrapes specific cards from master list."""

    # Source configurations
    SOURCES = {
        'creditcardgenius': {
            'base_url': 'https://creditcardgenius.ca',
            'search_url': 'https://creditcardgenius.ca/credit-cards',
            'priority': 1
        },
        'ratehub': {
            'base_url': 'https://www.ratehub.ca',
            'search_url': 'https://www.ratehub.ca/credit-cards',
            'priority': 2
        },
        'greedyrates': {
            'base_url': 'https://www.greedyrates.ca',
            'search_url': 'https://www.greedyrates.ca/credit-cards',
            'priority': 3
        },
        'nerdwallet': {
            'base_url': 'https://www.nerdwallet.com/ca',
            'search_url': 'https://www.nerdwallet.com/ca/credit-cards',
            'priority': 4
        },
        'moneysense': {
            'base_url': 'https://www.moneysense.ca',
            'search_url': 'https://www.moneysense.ca/save/credit-cards',
            'priority': 5
        }
    }

    def __init__(self, db_client=None, delay: float = 2.0):
        """Initialize scraper."""
        self.manager = CardMasterManager() if not db_client else CardMasterManager()
        self.delay = delay
        self.session = self._create_session()

        # Initialize matcher with master cards
        master_cards = self.manager.get_all_active_cards()
        self.matcher = CardMatcher(master_cards)

        logger.info(f"TargetedScraper initialized with {len(master_cards)} master cards")

    def _create_session(self) -> requests.Session:
        """Create HTTP session with appropriate headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-CA,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        return session

    def scrape_card(self, master_card: MasterCard) -> List[ScrapedCardData]:
        """
        Scrape all sources for a specific card.

        Args:
            master_card: The master card to search for

        Returns:
            List of ScrapedCardData from each source that found the card
        """
        results = []

        for source_name, source_config in self.SOURCES.items():
            try:
                logger.info(f"Scraping {source_name} for {master_card.canonical_name}")

                scraped = self._scrape_source(source_name, source_config, master_card)
                if scraped:
                    results.append(scraped)
                    logger.info(f"  Found data from {source_name} (confidence: {scraped.match_confidence:.2%})")
                else:
                    logger.debug(f"  Not found on {source_name}")

                time.sleep(self.delay)

            except Exception as e:
                logger.error(f"Error scraping {source_name} for {master_card.canonical_name}: {e}")

        return results

    def _scrape_source(self, source_name: str, config: Dict,
                       master_card: MasterCard) -> Optional[ScrapedCardData]:
        """Scrape a specific source for the card."""

        if source_name == 'creditcardgenius':
            return self._scrape_creditcardgenius(master_card)
        elif source_name == 'ratehub':
            return self._scrape_ratehub(master_card)
        elif source_name == 'greedyrates':
            return self._scrape_greedyrates(master_card)
        elif source_name == 'nerdwallet':
            return self._scrape_nerdwallet(master_card)
        elif source_name == 'moneysense':
            return self._scrape_moneysense(master_card)

        return None

    def _scrape_creditcardgenius(self, master_card: MasterCard) -> Optional[ScrapedCardData]:
        """Scrape CreditCardGenius for card data."""
        # Build search URL based on issuer
        issuer_slug = master_card.canonical_issuer.lower().replace(' ', '-')
        search_url = f"https://creditcardgenius.ca/credit-cards/{issuer_slug}"

        try:
            response = self.session.get(search_url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find card containers
            card_elements = soup.find_all(['article', 'div'], class_=re.compile(r'card|product', re.I))

            for element in card_elements:
                # Extract card name
                name_elem = element.find(['h2', 'h3', 'h4'])
                if not name_elem:
                    continue

                card_name = name_elem.get_text(strip=True)

                # Match against master card
                match = self.matcher.find_best_match(card_name, master_card.canonical_issuer)

                if match.master_card and match.master_card.id == master_card.id and match.confidence >= 0.85:
                    # Found it! Extract data
                    return self._extract_creditcardgenius_data(element, master_card, match.confidence, search_url)

            return None

        except Exception as e:
            logger.error(f"CreditCardGenius scrape error: {e}")
            return None

    def _extract_creditcardgenius_data(self, element, master_card: MasterCard,
                                        confidence: float, url: str) -> ScrapedCardData:
        """Extract card data from CreditCardGenius element."""
        data = ScrapedCardData(
            master_card_id=master_card.id,
            source_name='creditcardgenius',
            source_url=url,
            match_confidence=confidence
        )

        # Extract annual fee
        fee_elem = element.find(string=re.compile(r'\$\d+.*(?:annual|year|fee)', re.I))
        if fee_elem:
            fee_match = re.search(r'\$(\d+(?:\.\d{2})?)', fee_elem)
            if fee_match:
                data.annual_fee = float(fee_match.group(1))

        # Extract reward rate
        rate_elem = element.find(string=re.compile(r'(\d+(?:\.\d+)?)[x%]', re.I))
        if rate_elem:
            rate_match = re.search(r'(\d+(?:\.\d+)?)\s*([x%])', rate_elem)
            if rate_match:
                data.base_reward_rate = float(rate_match.group(1))
                data.base_reward_unit = 'multiplier' if rate_match.group(2) == 'x' else 'percent'

        # Extract category rewards
        data.category_rewards = self._extract_category_rewards(element)

        # Store raw HTML for debugging
        data.raw_data = {'html': str(element)[:5000]}

        return data

    def _scrape_ratehub(self, master_card: MasterCard) -> Optional[ScrapedCardData]:
        """Scrape Ratehub for card data."""
        # Ratehub uses search parameter
        search_term = quote_plus(master_card.canonical_name)
        search_url = f"https://www.ratehub.ca/credit-cards?search={search_term}"

        try:
            response = self.session.get(search_url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find card listings
            card_elements = soup.find_all('div', class_=re.compile(r'card-listing|product-card', re.I))

            for element in card_elements:
                name_elem = element.find(['h2', 'h3', 'a'], class_=re.compile(r'card-name|title', re.I))
                if not name_elem:
                    continue

                card_name = name_elem.get_text(strip=True)
                match = self.matcher.find_best_match(card_name, master_card.canonical_issuer)

                if match.master_card and match.master_card.id == master_card.id and match.confidence >= 0.85:
                    return self._extract_ratehub_data(element, master_card, match.confidence, search_url)

            return None

        except Exception as e:
            logger.error(f"Ratehub scrape error: {e}")
            return None

    def _extract_ratehub_data(self, element, master_card: MasterCard,
                              confidence: float, url: str) -> ScrapedCardData:
        """Extract card data from Ratehub element."""
        data = ScrapedCardData(
            master_card_id=master_card.id,
            source_name='ratehub',
            source_url=url,
            match_confidence=confidence
        )

        # Extract annual fee
        fee_elem = element.find(string=re.compile(r'annual fee', re.I))
        if fee_elem:
            parent = fee_elem.parent
            fee_text = parent.get_text() if parent else str(fee_elem)
            fee_match = re.search(r'\$(\d+(?:\.\d{2})?)', fee_text)
            if fee_match:
                data.annual_fee = float(fee_match.group(1))

        data.raw_data = {'html': str(element)[:5000]}
        return data

    def _scrape_greedyrates(self, master_card: MasterCard) -> Optional[ScrapedCardData]:
        """Scrape GreedyRates for card data."""
        # Similar pattern to other scrapers
        search_url = f"https://www.greedyrates.ca/credit-cards/"

        try:
            response = self.session.get(search_url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Search for card name in page content
            card_mentions = soup.find_all(string=re.compile(re.escape(master_card.canonical_name[:30]), re.I))

            if card_mentions:
                # Found mention, try to extract data from context
                for mention in card_mentions:
                    parent = mention.find_parent(['article', 'div', 'section'])
                    if parent:
                        return self._extract_greedyrates_data(parent, master_card, 0.80, search_url)

            return None

        except Exception as e:
            logger.error(f"GreedyRates scrape error: {e}")
            return None

    def _extract_greedyrates_data(self, element, master_card: MasterCard,
                                   confidence: float, url: str) -> ScrapedCardData:
        """Extract card data from GreedyRates element."""
        data = ScrapedCardData(
            master_card_id=master_card.id,
            source_name='greedyrates',
            source_url=url,
            match_confidence=confidence
        )

        text = element.get_text()

        # Extract annual fee
        fee_match = re.search(r'annual fee[:\s]*\$?(\d+(?:\.\d{2})?)', text, re.I)
        if fee_match:
            data.annual_fee = float(fee_match.group(1))

        data.raw_data = {'text': text[:3000]}
        return data

    def _scrape_nerdwallet(self, master_card: MasterCard) -> Optional[ScrapedCardData]:
        """Scrape NerdWallet Canada for card data."""
        search_url = "https://www.nerdwallet.com/ca/credit-cards"

        try:
            response = self.session.get(search_url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Search for card name
            card_mentions = soup.find_all(string=re.compile(re.escape(master_card.canonical_name[:25]), re.I))

            for mention in card_mentions:
                parent = mention.find_parent(['article', 'div'])
                if parent:
                    return ScrapedCardData(
                        master_card_id=master_card.id,
                        source_name='nerdwallet',
                        source_url=search_url,
                        match_confidence=0.75,
                        raw_data={'text': parent.get_text()[:2000]}
                    )

            return None

        except Exception as e:
            logger.error(f"NerdWallet scrape error: {e}")
            return None

    def _scrape_moneysense(self, master_card: MasterCard) -> Optional[ScrapedCardData]:
        """Scrape MoneySense for card data."""
        search_url = "https://www.moneysense.ca/save/credit-cards/best-credit-cards-in-canada/"

        try:
            response = self.session.get(search_url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Search for card name in article
            card_mentions = soup.find_all(string=re.compile(re.escape(master_card.canonical_name[:20]), re.I))

            for mention in card_mentions:
                parent = mention.find_parent(['section', 'div', 'article'])
                if parent:
                    return ScrapedCardData(
                        master_card_id=master_card.id,
                        source_name='moneysense',
                        source_url=search_url,
                        match_confidence=0.70,
                        raw_data={'text': parent.get_text()[:2000]}
                    )

            return None

        except Exception as e:
            logger.error(f"MoneySense scrape error: {e}")
            return None

    def _extract_category_rewards(self, element) -> List[Dict]:
        """Extract category rewards from element."""
        rewards = []

        category_patterns = {
            'groceries': r'grocer(?:y|ies)',
            'dining': r'din(?:ing|e)|restaurant',
            'gas': r'gas|fuel|petrol',
            'travel': r'travel|flight|hotel|airline',
            'drugstore': r'drug(?:store)?|pharmacy',
            'entertainment': r'entertainment|movie|streaming',
            'transit': r'transit|uber|lyft',
            'online_shopping': r'online|amazon'
        }

        text = element.get_text()

        for category, pattern in category_patterns.items():
            # Look for patterns like "5x on groceries" or "5% on dining"
            match = re.search(rf'(\d+(?:\.\d+)?)\s*([x%])\s*(?:on\s+)?{pattern}', text, re.I)
            if match:
                rewards.append({
                    'category': category,
                    'multiplier': float(match.group(1)),
                    'reward_unit': 'multiplier' if match.group(2) == 'x' else 'percent'
                })

        return rewards

    def scrape_all_cards(self, limit: Optional[int] = None) -> Dict[str, List[ScrapedCardData]]:
        """
        Scrape all master cards.

        Args:
            limit: Optional limit on number of cards to scrape

        Returns:
            Dict mapping master_card_id to list of scraped data
        """
        master_cards = self.manager.get_all_active_cards()
        if limit:
            master_cards = master_cards[:limit]

        logger.info(f"Starting scrape for {len(master_cards)} cards")

        results = {}
        found_count = 0
        not_found_count = 0

        for i, card in enumerate(master_cards, 1):
            logger.info(f"[{i}/{len(master_cards)}] Scraping {card.canonical_name}")

            scraped = self.scrape_card(card)

            if scraped:
                results[card.id] = scraped
                found_count += 1
                self.manager.update_scrape_status(card.id, 'found', found=True)
            else:
                not_found_count += 1
                self.manager.update_scrape_status(card.id, 'not_found', found=False)
                logger.warning(f"  Card not found on any source: {card.canonical_name}")

        logger.info(f"Scraping complete: {found_count} found, {not_found_count} not found")
        return results


# CLI
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Targeted Credit Card Scraper')
    parser.add_argument('--card', type=str, help='Scrape specific card by name')
    parser.add_argument('--all', action='store_true', help='Scrape all cards')
    parser.add_argument('--limit', type=int, help='Limit number of cards')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests')
    args = parser.parse_args()

    scraper = TargetedScraper(delay=args.delay)

    if args.card:
        card = scraper.manager.get_card_by_name(args.card)
        if card:
            results = scraper.scrape_card(card)
            print(f"Found {len(results)} sources for {card.canonical_name}")
            for r in results:
                print(f"  - {r.source_name}: fee=${r.annual_fee}, confidence={r.match_confidence:.2%}")
        else:
            print(f"Card not found: {args.card}")

    elif args.all:
        results = scraper.scrape_all_cards(limit=args.limit)
        print(f"Scraped {len(results)} cards with data")

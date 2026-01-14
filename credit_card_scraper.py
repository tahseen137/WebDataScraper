"""
Credit Card Scraper - Scrapes Canadian credit card information for the Rewards Optimizer.
Populates the Supabase database with card data, category rewards, and signup bonuses.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
from enum import Enum


class RewardCurrency(Enum):
    CASHBACK = "cashback"
    POINTS = "points"
    AIRLINE_MILES = "airline_miles"
    HOTEL_POINTS = "hotel_points"


class SpendingCategory(Enum):
    GROCERIES = "groceries"
    DINING = "dining"
    GAS = "gas"
    TRAVEL = "travel"
    ONLINE_SHOPPING = "online_shopping"
    ENTERTAINMENT = "entertainment"
    DRUGSTORES = "drugstores"
    HOME_IMPROVEMENT = "home_improvement"
    OTHER = "other"


@dataclass
class CategoryReward:
    category: str
    multiplier: float
    reward_unit: str  # "percent" or "multiplier"
    description: str
    description_fr: Optional[str] = None
    has_spend_limit: bool = False
    spend_limit: Optional[float] = None
    spend_limit_period: Optional[str] = None


@dataclass
class SignupBonus:
    bonus_amount: int
    bonus_currency: str
    spend_requirement: float
    timeframe_days: int
    valid_until: Optional[str] = None


@dataclass
class CreditCard:
    card_key: str
    name: str
    issuer: str
    reward_program: str
    reward_currency: str
    point_valuation: float
    annual_fee: float
    base_reward_rate: float
    base_reward_unit: str = "percent"
    name_fr: Optional[str] = None
    image_url: Optional[str] = None
    apply_url: Optional[str] = None
    category_rewards: list = None
    signup_bonus: Optional[SignupBonus] = None

    def __post_init__(self):
        if self.category_rewards is None:
            self.category_rewards = []


class CreditCardScraper:
    """Scrapes Canadian credit card information from various sources."""

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8',
        }
        self.cards: list[CreditCard] = []
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _generate_card_key(self, name: str, issuer: str) -> str:
        """Generate a unique card key from name and issuer."""
        combined = f"{issuer}-{name}"
        key = combined.lower()
        key = re.sub(r'[^a-z0-9\s-]', '', key)
        key = re.sub(r'\s+', '-', key)
        key = re.sub(r'-+', '-', key)
        return key.strip('-')

    def _parse_annual_fee(self, fee_text: str) -> float:
        """Parse annual fee from text like '$139' or 'No annual fee'."""
        if not fee_text:
            return 0.0
        fee_text = fee_text.lower().strip()
        if 'no' in fee_text or 'free' in fee_text or fee_text == '$0':
            return 0.0
        match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', fee_text)
        if match:
            return float(match.group(1).replace(',', ''))
        return 0.0

    def _parse_reward_rate(self, rate_text: str) -> tuple[float, str]:
        """Parse reward rate from text like '5%' or '5x'."""
        if not rate_text:
            return (1.0, "percent")
        rate_text = rate_text.lower().strip()
        # Check for multiplier (e.g., "5x")
        match = re.search(r'([\d.]+)\s*x', rate_text)
        if match:
            return (float(match.group(1)), "multiplier")
        # Check for percentage (e.g., "5%")
        match = re.search(r'([\d.]+)\s*%', rate_text)
        if match:
            return (float(match.group(1)), "percent")
        # Try to find any number
        match = re.search(r'([\d.]+)', rate_text)
        if match:
            return (float(match.group(1)), "percent")
        return (1.0, "percent")


    def _map_category(self, category_text: str) -> str:
        """Map category text to SpendingCategory enum value."""
        category_text = category_text.lower()
        mappings = {
            'grocery': SpendingCategory.GROCERIES.value,
            'groceries': SpendingCategory.GROCERIES.value,
            'supermarket': SpendingCategory.GROCERIES.value,
            'food': SpendingCategory.GROCERIES.value,
            'dining': SpendingCategory.DINING.value,
            'restaurant': SpendingCategory.DINING.value,
            'restaurants': SpendingCategory.DINING.value,
            'eat': SpendingCategory.DINING.value,
            'gas': SpendingCategory.GAS.value,
            'fuel': SpendingCategory.GAS.value,
            'petrol': SpendingCategory.GAS.value,
            'travel': SpendingCategory.TRAVEL.value,
            'hotel': SpendingCategory.TRAVEL.value,
            'flight': SpendingCategory.TRAVEL.value,
            'airline': SpendingCategory.TRAVEL.value,
            'online': SpendingCategory.ONLINE_SHOPPING.value,
            'amazon': SpendingCategory.ONLINE_SHOPPING.value,
            'entertainment': SpendingCategory.ENTERTAINMENT.value,
            'movie': SpendingCategory.ENTERTAINMENT.value,
            'streaming': SpendingCategory.ENTERTAINMENT.value,
            'drugstore': SpendingCategory.DRUGSTORES.value,
            'pharmacy': SpendingCategory.DRUGSTORES.value,
            'drug': SpendingCategory.DRUGSTORES.value,
            'home': SpendingCategory.HOME_IMPROVEMENT.value,
            'hardware': SpendingCategory.HOME_IMPROVEMENT.value,
            'transit': SpendingCategory.OTHER.value,
            'recurring': SpendingCategory.OTHER.value,
        }
        for key, value in mappings.items():
            if key in category_text:
                return value
        return SpendingCategory.OTHER.value

    def _determine_reward_currency(self, program: str, card_name: str) -> str:
        """Determine reward currency based on program name."""
        program_lower = program.lower()
        name_lower = card_name.lower()
        
        if any(x in program_lower for x in ['aeroplan', 'air miles', 'avion', 'westjet']):
            return RewardCurrency.AIRLINE_MILES.value
        if any(x in program_lower for x in ['marriott', 'hilton', 'bonvoy']):
            return RewardCurrency.HOTEL_POINTS.value
        if any(x in program_lower or x in name_lower for x in ['cash', 'cashback', 'cash back']):
            return RewardCurrency.CASHBACK.value
        return RewardCurrency.POINTS.value

    def _estimate_point_value(self, reward_currency: str, program: str) -> float:
        """Estimate point value in CAD cents based on program."""
        program_lower = program.lower()
        
        if reward_currency == RewardCurrency.CASHBACK.value:
            return 1.0
        if 'aeroplan' in program_lower:
            return 1.8
        if 'membership rewards' in program_lower or 'amex' in program_lower:
            return 2.0
        if 'scene' in program_lower:
            return 1.0
        if 'avion' in program_lower:
            return 1.5
        if 'td rewards' in program_lower:
            return 0.5
        if 'bmo rewards' in program_lower:
            return 0.7
        if 'aventura' in program_lower:
            return 1.0
        if reward_currency == RewardCurrency.AIRLINE_MILES.value:
            return 1.5
        if reward_currency == RewardCurrency.HOTEL_POINTS.value:
            return 0.7
        return 1.0


    def scrape_ratehub(self) -> list[CreditCard]:
        """Scrape credit card data from Ratehub.ca (Canadian comparison site)."""
        print("Scraping Ratehub.ca for Canadian credit cards...")
        cards = []
        
        # Ratehub categories to scrape
        categories = [
            ('cash-back', 'Cashback'),
            ('travel', 'Travel'),
            ('rewards', 'Rewards'),
            ('no-fee', 'No Fee'),
        ]
        
        for category_slug, category_name in categories:
            url = f"https://www.ratehub.ca/credit-cards/{category_slug}"
            print(f"  Fetching {category_name} cards from {url}")
            
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Find card listings (structure may vary)
                card_elements = soup.find_all('div', class_=re.compile(r'card-listing|product-card'))
                
                for card_el in card_elements:
                    try:
                        card = self._parse_ratehub_card(card_el, category_name)
                        if card and card.card_key not in [c.card_key for c in cards]:
                            cards.append(card)
                    except Exception as e:
                        print(f"    Error parsing card: {e}")
                        continue
                
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"  Error fetching {url}: {e}")
                continue
        
        print(f"Found {len(cards)} cards from Ratehub")
        return cards

    def _parse_ratehub_card(self, card_el, category: str) -> Optional[CreditCard]:
        """Parse a single card element from Ratehub."""
        # Try to find card name
        name_el = card_el.find(['h2', 'h3', 'h4'], class_=re.compile(r'card-name|title'))
        if not name_el:
            name_el = card_el.find('a', class_=re.compile(r'card-name|title'))
        if not name_el:
            return None
        
        name = name_el.get_text(strip=True)
        if not name:
            return None
        
        # Try to find issuer
        issuer = self._extract_issuer(name)
        
        # Try to find annual fee
        fee_el = card_el.find(string=re.compile(r'annual fee|yearly fee', re.I))
        annual_fee = 0.0
        if fee_el:
            fee_text = fee_el.find_parent().get_text() if fee_el.find_parent() else str(fee_el)
            annual_fee = self._parse_annual_fee(fee_text)
        
        # Determine reward program and currency
        reward_program = self._extract_reward_program(name)
        reward_currency = self._determine_reward_currency(reward_program, name)
        point_valuation = self._estimate_point_value(reward_currency, reward_program)
        
        # Generate card key
        card_key = self._generate_card_key(name, issuer)
        
        return CreditCard(
            card_key=card_key,
            name=name,
            issuer=issuer,
            reward_program=reward_program,
            reward_currency=reward_currency,
            point_valuation=point_valuation,
            annual_fee=annual_fee,
            base_reward_rate=1.0,
            base_reward_unit="percent",
        )


    def _extract_issuer(self, card_name: str) -> str:
        """Extract issuer from card name."""
        issuers = {
            'TD': ['td ', 'td-'],
            'RBC': ['rbc ', 'royal bank'],
            'BMO': ['bmo '],
            'CIBC': ['cibc '],
            'Scotiabank': ['scotiabank', 'scotia '],
            'American Express': ['amex', 'american express'],
            'MBNA': ['mbna '],
            'Capital One': ['capital one'],
            'Tangerine': ['tangerine'],
            'Simplii': ['simplii'],
            'PC Financial': ['pc ', 'president'],
            'HSBC': ['hsbc'],
            'National Bank': ['national bank'],
            'Desjardins': ['desjardins'],
        }
        
        name_lower = card_name.lower()
        for issuer, patterns in issuers.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return issuer
        return "Unknown"

    def _extract_reward_program(self, card_name: str) -> str:
        """Extract reward program from card name."""
        programs = {
            'Aeroplan': ['aeroplan'],
            'Scene+': ['scene'],
            'Air Miles': ['air miles'],
            'Avion': ['avion'],
            'TD Rewards': ['td rewards', 'td first class'],
            'BMO Rewards': ['bmo rewards'],
            'Aventura': ['aventura'],
            'Membership Rewards': ['membership rewards', 'amex', 'cobalt', 'gold rewards', 'platinum'],
            'Cashback': ['cash back', 'cashback', 'cash-back'],
            'PC Optimum': ['pc optimum', 'pc financial'],
            'Triangle Rewards': ['triangle'],
            'Marriott Bonvoy': ['marriott', 'bonvoy'],
            'Hilton Honors': ['hilton'],
            'WestJet Rewards': ['westjet'],
        }
        
        name_lower = card_name.lower()
        for program, patterns in programs.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return program
        return "Points"

    def load_from_json(self, filepath: str) -> list[CreditCard]:
        """Load card data from a JSON file (e.g., existing cards.json)."""
        print(f"Loading cards from {filepath}...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cards = []
        for card_data in data.get('cards', []):
            category_rewards = []
            for cr in card_data.get('categoryRewards', []):
                rate = cr.get('rewardRate', {})
                category_rewards.append(CategoryReward(
                    category=cr.get('category', 'other'),
                    multiplier=rate.get('value', 1.0),
                    reward_unit=rate.get('unit', 'percent'),
                    description=f"{rate.get('value', 1)}{'%' if rate.get('unit') == 'percent' else 'x'} on {cr.get('category', 'purchases')}",
                ))
            
            signup_bonus = None
            sb_data = card_data.get('signupBonus')
            if sb_data:
                signup_bonus = SignupBonus(
                    bonus_amount=sb_data.get('amount', 0),
                    bonus_currency=sb_data.get('currency', 'points'),
                    spend_requirement=sb_data.get('spendRequirement', 0),
                    timeframe_days=sb_data.get('timeframeDays', 90),
                )
            
            base_rate = card_data.get('baseRewardRate', {})
            card = CreditCard(
                card_key=card_data.get('id', ''),
                name=card_data.get('name', ''),
                issuer=card_data.get('issuer', ''),
                reward_program=card_data.get('rewardProgram', ''),
                reward_currency=base_rate.get('type', 'points'),
                point_valuation=1.0,
                annual_fee=card_data.get('annualFee', 0),
                base_reward_rate=base_rate.get('value', 1.0),
                base_reward_unit=base_rate.get('unit', 'percent'),
                category_rewards=category_rewards,
                signup_bonus=signup_bonus,
            )
            cards.append(card)
        
        print(f"Loaded {len(cards)} cards from JSON")
        return cards


    def save_to_json(self, filepath: str = 'credit_cards.json'):
        """Save scraped cards to JSON file."""
        data = {
            'scraped_at': datetime.now().isoformat(),
            'count': len(self.cards),
            'cards': [self._card_to_dict(card) for card in self.cards]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(self.cards)} cards to {filepath}")

    def _card_to_dict(self, card: CreditCard) -> dict:
        """Convert CreditCard to dictionary for JSON serialization."""
        result = {
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
            'category_rewards': [asdict(cr) for cr in card.category_rewards],
        }
        if card.signup_bonus:
            result['signup_bonus'] = asdict(card.signup_bonus)
        return result

    def upload_to_supabase(self):
        """Upload all scraped cards to Supabase."""
        from credit_card_uploader import CreditCardUploader
        
        uploader = CreditCardUploader()
        result = uploader.upload_cards(self.cards)
        return result


def main():
    """Main entry point for the credit card scraper."""
    scraper = CreditCardScraper(delay=2.0)
    
    print("=" * 60)
    print("Canadian Credit Card Scraper")
    print("=" * 60)
    print("\nOptions:")
    print("1. Load from existing JSON file (fintech-idea/rewards-optimizer/src/data/cards.json)")
    print("2. Scrape from web sources")
    print("3. Both (load JSON + scrape for updates)")
    
    choice = input("\nSelect option (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        json_path = input("JSON file path (or press Enter for default): ").strip()
        if not json_path:
            json_path = "../fintech-idea/rewards-optimizer/src/data/cards.json"
        
        try:
            json_cards = scraper.load_from_json(json_path)
            scraper.cards.extend(json_cards)
        except Exception as e:
            print(f"Error loading JSON: {e}")
    
    if choice in ['2', '3']:
        try:
            web_cards = scraper.scrape_ratehub()
            # Add only new cards not already in the list
            existing_keys = {c.card_key for c in scraper.cards}
            for card in web_cards:
                if card.card_key not in existing_keys:
                    scraper.cards.append(card)
        except Exception as e:
            print(f"Error scraping web: {e}")
    
    if not scraper.cards:
        print("No cards found. Exiting.")
        return
    
    print(f"\nTotal cards: {len(scraper.cards)}")
    
    # Display summary
    print("\nCards by issuer:")
    issuers = {}
    for card in scraper.cards:
        issuers[card.issuer] = issuers.get(card.issuer, 0) + 1
    for issuer, count in sorted(issuers.items(), key=lambda x: -x[1]):
        print(f"  {issuer}: {count}")
    
    # Save/upload options
    action = input("\nAction (json/supabase/both/none): ").strip().lower()
    
    if action in ['json', 'both']:
        output_file = input("Output filename (default: credit_cards.json): ").strip()
        if not output_file:
            output_file = "credit_cards.json"
        scraper.save_to_json(output_file)
    
    if action in ['supabase', 'both']:
        try:
            result = scraper.upload_to_supabase()
            print(f"Upload result: {result}")
        except Exception as e:
            print(f"Upload failed: {e}")
            print("Make sure SUPABASE_URL and SUPABASE_KEY are set in .env")


if __name__ == '__main__':
    main()

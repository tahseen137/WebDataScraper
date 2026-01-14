"""
Automated Credit Card Scraper
Scrapes Canadian credit card data from websites and uploads to Supabase.
No user input required - just run it.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class CategoryReward:
    category: str
    multiplier: float
    reward_unit: str
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


class CreditCardWebScraper:
    """Scrapes credit card data from Canadian financial websites."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-CA,en;q=0.9',
        })
        self.cards = []
        self.delay = 2.0

    def _generate_card_key(self, name: str, issuer: str) -> str:
        combined = f"{issuer}-{name}"
        key = combined.lower()
        key = re.sub(r'[^a-z0-9\s-]', '', key)
        key = re.sub(r'\s+', '-', key)
        key = re.sub(r'-+', '-', key)
        return key.strip('-')[:100]

    def _parse_fee(self, text: str) -> float:
        if not text:
            return 0.0
        text = text.lower().strip()
        if 'no' in text or 'free' in text or '$0' in text:
            return 0.0
        match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', text)
        return float(match.group(1).replace(',', '')) if match else 0.0

    def _parse_rate(self, text: str) -> tuple:
        if not text:
            return (1.0, "percent")
        text = text.lower()
        match = re.search(r'([\d.]+)\s*x', text)
        if match:
            return (float(match.group(1)), "multiplier")
        match = re.search(r'([\d.]+)\s*%', text)
        if match:
            return (float(match.group(1)), "percent")
        match = re.search(r'([\d.]+)', text)
        return (float(match.group(1)), "percent") if match else (1.0, "percent")

    def _get_reward_currency(self, program: str, name: str) -> str:
        text = (program + " " + name).lower()
        if any(x in text for x in ['aeroplan', 'air miles', 'avion', 'westjet', 'miles']):
            return "airline_miles"
        if any(x in text for x in ['marriott', 'hilton', 'bonvoy', 'hotel']):
            return "hotel_points"
        if any(x in text for x in ['cash', 'cashback']):
            return "cashback"
        return "points"

    def _get_point_value(self, currency: str, program: str) -> float:
        program = program.lower()
        if currency == "cashback":
            return 1.0
        if 'aeroplan' in program:
            return 1.8
        if 'membership rewards' in program or 'cobalt' in program:
            return 2.0
        if 'scene' in program:
            return 1.0
        if 'avion' in program:
            return 1.5
        return 1.0

    def _extract_issuer(self, name: str) -> str:
        issuers = {
            'TD': ['td '], 'RBC': ['rbc '], 'BMO': ['bmo '],
            'CIBC': ['cibc '], 'Scotiabank': ['scotiabank', 'scotia '],
            'American Express': ['amex', 'american express'],
            'MBNA': ['mbna'], 'Capital One': ['capital one'],
            'Tangerine': ['tangerine'], 'Simplii': ['simplii'],
            'PC Financial': ['pc '], 'HSBC': ['hsbc'],
            'National Bank': ['national bank'], 'Desjardins': ['desjardins'],
        }
        name_lower = name.lower()
        for issuer, patterns in issuers.items():
            if any(p in name_lower for p in patterns):
                return issuer
        return "Other"

    def _extract_program(self, name: str) -> str:
        programs = {
            'Aeroplan': ['aeroplan'], 'Scene+': ['scene'],
            'Air Miles': ['air miles'], 'Avion': ['avion'],
            'TD Rewards': ['td rewards'], 'BMO Rewards': ['bmo rewards'],
            'Aventura': ['aventura'], 'Membership Rewards': ['cobalt', 'gold', 'platinum'],
            'Cashback': ['cash back', 'cashback'], 'PC Optimum': ['pc optimum'],
            'Triangle Rewards': ['triangle'], 'WestJet Rewards': ['westjet'],
        }
        name_lower = name.lower()
        for program, patterns in programs.items():
            if any(p in name_lower for p in patterns):
                return program
        return "Points"


    def scrape_creditcardgenius(self) -> list:
        """Scrape from CreditCardGenius.ca - Canadian credit card comparison site."""
        print("\n[1/3] Scraping CreditCardGenius.ca...")
        cards = []
        
        urls = [
            "https://creditcardgenius.ca/best-credit-cards/cash-back",
            "https://creditcardgenius.ca/best-credit-cards/travel",
            "https://creditcardgenius.ca/best-credit-cards/rewards",
            "https://creditcardgenius.ca/best-credit-cards/no-fee",
        ]
        
        for url in urls:
            try:
                print(f"  Fetching: {url}")
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, 'lxml')
                
                # Find card containers
                card_divs = soup.find_all('div', class_=re.compile(r'card-item|product-card|credit-card'))
                
                for div in card_divs:
                    try:
                        # Try to find card name
                        name_el = div.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|heading'))
                        if not name_el:
                            name_el = div.find(['h2', 'h3', 'h4'])
                        if not name_el:
                            continue
                        
                        name = name_el.get_text(strip=True)
                        if not name or len(name) < 5:
                            continue
                        
                        issuer = self._extract_issuer(name)
                        program = self._extract_program(name)
                        currency = self._get_reward_currency(program, name)
                        
                        # Try to find annual fee
                        fee = 0.0
                        fee_el = div.find(string=re.compile(r'annual fee|yearly', re.I))
                        if fee_el:
                            fee = self._parse_fee(fee_el.parent.get_text() if fee_el.parent else str(fee_el))
                        
                        card = CreditCard(
                            card_key=self._generate_card_key(name, issuer),
                            name=name,
                            issuer=issuer,
                            reward_program=program,
                            reward_currency=currency,
                            point_valuation=self._get_point_value(currency, program),
                            annual_fee=fee,
                            base_reward_rate=1.0,
                        )
                        
                        if card.card_key not in [c.card_key for c in cards]:
                            cards.append(card)
                            
                    except Exception as e:
                        continue
                
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"  Error: {e}")
        
        print(f"  Found {len(cards)} cards")
        return cards

    def scrape_greedyrates(self) -> list:
        """Scrape from GreedyRates.ca - Canadian credit card reviews."""
        print("\n[2/3] Scraping GreedyRates.ca...")
        cards = []
        
        urls = [
            "https://www.greedyrates.ca/blog/best-cash-back-credit-cards-canada/",
            "https://www.greedyrates.ca/blog/best-travel-credit-cards-canada/",
            "https://www.greedyrates.ca/blog/best-rewards-credit-cards-canada/",
        ]
        
        for url in urls:
            try:
                print(f"  Fetching: {url}")
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, 'lxml')
                
                # Find card mentions in article
                headings = soup.find_all(['h2', 'h3'], string=re.compile(r'(TD|RBC|BMO|CIBC|Scotiabank|Amex|MBNA|Tangerine|Simplii)', re.I))
                
                for heading in headings:
                    try:
                        name = heading.get_text(strip=True)
                        # Clean up the name
                        name = re.sub(r'^\d+\.\s*', '', name)  # Remove numbering
                        name = re.sub(r'\s*[-–]\s*.*$', '', name)  # Remove trailing descriptions
                        
                        if len(name) < 10:
                            continue
                        
                        issuer = self._extract_issuer(name)
                        program = self._extract_program(name)
                        currency = self._get_reward_currency(program, name)
                        
                        card = CreditCard(
                            card_key=self._generate_card_key(name, issuer),
                            name=name,
                            issuer=issuer,
                            reward_program=program,
                            reward_currency=currency,
                            point_valuation=self._get_point_value(currency, program),
                            annual_fee=0.0,
                            base_reward_rate=1.0,
                        )
                        
                        if card.card_key not in [c.card_key for c in cards]:
                            cards.append(card)
                            
                    except Exception:
                        continue
                
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"  Error: {e}")
        
        print(f"  Found {len(cards)} cards")
        return cards


    def scrape_nerdwallet(self) -> list:
        """Scrape from NerdWallet Canada."""
        print("\n[3/3] Scraping NerdWallet.com/ca...")
        cards = []
        
        urls = [
            "https://www.nerdwallet.com/ca/credit-cards/best-cash-back-credit-cards",
            "https://www.nerdwallet.com/ca/credit-cards/best-travel-credit-cards",
            "https://www.nerdwallet.com/ca/credit-cards/best-rewards-credit-cards",
        ]
        
        for url in urls:
            try:
                print(f"  Fetching: {url}")
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, 'lxml')
                
                # Find card names in the page
                card_elements = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'(Visa|Mastercard|Card)', re.I))
                
                for el in card_elements:
                    try:
                        name = el.get_text(strip=True)
                        if len(name) < 10 or len(name) > 100:
                            continue
                        
                        issuer = self._extract_issuer(name)
                        if issuer == "Other":
                            continue
                            
                        program = self._extract_program(name)
                        currency = self._get_reward_currency(program, name)
                        
                        card = CreditCard(
                            card_key=self._generate_card_key(name, issuer),
                            name=name,
                            issuer=issuer,
                            reward_program=program,
                            reward_currency=currency,
                            point_valuation=self._get_point_value(currency, program),
                            annual_fee=0.0,
                            base_reward_rate=1.0,
                        )
                        
                        if card.card_key not in [c.card_key for c in cards]:
                            cards.append(card)
                            
                    except Exception:
                        continue
                
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"  Error: {e}")
        
        print(f"  Found {len(cards)} cards")
        return cards

    def scrape_all(self) -> list:
        """Scrape from all sources."""
        all_cards = []
        seen_keys = set()
        
        # Scrape each source
        for scrape_func in [self.scrape_creditcardgenius, self.scrape_greedyrates, self.scrape_nerdwallet]:
            try:
                cards = scrape_func()
                for card in cards:
                    if card.card_key not in seen_keys:
                        all_cards.append(card)
                        seen_keys.add(card.card_key)
            except Exception as e:
                print(f"  Source error: {e}")
        
        self.cards = all_cards
        return all_cards


def upload_to_supabase(cards: list) -> dict:
    """Upload cards to Supabase."""
    from supabase import create_client
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    
    client = create_client(url, key)
    results = {'inserted': 0, 'updated': 0, 'errors': []}
    
    for card in cards:
        try:
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
            }
            
            # Check if exists
            existing = client.table('cards').select('id').eq('card_key', card.card_key).execute()
            
            if existing.data:
                client.table('cards').update(card_data).eq('card_key', card.card_key).execute()
                results['updated'] += 1
            else:
                client.table('cards').insert(card_data).execute()
                results['inserted'] += 1
                
        except Exception as e:
            results['errors'].append({'card': card.card_key, 'error': str(e)})
    
    return results


def main():
    print("=" * 60)
    print("Canadian Credit Card Web Scraper")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Scrape cards
    scraper = CreditCardWebScraper()
    cards = scraper.scrape_all()
    
    print("\n" + "=" * 60)
    print(f"Total unique cards found: {len(cards)}")
    
    if cards:
        # Show by issuer
        issuers = {}
        for card in cards:
            issuers[card.issuer] = issuers.get(card.issuer, 0) + 1
        print("\nBy issuer:")
        for issuer, count in sorted(issuers.items(), key=lambda x: -x[1]):
            print(f"  {issuer}: {count}")
        
        # Save to JSON
        output = {
            'scraped_at': datetime.now().isoformat(),
            'count': len(cards),
            'cards': [asdict(c) for c in cards]
        }
        with open('scraped_cards.json', 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nSaved to scraped_cards.json")
        
        # Upload to Supabase
        print("\nUploading to Supabase...")
        try:
            result = upload_to_supabase(cards)
            print(f"  Inserted: {result['inserted']}")
            print(f"  Updated: {result['updated']}")
            if result['errors']:
                print(f"  Errors: {len(result['errors'])}")
        except ValueError as e:
            print(f"  Skipped: {e}")
        except Exception as e:
            print(f"  Upload failed: {e}")
    
    print("\n" + "=" * 60)
    print("Done!")


if __name__ == '__main__':
    main()

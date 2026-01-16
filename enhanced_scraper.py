"""
Enhanced Canadian Credit Card Scraper
- Multiple data sources for comprehensive coverage
- Extracts detailed reward rates and category bonuses
- Data verification and validation step
- Automatic upload to Supabase
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
import os
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class CategoryReward:
    category: str
    multiplier: float
    reward_unit: str
    description: str
    description_fr: Optional[str] = None
    has_spend_limit: bool = False
    spend_limit: Optional[float] = None


@dataclass
class SignupBonus:
    bonus_amount: int
    bonus_currency: str
    spend_requirement: float
    timeframe_days: int


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
    category_rewards: List[CategoryReward] = field(default_factory=list)
    signup_bonus: Optional[SignupBonus] = None
    source: str = ""  # Track where data came from
    confidence: float = 0.0  # Data confidence score 0-1
    last_verified: Optional[str] = None


# =============================================================================
# Known Canadian Credit Cards Database (for verification)
# =============================================================================

KNOWN_CARDS = {
    # TD Cards
    "td-aeroplan-visa-infinite": {"issuer": "TD", "program": "Aeroplan", "fee_range": (120, 160)},
    "td-cash-back-visa-infinite": {"issuer": "TD", "program": "Cashback", "fee_range": (0, 150)},
    "td-first-class-travel-visa-infinite": {"issuer": "TD", "program": "TD Rewards", "fee_range": (120, 160)},
    
    # RBC Cards
    "rbc-avion-visa-infinite": {"issuer": "RBC", "program": "Avion", "fee_range": (120, 160)},
    "rbc-cash-back-mastercard": {"issuer": "RBC", "program": "Cashback", "fee_range": (0, 50)},
    
    # BMO Cards
    "bmo-eclipse-visa-infinite": {"issuer": "BMO", "program": "BMO Rewards", "fee_range": (150, 200)},
    "bmo-cash-back-mastercard": {"issuer": "BMO", "program": "Cashback", "fee_range": (0, 150)},
    
    # Scotiabank Cards
    "scotiabank-gold-amex": {"issuer": "Scotiabank", "program": "Scene+", "fee_range": (100, 160)},
    "scotiabank-scene-visa": {"issuer": "Scotiabank", "program": "Scene+", "fee_range": (0, 0)},
    
    # CIBC Cards
    "cibc-aventura-visa-infinite": {"issuer": "CIBC", "program": "Aventura", "fee_range": (120, 160)},
    "cibc-dividend-visa-infinite": {"issuer": "CIBC", "program": "Cashback", "fee_range": (0, 150)},
    
    # Amex Cards
    "amex-cobalt": {"issuer": "American Express", "program": "Membership Rewards", "fee_range": (150, 170)},
    "amex-gold-rewards": {"issuer": "American Express", "program": "Membership Rewards", "fee_range": (150, 200)},
    "amex-platinum": {"issuer": "American Express", "program": "Membership Rewards", "fee_range": (600, 800)},
    "amex-simply-cash": {"issuer": "American Express", "program": "Cashback", "fee_range": (0, 100)},
    
    # No-Fee Cards
    "tangerine-money-back": {"issuer": "Tangerine", "program": "Cashback", "fee_range": (0, 0)},
    "simplii-cash-back-visa": {"issuer": "Simplii", "program": "Cashback", "fee_range": (0, 0)},
    "pc-financial-mastercard": {"issuer": "PC Financial", "program": "PC Optimum", "fee_range": (0, 0)},
    "canadian-tire-triangle-mastercard": {"issuer": "Canadian Tire", "program": "Triangle Rewards", "fee_range": (0, 0)},
}


# Known category reward patterns for popular cards
KNOWN_CATEGORY_REWARDS = {
    "amex-cobalt": [
        {"category": "dining", "multiplier": 5.0, "unit": "multiplier"},
        {"category": "groceries", "multiplier": 5.0, "unit": "multiplier"},
        {"category": "travel", "multiplier": 2.0, "unit": "multiplier"},
    ],
    "td-aeroplan-visa-infinite": [
        {"category": "groceries", "multiplier": 1.5, "unit": "multiplier"},
        {"category": "gas", "multiplier": 1.5, "unit": "multiplier"},
    ],
    "scotiabank-gold-amex": [
        {"category": "groceries", "multiplier": 5.0, "unit": "multiplier"},
        {"category": "dining", "multiplier": 5.0, "unit": "multiplier"},
        {"category": "entertainment", "multiplier": 3.0, "unit": "multiplier"},
    ],
    "tangerine-money-back": [
        {"category": "groceries", "multiplier": 2.0, "unit": "percent"},
        {"category": "dining", "multiplier": 2.0, "unit": "percent"},
        {"category": "gas", "multiplier": 2.0, "unit": "percent"},
    ],
}


# =============================================================================
# Scraper Class
# =============================================================================

class EnhancedCreditCardScraper:
    """Enhanced scraper with multiple sources and data verification."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8',
        })
        self.cards: Dict[str, CreditCard] = {}  # key -> card
        self.delay = 2.0
        self.verification_results = []

    def _generate_key(self, name: str, issuer: str) -> str:
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
        if any(x in text for x in ['no annual', 'no fee', '$0', 'free']):
            return 0.0
        match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', text)
        return float(match.group(1).replace(',', '')) if match else 0.0

    def _parse_rate(self, text: str) -> tuple:
        if not text:
            return (1.0, "percent")
        text = text.lower()
        # Check for multiplier (5x, 5X)
        match = re.search(r'([\d.]+)\s*x', text)
        if match:
            return (float(match.group(1)), "multiplier")
        # Check for percentage (5%, 5 percent)
        match = re.search(r'([\d.]+)\s*%', text)
        if match:
            return (float(match.group(1)), "percent")
        match = re.search(r'([\d.]+)', text)
        return (float(match.group(1)), "percent") if match else (1.0, "percent")

    def _extract_category_rewards(self, text: str) -> List[CategoryReward]:
        """Extract category rewards from descriptive text."""
        rewards = []
        text = text.lower()
        
        patterns = [
            (r'(\d+(?:\.\d+)?)\s*[x%]\s*(?:on\s+)?(?:at\s+)?(groceries|grocery)', 'groceries'),
            (r'(\d+(?:\.\d+)?)\s*[x%]\s*(?:on\s+)?(?:at\s+)?(dining|restaurant)', 'dining'),
            (r'(\d+(?:\.\d+)?)\s*[x%]\s*(?:on\s+)?(?:at\s+)?(gas|fuel)', 'gas'),
            (r'(\d+(?:\.\d+)?)\s*[x%]\s*(?:on\s+)?(?:at\s+)?(travel)', 'travel'),
            (r'(\d+(?:\.\d+)?)\s*[x%]\s*(?:on\s+)?(?:at\s+)?(drugstore|pharmacy)', 'drugstores'),
            (r'(\d+(?:\.\d+)?)\s*[x%]\s*(?:on\s+)?(?:at\s+)?(entertainment|movie)', 'entertainment'),
            (r'(\d+(?:\.\d+)?)\s*[x%]\s*(?:on\s+)?(?:at\s+)?(online|amazon)', 'online_shopping'),
        ]
        
        for pattern, category in patterns:
            match = re.search(pattern, text)
            if match:
                rate = float(match.group(1))
                unit = "multiplier" if 'x' in text[match.start():match.end()+2] else "percent"
                rewards.append(CategoryReward(
                    category=category,
                    multiplier=rate,
                    reward_unit=unit,
                    description=f"{rate}{'x' if unit == 'multiplier' else '%'} on {category}"
                ))
        
        return rewards

    def _get_issuer(self, name: str) -> str:
        issuers = {
            'TD': ['td '], 'RBC': ['rbc '], 'BMO': ['bmo '],
            'CIBC': ['cibc '], 'Scotiabank': ['scotiabank', 'scotia '],
            'American Express': ['amex', 'american express'],
            'MBNA': ['mbna'], 'Capital One': ['capital one'],
            'Tangerine': ['tangerine'], 'Simplii': ['simplii'],
            'PC Financial': ['pc financial', 'pc '], 'HSBC': ['hsbc'],
            'National Bank': ['national bank'], 'Desjardins': ['desjardins'],
            'Canadian Tire': ['canadian tire', 'triangle'],
        }
        name_lower = name.lower()
        for issuer, patterns in issuers.items():
            if any(p in name_lower for p in patterns):
                return issuer
        return "Other"

    def _get_program(self, name: str) -> str:
        programs = {
            'Aeroplan': ['aeroplan'], 'Scene+': ['scene'],
            'Air Miles': ['air miles'], 'Avion': ['avion'],
            'TD Rewards': ['td rewards', 'first class'],
            'BMO Rewards': ['bmo rewards', 'eclipse'],
            'Aventura': ['aventura'],
            'Membership Rewards': ['cobalt', 'gold rewards', 'platinum', 'amex'],
            'Cashback': ['cash back', 'cashback', 'dividend', 'simply cash'],
            'PC Optimum': ['pc optimum', 'pc financial'],
            'Triangle Rewards': ['triangle'],
            'WestJet Rewards': ['westjet'],
        }
        name_lower = name.lower()
        for program, patterns in programs.items():
            if any(p in name_lower for p in patterns):
                return program
        return "Points"

    def _get_currency(self, program: str, name: str) -> str:
        text = (program + " " + name).lower()
        if any(x in text for x in ['aeroplan', 'air miles', 'avion', 'westjet', 'miles']):
            return "airline_miles"
        if any(x in text for x in ['marriott', 'hilton', 'bonvoy', 'hotel']):
            return "hotel_points"
        if any(x in text for x in ['cash', 'cashback', 'dividend']):
            return "cashback"
        return "points"

    def _get_point_value(self, currency: str, program: str) -> float:
        program = program.lower()
        values = {
            "cashback": 1.0, "aeroplan": 1.8, "membership rewards": 2.0,
            "scene": 1.0, "avion": 1.5, "td rewards": 0.5,
            "bmo rewards": 0.7, "aventura": 1.0, "pc optimum": 0.1,
            "triangle": 0.1, "air miles": 0.1,
        }
        if currency == "cashback":
            return 1.0
        for key, val in values.items():
            if key in program:
                return val
        return 1.0


    # =========================================================================
    # Source 1: CreditCardGenius.ca
    # =========================================================================
    def scrape_creditcardgenius(self):
        """Scrape from CreditCardGenius.ca - detailed card comparisons."""
        print("\n[1/5] Scraping CreditCardGenius.ca...")
        
        urls = [
            ("https://creditcardgenius.ca/best-credit-cards/cash-back", "cashback"),
            ("https://creditcardgenius.ca/best-credit-cards/travel", "travel"),
            ("https://creditcardgenius.ca/best-credit-cards/rewards", "rewards"),
            ("https://creditcardgenius.ca/best-credit-cards/no-fee", "no-fee"),
            ("https://creditcardgenius.ca/best-credit-cards/groceries", "groceries"),
        ]
        
        count = 0
        for url, category in urls:
            try:
                print(f"  Fetching: {category} cards...")
                resp = self.session.get(url, timeout=15)
                soup = BeautifulSoup(resp.content, 'lxml')
                
                # Find card containers
                for div in soup.find_all(['div', 'article'], class_=re.compile(r'card|product', re.I)):
                    card = self._parse_card_element(div, "creditcardgenius")
                    if card:
                        self._add_or_merge_card(card)
                        count += 1
                
                time.sleep(self.delay)
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"  Found {count} card entries")

    # =========================================================================
    # Source 2: Ratehub.ca
    # =========================================================================
    def scrape_ratehub(self):
        """Scrape from Ratehub.ca - comprehensive card database."""
        print("\n[2/5] Scraping Ratehub.ca...")
        
        urls = [
            "https://www.ratehub.ca/credit-cards/cash-back",
            "https://www.ratehub.ca/credit-cards/travel",
            "https://www.ratehub.ca/credit-cards/rewards",
            "https://www.ratehub.ca/credit-cards/no-fee",
        ]
        
        count = 0
        for url in urls:
            try:
                print(f"  Fetching: {url.split('/')[-1]}...")
                resp = self.session.get(url, timeout=15)
                soup = BeautifulSoup(resp.content, 'lxml')
                
                for div in soup.find_all(['div', 'article'], class_=re.compile(r'card|product|listing', re.I)):
                    card = self._parse_card_element(div, "ratehub")
                    if card:
                        self._add_or_merge_card(card)
                        count += 1
                
                time.sleep(self.delay)
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"  Found {count} card entries")

    # =========================================================================
    # Source 3: MoneySense.ca
    # =========================================================================
    def scrape_moneysense(self):
        """Scrape from MoneySense.ca - annual card rankings."""
        print("\n[3/5] Scraping MoneySense.ca...")
        
        urls = [
            "https://www.moneysense.ca/spend/credit-cards/best-credit-cards-in-canada/",
            "https://www.moneysense.ca/spend/credit-cards/best-cash-back-credit-cards-in-canada/",
            "https://www.moneysense.ca/spend/credit-cards/best-travel-credit-cards-in-canada/",
        ]
        
        count = 0
        for url in urls:
            try:
                print(f"  Fetching article...")
                resp = self.session.get(url, timeout=15)
                soup = BeautifulSoup(resp.content, 'lxml')
                
                # Find card mentions in headings
                for heading in soup.find_all(['h2', 'h3'], string=re.compile(r'(Visa|Mastercard|Card|Amex)', re.I)):
                    name = heading.get_text(strip=True)
                    name = re.sub(r'^\d+\.\s*', '', name)
                    
                    if len(name) > 10:
                        card = self._create_card_from_name(name, "moneysense")
                        if card:
                            self._add_or_merge_card(card)
                            count += 1
                
                time.sleep(self.delay)
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"  Found {count} card entries")

    # =========================================================================
    # Source 4: NerdWallet Canada
    # =========================================================================
    def scrape_nerdwallet(self):
        """Scrape from NerdWallet Canada."""
        print("\n[4/5] Scraping NerdWallet.com/ca...")
        
        urls = [
            "https://www.nerdwallet.com/ca/credit-cards/best-cash-back-credit-cards",
            "https://www.nerdwallet.com/ca/credit-cards/best-travel-credit-cards",
            "https://www.nerdwallet.com/ca/credit-cards/best-rewards-credit-cards",
            "https://www.nerdwallet.com/ca/credit-cards/best-no-fee-credit-cards",
        ]
        
        count = 0
        for url in urls:
            try:
                print(f"  Fetching: {url.split('/')[-1]}...")
                resp = self.session.get(url, timeout=15)
                soup = BeautifulSoup(resp.content, 'lxml')
                
                for el in soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'(Visa|Mastercard|Card)', re.I)):
                    name = el.get_text(strip=True)
                    if 10 < len(name) < 100:
                        card = self._create_card_from_name(name, "nerdwallet")
                        if card:
                            self._add_or_merge_card(card)
                            count += 1
                
                time.sleep(self.delay)
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"  Found {count} card entries")

    # =========================================================================
    # Source 5: GreedyRates.ca
    # =========================================================================
    def scrape_greedyrates(self):
        """Scrape from GreedyRates.ca - detailed reviews."""
        print("\n[5/5] Scraping GreedyRates.ca...")
        
        urls = [
            "https://www.greedyrates.ca/blog/best-cash-back-credit-cards-canada/",
            "https://www.greedyrates.ca/blog/best-travel-credit-cards-canada/",
            "https://www.greedyrates.ca/blog/best-rewards-credit-cards-canada/",
            "https://www.greedyrates.ca/blog/best-no-fee-credit-cards-canada/",
        ]
        
        count = 0
        for url in urls:
            try:
                print(f"  Fetching article...")
                resp = self.session.get(url, timeout=15)
                soup = BeautifulSoup(resp.content, 'lxml')
                
                for heading in soup.find_all(['h2', 'h3']):
                    text = heading.get_text(strip=True)
                    if any(issuer in text for issuer in ['TD', 'RBC', 'BMO', 'CIBC', 'Scotiabank', 'Amex', 'Tangerine']):
                        name = re.sub(r'^\d+\.\s*', '', text)
                        name = re.sub(r'\s*[-–].*$', '', name)
                        
                        if len(name) > 10:
                            card = self._create_card_from_name(name, "greedyrates")
                            if card:
                                self._add_or_merge_card(card)
                                count += 1
                
                time.sleep(self.delay)
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"  Found {count} card entries")


    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _parse_card_element(self, element, source: str) -> Optional[CreditCard]:
        """Parse a card from an HTML element."""
        try:
            # Find card name
            name_el = element.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|heading', re.I))
            if not name_el:
                name_el = element.find(['h2', 'h3', 'h4'])
            if not name_el:
                return None
            
            name = name_el.get_text(strip=True)
            if not name or len(name) < 5:
                return None
            
            return self._create_card_from_name(name, source, element)
        except:
            return None

    def _create_card_from_name(self, name: str, source: str, element=None) -> Optional[CreditCard]:
        """Create a card object from just the name."""
        issuer = self._get_issuer(name)
        if issuer == "Other":
            return None
        
        program = self._get_program(name)
        currency = self._get_currency(program, name)
        card_key = self._generate_key(name, issuer)
        
        # Try to extract fee from element
        fee = 0.0
        if element:
            fee_text = element.get_text()
            fee_match = re.search(r'annual fee[:\s]*\$?([\d,]+)', fee_text, re.I)
            if fee_match:
                fee = float(fee_match.group(1).replace(',', ''))
            elif 'no annual fee' in fee_text.lower() or 'no fee' in fee_text.lower():
                fee = 0.0
        
        # Try to extract category rewards
        category_rewards = []
        if element:
            category_rewards = self._extract_category_rewards(element.get_text())
        
        return CreditCard(
            card_key=card_key,
            name=name,
            issuer=issuer,
            reward_program=program,
            reward_currency=currency,
            point_valuation=self._get_point_value(currency, program),
            annual_fee=fee,
            base_reward_rate=1.0,
            category_rewards=category_rewards,
            source=source,
            confidence=0.5,
        )

    def _add_or_merge_card(self, new_card: CreditCard):
        """Add a new card or merge with existing data."""
        key = new_card.card_key
        
        if key in self.cards:
            existing = self.cards[key]
            # Merge data - prefer non-zero values
            if new_card.annual_fee > 0 and existing.annual_fee == 0:
                existing.annual_fee = new_card.annual_fee
            if new_card.category_rewards and not existing.category_rewards:
                existing.category_rewards = new_card.category_rewards
            # Increase confidence when seen from multiple sources
            existing.confidence = min(1.0, existing.confidence + 0.2)
            existing.source += f", {new_card.source}"
        else:
            self.cards[key] = new_card

    # =========================================================================
    # Data Enrichment
    # =========================================================================
    
    def enrich_with_known_data(self):
        """Enrich scraped data with known accurate information."""
        print("\n[Enrichment] Adding known category rewards...")
        
        enriched = 0
        for key, rewards in KNOWN_CATEGORY_REWARDS.items():
            if key in self.cards:
                card = self.cards[key]
                if not card.category_rewards:
                    card.category_rewards = [
                        CategoryReward(
                            category=r["category"],
                            multiplier=r["multiplier"],
                            reward_unit=r["unit"],
                            description=f"{r['multiplier']}{'x' if r['unit'] == 'multiplier' else '%'} on {r['category']}"
                        )
                        for r in rewards
                    ]
                    card.confidence = min(1.0, card.confidence + 0.3)
                    enriched += 1
        
        print(f"  Enriched {enriched} cards with known category rewards")

    # =========================================================================
    # Data Verification
    # =========================================================================
    
    def verify_data(self):
        """Verify scraped data against known information."""
        print("\n" + "=" * 60)
        print("DATA VERIFICATION")
        print("=" * 60)
        
        self.verification_results = []
        verified = 0
        warnings = 0
        errors = 0
        
        for key, card in self.cards.items():
            issues = []
            
            # Check 1: Valid issuer
            if card.issuer == "Other":
                issues.append("Unknown issuer")
            
            # Check 2: Reasonable annual fee
            if card.annual_fee > 1000:
                issues.append(f"Unusually high fee: ${card.annual_fee}")
            
            # Check 3: Valid reward currency
            if card.reward_currency not in ["cashback", "points", "airline_miles", "hotel_points"]:
                issues.append(f"Invalid reward currency: {card.reward_currency}")
            
            # Check 4: Compare with known cards
            if key in KNOWN_CARDS:
                known = KNOWN_CARDS[key]
                fee_min, fee_max = known["fee_range"]
                if not (fee_min <= card.annual_fee <= fee_max):
                    issues.append(f"Fee ${card.annual_fee} outside expected range ${fee_min}-${fee_max}")
                if card.issuer != known["issuer"]:
                    issues.append(f"Issuer mismatch: {card.issuer} vs {known['issuer']}")
                card.confidence = min(1.0, card.confidence + 0.2)
            
            # Check 5: Category rewards validation
            for cr in card.category_rewards:
                if cr.multiplier > 10:
                    issues.append(f"Unusually high reward rate: {cr.multiplier}x on {cr.category}")
            
            # Record results
            if issues:
                status = "WARNING" if len(issues) < 3 else "ERROR"
                if status == "WARNING":
                    warnings += 1
                else:
                    errors += 1
                self.verification_results.append({
                    "card": card.name,
                    "key": key,
                    "status": status,
                    "issues": issues
                })
            else:
                verified += 1
                card.last_verified = datetime.now().isoformat()
        
        # Print summary
        print(f"\nVerification Results:")
        print(f"  ✓ Verified: {verified}")
        print(f"  ⚠ Warnings: {warnings}")
        print(f"  ✗ Errors: {errors}")
        
        if self.verification_results:
            print(f"\nIssues found:")
            for result in self.verification_results[:10]:  # Show first 10
                print(f"  [{result['status']}] {result['card']}")
                for issue in result['issues']:
                    print(f"    - {issue}")
        
        return verified, warnings, errors


    # =========================================================================
    # Main Scrape Method
    # =========================================================================
    
    def scrape_all(self):
        """Run all scrapers."""
        self.scrape_creditcardgenius()
        self.scrape_ratehub()
        self.scrape_moneysense()
        self.scrape_nerdwallet()
        self.scrape_greedyrates()
        
        return list(self.cards.values())

    def save_to_json(self, filepath: str = "scraped_cards.json"):
        """Save cards to JSON file."""
        output = {
            "scraped_at": datetime.now().isoformat(),
            "count": len(self.cards),
            "verification": {
                "results": self.verification_results[:20]  # First 20 issues
            },
            "cards": [
                {
                    **asdict(card),
                    "category_rewards": [asdict(cr) for cr in card.category_rewards]
                }
                for card in self.cards.values()
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\nSaved to {filepath}")


# =============================================================================
# Supabase Upload
# =============================================================================

def upload_to_supabase(cards: List[CreditCard]) -> dict:
    """Upload verified cards to Supabase using the CreditCardUploader."""
    from credit_card_uploader import CreditCardUploader
    
    try:
        uploader = CreditCardUploader()
        results = uploader.upload_cards(cards)
        
        # Print first error if any
        if results['errors']:
            print(f"    First error: {results['errors'][0]['error'][:200]}")
        
        return {
            'inserted': results['cards_inserted'],
            'updated': results['cards_updated'],
            'category_rewards': results['category_rewards_inserted'],
            'errors': results['errors']
        }
    except Exception as e:
        print(f"    Upload error: {str(e)[:200]}")
        return {'inserted': 0, 'updated': 0, 'category_rewards': 0, 'errors': [{'error': str(e)}]}


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    print("=" * 60)
    print("Enhanced Canadian Credit Card Scraper")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize scraper
    scraper = EnhancedCreditCardScraper()
    
    # Step 1: Scrape from all sources
    print("\n" + "=" * 60)
    print("STEP 1: SCRAPING DATA")
    print("=" * 60)
    scraper.scrape_all()
    
    # Step 2: Enrich with known data
    print("\n" + "=" * 60)
    print("STEP 2: DATA ENRICHMENT")
    print("=" * 60)
    scraper.enrich_with_known_data()
    
    # Step 3: Verify data
    print("\n" + "=" * 60)
    print("STEP 3: DATA VERIFICATION")
    print("=" * 60)
    verified, warnings, errors = scraper.verify_data()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total unique cards: {len(scraper.cards)}")
    print(f"Verified: {verified}, Warnings: {warnings}, Errors: {errors}")
    
    # Show by issuer
    issuers = {}
    for card in scraper.cards.values():
        issuers[card.issuer] = issuers.get(card.issuer, 0) + 1
    print("\nBy issuer:")
    for issuer, count in sorted(issuers.items(), key=lambda x: -x[1]):
        print(f"  {issuer}: {count}")
    
    # Step 4: Save to JSON
    scraper.save_to_json("scraped_cards.json")
    
    # Step 5: Upload to Supabase
    print("\n" + "=" * 60)
    print("STEP 4: UPLOAD TO SUPABASE")
    print("=" * 60)
    
    try:
        # Only upload cards with confidence > 0.3
        confident_cards = [c for c in scraper.cards.values() if c.confidence > 0.3]
        print(f"Uploading {len(confident_cards)} cards (confidence > 0.3)...")
        
        result = upload_to_supabase(confident_cards)
        print(f"  Inserted: {result['inserted']}")
        print(f"  Updated: {result['updated']}")
        print(f"  Category rewards: {result['category_rewards']}")
        if result['errors']:
            print(f"  Errors: {len(result['errors'])}")
    except ValueError as e:
        print(f"  Skipped: {e}")
    except Exception as e:
        print(f"  Upload failed: {e}")
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)


if __name__ == '__main__':
    main()

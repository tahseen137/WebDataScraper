# Canadian Credit Card Scraper

A Python toolkit for scraping and managing Canadian credit card data, designed to populate the Rewards Optimizer database.

## Features

- **Multi-source scraping**: Collects data from Ratehub, MoneySense, NerdWallet, and more
- **Curated card database**: 34+ Canadian credit cards with accurate category rewards
- **Supabase integration**: Direct upload to your database
- **Data verification**: Validates scraped data against known card information
- **Duplicate detection**: Identifies and handles duplicate entries

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and add your Supabase credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-service-role-key
```

> **Note**: Use the `service_role` key (not `anon` key) for write access. Find it in Supabase Dashboard → Settings → API.

### 3. Seed the database with curated cards

```bash
python seed_known_cards.py
```

This uploads 34 Canadian credit cards with full category rewards and signup bonuses.

## Scripts

| Script | Description |
|--------|-------------|
| `seed_known_cards.py` | Upload curated cards with accurate rewards (recommended) |
| `enhanced_scraper.py` | Scrape cards from multiple websites |
| `check_duplicates.py` | Check for duplicate cards in database |
| `cleanup_duplicates.py` | Remove cards without category rewards |

## Database Schema

The scraper populates these Supabase tables:

- **cards**: Credit card info (name, issuer, fees, base rewards)
- **category_rewards**: Bonus rates for spending categories
- **signup_bonuses**: Welcome offers for new cardholders

## Included Cards

34 cards from major Canadian issuers:

- **American Express** (6): Cobalt, Gold, Platinum, Aeroplan Reserve, SimplyCash
- **BMO** (4): CashBack, Eclipse, AIR MILES World Elite, CashBack World Elite
- **CIBC** (4): Dividend, Dividend Infinite, Aventura, Aeroplan
- **Scotiabank** (3): Gold Amex, Momentum, Passport
- **TD** (3): Aeroplan, Cash Back, First Class Travel
- **RBC** (3): Avion, Cash Back, WestJet
- **Neo Financial** (2): Neo Mastercard, World Elite
- **Desjardins** (2): Odyssey, Cash Back World Elite
- Plus: MBNA, National Bank, PC Financial, Rogers, Simplii, Tangerine, Triangle

## Adding New Cards

Edit `seed_known_cards.py` and add to the `KNOWN_CARDS` list:

```python
{
    "card_key": "issuer-card-name",
    "name": "Card Display Name",
    "issuer": "Issuer Name",
    "reward_program": "Program Name",
    "reward_currency": "cashback",  # or "points", "airline_miles"
    "point_valuation": 1.0,
    "annual_fee": 0,
    "base_reward_rate": 1.0,
    "base_reward_unit": "percent",  # or "multiplier"
    "category_rewards": [
        {"category": "groceries", "multiplier": 2.0, "reward_unit": "percent", "description": "2% on groceries"},
    ],
    "signup_bonus": {"bonus_amount": 200, "bonus_currency": "cashback", "spend_requirement": 1000, "timeframe_days": 90}
}
```

Then run `python seed_known_cards.py` to update the database.

## Spending Categories

- `groceries`, `dining`, `gas`, `travel`
- `online_shopping`, `entertainment`, `drugstores`
- `home_improvement`, `other`

## License

MIT

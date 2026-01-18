# Canadian Credit Card Scraper

A robust Python toolkit for scraping and managing Canadian credit card data, designed to populate the Rewards Optimizer database with production-ready reliability features.

## Features

### Core Functionality
- **Multi-source scraping**: Collects data from Ratehub, MoneySense, NerdWallet, CreditCardGenius, and GreedyRates
- **Curated card database**: 34+ Canadian credit cards with accurate category rewards
- **Supabase integration**: Direct upload to your database
- **Data verification**: Validates scraped data against known card information
- **Duplicate detection**: Identifies and handles duplicate entries

### Production Features ✨ NEW
- **Professional logging**: Structured logging with file and console handlers
- **Smart rate limiting**: Domain-based throttling with exponential backoff
- **Retry logic**: Automatic retry with configurable backoff on failures
- **Error tracking**: Comprehensive error monitoring and recovery
- **Configuration management**: All settings via environment variables
- **Unit tests**: 20+ tests with code coverage reporting

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Supabase Configuration (Required)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-service-role-key

# Scraper Configuration (Optional)
SCRAPER_DELAY=2.0                    # Delay between requests (seconds)
SCRAPER_MIN_DELAY=1.0               # Minimum delay
SCRAPER_MAX_DELAY=10.0              # Maximum delay
SCRAPER_TIMEOUT=15                  # Request timeout
SCRAPER_MAX_RETRIES=3               # Maximum retry attempts
SCRAPER_RETRY_BACKOFF=2.0           # Exponential backoff multiplier
MIN_CONFIDENCE_THRESHOLD=0.3        # Minimum confidence for uploading

# Logging Configuration (Optional)
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_FILE=true                    # Write logs to file
LOG_DIR=logs                        # Log file directory
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
| `deduplicate_cards.py` | Advanced deduplication utilities |

## Architecture

### Core Modules

- **`config.py`** - Centralized configuration management
- **`logger_config.py`** - Logging setup with file and console handlers
- **`rate_limiter.py`** - Adaptive rate limiting with domain tracking
- **`retry_util.py`** - Retry decorators and session with exponential backoff
- **`error_handler.py`** - Custom exceptions and error tracking
- **`credit_card_scraper.py`** - Base scraper with parsing utilities
- **`enhanced_scraper.py`** - Multi-source scraper with verification
- **`credit_card_uploader.py`** - Supabase database interface
- **`supabase_client.py`** - Generic Supabase client

### Data Models

```python
CreditCard
├── card_key: str (unique identifier)
├── name: str
├── issuer: str
├── reward_program: str
├── reward_currency: str (cashback|points|airline_miles)
├── point_valuation: float
├── annual_fee: float
├── base_reward_rate: float
├── category_rewards: List[CategoryReward]
└── signup_bonus: Optional[SignupBonus]

CategoryReward
├── category: str
├── multiplier: float
├── reward_unit: str (percent|multiplier)
├── description: str
└── spend_limit: Optional[float]

SignupBonus
├── bonus_amount: int
├── bonus_currency: str
├── spend_requirement: float
└── timeframe_days: int
```

## Database Schema

The scraper populates these Supabase tables:

- **cards**: Credit card info (name, issuer, fees, base rewards)
- **category_rewards**: Bonus rates for spending categories
- **signup_bonuses**: Welcome offers for new cardholders

## Testing

### Run tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_scraper.py

# Run tests matching a pattern
pytest -k "parse"
```

View coverage report: `htmlcov/index.html`

See [`tests/README.md`](tests/README.md) for more testing details.

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

## Advanced Usage

### Custom Configuration

Create a custom configuration by setting environment variables:

```bash
# Slow down scraping for rate-limited sites
export SCRAPER_DELAY=5.0
export SCRAPER_MAX_DELAY=30.0

# Enable debug logging
export LOG_LEVEL=DEBUG

# Adjust retry behavior
export SCRAPER_MAX_RETRIES=5
export SCRAPER_RETRY_BACKOFF=3.0
```

### Using Retry Utilities

```python
from retry_util import retry_with_backoff, RetrySession

# Decorate any function
@retry_with_backoff(max_retries=3, backoff_factor=2.0)
def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# Or use RetrySession
session = RetrySession(max_retries=3, backoff_factor=2.0, timeout=15)
response = session.get("https://example.com")
```

### Error Tracking

```python
from error_handler import ErrorTracker, ErrorRecovery

tracker = ErrorTracker()

try:
    # Some operation
    scrape_website(url)
except Exception as e:
    ErrorRecovery.handle_network_error(url, e, tracker)

# Get error summary
summary = tracker.get_summary()
print(f"Total errors: {summary['total_errors']}")
print(f"Errors per minute: {summary['errors_per_minute']}")
```

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

## Logging

Logs are written to:
- Console (INFO level and above)
- File: `logs/webdatascraper_YYYYMMDD_HHMMSS.log` (DEBUG level and above)

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Troubleshooting

### Rate Limited by Websites

Increase delays in `.env`:
```env
SCRAPER_DELAY=5.0
SCRAPER_MAX_DELAY=30.0
```

### Scraper Failures

Check logs in `logs/` directory for detailed error traces. The scraper automatically:
- Retries failed requests up to 3 times
- Applies exponential backoff on errors
- Tracks and reports all errors

### Database Connection Issues

Verify your Supabase credentials in `.env`:
```bash
# Test connection
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); print('Connected!' if create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')) else 'Failed')"
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Coverage

```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Git Workflow

All improvements are developed in feature branches:

```bash
git checkout main
git pull
git checkout -b feature/your-feature-name
# Make changes
git add .
git commit -m "feat: Your feature description"
git push -u origin feature/your-feature-name
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT

## Changelog

### v2.0.0 (Latest)
- ✨ Added professional logging framework
- ✨ Added smart rate limiting with domain tracking
- ✨ Added retry logic with exponential backoff
- ✨ Added comprehensive error handling
- ✨ Added configuration management via environment variables
- ✨ Added unit tests with pytest
- 📝 Improved documentation

### v1.0.0
- Initial release with basic scraping functionality
- Curated database of 34 Canadian credit cards
- Multi-source scraping from 5 websites
- Supabase integration

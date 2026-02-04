# 💳 WebDataScraper

**Production-ready Python toolkit for scraping Canadian credit card data and uploading to Supabase.**

Built to populate the [Rewards Optimizer](https://github.com/tahseen137/rewards-optimizer) database with comprehensive, accurate credit card information including category rewards, signup bonuses, and point valuations.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- **🎯 Curated Data** - 34+ Canadian credit cards with verified category rewards
- **🔄 Multi-Source Scraping** - Ratehub, MoneySense, NerdWallet, CreditCardGenius, GreedyRates
- **☁️ Supabase Integration** - Direct database upload with duplicate prevention
- **🛡️ Production Ready** - Rate limiting, retry logic, error tracking, structured logging
- **✅ Tested** - 20+ unit tests with coverage reporting
- **⚙️ Configurable** - Environment-based configuration for all settings

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/tahseen137/WebDataScraper.git
cd WebDataScraper
pip install -r requirements.txt
```

### 2. Configuration

Copy and configure your environment:

```bash
cp .env.example .env
```

Edit `.env` with your Supabase credentials:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-service-role-key
```

> **Note:** Use the `service_role` key (not `anon` key) from Supabase Dashboard → Settings → API

### 3. Seed Database

Upload 34 curated Canadian credit cards:

```bash
python seed_cards.py
```

That's it! Your database now contains production-ready credit card data.

## 📊 What's Included

### 34 Canadian Credit Cards

- **American Express** (6) - Cobalt, Gold, Platinum, Aeroplan Reserve, SimplyCash
- **BMO** (4) - CashBack, Eclipse, AIR MILES, CashBack World Elite
- **CIBC** (4) - Dividend, Dividend Infinite, Aventura, Aeroplan
- **Scotiabank** (3) - Gold Amex, Momentum, Passport
- **TD** (3) - Aeroplan, Cash Back, First Class Travel
- **RBC** (3) - Avion, Cash Back, WestJet
- **Plus** - Neo, Desjardins, MBNA, National Bank, PC Financial, Rogers, Simplii, Tangerine, Triangle

### Complete Data Coverage

Each card includes:
- ✅ Base reward rates (cashback/points/miles)
- ✅ Category bonuses (groceries, dining, gas, travel, etc.)
- ✅ Signup bonuses with requirements
- ✅ Annual fees and point valuations
- ✅ Reward program associations

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Web Scraping:** BeautifulSoup4, Requests, Newspaper3k
- **Database:** Supabase (PostgreSQL)
- **Data Processing:** Pandas, Jellyfish (fuzzy matching)
- **Testing:** Pytest with coverage
- **Configuration:** python-dotenv

## 📖 Documentation

- **[SCRIPTS.md](SCRIPTS.md)** - Reference for all 37 Python scripts
- **[.env.example](.env.example)** - Configuration options
- **[tests/README.md](tests/README.md)** - Testing guide
- **[docs/](docs/)** - Additional documentation

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific tests
pytest tests/test_scraper.py -v
```

## 📝 Usage Examples

### Seed Curated Cards (Recommended)

```bash
python seed_cards.py
```

### Scrape Fresh Data

```bash
python scrape_workflow.py
```

### Check for Duplicates

```bash
python check_duplicates.py
```

### Custom Configuration

Set environment variables or edit `.env`:

```env
SCRAPER_DELAY=5.0          # Slow down requests
LOG_LEVEL=DEBUG            # Detailed logging
SCRAPER_MAX_RETRIES=5      # More retry attempts
```

## 🏗️ Architecture

### Core Modules

| Module | Purpose |
|--------|---------|
| `config.py` | Environment-based configuration |
| `scraper.py` | HTML parsing and data extraction |
| `credit_card_uploader.py` | Supabase database operations |
| `logger_config.py` | Structured logging setup |
| `rate_limiter.py` | Domain-based rate limiting |
| `retry_util.py` | Exponential backoff retry logic |

### Data Flow

```
┌─────────────────┐
│  Web Sources    │
│  (5 websites)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Scrapers      │
│  (BeautifulSoup)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Merger    │
│  & Validator    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Duplicate      │
│  Prevention     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Supabase      │
│   Database      │
└─────────────────┘
```

## 🗃️ Database Schema

The scraper populates three Supabase tables:

### `cards`
- `id`, `card_key` (unique), `name`, `issuer`
- `reward_program`, `reward_currency`, `point_valuation`
- `annual_fee`, `base_reward_rate`, `base_reward_unit`

### `category_rewards`
- `id`, `card_id`, `category`, `multiplier`
- `reward_unit`, `description`, `spend_limit`

### `signup_bonuses`
- `id`, `card_id`, `bonus_amount`, `bonus_currency`
- `spend_requirement`, `timeframe_days`

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Run tests (`pytest`)
5. Commit (`git commit -m 'feat: Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest --cov=. --cov-report=html

# Check code quality
pylint *.py
```

## 🐛 Troubleshooting

### Rate Limited by Websites

Increase delays in `.env`:
```env
SCRAPER_DELAY=5.0
SCRAPER_MAX_DELAY=30.0
```

### Database Connection Issues

Verify Supabase credentials:
```bash
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); print('✅ Connected!' if create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')) else '❌ Failed')"
```

### Check Logs

Logs are written to `logs/webdatascraper_YYYYMMDD_HHMMSS.log` with detailed error traces.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built for the [Rewards Optimizer](https://github.com/tahseen137/rewards-optimizer) project to help Canadians maximize credit card rewards.

Data sources:
- [Ratehub](https://www.ratehub.ca/)
- [MoneySense](https://www.moneysense.ca/)
- [NerdWallet Canada](https://www.nerdwallet.com/ca/)
- [CreditCardGenius](https://creditcardgenius.ca/)
- [GreedyRates](https://www.greedyrates.ca/)

## 📧 Contact

**Tahseen Ahmed**
- GitHub: [@tahseen137](https://github.com/tahseen137)
- Project: [WebDataScraper](https://github.com/tahseen137/WebDataScraper)

---

⭐ **Star this repo** if you find it useful!

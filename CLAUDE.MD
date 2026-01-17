# CLAUDE.MD - Canadian Credit Card Scraper

This document provides context for AI assistants working with the Canadian Credit Card Scraper codebase.

## Project Overview

A Python toolkit for scraping and managing Canadian credit card data with Supabase integration. The project includes:
- Multi-source web scraping for credit card information
- A curated database of 34+ Canadian credit cards with accurate category rewards
- Database deduplication and validation tools
- Direct Supabase integration for the Rewards Optimizer application

## Technology Stack

- **Language**: Python 3.x
- **Web Scraping**: BeautifulSoup4, lxml, newspaper3k, requests
- **Database**: Supabase (PostgreSQL)
- **Data Processing**: pandas
- **Configuration**: python-dotenv for environment management

## Project Structure

### Core Scripts

| File | Purpose |
|------|---------|
| `seed_known_cards.py` | Upload curated cards with accurate rewards (primary data source) |
| `enhanced_scraper.py` | Multi-source web scraper for credit card data |
| `supabase_client.py` | Supabase database client initialization |
| `upload_cards.py` | Upload scraped card data to Supabase |

### Data Management Scripts

| File | Purpose |
|------|---------|
| `check_duplicates.py` | Identify duplicate cards in database |
| `cleanup_duplicates.py` | Remove cards without category rewards |
| `deduplicate_cards.py` | Basic deduplication utility |
| `advanced_deduplicate.py` | Advanced deduplication with merge logic |
| `reset_to_seed_data.py` | Reset database to curated seed data |

### Legacy Scripts

| File | Purpose |
|------|---------|
| `scraper.py` | Original scraper implementation |
| `credit_card_scraper.py` | Alternative scraper version |
| `credit_card_uploader.py` | Alternative upload utility |
| `scrape_and_upload.py` | Combined scrape and upload workflow |

## Database Schema

The project works with three main Supabase tables:

### cards
- `id` (uuid, primary key)
- `card_key` (text, unique identifier)
- `name` (text)
- `issuer` (text)
- `reward_program` (text)
- `reward_currency` (text: 'cashback', 'points', 'airline_miles')
- `point_valuation` (numeric)
- `annual_fee` (numeric)
- `base_reward_rate` (numeric)
- `base_reward_unit` (text: 'percent', 'multiplier')

### category_rewards
- `id` (uuid, primary key)
- `card_id` (uuid, foreign key to cards)
- `category` (text: 'groceries', 'dining', 'gas', 'travel', etc.)
- `multiplier` (numeric)
- `reward_unit` (text)
- `description` (text)

### signup_bonuses
- `id` (uuid, primary key)
- `card_id` (uuid, foreign key to cards)
- `bonus_amount` (numeric)
- `bonus_currency` (text)
- `spend_requirement` (numeric)
- `timeframe_days` (integer)

## Setup Instructions

### 1. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` with Supabase credentials:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-service-role-key  # Use service_role key for write access
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
# Upload curated cards (recommended first step)
python seed_known_cards.py
```

## Common Workflows

### Adding New Cards

1. Edit `seed_known_cards.py`
2. Add card to the `KNOWN_CARDS` list with full schema
3. Run `python seed_known_cards.py` (uses upsert, safe to re-run)

### Scraping Additional Cards

```bash
# Scrape from multiple sources
python enhanced_scraper.py

# Upload scraped data
python upload_cards.py
```

### Data Maintenance

```bash
# Check for duplicates
python check_duplicates.py

# Remove incomplete entries
python cleanup_duplicates.py

# Reset to seed data
python reset_to_seed_data.py
```

## Spending Categories

Standard categories used across the database:
- `groceries`
- `dining`
- `gas`
- `travel`
- `online_shopping`
- `entertainment`
- `drugstores`
- `home_improvement`
- `other`

## Important Notes for AI Assistants

### Data Quality
- **Prefer curated data**: The `seed_known_cards.py` contains manually verified, accurate card information
- **Scraped data varies**: Web scraping results can be incomplete or inaccurate
- **Category rewards are critical**: Cards without category rewards are less useful for optimization

### Upsert Logic
- The seed script uses upsert logic (insert or update) based on `card_key`
- Safe to run `seed_known_cards.py` multiple times
- Existing cards are updated, new cards are inserted

### Key Identifiers
- `card_key`: Unique identifier in format `issuer-card-name` (e.g., "amex-cobalt")
- Used for deduplication and upsert operations
- Should be lowercase, hyphenated

### Reward Rate Formats
- **Cashback**: Use `reward_unit: "percent"`, `multiplier` as percentage (e.g., 2.0 = 2%)
- **Points**: Use `reward_unit: "multiplier"`, `multiplier` as points per dollar (e.g., 5.0 = 5x points)
- **Base rate**: Some cards use percentage, others use multipliers - check `base_reward_unit`

### Foreign Key Relationships
- When adding category rewards or signup bonuses, you need the `card_id` (UUID) from the cards table
- The seed script handles this automatically by fetching card IDs after insert

### Error Handling
- Supabase operations may fail due to network issues or invalid credentials
- Scripts should validate environment variables before executing
- Check that `.env` file exists and contains valid Supabase credentials

### Testing Changes
- Before modifying seed data, consider backing up the database
- Use `check_duplicates.py` to verify data integrity after changes
- Test with a subset of cards before running full uploads

## Development Guidelines

### When Adding New Scripts
- Follow the existing naming convention
- Include docstrings and comments for complex logic
- Handle environment variables with python-dotenv
- Implement error handling for network and database operations

### When Modifying Card Data
- Verify reward rates and categories are accurate
- Ensure `card_key` is unique and follows naming convention
- Include all three data types: card, category_rewards, signup_bonus (if applicable)
- Test the full upsert workflow

### When Working with Scrapers
- Web scraping is inherently fragile (sites change frequently)
- Always validate scraped data before upload
- Consider rate limiting and respectful scraping practices
- Document the source URLs and scraping logic

## Related Systems

This scraper feeds data into the **Rewards Optimizer** application, which:
- Analyzes user spending patterns
- Recommends optimal credit card combinations
- Calculates potential rewards based on category spending

The accuracy of category rewards data directly impacts optimization quality.

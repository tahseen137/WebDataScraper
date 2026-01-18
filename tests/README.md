# WebDataScraper Tests

Unit and integration tests for the WebDataScraper project.

## Running Tests

### Install test dependencies

```bash
pip install -r requirements.txt
```

### Run all tests

```bash
pytest
```

### Run with coverage report

```bash
pytest --cov=. --cov-report=html
```

View the coverage report by opening `htmlcov/index.html` in your browser.

### Run specific test files

```bash
pytest tests/test_scraper.py
```

### Run specific test functions

```bash
pytest tests/test_scraper.py::TestCreditCardScraper::test_parse_fee
```

### Run tests matching a pattern

```bash
pytest -k "parse"
```

### Run only fast tests (skip slow tests)

```bash
pytest -m "not slow"
```

## Test Structure

- `test_scraper.py` - Tests for scraping and parsing logic
- `__init__.py` - Package initialization

## Writing Tests

### Test naming conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example test

```python
def test_parse_fee():
    """Test annual fee parsing."""
    scraper = CreditCardScraper()

    assert scraper._parse_fee("$120") == 120.0
    assert scraper._parse_fee("No fee") == 0.0
```

### Using fixtures

```python
@pytest.fixture
def scraper():
    """Fixture providing a scraper instance."""
    return CreditCardScraper(delay=0.1)

def test_something(scraper):
    """Test using the scraper fixture."""
    assert scraper.delay == 0.1
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch

## Coverage Goals

- Target: 80%+ code coverage
- Focus on critical parsing and validation logic

# Duplicate Prevention System - Quick Start Guide

**Ready to use in 5 minutes!** ⚡

---

## Prerequisites

✅ Python 3.8+
✅ Supabase account with database
✅ Existing WebDataScraper installation

---

## Step 1: Install Dependencies (1 minute)

```bash
cd C:\Projects\SourceCodes\WebDataScraper
pip install jellyfish>=1.0.0
```

---

## Step 2: Run Database Migration (2 minutes)

### Option A: Using Supabase Dashboard

1. Open your Supabase project
2. Go to **SQL Editor**
3. Copy contents of `migrations/003_add_duplicate_prevention.sql`
4. Execute the script

### Option B: Using psql

```bash
psql -h your-db-host -U postgres -d your-database -f migrations/003_add_duplicate_prevention.sql
```

**Verify migration**:
```sql
-- Check new columns exist
SELECT column_name FROM information_schema.columns
WHERE table_name = 'cards'
AND column_name IN ('fingerprint', 'normalized_name', 'sources', 'confidence_score');

-- Check new table exists
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'duplicate_detection_log');
```

---

## Step 3: Test the System (2 minutes)

### Quick Test

```python
from card_identity_manager import CardFingerprintGenerator, calculate_advanced_similarity

# Create generator
generator = CardFingerprintGenerator()

# Test fingerprint generation
fp1, components1 = generator.generate_semantic_fingerprint(
    issuer="TD",
    name="TD® Aeroplan® Visa Infinite*",
    program="Aeroplan",
    annual_fee=139.0
)

fp2, components2 = generator.generate_semantic_fingerprint(
    issuer="TD",
    name="TD Aeroplan Visa Infinite Card",  # Different formatting
    program="Aeroplan",
    annual_fee=139.99
)

# Check if same fingerprint
print(f"Fingerprints match: {fp1 == fp2}")  # Should print: True

# Test similarity calculation
similarity = calculate_advanced_similarity(
    "TD Aeroplan Visa Infinite",
    "TD Aeroplan Visa Infinite Card"
)
print(f"Similarity: {similarity:.2%}")  # Should be >90%
```

**Expected output**:
```
Fingerprints match: True
Similarity: 92%
```

---

## Step 4: Run Bulk Deduplication (if needed)

**If you have existing duplicates in your database:**

```bash
# Preview what will be changed (DRY RUN - safe!)
python bulk_deduplicate.py --dry-run

# Review output, then execute if satisfied
python bulk_deduplicate.py
```

**Example output**:
```
============================================================
BULK DEDUPLICATION SUMMARY
============================================================
Mode: LIVE
Total cards processed: 150
Fingerprints generated: 150
Duplicates found: 23
Auto-merged: 23
Manual review needed: 0
Errors: 0
============================================================
```

---

## Step 5: Normal Operation

**The system is now active!** 🎉

Every time you run the scraper, duplicates are automatically prevented:

```bash
python enhanced_scraper.py
```

**What happens automatically:**
1. ✅ Card scraped from source
2. ✅ Fingerprint generated
3. ✅ Duplicate check (exact + fuzzy)
4. ✅ Auto-merge if similarity ≥ 85%
5. ✅ Flag for manual review if 70-85%
6. ✅ Insert new card if unique
7. ✅ All actions logged

---

## Monitoring & Maintenance

### View Activity Report

```bash
# Last 7 days summary
python monitor_duplicates.py --days 7

# Export detailed report
python monitor_duplicates.py --days 30 --export monthly_report.json
```

**Sample output**:
```
======================================================================
DUPLICATE DETECTION SUMMARY - Last 7 Days
======================================================================

📊 Activity Overview:
   Total Detections: 45
   Unique Cards Involved: 30
   Average Similarity: 0.89

🔀 Actions Taken:
   auto_merged: 38
   flagged_manual_review: 7
   ignored: 0

📈 Similarity Distribution:
   Exact Match (≥0.95): 25
   High Similarity (0.85-0.95): 13
   Medium Similarity (<0.85): 7

⚠️  Manual Review Queue: 7 items
```

### Review Flagged Duplicates

```bash
# Interactive review mode
python review_duplicates.py
```

**Interactive prompts:**
```
DUPLICATE REVIEW - Similarity: 78%
================================================================================

Card 1: TD Aeroplan Visa Infinite
Card 2: CIBC Aeroplan Visa Infinite

Field                Card 1                         Card 2
--------------------------------------------------------------------------------
issuer               TD                             CIBC
reward_program       Aeroplan                       Aeroplan
annual_fee           139.0                          139.0

Options:
  1. Merge (keep Card 1, merge Card 2)
  2. Merge (keep Card 2, merge Card 1)
  3. NOT duplicates (reject)
  4. Skip (review later)
  q. Quit

Your choice:
```

**Auto-approve mode:**
```bash
# Auto-approve merges with ≥90% similarity
python review_duplicates.py --auto-approve 0.90
```

---

## Monitoring Database

### Check Duplicate Logs

```sql
-- Recent duplicate detections
SELECT
    card_key_1,
    card_key_2,
    similarity_score,
    action_taken,
    created_at
FROM duplicate_detection_log
ORDER BY created_at DESC
LIMIT 20;
```

### Count by Action

```sql
SELECT
    action_taken,
    COUNT(*) as count
FROM duplicate_detection_log
GROUP BY action_taken;
```

**Expected results**:
```
action_taken              | count
--------------------------+-------
auto_merged               | 142
flagged_manual_review     | 8
manually_merged           | 5
manually_rejected         | 2
```

### Check Card Quality

```sql
-- Cards with multiple sources (high confidence)
SELECT
    name,
    issuer,
    array_length(sources, 1) as source_count,
    confidence_score
FROM cards
WHERE array_length(sources, 1) > 1
ORDER BY source_count DESC
LIMIT 10;
```

---

## Troubleshooting

### Issue: Fingerprint generation errors

**Solution**: Check that jellyfish is installed
```bash
pip install jellyfish
python -c "import jellyfish; print('✅ jellyfish installed')"
```

### Issue: Database constraint violations

**Solution**: Ensure migration ran successfully
```sql
-- Check for unique constraint on fingerprint
SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_name = 'cards'
AND constraint_type = 'UNIQUE'
AND constraint_name LIKE '%fingerprint%';
```

### Issue: Slow duplicate detection

**Solution**: Check indexes exist
```sql
-- Check for required indexes
SELECT indexname FROM pg_indexes
WHERE tablename = 'cards'
AND indexname LIKE '%fingerprint%'
OR indexname LIKE '%normalized%';
```

**Expected indexes:**
- `idx_cards_fingerprint` (UNIQUE)
- `idx_cards_normalized`
- `idx_cards_normalized_trgm` (if pg_trgm available)

### Issue: Too many false positives

**Solution**: Adjust similarity threshold in `credit_card_uploader.py`:

```python
# Default threshold (line ~164)
if match_type in ['auto_merge', 'exact_fingerprint']:
    # Merge

# Change to higher threshold
if similarity >= 0.90 and match_type in ['auto_merge', 'exact_fingerprint']:
    # Merge only if ≥90% similarity
```

---

## Performance Benchmarks

**Expected performance** (on typical hardware):

| Operation | Target | Typical |
|-----------|--------|---------|
| Fingerprint generation | <5ms | ~2ms ✅ |
| Similarity calculation | <10ms | ~5ms ✅ |
| Exact fingerprint lookup | <20ms | ~10ms ✅ |
| Fuzzy match (20 candidates) | <50ms | ~20ms ✅ |
| Bulk dedup (1000 cards) | <10s | ~5s ✅ |

---

## Next Steps

1. ✅ **Run for 1 week** - Monitor activity with `monitor_duplicates.py`
2. ✅ **Review flagged items** - Use `review_duplicates.py` to handle edge cases
3. ✅ **Tune thresholds** - Adjust based on your data patterns
4. ✅ **Set up monitoring** - Schedule weekly reports
5. ✅ **Train team** - Share this guide with team members

---

## Support

**Documentation**:
- `TASK_DUPLICATE_PREVENTION.md` - Full technical specification
- `IMPLEMENTATION_SUMMARY.md` - Complete implementation details

**Common Commands**:
```bash
# Run scraper with duplicate prevention (automatic)
python enhanced_scraper.py

# Bulk deduplicate existing data
python bulk_deduplicate.py --dry-run

# Monitor activity
python monitor_duplicates.py --days 7

# Review flagged duplicates
python review_duplicates.py

# Run tests
python -m pytest tests/test_duplicate_prevention.py -v
```

---

## Success Indicators

After 1 week, you should see:

✅ **Zero new duplicates** in database
✅ **High auto-merge rate** (>80% of detections)
✅ **Low manual review queue** (<10 items)
✅ **Increasing confidence scores** (as cards gain more sources)
✅ **Faster scraping** (no manual deduplication needed)

**Congratulations!** Your duplicate prevention system is now live! 🎉

---

**Last Updated**: January 18, 2026
**Version**: 1.0.0
**Readiness**: Production-ready ✅

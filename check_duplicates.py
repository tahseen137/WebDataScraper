"""Check for duplicate cards in the database."""
from supabase import create_client
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv(override=True)

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get all cards
cards = client.table('cards').select('id, card_key, name, issuer').execute()

print(f"Total cards: {len(cards.data)}")

# Check for duplicate card_keys (shouldn't happen due to unique constraint)
keys = {}
duplicates = []
for c in cards.data:
    key = c['card_key']
    if key in keys:
        duplicates.append((key, keys[key], c['name']))
    else:
        keys[key] = c['name']

if duplicates:
    print(f"\nDuplicate card_keys found: {len(duplicates)}")
    for key, name1, name2 in duplicates:
        print(f"  {key}:")
        print(f"    - {name1}")
        print(f"    - {name2}")
else:
    print("\nNo duplicate card_keys found.")

# Check for similar card names (potential duplicates with different keys)
print("\n" + "="*60)
print("Cards by issuer (checking for similar names):")
print("="*60)

by_issuer = defaultdict(list)
for c in cards.data:
    by_issuer[c['issuer']].append((c['card_key'], c['name']))

for issuer in sorted(by_issuer.keys()):
    cards_list = by_issuer[issuer]
    print(f"\n{issuer} ({len(cards_list)} cards):")
    for key, name in sorted(cards_list, key=lambda x: x[1]):
        print(f"  - [{key}] {name}")

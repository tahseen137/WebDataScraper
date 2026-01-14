"""
Clean up duplicate cards from the database.
Keeps only cards that have category rewards (the curated ones).
"""
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv(override=True)

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get all cards
all_cards = client.table('cards').select('id, card_key, name').execute()
print(f"Total cards before cleanup: {len(all_cards.data)}")

# Get cards that have category rewards
cards_with_rewards = client.table('category_rewards').select('card_id').execute()
card_ids_with_rewards = set(r['card_id'] for r in cards_with_rewards.data)
print(f"Cards with category rewards: {len(card_ids_with_rewards)}")

# Find cards to delete (no category rewards)
cards_to_delete = []
for card in all_cards.data:
    if card['id'] not in card_ids_with_rewards:
        cards_to_delete.append(card)

print(f"Cards to delete (no rewards): {len(cards_to_delete)}")

# Delete cards without rewards
if cards_to_delete:
    print("\nDeleting cards without category rewards...")
    for card in cards_to_delete:
        client.table('cards').delete().eq('id', card['id']).execute()
    print(f"Deleted {len(cards_to_delete)} cards")

# Verify
remaining = client.table('cards').select('id', count='exact').execute()
print(f"\nCards remaining: {remaining.count}")

# Show remaining cards
cards = client.table('cards').select('card_key, name, issuer').order('issuer').execute()
print("\nRemaining cards:")
for c in cards.data:
    print(f"  [{c['issuer']}] {c['name']}")

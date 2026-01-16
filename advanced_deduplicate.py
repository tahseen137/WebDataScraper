"""
Advanced deduplication - removes duplicates by matching issuer + normalized name
Keeps only the card with the most complete data (category rewards, etc.)
"""
from supabase import create_client
import os
from dotenv import load_dotenv
from collections import defaultdict
import re

load_dotenv(override=True)

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("=" * 60)
print("ADVANCED CARD DEDUPLICATION")
print("=" * 60)

# Get all cards
all_cards = client.table('cards').select('*').execute()
print(f"\nTotal cards: {len(all_cards.data)}")

# Get category rewards for each card
category_rewards = client.table('category_rewards').select('card_id').execute()
cards_with_rewards = {}
for cr in category_rewards.data:
    card_id = cr['card_id']
    cards_with_rewards[card_id] = cards_with_rewards.get(card_id, 0) + 1

def normalize_card_name(name, issuer):
    """Aggressively normalize card name for comparison"""
    # Combine issuer and name
    full_name = f"{issuer} {name}".lower()
    
    # Remove all special characters and extra words
    full_name = re.sub(r'[®™*©]', '', full_name)
    full_name = re.sub(r'\s+', ' ', full_name)
    
    # Remove common noise words
    noise_words = [
        'card', 'credit', 'mastercard', 'visa', 'american express',
        'best', 'perks of the', 'perks of', 'the', 'a', 'an',
        'for', 'with', 'from', ':'
    ]
    for word in noise_words:
        full_name = full_name.replace(word, '')
    
    # Remove extra spaces
    full_name = ' '.join(full_name.split())
    
    return full_name.strip()

# Group cards by normalized name
card_groups = defaultdict(list)
for card in all_cards.data:
    normalized = normalize_card_name(card['name'], card['issuer'])
    card_groups[normalized].append(card)

print(f"\nUnique card names after normalization: {len(card_groups)}")

# Find and score duplicates
duplicates_found = 0
cards_to_delete = []

for norm_name, cards in card_groups.items():
    if len(cards) > 1:
        duplicates_found += len(cards) - 1
        
        print(f"\n{'='*60}")
        print(f"Duplicate group: {norm_name}")
        print(f"Found {len(cards)} versions:")
        
        # Score each card
        scored_cards = []
        for card in cards:
            score = 0
            
            # Has category rewards? +100 per reward
            reward_count = cards_with_rewards.get(card['id'], 0)
            score += reward_count * 100
            
            # Shorter card_key (cleaner) +50
            if len(card['card_key']) < 50:
                score += 50
            
            # Has annual fee data +20
            if card['annual_fee'] is not None and card['annual_fee'] >= 0:
                score += 20
            
            # Base reward rate > 0 +10
            if card['base_reward_rate'] and card['base_reward_rate'] > 0:
                score += 10
            
            # Prefer cards without "best", "perks" in key -50
            if any(word in card['card_key'] for word in ['best-', 'perks-']):
                score -= 50
            
            scored_cards.append((score, card))
            print(f"  [{score:4d}] {card['name'][:50]} ({card['card_key'][:40]})")
        
        # Sort by score (highest first)
        scored_cards.sort(reverse=True, key=lambda x: x[0])
        
        # Keep the best one, delete the rest
        best_card = scored_cards[0][1]
        print(f"\n  ✓ KEEPING: {best_card['name'][:50]}")
        
        for score, card in scored_cards[1:]:
            cards_to_delete.append(card)
            print(f"  ✗ DELETING: {card['name'][:50]}")

print(f"\n" + "=" * 60)
print(f"Summary:")
print(f"  Total cards: {len(all_cards.data)}")
print(f"  Unique cards: {len(card_groups)}")
print(f"  Duplicates found: {duplicates_found}")
print(f"  Cards to delete: {len(cards_to_delete)}")
print("=" * 60)

if cards_to_delete:
    print(f"\nThis will delete {len(cards_to_delete)} duplicate cards.")
    print(f"You will have {len(all_cards.data) - len(cards_to_delete)} unique cards remaining.")
    confirm = input("\nProceed with deletion? (yes/no): ")
    
    if confirm.lower() == 'yes':
        print("\nDeleting duplicates...")
        deleted_count = 0
        for card in cards_to_delete:
            try:
                # Delete category rewards first
                client.table('category_rewards').delete().eq('card_id', card['id']).execute()
                # Delete signup bonuses
                client.table('signup_bonuses').delete().eq('card_id', card['id']).execute()
                # Delete card
                client.table('cards').delete().eq('id', card['id']).execute()
                deleted_count += 1
            except Exception as e:
                print(f"  Error deleting {card['name']}: {e}")
        
        print(f"\n✓ Successfully deleted {deleted_count} duplicate cards")
        
        # Show final count
        remaining = client.table('cards').select('id', count='exact').execute()
        print(f"\nFinal card count: {remaining.count}")
    else:
        print("\nCancelled.")
else:
    print("\n✓ No duplicates found!")

"""
Remove duplicate cards from database by keeping the best version of each card.
Prioritizes cards with category rewards and more complete data.
"""
from supabase import create_client
import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv(override=True)

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

print("=" * 60)
print("DEDUPLICATING CARDS")
print("=" * 60)

# Get all cards
all_cards = client.table('cards').select('*').execute()
print(f"\nTotal cards: {len(all_cards.data)}")

# Get category rewards for each card
category_rewards = client.table('category_rewards').select('card_id').execute()
cards_with_rewards = set(r['card_id'] for r in category_rewards.data)

# Group cards by normalized name
def normalize_name(name):
    """Normalize card name for comparison"""
    name = name.lower()
    # Remove common prefixes/suffixes
    name = name.replace('®', '').replace('™', '').replace('*', '')
    name = name.replace('card', '').replace('mastercard', '').replace('visa', '')
    name = name.replace('best ', '').replace('perks of the ', '')
    name = name.replace('  ', ' ').strip()
    return name

# Group cards by issuer and normalized name
card_groups = defaultdict(list)
for card in all_cards.data:
    key = (card['issuer'].lower(), normalize_name(card['name']))
    card_groups[key].append(card)

# Find duplicates
duplicates_found = 0
cards_to_delete = []

for (issuer, norm_name), cards in card_groups.items():
    if len(cards) > 1:
        duplicates_found += len(cards) - 1
        
        # Score each card (higher is better)
        scored_cards = []
        for card in cards:
            score = 0
            # Has category rewards? +100
            if card['id'] in cards_with_rewards:
                score += 100
            # Shorter card_key (usually cleaner) +10
            if len(card['card_key']) < 50:
                score += 10
            # Has annual fee data +5
            if card['annual_fee'] is not None:
                score += 5
            # Base reward rate > 0 +5
            if card['base_reward_rate'] > 0:
                score += 5
            
            scored_cards.append((score, card))
        
        # Sort by score (highest first)
        scored_cards.sort(reverse=True, key=lambda x: x[0])
        
        # Keep the best one, delete the rest
        best_card = scored_cards[0][1]
        for score, card in scored_cards[1:]:
            cards_to_delete.append(card)
            print(f"\n  Duplicate: {card['name'][:60]}")
            print(f"    Keeping: {best_card['card_key']} (score: {scored_cards[0][0]})")
            print(f"    Deleting: {card['card_key']} (score: {score})")

print(f"\n" + "=" * 60)
print(f"Found {duplicates_found} duplicate cards")
print(f"Will delete {len(cards_to_delete)} cards")
print("=" * 60)

if cards_to_delete:
    confirm = input("\nProceed with deletion? (yes/no): ")
    if confirm.lower() == 'yes':
        print("\nDeleting duplicates...")
        for card in cards_to_delete:
            # Delete category rewards first
            client.table('category_rewards').delete().eq('card_id', card['id']).execute()
            # Delete signup bonuses
            client.table('signup_bonuses').delete().eq('card_id', card['id']).execute()
            # Delete card
            client.table('cards').delete().eq('id', card['id']).execute()
        
        print(f"✓ Deleted {len(cards_to_delete)} duplicate cards")
        
        # Show final count
        remaining = client.table('cards').select('id', count='exact').execute()
        print(f"\nCards remaining: {remaining.count}")
    else:
        print("Cancelled.")
else:
    print("\nNo duplicates found!")

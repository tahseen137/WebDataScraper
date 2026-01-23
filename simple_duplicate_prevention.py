"""
Simple Duplicate Prevention for WebDataScraper

A lightweight version that works with the existing scraper structure.
Focuses on preventing the most common duplicates without major refactoring.

Author: Kiro AI
Created: January 18, 2026
"""

import re
import hashlib
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher


def normalize_card_name(name: str) -> str:
    """
    Normalize card name for duplicate detection.
    
    Removes common formatting variations:
    - Trademark symbols (®™©℠)
    - Marketing characters (*†‡§)
    - "Card" suffix
    - Extra whitespace
    - Punctuation
    
    Args:
        name: Raw card name
        
    Returns:
        Normalized name
    """
    if not name:
        return ""
    
    # Lowercase
    name = name.lower()
    
    # Remove trademark symbols
    name = re.sub(r'[®™©℠]', '', name)
    
    # Remove marketing characters
    name = re.sub(r'[*†‡§]', '', name)
    
    # Remove "Card" suffix
    name = re.sub(r'\s+card\s*$', '', name)
    
    # Remove "Perks of the" prefix
    name = re.sub(r'^perks\s+of\s+the\s+', '', name)
    
    # Replace punctuation with spaces
    name = re.sub(r'[^\w\s]', ' ', name)
    
    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name)
    
    return name.strip()


def generate_card_fingerprint(card_dict: Dict) -> str:
    """
    Generate a fingerprint for duplicate detection.
    
    Args:
        card_dict: Card data dictionary
        
    Returns:
        16-character fingerprint hash
    """
    # Extract key fields
    name = card_dict.get('name', '')
    issuer = card_dict.get('issuer', '')
    program = card_dict.get('reward_program', '')
    fee = float(card_dict.get('annual_fee', 0))
    
    # Normalize components
    normalized_name = normalize_card_name(name)
    normalized_issuer = issuer.lower().strip()
    normalized_program = re.sub(r'[®™©℠]', '', program.lower().strip())
    
    # Round fee to nearest $10 for bucketing
    fee_bucket = round(fee / 10) * 10
    
    # Create fingerprint string
    fingerprint_str = f"{normalized_issuer}|{normalized_name}|{normalized_program}|{fee_bucket}"
    
    # Generate hash
    hash_obj = hashlib.sha256(fingerprint_str.encode('utf-8'))
    return hash_obj.hexdigest()[:16]


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between two card names.
    
    Args:
        name1: First card name
        name2: Second card name
        
    Returns:
        Similarity score from 0.0 to 1.0
    """
    # Normalize both names
    norm1 = normalize_card_name(name1)
    norm2 = normalize_card_name(name2)
    
    # Handle empty strings
    if not norm1 and not norm2:
        return 1.0
    if not norm1 or not norm2:
        return 0.0
    
    # Exact match
    if norm1 == norm2:
        return 1.0
    
    # Calculate edit distance similarity
    edit_similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    # Calculate token overlap
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    
    if len(tokens1) == 0 and len(tokens2) == 0:
        return 1.0
    
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    
    if len(union) == 0:
        return 0.0
    
    token_similarity = len(intersection) / len(union)
    
    # Weighted combination (60% edit distance, 40% token overlap)
    return (edit_similarity * 0.6) + (token_similarity * 0.4)


def is_likely_duplicate(card1: Dict, card2: Dict, threshold: float = 0.85) -> bool:
    """
    Check if two cards are likely duplicates.
    
    Args:
        card1: First card dictionary
        card2: Second card dictionary
        threshold: Similarity threshold (default 0.85)
        
    Returns:
        True if cards are likely duplicates
    """
    # Must have same issuer and program
    if (card1.get('issuer', '').lower() != card2.get('issuer', '').lower() or
        card1.get('reward_program', '').lower() != card2.get('reward_program', '').lower()):
        return False
    
    # Annual fee must be within $20
    fee1 = float(card1.get('annual_fee', 0))
    fee2 = float(card2.get('annual_fee', 0))
    if abs(fee1 - fee2) > 20:
        return False
    
    # Check name similarity
    name_similarity = calculate_name_similarity(
        card1.get('name', ''),
        card2.get('name', '')
    )
    
    return name_similarity >= threshold


def find_duplicates_in_batch(cards: List[Dict], threshold: float = 0.85) -> List[Tuple[int, int, float]]:
    """
    Find duplicate pairs in a batch of cards.
    
    Args:
        cards: List of card dictionaries
        threshold: Similarity threshold
        
    Returns:
        List of (index1, index2, similarity) tuples
    """
    duplicates = []
    
    for i in range(len(cards)):
        for j in range(i + 1, len(cards)):
            if is_likely_duplicate(cards[i], cards[j], threshold):
                similarity = calculate_name_similarity(
                    cards[i].get('name', ''),
                    cards[j].get('name', '')
                )
                duplicates.append((i, j, similarity))
    
    return duplicates


def merge_duplicate_cards(primary: Dict, duplicate: Dict) -> Dict:
    """
    Merge two duplicate cards, keeping the best data from each.
    
    Args:
        primary: Primary card to keep
        duplicate: Duplicate card to merge
        
    Returns:
        Merged card dictionary
    """
    merged = primary.copy()
    
    # Track sources
    primary_sources = primary.get('sources', [])
    duplicate_sources = duplicate.get('sources', [])
    if isinstance(primary_sources, str):
        primary_sources = [primary_sources]
    if isinstance(duplicate_sources, str):
        duplicate_sources = [duplicate_sources]
    
    all_sources = list(set(primary_sources + duplicate_sources))
    merged['sources'] = all_sources
    
    # Increase confidence
    merged['confidence'] = min(1.0, primary.get('confidence', 0.5) + 0.2)
    
    # Prefer non-zero annual fee
    if duplicate.get('annual_fee', 0) > 0 and primary.get('annual_fee', 0) == 0:
        merged['annual_fee'] = duplicate['annual_fee']
    elif primary.get('annual_fee', 0) > 0 and duplicate.get('annual_fee', 0) > 0:
        # Average the fees
        merged['annual_fee'] = (primary.get('annual_fee', 0) + duplicate.get('annual_fee', 0)) / 2
    
    # Add fingerprint and normalized name
    merged['fingerprint'] = generate_card_fingerprint(merged)
    merged['normalized_name'] = normalize_card_name(merged.get('name', ''))
    
    return merged


def deduplicate_card_list(cards: List[Dict], threshold: float = 0.90) -> List[Dict]:
    """
    Remove duplicates from a list of cards.
    
    Args:
        cards: List of card dictionaries
        threshold: Similarity threshold for merging
        
    Returns:
        Deduplicated list of cards
    """
    if len(cards) <= 1:
        return cards
    
    # Find duplicates
    duplicates = find_duplicates_in_batch(cards, threshold)
    
    if not duplicates:
        # No duplicates found, just add fingerprints
        for card in cards:
            card['fingerprint'] = generate_card_fingerprint(card)
            card['normalized_name'] = normalize_card_name(card.get('name', ''))
        return cards
    
    # Create a set to track which cards to remove
    to_remove = set()
    
    # Process duplicates (merge into first occurrence)
    for i, j, similarity in duplicates:
        if j not in to_remove:  # Only merge if duplicate hasn't been removed yet
            # Merge j into i
            cards[i] = merge_duplicate_cards(cards[i], cards[j])
            to_remove.add(j)
            print(f"Merged duplicate: '{cards[j].get('name', '')}' -> '{cards[i].get('name', '')}' (similarity: {similarity:.3f})")
    
    # Remove duplicates (in reverse order to maintain indices)
    for idx in sorted(to_remove, reverse=True):
        cards.pop(idx)
    
    # Add fingerprints to remaining cards
    for card in cards:
        if 'fingerprint' not in card:
            card['fingerprint'] = generate_card_fingerprint(card)
        if 'normalized_name' not in card:
            card['normalized_name'] = normalize_card_name(card.get('name', ''))
    
    return cards


# Example usage and testing
if __name__ == "__main__":
    # Test data
    test_cards = [
        {
            'name': 'TD® Aeroplan® Visa Infinite*',
            'issuer': 'TD',
            'reward_program': 'Aeroplan',
            'annual_fee': 139.99,
            'sources': ['Ratehub']
        },
        {
            'name': 'TD Aeroplan Visa Infinite Card',
            'issuer': 'TD',
            'reward_program': 'Aeroplan',
            'annual_fee': 139,
            'sources': ['NerdWallet']
        },
        {
            'name': 'American Express Cobalt Card',
            'issuer': 'American Express',
            'reward_program': 'Membership Rewards',
            'annual_fee': 120,
            'sources': ['MoneySense']
        }
    ]
    
    print("Original cards:", len(test_cards))
    for card in test_cards:
        print(f"  - {card['name']}")
    
    print("\nTesting duplicate detection...")
    duplicates = find_duplicates_in_batch(test_cards)
    print(f"Found {len(duplicates)} duplicate pairs:")
    for i, j, sim in duplicates:
        print(f"  {i} <-> {j}: {sim:.3f}")
    
    print("\nDeduplicating...")
    deduplicated = deduplicate_card_list(test_cards.copy())
    print(f"After deduplication: {len(deduplicated)} cards")
    for card in deduplicated:
        print(f"  - {card['name']} (sources: {card.get('sources', [])})")
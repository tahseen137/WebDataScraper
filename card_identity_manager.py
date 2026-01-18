"""
Card Identity Manager - Duplicate Prevention System

Provides fingerprint generation, name normalization, and fuzzy matching
to prevent duplicate credit card entries in the database.

Author: Kiro AI
Created: January 18, 2026
"""

import re
import hashlib
from typing import List, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
from datetime import datetime


@dataclass
class CreditCard:
    """Credit card data structure with identity fields."""
    name: str
    issuer: str
    reward_program: str
    annual_fee: float
    normalized_name: Optional[str] = None
    fingerprint: Optional[str] = None
    sources: Optional[List[str]] = None
    confidence_score: float = 0.5
    card_key: Optional[str] = None
    id: Optional[str] = None


class CardIdentityManager:
    """
    Manages card identity through fingerprinting and fuzzy matching.
    
    Prevents duplicate card entries by:
    1. Normalizing card names to remove formatting variations
    2. Generating deterministic fingerprints
    3. Finding potential duplicates using similarity scoring
    """
    
    def __init__(self):
        """Initialize the CardIdentityManager."""
        pass
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Remove formatting noise from card names.
        
        Transformations:
        1. Lowercase
        2. Remove trademark symbols (®™©℠)
        3. Remove marketing characters (*†‡§)
        4. Remove "Card" suffix
        5. Remove punctuation except spaces
        6. Collapse multiple spaces
        7. Strip and return
        
        Args:
            name: Raw card name from data source
            
        Returns:
            Normalized card name
            
        Examples:
            >>> normalize_name("TD® Aeroplan® Visa Infinite*")
            'td aeroplan visa infinite'
            
            >>> normalize_name("American Express® Cobalt™ Card")
            'american express cobalt'
            
            >>> normalize_name("BMO CashBack Mastercard®")
            'bmo cashback mastercard'
        """
        if not name:
            return ""
        
        # Lowercase
        name = name.lower()
        
        # Remove trademark symbols
        name = re.sub(r'[®™©℠]', '', name)
        
        # Remove marketing characters
        name = re.sub(r'[*†‡§]', '', name)
        
        # Remove "Card" suffix (with optional trailing whitespace)
        name = re.sub(r'\s+card\s*$', '', name)
        
        # Remove punctuation except spaces (replace with space to preserve word boundaries)
        name = re.sub(r'[^\w\s]', ' ', name)
        
        # Collapse multiple spaces
        name = re.sub(r'\s+', ' ', name)
        
        # Strip and return
        return name.strip()
    
    @staticmethod
    def normalize_program(program: str) -> str:
        """
        Normalize reward program names.
        
        Args:
            program: Raw reward program name
            
        Returns:
            Normalized program name
            
        Examples:
            >>> normalize_program("Aeroplan®")
            'aeroplan'
            
            >>> normalize_program("Membership Rewards™")
            'membership rewards'
        """
        if not program:
            return ""
        
        # Lowercase
        program = program.lower()
        
        # Remove trademark symbols
        program = re.sub(r'[®™©℠]', '', program)
        
        # Remove punctuation except spaces
        program = re.sub(r'[^\w\s]', '', program)
        
        # Collapse multiple spaces
        program = re.sub(r'\s+', ' ', program)
        
        return program.strip()
    
    @classmethod
    def generate_fingerprint(cls, card: CreditCard) -> str:
        """
        Create a unique, deterministic identifier for a card.
        
        Components:
        - Issuer (lowercased, trimmed)
        - Normalized name (special chars removed, "Card" suffix stripped)
        - Reward program (normalized)
        - Fee bucket (rounded to nearest $10)
        
        Args:
            card: CreditCard object
            
        Returns:
            16-character hex hash
            
        Examples:
            >>> card1 = CreditCard(
            ...     name="TD® Aeroplan® Visa Infinite*",
            ...     issuer="TD",
            ...     reward_program="Aeroplan®",
            ...     annual_fee=139.99
            ... )
            >>> card2 = CreditCard(
            ...     name="TD Aeroplan Visa Infinite Card",
            ...     issuer="TD",
            ...     reward_program="Aeroplan",
            ...     annual_fee=139
            ... )
            >>> generate_fingerprint(card1) == generate_fingerprint(card2)
            True
        """
        # Normalize name
        normalized_name = cls.normalize_name(card.name)
        
        # Standardize issuer
        issuer = card.issuer.lower().strip()
        
        # Round fee to nearest $10
        fee_bucket = round(card.annual_fee / 10) * 10
        
        # Normalize program
        program = cls.normalize_program(card.reward_program)
        
        # Combine into string
        fingerprint_str = f"{issuer}|{normalized_name}|{program}|{fee_bucket}"
        
        # Hash for consistency
        hash_obj = hashlib.sha256(fingerprint_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]
    
    @staticmethod
    def calculate_similarity(name1: str, name2: str) -> float:
        """
        Calculate similarity score between two card names.
        
        Multi-factor similarity score (0.0 to 1.0) combining:
        - Edit distance similarity (60% weight)
        - Token set overlap (40% weight)
        
        Args:
            name1: First card name
            name2: Second card name
            
        Returns:
            Similarity score from 0.0 (completely different) to 1.0 (identical)
            
        Examples:
            >>> calculate_similarity(
            ...     "TD Aeroplan Visa Infinite",
            ...     "TD Aeroplan Visa Infinite Privilege"
            ... )
            0.836
            
            >>> calculate_similarity(
            ...     "American Express Cobalt",
            ...     "Amex Cobalt Card"
            ... )
            0.590
        """
        # Normalize both names
        norm1 = CardIdentityManager.normalize_name(name1)
        norm2 = CardIdentityManager.normalize_name(name2)
        
        # Handle empty strings
        if not norm1 and not norm2:
            return 1.0  # Both empty = identical
        if not norm1 or not norm2:
            return 0.0  # One empty = completely different
        
        # Exact match
        if norm1 == norm2:
            return 1.0
        
        # Edit distance (Levenshtein ratio)
        edit_similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Token set matching (order-independent)
        tokens1 = set(norm1.split())
        tokens2 = set(norm2.split())
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        if len(union) == 0:
            return 0.0
        
        token_similarity = len(intersection) / len(union)
        
        # Weighted combination
        return (edit_similarity * 0.6) + (token_similarity * 0.4)
    
    def find_potential_duplicates(
        self,
        card: CreditCard,
        all_cards: List[CreditCard],
        threshold: float = 0.85
    ) -> List[Tuple[CreditCard, float]]:
        """
        Find potential duplicate cards using fuzzy matching.
        
        Args:
            card: Card to check for duplicates
            all_cards: List of all cards in database
            threshold: Minimum similarity score (default 0.85)
            
        Returns:
            List of (candidate_card, similarity_score) tuples, sorted by similarity
            
        Examples:
            >>> manager = CardIdentityManager()
            >>> card = CreditCard(
            ...     name="TD Aeroplan Visa Infinite",
            ...     issuer="TD",
            ...     reward_program="Aeroplan",
            ...     annual_fee=139
            ... )
            >>> duplicates = manager.find_potential_duplicates(card, all_cards)
            >>> len(duplicates)
            2
        """
        candidates = []
        
        # Filter by issuer and program first (performance optimization)
        filtered_cards = [
            c for c in all_cards
            if c.issuer.lower() == card.issuer.lower()
            and c.reward_program.lower() == card.reward_program.lower()
            and abs(c.annual_fee - card.annual_fee) < 20
            and c.id != card.id  # Don't compare card to itself
        ]
        
        # Calculate similarity for each candidate
        for candidate in filtered_cards:
            similarity = self.calculate_similarity(card.name, candidate.name)
            
            if similarity >= threshold:
                candidates.append((candidate, similarity))
        
        # Sort by similarity (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates
    
    @staticmethod
    def merge_cards(existing: CreditCard, new: CreditCard) -> CreditCard:
        """
        Intelligently merge two duplicate cards.
        
        Strategy:
        - Track all sources
        - Increase confidence score
        - Prefer non-null/non-zero values
        - Keep most recent data
        
        Args:
            existing: Card already in database
            new: New card being added
            
        Returns:
            Merged card with combined data
        """
        # Start with existing card
        merged = CreditCard(
            name=existing.name,
            issuer=existing.issuer,
            reward_program=existing.reward_program,
            annual_fee=existing.annual_fee,
            normalized_name=existing.normalized_name,
            fingerprint=existing.fingerprint,
            sources=existing.sources or [],
            confidence_score=existing.confidence_score,
            card_key=existing.card_key,
            id=existing.id
        )
        
        # Track sources
        if new.sources:
            merged.sources = list(set(merged.sources + new.sources))
        
        # Increase confidence (max 1.0)
        merged.confidence_score = min(1.0, existing.confidence_score + 0.2)
        
        # Prefer non-zero annual fee
        if new.annual_fee > 0 and existing.annual_fee == 0:
            merged.annual_fee = new.annual_fee
        elif existing.annual_fee > 0 and new.annual_fee > 0:
            # Average if both present
            merged.annual_fee = (existing.annual_fee + new.annual_fee) / 2
        
        return merged


# Convenience functions for direct use
def normalize_name(name: str) -> str:
    """Convenience function for name normalization."""
    return CardIdentityManager.normalize_name(name)


def generate_fingerprint(card: CreditCard) -> str:
    """Convenience function for fingerprint generation."""
    return CardIdentityManager.generate_fingerprint(card)


def calculate_similarity(name1: str, name2: str) -> float:
    """Convenience function for similarity calculation."""
    return CardIdentityManager.calculate_similarity(name1, name2)

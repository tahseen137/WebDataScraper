"""
Reward Program Registry - Complete Taxonomy for Canadian Credit Card Programs

Comprehensive registry of all major Canadian credit card reward programs with:
- Program families and hierarchies
- Currency types and classifications
- Accurate valuations by redemption type
- Transfer partners
- Issuer banks

Author: WebDataScraper Team
Created: January 18, 2026
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


# ============================================================================
# CURRENCY TYPE DEFINITIONS
# ============================================================================

CURRENCY_TYPES = {
    'cashback': {
        'name': 'Cash Back',
        'description': 'Direct cash value, deposited to account or statement credit',
        'valuation_range': (1.0, 1.0),  # Always 1.0¢ per dollar
        'flexibility': 'highest',
        'transferable': False
    },
    'airline_miles': {
        'name': 'Airline Miles',
        'description': 'Miles redeemable for flights, upgrades, or airline-specific rewards',
        'valuation_range': (0.1, 2.1),  # 0.1¢ - 2.1¢ per mile
        'flexibility': 'low',
        'transferable': True
    },
    'flexible_points': {
        'name': 'Flexible Points',
        'description': 'Points transferable to multiple partners or redeemable for various rewards',
        'valuation_range': (1.0, 2.0),  # 1.0¢ - 2.0¢ per point
        'flexibility': 'high',
        'transferable': True
    },
    'retail_points': {
        'name': 'Retail Points',
        'description': 'Points redeemable for merchandise, statement credit, or bank-specific rewards',
        'valuation_range': (0.1, 1.0),  # 0.1¢ - 1.0¢ per point
        'flexibility': 'medium',
        'transferable': False
    },
    'entertainment_points': {
        'name': 'Entertainment Points',
        'description': 'Points for movies, dining, groceries, and entertainment',
        'valuation_range': (0.8, 1.0),  # 0.8¢ - 1.0¢ per point
        'flexibility': 'medium',
        'transferable': False
    },
    'travel_points': {
        'name': 'Travel Points',
        'description': 'Points redeemable for travel bookings',
        'valuation_range': (0.8, 1.0),  # 0.8¢ - 1.0¢ per point
        'flexibility': 'medium',
        'transferable': False
    },
    'hotel_points': {
        'name': 'Hotel Points',
        'description': 'Points for hotel stays and hotel-specific rewards',
        'valuation_range': (0.5, 0.8),  # 0.5¢ - 0.8¢ per point
        'flexibility': 'low',
        'transferable': True
    }
}


# ============================================================================
# COMPLETE REWARD PROGRAM REGISTRY
# ============================================================================

REWARD_PROGRAMS = {
    # =================================================================
    # AIRLINE MILES PROGRAMS
    # =================================================================

    'aeroplan': {
        'program_family': 'Aeroplan',
        'program_name': 'Aeroplan',
        'currency_type': 'airline_miles',
        'base_valuation': 1.8,  # cents per mile
        'valuations': {
            'flight_redemption': 1.8,
            'upgrade': 1.5,
            'merchandise': 0.7
        },
        'transfer_partners': [
            'Air Canada',
            'Star Alliance Partners',
            'United Airlines',
            'Lufthansa'
        ],
        'redemption_options': [
            'flights',
            'upgrades',
            'hotels',
            'car_rentals',
            'merchandise'
        ],
        'issuer_banks': ['TD', 'CIBC', 'American Express'],
        'currency_name': 'miles',
        'minimum_redemption': 5000,
        'expiry_policy': 'No expiry with activity',
        'notes': 'Premium airline program, best value for long-haul flights'
    },

    'air_miles': {
        'program_family': 'AIR MILES',
        'program_name': 'AIR MILES',
        'currency_type': 'airline_miles',
        'base_valuation': 0.12,  # cents per mile
        'valuations': {
            'flight_redemption': 0.12,
            'merchandise': 0.10,
            'cash': 0.10
        },
        'transfer_partners': [],
        'redemption_options': [
            'flights',
            'merchandise',
            'cash_redemption',
            'experiences'
        ],
        'issuer_banks': ['BMO', 'American Express', 'Safeway'],
        'currency_name': 'miles',
        'minimum_redemption': 95,  # Cash Miles
        'expiry_policy': '5 years',
        'notes': 'Two tiers: Cash Miles and Dream Miles'
    },

    'westjet_rewards': {
        'program_family': 'WestJet Rewards',
        'program_name': 'WestJet Dollars',
        'currency_type': 'airline_miles',
        'base_valuation': 1.5,  # cents per dollar
        'valuations': {
            'flight_redemption': 1.5,
            'vacation_packages': 1.0
        },
        'transfer_partners': ['WestJet'],
        'redemption_options': [
            'flights',
            'vacation_packages',
            'seat_upgrades'
        ],
        'issuer_banks': ['RBC', 'WestJet'],
        'currency_name': 'WestJet dollars',
        'minimum_redemption': 1,
        'expiry_policy': 'No expiry',
        'notes': 'Direct dollar value for WestJet flights'
    },

    # =================================================================
    # FLEXIBLE POINTS PROGRAMS
    # =================================================================

    'membership_rewards': {
        'program_family': 'Membership Rewards',
        'program_name': 'Membership Rewards',
        'currency_type': 'flexible_points',
        'base_valuation': 2.0,  # cents per point
        'valuations': {
            'travel_transfer': 2.0,
            'fixed_points_travel': 1.0,
            'statement_credit': 0.6,
            'merchandise': 0.5
        },
        'transfer_partners': [
            'Aeroplan',
            'British Airways Avios',
            'Marriott Bonvoy',
            'Hilton Honors',
            'Delta SkyMiles'
        ],
        'redemption_options': [
            'travel_transfers',
            'fixed_points_travel',
            'statement_credit',
            'merchandise',
            'gift_cards'
        ],
        'issuer_banks': ['American Express'],
        'currency_name': 'points',
        'minimum_redemption': 1000,
        'expiry_policy': 'No expiry with card open',
        'notes': 'Premium flexible program, best value with travel transfers'
    },

    'avion': {
        'program_family': 'Avion',
        'program_name': 'Avion Rewards',
        'currency_type': 'flexible_points',
        'base_valuation': 1.5,  # cents per point
        'valuations': {
            'travel_redemption': 1.5,
            'statement_credit': 1.0,
            'merchandise': 0.7
        },
        'transfer_partners': [
            'British Airways Avios',
            'Cathay Pacific',
            'WestJet Rewards'
        ],
        'redemption_options': [
            'travel',
            'statement_credit',
            'merchandise',
            'gift_cards'
        ],
        'issuer_banks': ['RBC'],
        'currency_name': 'points',
        'minimum_redemption': 15000,
        'expiry_policy': 'No expiry',
        'notes': 'RBC premium program, good for travel redemptions'
    },

    'aventura': {
        'program_family': 'Aventura',
        'program_name': 'Aventura Rewards',
        'currency_type': 'flexible_points',
        'base_valuation': 1.0,  # cents per point
        'valuations': {
            'travel_redemption': 1.0,
            'statement_credit': 0.8,
            'merchandise': 0.6
        },
        'transfer_partners': [],
        'redemption_options': [
            'travel',
            'statement_credit',
            'merchandise'
        ],
        'issuer_banks': ['CIBC'],
        'currency_name': 'points',
        'minimum_redemption': 10000,
        'expiry_policy': 'No expiry',
        'notes': 'CIBC flexible program'
    },

    # =================================================================
    # RETAIL POINTS PROGRAMS
    # =================================================================

    'td_rewards': {
        'program_family': 'TD Rewards',
        'program_name': 'TD Rewards',
        'currency_type': 'retail_points',
        'base_valuation': 0.5,  # cents per point
        'valuations': {
            'travel': 0.5,
            'statement_credit': 0.4,
            'merchandise': 0.4
        },
        'transfer_partners': [],
        'redemption_options': [
            'travel',
            'statement_credit',
            'merchandise',
            'gift_cards'
        ],
        'issuer_banks': ['TD'],
        'currency_name': 'points',
        'minimum_redemption': 20000,
        'expiry_policy': 'No expiry',
        'notes': 'TD bank-specific program'
    },

    'bmo_rewards': {
        'program_family': 'BMO Rewards',
        'program_name': 'BMO Rewards',
        'currency_type': 'retail_points',
        'base_valuation': 0.7,  # cents per point
        'valuations': {
            'travel': 0.7,
            'statement_credit': 0.5,
            'merchandise': 0.5
        },
        'transfer_partners': [],
        'redemption_options': [
            'travel',
            'statement_credit',
            'merchandise',
            'investments'
        ],
        'issuer_banks': ['BMO'],
        'currency_name': 'points',
        'minimum_redemption': 15000,
        'expiry_policy': 'No expiry',
        'notes': 'BMO bank-specific program'
    },

    'pc_optimum': {
        'program_family': 'PC Optimum',
        'program_name': 'PC Optimum',
        'currency_type': 'retail_points',
        'base_valuation': 0.1,  # cents per point
        'valuations': {
            'grocery_redemption': 0.1,
            'gas': 0.1
        },
        'transfer_partners': [],
        'redemption_options': [
            'groceries',
            'gas',
            'pharmacy'
        ],
        'issuer_banks': ['PC Financial'],
        'currency_name': 'points',
        'minimum_redemption': 10000,
        'expiry_policy': 'No expiry',
        'notes': 'Loblaws ecosystem program'
    },

    'triangle_rewards': {
        'program_family': 'Triangle Rewards',
        'program_name': 'Triangle Rewards',
        'currency_type': 'retail_points',
        'base_valuation': 0.1,  # cents per point (Canadian Tire Money)
        'valuations': {
            'retail_redemption': 0.1
        },
        'transfer_partners': [],
        'redemption_options': [
            'canadian_tire',
            'gas',
            'sports_chek',
            'marks'
        ],
        'issuer_banks': ['Canadian Tire Financial Services'],
        'currency_name': 'Canadian Tire Money',
        'minimum_redemption': 500,
        'expiry_policy': 'No expiry',
        'notes': 'Canadian Tire ecosystem'
    },

    'mbna_rewards': {
        'program_family': 'MBNA Rewards',
        'program_name': 'MBNA Rewards',
        'currency_type': 'retail_points',
        'base_valuation': 1.0,  # cents per point
        'valuations': {
            'travel': 1.0,
            'statement_credit': 0.8,
            'merchandise': 0.7
        },
        'transfer_partners': [],
        'redemption_options': [
            'travel',
            'statement_credit',
            'merchandise'
        ],
        'issuer_banks': ['MBNA'],
        'currency_name': 'points',
        'minimum_redemption': 5000,
        'expiry_policy': 'No expiry',
        'notes': 'MBNA bank-specific program'
    },

    # =================================================================
    # ENTERTAINMENT POINTS PROGRAMS
    # =================================================================

    'scene_plus': {
        'program_family': 'Scene+',
        'program_name': 'Scene+',
        'currency_type': 'entertainment_points',
        'base_valuation': 1.0,  # cents per point
        'valuations': {
            'entertainment': 1.0,
            'groceries': 1.0,
            'gas': 1.0,
            'travel': 0.8
        },
        'transfer_partners': [],
        'redemption_options': [
            'movies',
            'dining',
            'groceries',
            'gas',
            'travel'
        ],
        'issuer_banks': ['Scotiabank'],
        'currency_name': 'points',
        'minimum_redemption': 1000,
        'expiry_policy': 'No expiry',
        'notes': 'Merged Scene and Scotia Rewards in 2022'
    },

    # =================================================================
    # TRAVEL POINTS PROGRAMS
    # =================================================================

    'odyssey_rewards': {
        'program_family': 'Odyssey',
        'program_name': 'Odyssey Rewards',
        'currency_type': 'travel_points',
        'base_valuation': 1.0,  # cents per point
        'valuations': {
            'travel': 1.0,
            'statement_credit': 0.8
        },
        'transfer_partners': [],
        'redemption_options': [
            'travel',
            'statement_credit'
        ],
        'issuer_banks': ['Desjardins'],
        'currency_name': 'points',
        'minimum_redemption': 10000,
        'expiry_policy': 'No expiry',
        'notes': 'Desjardins travel-focused program'
    },

    # =================================================================
    # CASHBACK PROGRAMS
    # =================================================================

    'cashback': {
        'program_family': 'Cash Back',
        'program_name': 'Straight Cash Back',
        'currency_type': 'cashback',
        'base_valuation': 1.0,  # Always 1.0¢ per dollar
        'valuations': {
            'cash': 1.0
        },
        'transfer_partners': [],
        'redemption_options': [
            'statement_credit',
            'direct_deposit',
            'cheque'
        ],
        'issuer_banks': ['All banks'],
        'currency_name': 'cash',
        'minimum_redemption': 25,  # $25 typical minimum
        'expiry_policy': 'No expiry',
        'notes': 'Generic cashback category for all cashback cards'
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_program_by_name(program_name: str) -> Optional[Dict]:
    """
    Get program details by program name.

    Args:
        program_name: Name of the program (e.g., 'aeroplan', 'membership_rewards')

    Returns:
        Program dictionary or None
    """
    return REWARD_PROGRAMS.get(program_name.lower().replace(' ', '_').replace('+', '_plus'))


def get_programs_by_currency_type(currency_type: str) -> List[Dict]:
    """
    Get all programs of a specific currency type.

    Args:
        currency_type: Type of currency (e.g., 'airline_miles', 'flexible_points')

    Returns:
        List of program dictionaries
    """
    return [
        {**program, 'key': key}
        for key, program in REWARD_PROGRAMS.items()
        if program['currency_type'] == currency_type
    ]


def get_programs_by_issuer(issuer: str) -> List[Dict]:
    """
    Get all programs from a specific issuer.

    Args:
        issuer: Issuer bank name (e.g., 'TD', 'American Express')

    Returns:
        List of program dictionaries
    """
    issuer_lower = issuer.lower()
    return [
        {**program, 'key': key}
        for key, program in REWARD_PROGRAMS.items()
        if any(issuer_lower in bank.lower() for bank in program['issuer_banks'])
    ]


def get_all_programs() -> List[Dict]:
    """
    Get all reward programs.

    Returns:
        List of all program dictionaries with keys
    """
    return [
        {**program, 'key': key}
        for key, program in REWARD_PROGRAMS.items()
    ]


def get_program_valuation(program_name: str, redemption_type: str = 'base') -> Optional[float]:
    """
    Get valuation for a specific redemption type.

    Args:
        program_name: Name of the program
        redemption_type: Type of redemption ('base', 'travel', etc.)

    Returns:
        Valuation in cents per point/mile, or None
    """
    program = get_program_by_name(program_name)
    if not program:
        return None

    if redemption_type == 'base':
        return program['base_valuation']

    return program.get('valuations', {}).get(redemption_type)


if __name__ == '__main__':
    # Example usage and validation
    print("=" * 70)
    print("REWARD PROGRAM REGISTRY")
    print("=" * 70)

    print(f"\nTotal programs: {len(REWARD_PROGRAMS)}")

    print("\nPrograms by currency type:")
    for currency_type in CURRENCY_TYPES.keys():
        programs = get_programs_by_currency_type(currency_type)
        print(f"  {currency_type}: {len(programs)} programs")

    print("\nSample program details (Membership Rewards):")
    mr = get_program_by_name('membership_rewards')
    if mr:
        print(f"  Family: {mr['program_family']}")
        print(f"  Type: {mr['currency_type']}")
        print(f"  Base Valuation: {mr['base_valuation']}¢")
        print(f"  Transfer Partners: {', '.join(mr['transfer_partners'][:3])}...")
        print(f"  Issuers: {', '.join(mr['issuer_banks'])}")

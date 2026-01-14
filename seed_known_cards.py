"""
Seed Known Cards with Category Rewards
Uploads the curated cards.json data to Supabase with full category rewards.
"""

import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(override=True)

# Comprehensive Canadian credit cards database with accurate category rewards and signup bonuses
KNOWN_CARDS = [
    # ============== TD CARDS ==============
    {
        "card_key": "td-aeroplan-visa-infinite",
        "name": "TD Aeroplan Visa Infinite",
        "issuer": "TD",
        "reward_program": "Aeroplan",
        "reward_currency": "airline_miles",
        "point_valuation": 1.8,
        "annual_fee": 139,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 1.5, "reward_unit": "multiplier", "description": "1.5x Aeroplan points on travel"},
            {"category": "gas", "multiplier": 1.5, "reward_unit": "multiplier", "description": "1.5x Aeroplan points on gas"},
            {"category": "groceries", "multiplier": 1.5, "reward_unit": "multiplier", "description": "1.5x Aeroplan points on groceries"},
        ],
        "signup_bonus": {"bonus_amount": 20000, "bonus_currency": "airline_miles", "spend_requirement": 1000, "timeframe_days": 90}
    },
    {
        "card_key": "td-cash-back-visa-infinite",
        "name": "TD Cash Back Visa Infinite",
        "issuer": "TD",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 139,
        "base_reward_rate": 1.0,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 3.0, "reward_unit": "percent", "description": "3% cash back on groceries"},
            {"category": "gas", "multiplier": 3.0, "reward_unit": "percent", "description": "3% cash back on gas"},
            {"category": "dining", "multiplier": 3.0, "reward_unit": "percent", "description": "3% cash back on dining"},
        ],
        "signup_bonus": {"bonus_amount": 100, "bonus_currency": "cashback", "spend_requirement": 500, "timeframe_days": 90}
    },
    {
        "card_key": "td-first-class-travel-visa-infinite",
        "name": "TD First Class Travel Visa Infinite",
        "issuer": "TD",
        "reward_program": "TD Rewards",
        "reward_currency": "points",
        "point_valuation": 0.5,
        "annual_fee": 139,
        "base_reward_rate": 3.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 9.0, "reward_unit": "multiplier", "description": "9x TD points on travel booked through Expedia for TD"},
        ],
        "signup_bonus": {"bonus_amount": 100000, "bonus_currency": "points", "spend_requirement": 1000, "timeframe_days": 90}
    },
    
    # ============== CIBC CARDS ==============
    {
        "card_key": "cibc-dividend-visa-infinite",
        "name": "CIBC Dividend Visa Infinite",
        "issuer": "CIBC",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 120,
        "base_reward_rate": 1.0,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 4.0, "reward_unit": "percent", "description": "4% cash back on groceries"},
            {"category": "gas", "multiplier": 4.0, "reward_unit": "percent", "description": "4% cash back on gas"},
            {"category": "dining", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on dining"},
        ],
        "signup_bonus": {"bonus_amount": 200, "bonus_currency": "cashback", "spend_requirement": 1000, "timeframe_days": 120}
    },
    {
        "card_key": "cibc-dividend-visa",
        "name": "CIBC Dividend Visa",
        "issuer": "CIBC",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 0,
        "base_reward_rate": 0.5,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on groceries"},
            {"category": "gas", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on gas"},
        ],
        "signup_bonus": None
    },
    {
        "card_key": "cibc-aventura-visa-infinite",
        "name": "CIBC Aventura Visa Infinite",
        "issuer": "CIBC",
        "reward_program": "Aventura",
        "reward_currency": "points",
        "point_valuation": 1.0,
        "annual_fee": 139,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x Aventura points on travel"},
            {"category": "gas", "multiplier": 1.5, "reward_unit": "multiplier", "description": "1.5x Aventura points on gas"},
            {"category": "groceries", "multiplier": 1.5, "reward_unit": "multiplier", "description": "1.5x Aventura points on groceries"},
        ],
        "signup_bonus": {"bonus_amount": 20000, "bonus_currency": "points", "spend_requirement": 1000, "timeframe_days": 120}
    },
    {
        "card_key": "cibc-aeroplan-visa-infinite",
        "name": "CIBC Aeroplan Visa Infinite",
        "issuer": "CIBC",
        "reward_program": "Aeroplan",
        "reward_currency": "airline_miles",
        "point_valuation": 1.8,
        "annual_fee": 139,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 1.5, "reward_unit": "multiplier", "description": "1.5x Aeroplan points on Air Canada"},
            {"category": "gas", "multiplier": 1.5, "reward_unit": "multiplier", "description": "1.5x Aeroplan points on gas"},
            {"category": "groceries", "multiplier": 1.5, "reward_unit": "multiplier", "description": "1.5x Aeroplan points on groceries"},
        ],
        "signup_bonus": {"bonus_amount": 40000, "bonus_currency": "airline_miles", "spend_requirement": 3000, "timeframe_days": 120}
    },
    
    # ============== SCOTIABANK CARDS ==============
    {
        "card_key": "scotiabank-gold-amex",
        "name": "Scotiabank Gold American Express",
        "issuer": "Scotiabank",
        "reward_program": "Scene+",
        "reward_currency": "points",
        "point_valuation": 1.0,
        "annual_fee": 150,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "groceries", "multiplier": 5.0, "reward_unit": "multiplier", "description": "5x Scene+ points on groceries"},
            {"category": "dining", "multiplier": 5.0, "reward_unit": "multiplier", "description": "5x Scene+ points on dining"},
            {"category": "entertainment", "multiplier": 3.0, "reward_unit": "multiplier", "description": "3x Scene+ points on entertainment"},
        ],
        "signup_bonus": {"bonus_amount": 30000, "bonus_currency": "points", "spend_requirement": 1000, "timeframe_days": 90}
    },
    {
        "card_key": "scotiabank-momentum-visa-infinite",
        "name": "Scotia Momentum Visa Infinite",
        "issuer": "Scotiabank",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 120,
        "base_reward_rate": 1.0,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 4.0, "reward_unit": "percent", "description": "4% cash back on groceries"},
            {"category": "dining", "multiplier": 4.0, "reward_unit": "percent", "description": "4% cash back on dining"},
            {"category": "gas", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on gas"},
        ],
        "signup_bonus": {"bonus_amount": 350, "bonus_currency": "cashback", "spend_requirement": 2000, "timeframe_days": 90}
    },
    {
        "card_key": "scotiabank-passport-visa-infinite",
        "name": "Scotiabank Passport Visa Infinite",
        "issuer": "Scotiabank",
        "reward_program": "Scene+",
        "reward_currency": "points",
        "point_valuation": 1.0,
        "annual_fee": 150,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "groceries", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x Scene+ points on groceries"},
            {"category": "dining", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x Scene+ points on dining"},
            {"category": "entertainment", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x Scene+ points on entertainment"},
            {"category": "travel", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x Scene+ points on travel"},
        ],
        "signup_bonus": {"bonus_amount": 35000, "bonus_currency": "points", "spend_requirement": 2000, "timeframe_days": 90}
    },
    
    # ============== AMERICAN EXPRESS CARDS ==============
    {
        "card_key": "amex-cobalt",
        "name": "American Express Cobalt Card",
        "issuer": "American Express",
        "reward_program": "Membership Rewards",
        "reward_currency": "points",
        "point_valuation": 2.0,
        "annual_fee": 156,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "dining", "multiplier": 5.0, "reward_unit": "multiplier", "description": "5x MR points on dining"},
            {"category": "groceries", "multiplier": 5.0, "reward_unit": "multiplier", "description": "5x MR points on groceries"},
            {"category": "travel", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x MR points on travel"},
            {"category": "gas", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x MR points on gas"},
        ],
        "signup_bonus": {"bonus_amount": 30000, "bonus_currency": "points", "spend_requirement": 3000, "timeframe_days": 90}
    },
    {
        "card_key": "amex-gold-rewards",
        "name": "American Express Gold Rewards Card",
        "issuer": "American Express",
        "reward_program": "Membership Rewards",
        "reward_currency": "points",
        "point_valuation": 2.0,
        "annual_fee": 150,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x MR points on travel"},
            {"category": "gas", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x MR points on gas"},
        ],
        "signup_bonus": {"bonus_amount": 40000, "bonus_currency": "points", "spend_requirement": 3000, "timeframe_days": 90}
    },
    {
        "card_key": "amex-simply-cash-preferred",
        "name": "SimplyCash Preferred Card from American Express",
        "issuer": "American Express",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 99,
        "base_reward_rate": 1.0,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on groceries"},
            {"category": "gas", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on gas"},
        ],
        "signup_bonus": {"bonus_amount": 400, "bonus_currency": "cashback", "spend_requirement": 3000, "timeframe_days": 90}
    },
    {
        "card_key": "amex-simply-cash",
        "name": "SimplyCash Card from American Express",
        "issuer": "American Express",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 0,
        "base_reward_rate": 1.25,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 1.25, "reward_unit": "percent", "description": "1.25% cash back on all purchases"},
        ],
        "signup_bonus": {"bonus_amount": 200, "bonus_currency": "cashback", "spend_requirement": 1500, "timeframe_days": 90}
    },
    {
        "card_key": "amex-aeroplan-reserve",
        "name": "American Express Aeroplan Reserve Card",
        "issuer": "American Express",
        "reward_program": "Aeroplan",
        "reward_currency": "airline_miles",
        "point_valuation": 1.8,
        "annual_fee": 599,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 3.0, "reward_unit": "multiplier", "description": "3x Aeroplan points on Air Canada"},
            {"category": "dining", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x Aeroplan points on dining"},
        ],
        "signup_bonus": {"bonus_amount": 80000, "bonus_currency": "airline_miles", "spend_requirement": 6000, "timeframe_days": 180}
    },
    {
        "card_key": "amex-platinum",
        "name": "The Platinum Card from American Express",
        "issuer": "American Express",
        "reward_program": "Membership Rewards",
        "reward_currency": "points",
        "point_valuation": 2.0,
        "annual_fee": 799,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 3.0, "reward_unit": "multiplier", "description": "3x MR points on travel booked through Amex Travel"},
            {"category": "dining", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x MR points on dining"},
        ],
        "signup_bonus": {"bonus_amount": 80000, "bonus_currency": "points", "spend_requirement": 8000, "timeframe_days": 90}
    },
    
    # ============== RBC CARDS ==============
    {
        "card_key": "rbc-avion-visa-infinite",
        "name": "RBC Avion Visa Infinite",
        "issuer": "RBC",
        "reward_program": "Avion",
        "reward_currency": "points",
        "point_valuation": 1.5,
        "annual_fee": 120,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 1.0, "reward_unit": "multiplier", "description": "1x Avion points on all purchases"},
        ],
        "signup_bonus": {"bonus_amount": 35000, "bonus_currency": "points", "spend_requirement": 5000, "timeframe_days": 90}
    },
    {
        "card_key": "rbc-cash-back-mastercard",
        "name": "RBC Cash Back Mastercard",
        "issuer": "RBC",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 0,
        "base_reward_rate": 0.5,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on groceries"},
        ],
        "signup_bonus": None
    },
    {
        "card_key": "rbc-westjet-world-elite",
        "name": "WestJet RBC World Elite Mastercard",
        "issuer": "RBC",
        "reward_program": "WestJet Rewards",
        "reward_currency": "points",
        "point_valuation": 1.5,
        "annual_fee": 119,
        "base_reward_rate": 1.5,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x WestJet points on WestJet purchases"},
            {"category": "groceries", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x WestJet points on groceries"},
            {"category": "gas", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x WestJet points on gas"},
        ],
        "signup_bonus": {"bonus_amount": 450, "bonus_currency": "points", "spend_requirement": 5000, "timeframe_days": 90}
    },
    
    # ============== BMO CARDS ==============
    {
        "card_key": "bmo-cashback-mastercard",
        "name": "BMO CashBack Mastercard",
        "issuer": "BMO",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 0,
        "base_reward_rate": 0.5,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 3.0, "reward_unit": "percent", "description": "3% cash back on groceries"},
        ],
        "signup_bonus": None
    },
    {
        "card_key": "bmo-eclipse-visa-infinite",
        "name": "BMO Eclipse Visa Infinite",
        "issuer": "BMO",
        "reward_program": "BMO Rewards",
        "reward_currency": "points",
        "point_valuation": 0.7,
        "annual_fee": 150,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "groceries", "multiplier": 5.0, "reward_unit": "multiplier", "description": "5x BMO points on groceries"},
            {"category": "dining", "multiplier": 5.0, "reward_unit": "multiplier", "description": "5x BMO points on dining"},
            {"category": "travel", "multiplier": 3.0, "reward_unit": "multiplier", "description": "3x BMO points on travel"},
        ],
        "signup_bonus": {"bonus_amount": 50000, "bonus_currency": "points", "spend_requirement": 3000, "timeframe_days": 90}
    },
    {
        "card_key": "bmo-air-miles-world-elite",
        "name": "BMO AIR MILES World Elite Mastercard",
        "issuer": "BMO",
        "reward_program": "AIR MILES",
        "reward_currency": "airline_miles",
        "point_valuation": 0.1,
        "annual_fee": 150,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "groceries", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2 AIR MILES per $12 on groceries"},
        ],
        "signup_bonus": {"bonus_amount": 5000, "bonus_currency": "airline_miles", "spend_requirement": 4500, "timeframe_days": 110}
    },
    {
        "card_key": "bmo-cashback-world-elite",
        "name": "BMO CashBack World Elite Mastercard",
        "issuer": "BMO",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 120,
        "base_reward_rate": 1.0,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 5.0, "reward_unit": "percent", "description": "5% cash back on groceries"},
            {"category": "gas", "multiplier": 5.0, "reward_unit": "percent", "description": "5% cash back on gas"},
            {"category": "dining", "multiplier": 5.0, "reward_unit": "percent", "description": "5% cash back on dining"},
        ],
        "signup_bonus": {"bonus_amount": 300, "bonus_currency": "cashback", "spend_requirement": 3000, "timeframe_days": 90}
    },
    
    # ============== NO-FEE CARDS ==============
    {
        "card_key": "tangerine-money-back",
        "name": "Tangerine Money-Back Credit Card",
        "issuer": "Tangerine",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 0,
        "base_reward_rate": 0.5,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on groceries (selected category)"},
            {"category": "gas", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on gas (selected category)"},
            {"category": "dining", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on dining (selected category)"},
        ],
        "signup_bonus": None
    },
    {
        "card_key": "simplii-cash-back-visa",
        "name": "Simplii Financial Cash Back Visa",
        "issuer": "Simplii",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 0,
        "base_reward_rate": 0.5,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "dining", "multiplier": 4.0, "reward_unit": "percent", "description": "4% cash back on dining"},
            {"category": "groceries", "multiplier": 1.5, "reward_unit": "percent", "description": "1.5% cash back on groceries"},
            {"category": "gas", "multiplier": 1.5, "reward_unit": "percent", "description": "1.5% cash back on gas"},
        ],
        "signup_bonus": {"bonus_amount": 400, "bonus_currency": "cashback", "spend_requirement": 5000, "timeframe_days": 120}
    },
    {
        "card_key": "rogers-world-elite-mastercard",
        "name": "Rogers World Elite Mastercard",
        "issuer": "Rogers Bank",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 0,
        "base_reward_rate": 1.5,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "online_shopping", "multiplier": 1.5, "reward_unit": "percent", "description": "1.5% cash back everywhere"},
        ],
        "signup_bonus": None
    },
    {
        "card_key": "pc-financial-world-elite",
        "name": "PC Financial World Elite Mastercard",
        "issuer": "PC Financial",
        "reward_program": "PC Optimum",
        "reward_currency": "points",
        "point_valuation": 0.1,
        "annual_fee": 0,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "groceries", "multiplier": 3.0, "reward_unit": "multiplier", "description": "3x PC Optimum points at Loblaws stores"},
        ],
        "signup_bonus": {"bonus_amount": 20000, "bonus_currency": "points", "spend_requirement": 0, "timeframe_days": 30}
    },
    {
        "card_key": "triangle-world-elite",
        "name": "Triangle World Elite Mastercard",
        "issuer": "Canadian Tire",
        "reward_program": "Triangle Rewards",
        "reward_currency": "points",
        "point_valuation": 0.1,
        "annual_fee": 0,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "gas", "multiplier": 4.0, "reward_unit": "multiplier", "description": "4x Triangle points at Canadian Tire Gas+"},
            {"category": "home_improvement", "multiplier": 4.0, "reward_unit": "multiplier", "description": "4x Triangle points at Canadian Tire"},
        ],
        "signup_bonus": None
    },
    
    # ============== NEO FINANCIAL CARDS ==============
    {
        "card_key": "neo-world-elite-mastercard",
        "name": "Neo World Elite Mastercard",
        "issuer": "Neo Financial",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 125,
        "base_reward_rate": 1.0,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 5.0, "reward_unit": "percent", "description": "5% cash back on groceries"},
            {"category": "gas", "multiplier": 3.0, "reward_unit": "percent", "description": "3% cash back on gas"},
        ],
        "signup_bonus": None
    },
    {
        "card_key": "neo-mastercard",
        "name": "Neo Mastercard",
        "issuer": "Neo Financial",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 0,
        "base_reward_rate": 0.5,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 1.0, "reward_unit": "percent", "description": "1% cash back on groceries"},
            {"category": "gas", "multiplier": 1.0, "reward_unit": "percent", "description": "1% cash back on gas"},
        ],
        "signup_bonus": None
    },
    
    # ============== MBNA CARDS ==============
    {
        "card_key": "mbna-rewards-world-elite",
        "name": "MBNA Rewards World Elite Mastercard",
        "issuer": "MBNA",
        "reward_program": "MBNA Rewards",
        "reward_currency": "points",
        "point_valuation": 1.0,
        "annual_fee": 120,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "groceries", "multiplier": 5.0, "reward_unit": "multiplier", "description": "5x MBNA points on groceries"},
            {"category": "dining", "multiplier": 5.0, "reward_unit": "multiplier", "description": "5x MBNA points on dining"},
        ],
        "signup_bonus": {"bonus_amount": 50000, "bonus_currency": "points", "spend_requirement": 5000, "timeframe_days": 90}
    },
    
    # ============== NATIONAL BANK CARDS ==============
    {
        "card_key": "national-bank-world-elite",
        "name": "National Bank World Elite Mastercard",
        "issuer": "National Bank",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 150,
        "base_reward_rate": 1.0,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 5.0, "reward_unit": "percent", "description": "5% cash back on groceries"},
            {"category": "dining", "multiplier": 5.0, "reward_unit": "percent", "description": "5% cash back on dining"},
            {"category": "gas", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on gas"},
        ],
        "signup_bonus": {"bonus_amount": 400, "bonus_currency": "cashback", "spend_requirement": 3000, "timeframe_days": 90}
    },
    
    # ============== DESJARDINS CARDS ==============
    {
        "card_key": "desjardins-odyssey-world-elite",
        "name": "Desjardins Odyssey World Elite Mastercard",
        "issuer": "Desjardins",
        "reward_program": "Odyssey",
        "reward_currency": "points",
        "point_valuation": 1.0,
        "annual_fee": 150,
        "base_reward_rate": 1.0,
        "base_reward_unit": "multiplier",
        "category_rewards": [
            {"category": "travel", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x Odyssey points on travel"},
            {"category": "dining", "multiplier": 2.0, "reward_unit": "multiplier", "description": "2x Odyssey points on dining"},
        ],
        "signup_bonus": {"bonus_amount": 30000, "bonus_currency": "points", "spend_requirement": 2000, "timeframe_days": 90}
    },
    {
        "card_key": "desjardins-cash-back-world-elite",
        "name": "Desjardins Cash Back World Elite Mastercard",
        "issuer": "Desjardins",
        "reward_program": "Cash Back",
        "reward_currency": "cashback",
        "point_valuation": 1.0,
        "annual_fee": 110,
        "base_reward_rate": 1.0,
        "base_reward_unit": "percent",
        "category_rewards": [
            {"category": "groceries", "multiplier": 4.0, "reward_unit": "percent", "description": "4% cash back on groceries"},
            {"category": "gas", "multiplier": 4.0, "reward_unit": "percent", "description": "4% cash back on gas"},
            {"category": "dining", "multiplier": 2.0, "reward_unit": "percent", "description": "2% cash back on dining"},
        ],
        "signup_bonus": {"bonus_amount": 200, "bonus_currency": "cashback", "spend_requirement": 1500, "timeframe_days": 90}
    },
]


def upload_known_cards():
    """Upload known cards with category rewards to Supabase."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    
    client = create_client(url, key)
    
    results = {'inserted': 0, 'updated': 0, 'category_rewards': 0, 'signup_bonuses': 0, 'errors': []}
    
    for card in KNOWN_CARDS:
        try:
            # Prepare card data (without nested objects)
            card_data = {
                'card_key': card['card_key'],
                'name': card['name'],
                'issuer': card['issuer'],
                'reward_program': card['reward_program'],
                'reward_currency': card['reward_currency'],
                'point_valuation': card['point_valuation'],
                'annual_fee': card['annual_fee'],
                'base_reward_rate': card['base_reward_rate'],
                'base_reward_unit': card['base_reward_unit'],
                'is_active': True,
            }
            
            # Check if card exists
            existing = client.table('cards').select('id').eq('card_key', card['card_key']).execute()
            
            if existing.data:
                card_id = existing.data[0]['id']
                client.table('cards').update(card_data).eq('id', card_id).execute()
                results['updated'] += 1
            else:
                result = client.table('cards').insert(card_data).execute()
                card_id = result.data[0]['id'] if result.data else None
                results['inserted'] += 1
            
            if not card_id:
                continue
            
            # Delete existing category rewards for this card
            client.table('category_rewards').delete().eq('card_id', card_id).execute()
            
            # Insert category rewards
            for cr in card.get('category_rewards', []):
                cr_data = {
                    'card_id': card_id,
                    'category': cr['category'],
                    'multiplier': cr['multiplier'],
                    'reward_unit': cr['reward_unit'],
                    'description': cr['description'],
                }
                client.table('category_rewards').insert(cr_data).execute()
                results['category_rewards'] += 1
            
            # Delete existing signup bonuses for this card
            client.table('signup_bonuses').delete().eq('card_id', card_id).execute()
            
            # Insert signup bonus if exists
            if card.get('signup_bonus'):
                sb = card['signup_bonus']
                sb_data = {
                    'card_id': card_id,
                    'bonus_amount': sb['bonus_amount'],
                    'bonus_currency': sb['bonus_currency'],
                    'spend_requirement': sb['spend_requirement'],
                    'timeframe_days': sb['timeframe_days'],
                    'is_active': True,
                }
                client.table('signup_bonuses').insert(sb_data).execute()
                results['signup_bonuses'] += 1
                
        except Exception as e:
            results['errors'].append({'card': card['card_key'], 'error': str(e)})
    
    return results


def main():
    print("=" * 60)
    print("Seeding Known Cards with Category Rewards")
    print("=" * 60)
    
    result = upload_known_cards()
    
    print(f"\nResults:")
    print(f"  Cards inserted: {result['inserted']}")
    print(f"  Cards updated: {result['updated']}")
    print(f"  Category rewards: {result['category_rewards']}")
    print(f"  Signup bonuses: {result['signup_bonuses']}")
    
    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for err in result['errors']:
            print(f"  - {err['card']}: {err['error']}")
    
    print("\nDone!")


if __name__ == '__main__':
    main()

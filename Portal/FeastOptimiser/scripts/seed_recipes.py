"""Seed all 108 recipes from cuisine_skill_trees.json into the CSV data store."""

import json
import os
import re
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.csv_store import CSVStore
from models.recipe import upsert_recipe


def slugify(name):
    """Convert recipe name to snake_case ID."""
    s = name.lower()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', '_', s.strip())
    return s


# ── Macros per serving (calories, protein_g, carbs_g, fat_g) ──────────────
# Approximate realistic values for each recipe.
RECIPE_MACROS = {
    # CHINESE - Beginner
    "Egg Fried Rice": {"calories": 400, "protein": 12, "carbs": 55, "fat": 14},
    "Stir-Fried Vegetables": {"calories": 150, "protein": 4, "carbs": 18, "fat": 7},
    "Steamed Rice": {"calories": 240, "protein": 5, "carbs": 53, "fat": 0.5},
    "Tomato Egg Stir-Fry": {"calories": 220, "protein": 12, "carbs": 10, "fat": 15},
    "Hot and Sour Soup": {"calories": 180, "protein": 10, "carbs": 15, "fat": 8},
    "Spring Rolls": {"calories": 320, "protein": 8, "carbs": 35, "fat": 16},
    # CHINESE - Intermediate
    "Kung Pao Chicken": {"calories": 380, "protein": 30, "carbs": 20, "fat": 20},
    "Mapo Tofu": {"calories": 280, "protein": 18, "carbs": 12, "fat": 18},
    "Sweet and Sour Pork": {"calories": 420, "protein": 22, "carbs": 40, "fat": 18},
    "Char Siu (BBQ Pork)": {"calories": 350, "protein": 28, "carbs": 22, "fat": 16},
    "Dan Dan Noodles": {"calories": 450, "protein": 18, "carbs": 50, "fat": 20},
    "Steamed Dumplings (Jiaozi)": {"calories": 300, "protein": 15, "carbs": 35, "fat": 12},
    # CHINESE - Advanced
    "Peking Duck": {"calories": 500, "protein": 25, "carbs": 30, "fat": 30},
    "Xiao Long Bao (Soup Dumplings)": {"calories": 280, "protein": 14, "carbs": 30, "fat": 12},
    "Hand-Pulled Noodles (La Mian)": {"calories": 380, "protein": 12, "carbs": 65, "fat": 6},
    "Crispy Skin Pork Belly": {"calories": 550, "protein": 30, "carbs": 5, "fat": 45},
    "General Tso's Chicken": {"calories": 430, "protein": 28, "carbs": 35, "fat": 20},
    "Cantonese Steamed Fish": {"calories": 200, "protein": 30, "carbs": 5, "fat": 8},

    # JAPANESE - Beginner
    "Japanese White Rice (Gohan)": {"calories": 240, "protein": 5, "carbs": 53, "fat": 0.5},
    "Miso Soup": {"calories": 60, "protein": 5, "carbs": 5, "fat": 2},
    "Tamagoyaki (Rolled Omelette)": {"calories": 150, "protein": 10, "carbs": 3, "fat": 11},
    "Onigiri (Rice Balls)": {"calories": 200, "protein": 5, "carbs": 42, "fat": 1},
    "Edamame with Salt": {"calories": 120, "protein": 11, "carbs": 9, "fat": 5},
    "Teriyaki Chicken": {"calories": 350, "protein": 32, "carbs": 18, "fat": 16},
    # JAPANESE - Intermediate
    "Tonkatsu (Pork Cutlet)": {"calories": 450, "protein": 28, "carbs": 25, "fat": 26},
    "Vegetable Tempura": {"calories": 300, "protein": 6, "carbs": 30, "fat": 18},
    "Shoyu Ramen": {"calories": 500, "protein": 25, "carbs": 55, "fat": 20},
    "Gyoza (Pan-Fried Dumplings)": {"calories": 280, "protein": 14, "carbs": 28, "fat": 13},
    "Katsu Curry": {"calories": 550, "protein": 30, "carbs": 55, "fat": 22},
    "Yakitori": {"calories": 250, "protein": 28, "carbs": 8, "fat": 12},
    # JAPANESE - Advanced
    "Nigiri Sushi": {"calories": 200, "protein": 15, "carbs": 28, "fat": 4},
    "Tonkotsu Ramen": {"calories": 600, "protein": 30, "carbs": 55, "fat": 28},
    "Sashimi Platter": {"calories": 180, "protein": 30, "carbs": 0, "fat": 6},
    "Okonomiyaki": {"calories": 400, "protein": 18, "carbs": 42, "fat": 16},
    "Chawanmushi (Steamed Egg Custard)": {"calories": 100, "protein": 8, "carbs": 3, "fat": 6},
    "Kakiage (Mixed Vegetable Tempura)": {"calories": 320, "protein": 7, "carbs": 32, "fat": 18},

    # ITALIAN - Beginner
    "Aglio e Olio": {"calories": 420, "protein": 12, "carbs": 55, "fat": 18},
    "Pomodoro Sauce with Spaghetti": {"calories": 380, "protein": 12, "carbs": 60, "fat": 10},
    "Bruschetta": {"calories": 180, "protein": 5, "carbs": 22, "fat": 8},
    "Caprese Salad": {"calories": 200, "protein": 12, "carbs": 5, "fat": 15},
    "Penne Arrabbiata": {"calories": 400, "protein": 12, "carbs": 58, "fat": 12},
    "Minestrone Soup": {"calories": 200, "protein": 8, "carbs": 30, "fat": 5},
    # ITALIAN - Intermediate
    "Carbonara": {"calories": 500, "protein": 22, "carbs": 50, "fat": 24},
    "Risotto alla Milanese": {"calories": 380, "protein": 10, "carbs": 55, "fat": 12},
    "Fresh Egg Pasta": {"calories": 300, "protein": 10, "carbs": 50, "fat": 6},
    "Bolognese (Ragu alla Bolognese)": {"calories": 450, "protein": 28, "carbs": 40, "fat": 18},
    "Chicken Parmigiana": {"calories": 520, "protein": 35, "carbs": 30, "fat": 28},
    "Gnocchi with Sage Butter": {"calories": 380, "protein": 8, "carbs": 50, "fat": 16},
    # ITALIAN - Advanced
    "Ravioli with Ricotta and Spinach": {"calories": 400, "protein": 18, "carbs": 42, "fat": 18},
    "Osso Buco": {"calories": 450, "protein": 38, "carbs": 15, "fat": 25},
    "Cacio e Pepe": {"calories": 480, "protein": 18, "carbs": 52, "fat": 22},
    "Lasagna": {"calories": 500, "protein": 25, "carbs": 40, "fat": 28},
    "Tiramisu": {"calories": 350, "protein": 8, "carbs": 35, "fat": 20},
    "Saltimbocca alla Romana": {"calories": 380, "protein": 35, "carbs": 5, "fat": 24},

    # THAI - Beginner
    "Pad Thai": {"calories": 400, "protein": 18, "carbs": 50, "fat": 14},
    "Thai Fried Rice (Khao Pad)": {"calories": 380, "protein": 14, "carbs": 52, "fat": 12},
    "Tom Yum Soup": {"calories": 120, "protein": 12, "carbs": 8, "fat": 4},
    "Thai Omelette (Khai Jiao)": {"calories": 250, "protein": 14, "carbs": 2, "fat": 20},
    "Green Papaya Salad (Som Tum)": {"calories": 120, "protein": 4, "carbs": 18, "fat": 4},
    "Stir-Fried Basil Chicken (Pad Krapao)": {"calories": 350, "protein": 28, "carbs": 15, "fat": 20},
    # THAI - Intermediate
    "Green Curry (Gaeng Keow Wan)": {"calories": 380, "protein": 22, "carbs": 18, "fat": 24},
    "Massaman Curry": {"calories": 450, "protein": 25, "carbs": 30, "fat": 26},
    "Tom Kha Gai": {"calories": 280, "protein": 20, "carbs": 10, "fat": 18},
    "Larb (Thai Minced Meat Salad)": {"calories": 250, "protein": 22, "carbs": 8, "fat": 15},
    "Satay Chicken with Peanut Sauce": {"calories": 380, "protein": 30, "carbs": 15, "fat": 22},
    "Pad See Ew": {"calories": 420, "protein": 20, "carbs": 50, "fat": 16},
    # THAI - Advanced
    "Red Curry Duck": {"calories": 450, "protein": 25, "carbs": 15, "fat": 32},
    "Crying Tiger (Suea Rong Hai)": {"calories": 350, "protein": 35, "carbs": 8, "fat": 20},
    "Khao Soi (Northern Thai Curry Noodles)": {"calories": 500, "protein": 25, "carbs": 45, "fat": 26},
    "Whole Fried Fish with Three-Flavor Sauce": {"calories": 380, "protein": 32, "carbs": 18, "fat": 20},
    "Mango Sticky Rice (Khao Niao Mamuang)": {"calories": 350, "protein": 5, "carbs": 65, "fat": 10},
    "Panang Curry": {"calories": 400, "protein": 24, "carbs": 15, "fat": 28},

    # INDIAN - Beginner
    "Jeera Rice (Cumin Rice)": {"calories": 260, "protein": 5, "carbs": 52, "fat": 4},
    "Dal Tadka (Tempered Lentils)": {"calories": 220, "protein": 14, "carbs": 32, "fat": 5},
    "Aloo Gobi (Potato and Cauliflower)": {"calories": 200, "protein": 5, "carbs": 28, "fat": 8},
    "Raita": {"calories": 80, "protein": 4, "carbs": 6, "fat": 4},
    "Chapati": {"calories": 120, "protein": 4, "carbs": 22, "fat": 2},
    "Egg Curry": {"calories": 280, "protein": 16, "carbs": 15, "fat": 18},
    # INDIAN - Intermediate
    "Butter Chicken (Murgh Makhani)": {"calories": 400, "protein": 30, "carbs": 15, "fat": 24},
    "Chana Masala": {"calories": 280, "protein": 12, "carbs": 38, "fat": 8},
    "Palak Paneer": {"calories": 300, "protein": 16, "carbs": 12, "fat": 22},
    "Naan Bread": {"calories": 260, "protein": 8, "carbs": 42, "fat": 6},
    "Tandoori Chicken": {"calories": 250, "protein": 32, "carbs": 6, "fat": 10},
    "Lamb Rogan Josh": {"calories": 420, "protein": 32, "carbs": 12, "fat": 28},
    # INDIAN - Advanced
    "Hyderabadi Biryani": {"calories": 480, "protein": 25, "carbs": 55, "fat": 18},
    "Dosa with Sambar": {"calories": 250, "protein": 10, "carbs": 40, "fat": 6},
    "Chole Bhature": {"calories": 500, "protein": 15, "carbs": 55, "fat": 24},
    "Fish Moilee (Kerala Fish Curry)": {"calories": 320, "protein": 28, "carbs": 10, "fat": 20},
    "Garam Masala from Scratch": {"calories": 15, "protein": 1, "carbs": 2, "fat": 1},
    "Lamb Nihari": {"calories": 480, "protein": 35, "carbs": 15, "fat": 32},

    # FRENCH - Beginner
    "French Omelette": {"calories": 250, "protein": 16, "carbs": 2, "fat": 20},
    "Vinaigrette": {"calories": 120, "protein": 0, "carbs": 2, "fat": 13},
    "Croque Monsieur": {"calories": 450, "protein": 22, "carbs": 30, "fat": 26},
    "French Onion Soup": {"calories": 300, "protein": 12, "carbs": 28, "fat": 14},
    "Salade Nicoise": {"calories": 350, "protein": 22, "carbs": 20, "fat": 20},
    "Pan-Fried Sole Meuniere": {"calories": 300, "protein": 28, "carbs": 8, "fat": 18},
    # FRENCH - Intermediate
    "Coq au Vin": {"calories": 420, "protein": 32, "carbs": 12, "fat": 26},
    "Bechamel Sauce": {"calories": 150, "protein": 5, "carbs": 10, "fat": 10},
    "Quiche Lorraine": {"calories": 380, "protein": 14, "carbs": 22, "fat": 26},
    "Ratatouille": {"calories": 180, "protein": 4, "carbs": 20, "fat": 10},
    "Steak Frites with Bearnaise": {"calories": 650, "protein": 40, "carbs": 35, "fat": 38},
    "Chicken Fricassee": {"calories": 380, "protein": 30, "carbs": 12, "fat": 24},
    # FRENCH - Advanced
    "Beef Bourguignon": {"calories": 480, "protein": 35, "carbs": 18, "fat": 28},
    "Souffle (Cheese)": {"calories": 280, "protein": 14, "carbs": 12, "fat": 20},
    "Duck Confit": {"calories": 500, "protein": 30, "carbs": 2, "fat": 40},
    "Bouillabaisse": {"calories": 350, "protein": 32, "carbs": 15, "fat": 16},
    "Tarte Tatin": {"calories": 320, "protein": 3, "carbs": 42, "fat": 16},
    "Creme Brulee": {"calories": 300, "protein": 5, "carbs": 30, "fat": 18},
}


# ── Ingredients per recipe ────────────────────────────────────────────────
# Each entry: list of (canonical_product_id, quantity, unit, notes)
RECIPE_INGREDIENTS = {
    # ═══════════════════════ CHINESE ═══════════════════════
    "Egg Fried Rice": [
        ("PROD_jasmine_rice", 0.3, "kg", "cooked, day-old preferred"),
        ("PROD_eggs", 3, "pcs", "beaten"),
        ("PROD_spring_onion", 3, "pcs", "sliced"),
        ("PROD_soy_sauce", 2, "tbsp", ""),
        ("PROD_sesame_oil", 1, "tsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Stir-Fried Vegetables": [
        ("PROD_broccoli", 0.2, "kg", "florets"),
        ("PROD_red_capsicum", 1, "pcs", "sliced"),
        ("PROD_carrot", 1, "pcs", "julienned"),
        ("PROD_mushrooms", 0.15, "kg", "sliced"),
        ("PROD_garlic", 3, "cloves", "minced"),
        ("PROD_soy_sauce", 2, "tbsp", ""),
        ("PROD_oyster_sauce", 1, "tbsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Steamed Rice": [
        ("PROD_jasmine_rice", 0.4, "kg", "washed"),
    ],
    "Tomato Egg Stir-Fry": [
        ("PROD_tomato", 3, "pcs", "wedged"),
        ("PROD_eggs", 4, "pcs", "beaten"),
        ("PROD_spring_onion", 2, "pcs", "sliced"),
        ("PROD_white_sugar", 1, "tsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
        ("PROD_salt", 0.5, "tsp", ""),
    ],
    "Hot and Sour Soup": [
        ("PROD_firm_tofu", 0.2, "kg", "julienned"),
        ("PROD_mushrooms", 0.1, "kg", "sliced"),
        ("PROD_eggs", 1, "pcs", "beaten"),
        ("PROD_soy_sauce", 2, "tbsp", ""),
        ("PROD_chicken_stock", 0.75, "L", ""),
        ("PROD_carrot", 1, "pcs", "julienned"),
    ],
    "Spring Rolls": [
        ("PROD_carrot", 1, "pcs", "julienned"),
        ("PROD_mushrooms", 0.1, "kg", "diced"),
        ("PROD_spring_onion", 3, "pcs", "sliced"),
        ("PROD_plain_flour", 0.2, "kg", "for wrappers"),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
        ("PROD_soy_sauce", 1, "tbsp", ""),
    ],
    "Kung Pao Chicken": [
        ("PROD_chicken_breast", 0.5, "kg", "diced"),
        ("PROD_chilli", 6, "pcs", "dried"),
        ("PROD_spring_onion", 3, "pcs", "sliced"),
        ("PROD_garlic", 3, "cloves", "minced"),
        ("PROD_ginger", 1, "cm", "minced"),
        ("PROD_soy_sauce", 2, "tbsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Mapo Tofu": [
        ("PROD_firm_tofu", 0.4, "kg", "cubed"),
        ("PROD_pork_mince", 0.15, "kg", ""),
        ("PROD_garlic", 3, "cloves", "minced"),
        ("PROD_ginger", 1, "cm", "minced"),
        ("PROD_spring_onion", 2, "pcs", "sliced"),
        ("PROD_soy_sauce", 1, "tbsp", ""),
        ("PROD_chilli", 2, "pcs", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Sweet and Sour Pork": [
        ("PROD_pork_mince", 0.4, "kg", "or pork loin, cubed"),
        ("PROD_red_capsicum", 1, "pcs", "chunks"),
        ("PROD_brown_onion", 1, "pcs", "chunks"),
        ("PROD_tomato_paste", 2, "tbsp", ""),
        ("PROD_white_sugar", 3, "tbsp", ""),
        ("PROD_plain_flour", 0.1, "kg", "for batter"),
        ("PROD_eggs", 1, "pcs", "for batter"),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
    ],
    "Char Siu (BBQ Pork)": [
        ("PROD_pork_mince", 0.6, "kg", "or pork shoulder"),
        ("PROD_soy_sauce", 3, "tbsp", ""),
        ("PROD_brown_sugar", 3, "tbsp", ""),
        ("PROD_garlic", 3, "cloves", "minced"),
        ("PROD_ginger", 2, "cm", "grated"),
        ("PROD_sesame_oil", 1, "tbsp", ""),
    ],
    "Dan Dan Noodles": [
        ("PROD_egg_noodles", 0.4, "kg", ""),
        ("PROD_pork_mince", 0.2, "kg", ""),
        ("PROD_soy_sauce", 3, "tbsp", ""),
        ("PROD_sesame_oil", 1, "tbsp", ""),
        ("PROD_chilli", 3, "pcs", ""),
        ("PROD_spring_onion", 3, "pcs", "sliced"),
        ("PROD_garlic", 2, "cloves", "minced"),
    ],
    "Steamed Dumplings (Jiaozi)": [
        ("PROD_pork_mince", 0.3, "kg", ""),
        ("PROD_plain_flour", 0.3, "kg", "for wrappers"),
        ("PROD_spring_onion", 4, "pcs", "finely chopped"),
        ("PROD_ginger", 2, "cm", "grated"),
        ("PROD_soy_sauce", 2, "tbsp", ""),
        ("PROD_sesame_oil", 1, "tsp", ""),
    ],
    "Peking Duck": [
        ("PROD_chicken_thigh", 1, "kg", "sub for duck"),
        ("PROD_brown_sugar", 2, "tbsp", "for glaze"),
        ("PROD_soy_sauce", 3, "tbsp", ""),
        ("PROD_spring_onion", 4, "pcs", ""),
        ("PROD_plain_flour", 0.2, "kg", "for pancakes"),
        ("PROD_ginger", 2, "cm", ""),
    ],
    "Xiao Long Bao (Soup Dumplings)": [
        ("PROD_pork_mince", 0.3, "kg", ""),
        ("PROD_plain_flour", 0.3, "kg", "for wrappers"),
        ("PROD_chicken_stock", 0.3, "L", "for aspic"),
        ("PROD_ginger", 2, "cm", "grated"),
        ("PROD_spring_onion", 3, "pcs", ""),
        ("PROD_soy_sauce", 1, "tbsp", ""),
    ],
    "Hand-Pulled Noodles (La Mian)": [
        ("PROD_plain_flour", 0.5, "kg", "high gluten"),
        ("PROD_salt", 1, "tsp", ""),
        ("PROD_vegetable_oil", 1, "tbsp", ""),
    ],
    "Crispy Skin Pork Belly": [
        ("PROD_pork_mince", 1, "kg", "or pork belly"),
        ("PROD_salt", 2, "tbsp", ""),
        ("PROD_white_sugar", 1, "tbsp", ""),
        ("PROD_soy_sauce", 2, "tbsp", ""),
        ("PROD_garlic", 3, "cloves", ""),
    ],
    "General Tso's Chicken": [
        ("PROD_chicken_breast", 0.5, "kg", "cubed"),
        ("PROD_plain_flour", 0.1, "kg", "for coating"),
        ("PROD_eggs", 1, "pcs", "for batter"),
        ("PROD_soy_sauce", 3, "tbsp", ""),
        ("PROD_brown_sugar", 2, "tbsp", ""),
        ("PROD_chilli", 4, "pcs", "dried"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
    ],
    "Cantonese Steamed Fish": [
        ("PROD_salmon_fillet", 0.4, "kg", "or whole white fish"),
        ("PROD_ginger", 3, "cm", "julienned"),
        ("PROD_spring_onion", 3, "pcs", "shredded"),
        ("PROD_soy_sauce", 3, "tbsp", ""),
        ("PROD_sesame_oil", 1, "tsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", "for finishing"),
    ],

    # ═══════════════════════ JAPANESE ═══════════════════════
    "Japanese White Rice (Gohan)": [
        ("PROD_jasmine_rice", 0.4, "kg", "short grain preferred"),
    ],
    "Miso Soup": [
        ("PROD_firm_tofu", 0.15, "kg", "cubed"),
        ("PROD_spring_onion", 2, "pcs", "sliced"),
        ("PROD_chicken_stock", 0.75, "L", "sub for dashi"),
    ],
    "Tamagoyaki (Rolled Omelette)": [
        ("PROD_eggs", 4, "pcs", ""),
        ("PROD_white_sugar", 1, "tsp", ""),
        ("PROD_soy_sauce", 1, "tsp", ""),
        ("PROD_vegetable_oil", 1, "tbsp", ""),
    ],
    "Onigiri (Rice Balls)": [
        ("PROD_jasmine_rice", 0.3, "kg", "short grain, cooked"),
        ("PROD_salt", 0.5, "tsp", ""),
        ("PROD_salmon_fillet", 0.1, "kg", "cooked, flaked"),
    ],
    "Edamame with Salt": [
        ("PROD_salt", 1, "tsp", ""),
    ],
    "Teriyaki Chicken": [
        ("PROD_chicken_thigh", 0.5, "kg", ""),
        ("PROD_soy_sauce", 3, "tbsp", ""),
        ("PROD_brown_sugar", 2, "tbsp", ""),
        ("PROD_ginger", 1, "cm", "grated"),
        ("PROD_garlic", 2, "cloves", ""),
        ("PROD_vegetable_oil", 1, "tbsp", ""),
    ],
    "Tonkatsu (Pork Cutlet)": [
        ("PROD_pork_mince", 0.4, "kg", "or pork loin"),
        ("PROD_plain_flour", 0.05, "kg", ""),
        ("PROD_eggs", 2, "pcs", "beaten"),
        ("PROD_bread", 0.1, "kg", "for panko crumbs"),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
    ],
    "Vegetable Tempura": [
        ("PROD_broccoli", 0.15, "kg", "florets"),
        ("PROD_sweet_potato", 1, "pcs", "sliced"),
        ("PROD_red_capsicum", 1, "pcs", "sliced"),
        ("PROD_plain_flour", 0.15, "kg", "for batter"),
        ("PROD_eggs", 1, "pcs", ""),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
    ],
    "Shoyu Ramen": [
        ("PROD_egg_noodles", 0.4, "kg", "ramen noodles"),
        ("PROD_chicken_stock", 1, "L", ""),
        ("PROD_soy_sauce", 3, "tbsp", ""),
        ("PROD_eggs", 2, "pcs", "soft-boiled"),
        ("PROD_spring_onion", 3, "pcs", "sliced"),
        ("PROD_pork_mince", 0.2, "kg", "for chashu"),
        ("PROD_garlic", 2, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
    ],
    "Gyoza (Pan-Fried Dumplings)": [
        ("PROD_pork_mince", 0.25, "kg", ""),
        ("PROD_plain_flour", 0.2, "kg", "for wrappers"),
        ("PROD_spring_onion", 3, "pcs", "chopped"),
        ("PROD_garlic", 2, "cloves", "minced"),
        ("PROD_ginger", 1, "cm", "grated"),
        ("PROD_soy_sauce", 2, "tbsp", ""),
        ("PROD_sesame_oil", 1, "tsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Katsu Curry": [
        ("PROD_chicken_breast", 0.4, "kg", ""),
        ("PROD_plain_flour", 0.05, "kg", ""),
        ("PROD_eggs", 2, "pcs", ""),
        ("PROD_bread", 0.1, "kg", "for panko"),
        ("PROD_brown_onion", 1, "pcs", "diced"),
        ("PROD_carrot", 1, "pcs", "diced"),
        ("PROD_potato", 1, "pcs", "diced"),
        ("PROD_curry_powder", 2, "tbsp", ""),
        ("PROD_chicken_stock", 0.5, "L", ""),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
    ],
    "Yakitori": [
        ("PROD_chicken_thigh", 0.5, "kg", "cubed"),
        ("PROD_spring_onion", 4, "pcs", "cut into segments"),
        ("PROD_soy_sauce", 3, "tbsp", ""),
        ("PROD_brown_sugar", 2, "tbsp", ""),
        ("PROD_garlic", 2, "cloves", ""),
    ],
    "Nigiri Sushi": [
        ("PROD_jasmine_rice", 0.3, "kg", "sushi rice"),
        ("PROD_salmon_fillet", 0.3, "kg", "sashimi grade"),
        ("PROD_soy_sauce", 2, "tbsp", "for serving"),
    ],
    "Tonkotsu Ramen": [
        ("PROD_egg_noodles", 0.4, "kg", "ramen noodles"),
        ("PROD_pork_mince", 0.3, "kg", "for broth and chashu"),
        ("PROD_chicken_stock", 1, "L", "sub for pork bone broth"),
        ("PROD_eggs", 2, "pcs", "soft-boiled"),
        ("PROD_spring_onion", 3, "pcs", ""),
        ("PROD_garlic", 4, "cloves", ""),
        ("PROD_ginger", 3, "cm", ""),
        ("PROD_soy_sauce", 2, "tbsp", ""),
        ("PROD_sesame_oil", 1, "tbsp", ""),
    ],
    "Sashimi Platter": [
        ("PROD_salmon_fillet", 0.4, "kg", "sashimi grade"),
        ("PROD_soy_sauce", 2, "tbsp", "for serving"),
        ("PROD_ginger", 2, "cm", "pickled"),
    ],
    "Okonomiyaki": [
        ("PROD_plain_flour", 0.15, "kg", ""),
        ("PROD_eggs", 3, "pcs", ""),
        ("PROD_carrot", 1, "pcs", "shredded"),
        ("PROD_spring_onion", 3, "pcs", "sliced"),
        ("PROD_pork_mince", 0.15, "kg", "or bacon"),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Chawanmushi (Steamed Egg Custard)": [
        ("PROD_eggs", 3, "pcs", ""),
        ("PROD_chicken_stock", 0.4, "L", "sub for dashi"),
        ("PROD_chicken_breast", 0.1, "kg", "small pieces"),
        ("PROD_prawns", 0.1, "kg", ""),
        ("PROD_soy_sauce", 1, "tsp", ""),
    ],
    "Kakiage (Mixed Vegetable Tempura)": [
        ("PROD_sweet_potato", 1, "pcs", "julienned"),
        ("PROD_carrot", 1, "pcs", "julienned"),
        ("PROD_spring_onion", 3, "pcs", "sliced"),
        ("PROD_plain_flour", 0.15, "kg", "for batter"),
        ("PROD_eggs", 1, "pcs", ""),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
    ],

    # ═══════════════════════ ITALIAN ═══════════════════════
    "Aglio e Olio": [
        ("PROD_spaghetti", 0.4, "kg", ""),
        ("PROD_garlic", 6, "cloves", "sliced"),
        ("PROD_chilli", 2, "pcs", "dried flakes"),
        ("PROD_olive_oil", 4, "tbsp", "extra virgin"),
    ],
    "Pomodoro Sauce with Spaghetti": [
        ("PROD_spaghetti", 0.4, "kg", ""),
        ("PROD_canned_tomatoes", 0.4, "kg", ""),
        ("PROD_garlic", 3, "cloves", "minced"),
        ("PROD_olive_oil", 2, "tbsp", ""),
        ("PROD_salt", 1, "tsp", ""),
    ],
    "Bruschetta": [
        ("PROD_bread", 0.2, "kg", "ciabatta or sourdough"),
        ("PROD_tomato", 4, "pcs", "diced"),
        ("PROD_garlic", 2, "cloves", ""),
        ("PROD_olive_oil", 2, "tbsp", ""),
        ("PROD_salt", 0.5, "tsp", ""),
    ],
    "Caprese Salad": [
        ("PROD_tomato", 3, "pcs", "sliced"),
        ("PROD_cheddar_cheese", 0.2, "kg", "sub for mozzarella"),
        ("PROD_olive_oil", 2, "tbsp", ""),
        ("PROD_salt", 0.5, "tsp", ""),
    ],
    "Penne Arrabbiata": [
        ("PROD_penne", 0.4, "kg", ""),
        ("PROD_canned_tomatoes", 0.4, "kg", ""),
        ("PROD_garlic", 4, "cloves", "sliced"),
        ("PROD_chilli", 3, "pcs", "dried"),
        ("PROD_olive_oil", 3, "tbsp", ""),
    ],
    "Minestrone Soup": [
        ("PROD_carrot", 2, "pcs", "diced"),
        ("PROD_potato", 1, "pcs", "diced"),
        ("PROD_zucchini", 1, "pcs", "diced"),
        ("PROD_canned_tomatoes", 0.4, "kg", ""),
        ("PROD_brown_onion", 1, "pcs", "diced"),
        ("PROD_garlic", 2, "cloves", ""),
        ("PROD_chicken_stock", 1, "L", ""),
        ("PROD_olive_oil", 2, "tbsp", ""),
        ("PROD_penne", 0.1, "kg", "small pasta"),
    ],
    "Carbonara": [
        ("PROD_spaghetti", 0.4, "kg", ""),
        ("PROD_eggs", 4, "pcs", "yolks + whole"),
        ("PROD_cheddar_cheese", 0.1, "kg", "sub for pecorino/parmesan"),
        ("PROD_pepper", 1, "tsp", "freshly cracked"),
    ],
    "Risotto alla Milanese": [
        ("PROD_white_rice", 0.3, "kg", "arborio"),
        ("PROD_brown_onion", 1, "pcs", "finely diced"),
        ("PROD_butter", 0.05, "kg", ""),
        ("PROD_chicken_stock", 1, "L", "warm"),
        ("PROD_cheddar_cheese", 0.05, "kg", "sub for parmesan"),
        ("PROD_turmeric", 0.5, "tsp", "sub for saffron"),
    ],
    "Fresh Egg Pasta": [
        ("PROD_plain_flour", 0.4, "kg", "tipo 00 preferred"),
        ("PROD_eggs", 4, "pcs", ""),
        ("PROD_olive_oil", 1, "tbsp", ""),
        ("PROD_salt", 0.5, "tsp", ""),
    ],
    "Bolognese (Ragu alla Bolognese)": [
        ("PROD_beef_mince", 0.5, "kg", ""),
        ("PROD_canned_tomatoes", 0.4, "kg", ""),
        ("PROD_brown_onion", 1, "pcs", "diced"),
        ("PROD_carrot", 1, "pcs", "diced"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_tomato_paste", 2, "tbsp", ""),
        ("PROD_olive_oil", 2, "tbsp", ""),
        ("PROD_spaghetti", 0.4, "kg", ""),
    ],
    "Chicken Parmigiana": [
        ("PROD_chicken_breast", 0.5, "kg", "butterflied"),
        ("PROD_canned_tomatoes", 0.3, "kg", "for sauce"),
        ("PROD_cheddar_cheese", 0.15, "kg", "sub for mozzarella"),
        ("PROD_plain_flour", 0.05, "kg", ""),
        ("PROD_eggs", 2, "pcs", ""),
        ("PROD_bread", 0.1, "kg", "for breadcrumbs"),
        ("PROD_olive_oil", 3, "tbsp", ""),
    ],
    "Gnocchi with Sage Butter": [
        ("PROD_potato", 1, "kg", ""),
        ("PROD_plain_flour", 0.2, "kg", ""),
        ("PROD_eggs", 1, "pcs", ""),
        ("PROD_butter", 0.08, "kg", ""),
        ("PROD_salt", 1, "tsp", ""),
    ],
    "Ravioli with Ricotta and Spinach": [
        ("PROD_plain_flour", 0.4, "kg", "for pasta"),
        ("PROD_eggs", 4, "pcs", ""),
        ("PROD_spinach", 0.3, "kg", ""),
        ("PROD_cheddar_cheese", 0.2, "kg", "sub for ricotta"),
        ("PROD_cream", 0.05, "L", ""),
        ("PROD_butter", 0.05, "kg", ""),
    ],
    "Osso Buco": [
        ("PROD_beef_mince", 0.6, "kg", "sub for veal shanks"),
        ("PROD_brown_onion", 1, "pcs", "diced"),
        ("PROD_carrot", 2, "pcs", "diced"),
        ("PROD_canned_tomatoes", 0.4, "kg", ""),
        ("PROD_chicken_stock", 0.5, "L", ""),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_olive_oil", 3, "tbsp", ""),
        ("PROD_lemon", 1, "pcs", "for gremolata"),
    ],
    "Cacio e Pepe": [
        ("PROD_spaghetti", 0.4, "kg", ""),
        ("PROD_cheddar_cheese", 0.15, "kg", "sub for pecorino"),
        ("PROD_pepper", 2, "tsp", "freshly cracked"),
    ],
    "Lasagna": [
        ("PROD_dried_pasta", 0.3, "kg", "lasagna sheets"),
        ("PROD_beef_mince", 0.5, "kg", ""),
        ("PROD_canned_tomatoes", 0.4, "kg", ""),
        ("PROD_cheddar_cheese", 0.2, "kg", ""),
        ("PROD_butter", 0.05, "kg", "for bechamel"),
        ("PROD_plain_flour", 0.03, "kg", "for bechamel"),
        ("PROD_milk", 0.5, "L", "for bechamel"),
        ("PROD_brown_onion", 1, "pcs", ""),
        ("PROD_garlic", 3, "cloves", ""),
    ],
    "Tiramisu": [
        ("PROD_eggs", 4, "pcs", "separated"),
        ("PROD_cream", 0.25, "L", "sub for mascarpone"),
        ("PROD_white_sugar", 0.1, "kg", ""),
        ("PROD_plain_flour", 0.1, "kg", "for ladyfingers sub"),
    ],
    "Saltimbocca alla Romana": [
        ("PROD_chicken_breast", 0.5, "kg", "sub for veal"),
        ("PROD_butter", 0.04, "kg", ""),
        ("PROD_plain_flour", 0.03, "kg", "for dredging"),
        ("PROD_chicken_stock", 0.1, "L", "for deglazing"),
        ("PROD_olive_oil", 1, "tbsp", ""),
    ],

    # ═══════════════════════ THAI ═══════════════════════
    "Pad Thai": [
        ("PROD_rice_noodles", 0.3, "kg", "flat"),
        ("PROD_prawns", 0.2, "kg", "or chicken"),
        ("PROD_eggs", 2, "pcs", ""),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_brown_sugar", 2, "tbsp", "sub for palm sugar"),
        ("PROD_lime", 1, "pcs", ""),
        ("PROD_spring_onion", 3, "pcs", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Thai Fried Rice (Khao Pad)": [
        ("PROD_jasmine_rice", 0.3, "kg", "cooked, day-old"),
        ("PROD_eggs", 2, "pcs", ""),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_brown_onion", 0.5, "pcs", "diced"),
        ("PROD_spring_onion", 2, "pcs", ""),
        ("PROD_lime", 1, "pcs", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Tom Yum Soup": [
        ("PROD_prawns", 0.2, "kg", ""),
        ("PROD_mushrooms", 0.15, "kg", ""),
        ("PROD_chicken_stock", 0.75, "L", ""),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_lime", 2, "pcs", "juiced"),
        ("PROD_chilli", 3, "pcs", ""),
        ("PROD_ginger", 2, "cm", "sub for galangal"),
    ],
    "Thai Omelette (Khai Jiao)": [
        ("PROD_eggs", 3, "pcs", ""),
        ("PROD_fish_sauce", 1, "tbsp", ""),
        ("PROD_vegetable_oil", 3, "tbsp", "for frying"),
        ("PROD_spring_onion", 1, "pcs", ""),
    ],
    "Green Papaya Salad (Som Tum)": [
        ("PROD_carrot", 1, "pcs", "shredded, sub for green papaya"),
        ("PROD_tomato", 2, "pcs", "quartered"),
        ("PROD_lime", 2, "pcs", "juiced"),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_chilli", 2, "pcs", ""),
        ("PROD_brown_sugar", 1, "tbsp", ""),
    ],
    "Stir-Fried Basil Chicken (Pad Krapao)": [
        ("PROD_chicken_breast", 0.4, "kg", "minced or diced"),
        ("PROD_garlic", 4, "cloves", "minced"),
        ("PROD_chilli", 3, "pcs", "sliced"),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_soy_sauce", 1, "tbsp", ""),
        ("PROD_brown_sugar", 1, "tsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Green Curry (Gaeng Keow Wan)": [
        ("PROD_chicken_thigh", 0.4, "kg", "sliced"),
        ("PROD_coconut_milk", 0.4, "L", ""),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_brown_sugar", 1, "tbsp", ""),
        ("PROD_red_capsicum", 1, "pcs", "sliced"),
        ("PROD_broccoli", 0.15, "kg", "sub for thai eggplant"),
        ("PROD_chilli", 3, "pcs", "green"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_ginger", 2, "cm", "sub for galangal"),
    ],
    "Massaman Curry": [
        ("PROD_chicken_thigh", 0.5, "kg", "cubed"),
        ("PROD_coconut_milk", 0.4, "L", ""),
        ("PROD_potato", 2, "pcs", "cubed"),
        ("PROD_brown_onion", 1, "pcs", "quartered"),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_brown_sugar", 2, "tbsp", ""),
        ("PROD_curry_powder", 2, "tbsp", "sub for massaman paste"),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_coriander_ground", 1, "tsp", ""),
    ],
    "Tom Kha Gai": [
        ("PROD_chicken_breast", 0.3, "kg", "sliced"),
        ("PROD_coconut_milk", 0.4, "L", ""),
        ("PROD_mushrooms", 0.15, "kg", "sliced"),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_lime", 2, "pcs", "juiced"),
        ("PROD_ginger", 3, "cm", "sub for galangal"),
        ("PROD_chilli", 2, "pcs", ""),
        ("PROD_chicken_stock", 0.3, "L", ""),
    ],
    "Larb (Thai Minced Meat Salad)": [
        ("PROD_pork_mince", 0.4, "kg", "or chicken mince"),
        ("PROD_lime", 2, "pcs", "juiced"),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_chilli", 2, "pcs", ""),
        ("PROD_spring_onion", 3, "pcs", "sliced"),
        ("PROD_jasmine_rice", 0.03, "kg", "toasted, ground"),
    ],
    "Satay Chicken with Peanut Sauce": [
        ("PROD_chicken_breast", 0.5, "kg", "skewered"),
        ("PROD_coconut_milk", 0.2, "L", ""),
        ("PROD_curry_powder", 1, "tbsp", ""),
        ("PROD_turmeric", 1, "tsp", ""),
        ("PROD_fish_sauce", 1, "tbsp", ""),
        ("PROD_brown_sugar", 2, "tbsp", ""),
        ("PROD_garlic", 2, "cloves", ""),
        ("PROD_vegetable_oil", 1, "tbsp", ""),
    ],
    "Pad See Ew": [
        ("PROD_rice_noodles", 0.3, "kg", "wide flat"),
        ("PROD_chicken_breast", 0.3, "kg", "sliced"),
        ("PROD_broccoli", 0.2, "kg", "sub for chinese broccoli"),
        ("PROD_eggs", 2, "pcs", ""),
        ("PROD_soy_sauce", 3, "tbsp", ""),
        ("PROD_oyster_sauce", 1, "tbsp", ""),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Red Curry Duck": [
        ("PROD_chicken_thigh", 0.5, "kg", "sub for duck"),
        ("PROD_coconut_milk", 0.4, "L", ""),
        ("PROD_red_capsicum", 1, "pcs", "sliced"),
        ("PROD_chilli", 4, "pcs", "red, for paste"),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_brown_sugar", 1, "tbsp", ""),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
    ],
    "Crying Tiger (Suea Rong Hai)": [
        ("PROD_beef_mince", 0.5, "kg", "sub for steak"),
        ("PROD_lime", 2, "pcs", ""),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_chilli", 3, "pcs", ""),
        ("PROD_jasmine_rice", 0.03, "kg", "toasted, ground"),
        ("PROD_spring_onion", 2, "pcs", ""),
    ],
    "Khao Soi (Northern Thai Curry Noodles)": [
        ("PROD_egg_noodles", 0.4, "kg", ""),
        ("PROD_chicken_thigh", 0.4, "kg", ""),
        ("PROD_coconut_milk", 0.4, "L", ""),
        ("PROD_curry_powder", 2, "tbsp", ""),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_brown_sugar", 1, "tbsp", ""),
        ("PROD_lime", 1, "pcs", ""),
        ("PROD_chilli", 2, "pcs", ""),
        ("PROD_vegetable_oil", 0.3, "L", "for crispy noodles"),
    ],
    "Whole Fried Fish with Three-Flavor Sauce": [
        ("PROD_salmon_fillet", 0.5, "kg", "whole fish preferred"),
        ("PROD_garlic", 4, "cloves", ""),
        ("PROD_chilli", 4, "pcs", ""),
        ("PROD_fish_sauce", 3, "tbsp", ""),
        ("PROD_brown_sugar", 3, "tbsp", ""),
        ("PROD_lime", 1, "pcs", ""),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
    ],
    "Mango Sticky Rice (Khao Niao Mamuang)": [
        ("PROD_jasmine_rice", 0.3, "kg", "glutinous/sticky"),
        ("PROD_coconut_milk", 0.3, "L", ""),
        ("PROD_white_sugar", 0.05, "kg", ""),
        ("PROD_salt", 0.5, "tsp", ""),
    ],
    "Panang Curry": [
        ("PROD_chicken_breast", 0.4, "kg", "sliced"),
        ("PROD_coconut_cream", 0.3, "L", ""),
        ("PROD_coconut_milk", 0.2, "L", ""),
        ("PROD_fish_sauce", 2, "tbsp", ""),
        ("PROD_brown_sugar", 1, "tbsp", ""),
        ("PROD_chilli", 3, "pcs", "red, dried"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_red_capsicum", 1, "pcs", "sliced"),
    ],

    # ═══════════════════════ INDIAN ═══════════════════════
    "Jeera Rice (Cumin Rice)": [
        ("PROD_basmati_rice", 0.3, "kg", ""),
        ("PROD_cumin", 1, "tbsp", "whole seeds"),
        ("PROD_butter", 0.02, "kg", "or ghee"),
        ("PROD_salt", 1, "tsp", ""),
    ],
    "Dal Tadka (Tempered Lentils)": [
        ("PROD_brown_sugar", 0.3, "kg", "sub for red lentils"),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_cumin", 1, "tsp", "seeds"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
        ("PROD_brown_onion", 1, "pcs", "diced"),
        ("PROD_tomato", 1, "pcs", "diced"),
        ("PROD_vegetable_oil", 2, "tbsp", "or ghee"),
    ],
    "Aloo Gobi (Potato and Cauliflower)": [
        ("PROD_potato", 3, "pcs", "cubed"),
        ("PROD_broccoli", 0.3, "kg", "sub for cauliflower"),
        ("PROD_brown_onion", 1, "pcs", "diced"),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_coriander_ground", 1, "tsp", ""),
        ("PROD_chilli", 1, "pcs", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Raita": [
        ("PROD_yoghurt", 0.3, "kg", ""),
        ("PROD_tomato", 1, "pcs", "diced"),
        ("PROD_cumin", 0.5, "tsp", "roasted ground"),
        ("PROD_salt", 0.5, "tsp", ""),
    ],
    "Chapati": [
        ("PROD_plain_flour", 0.3, "kg", "wholemeal preferred"),
        ("PROD_salt", 0.5, "tsp", ""),
        ("PROD_vegetable_oil", 1, "tbsp", ""),
    ],
    "Egg Curry": [
        ("PROD_eggs", 6, "pcs", "hard-boiled"),
        ("PROD_brown_onion", 2, "pcs", "diced"),
        ("PROD_tomato", 2, "pcs", "pureed"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_coriander_ground", 1, "tsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Butter Chicken (Murgh Makhani)": [
        ("PROD_chicken_thigh", 0.5, "kg", ""),
        ("PROD_yoghurt", 0.15, "kg", "for marinade"),
        ("PROD_canned_tomatoes", 0.4, "kg", ""),
        ("PROD_butter", 0.05, "kg", ""),
        ("PROD_cream", 0.1, "L", ""),
        ("PROD_garlic", 4, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_paprika", 1, "tsp", ""),
    ],
    "Chana Masala": [
        ("PROD_canned_tomatoes", 0.4, "kg", "sub base for chickpeas"),
        ("PROD_brown_onion", 2, "pcs", "diced"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_coriander_ground", 1, "tsp", ""),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Palak Paneer": [
        ("PROD_spinach", 0.4, "kg", ""),
        ("PROD_firm_tofu", 0.3, "kg", "sub for paneer"),
        ("PROD_brown_onion", 1, "pcs", ""),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
        ("PROD_cream", 0.05, "L", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Naan Bread": [
        ("PROD_plain_flour", 0.4, "kg", ""),
        ("PROD_yoghurt", 0.1, "kg", ""),
        ("PROD_butter", 0.03, "kg", ""),
        ("PROD_white_sugar", 1, "tsp", ""),
        ("PROD_salt", 1, "tsp", ""),
    ],
    "Tandoori Chicken": [
        ("PROD_chicken_thigh", 0.6, "kg", ""),
        ("PROD_yoghurt", 0.2, "kg", "for marinade"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_paprika", 2, "tsp", ""),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_lemon", 1, "pcs", "juiced"),
        ("PROD_vegetable_oil", 1, "tbsp", ""),
    ],
    "Lamb Rogan Josh": [
        ("PROD_lamb_mince", 0.5, "kg", "or lamb shoulder"),
        ("PROD_brown_onion", 2, "pcs", "diced"),
        ("PROD_canned_tomatoes", 0.3, "kg", ""),
        ("PROD_yoghurt", 0.15, "kg", ""),
        ("PROD_garlic", 4, "cloves", ""),
        ("PROD_ginger", 3, "cm", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_paprika", 2, "tsp", "kashmiri chilli sub"),
        ("PROD_coriander_ground", 1, "tsp", ""),
        ("PROD_vegetable_oil", 3, "tbsp", ""),
    ],
    "Hyderabadi Biryani": [
        ("PROD_basmati_rice", 0.4, "kg", ""),
        ("PROD_chicken_thigh", 0.5, "kg", ""),
        ("PROD_yoghurt", 0.15, "kg", ""),
        ("PROD_brown_onion", 3, "pcs", "sliced"),
        ("PROD_garlic", 4, "cloves", ""),
        ("PROD_ginger", 3, "cm", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_butter", 0.04, "kg", "ghee"),
        ("PROD_milk", 0.05, "L", "for saffron infusion"),
    ],
    "Dosa with Sambar": [
        ("PROD_white_rice", 0.2, "kg", "soaked"),
        ("PROD_brown_onion", 1, "pcs", ""),
        ("PROD_tomato", 2, "pcs", ""),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_curry_powder", 1, "tbsp", ""),
        ("PROD_vegetable_oil", 2, "tbsp", ""),
    ],
    "Chole Bhature": [
        ("PROD_canned_tomatoes", 0.4, "kg", "sub for chickpeas"),
        ("PROD_plain_flour", 0.3, "kg", "for bhature"),
        ("PROD_yoghurt", 0.05, "kg", "for dough"),
        ("PROD_brown_onion", 2, "pcs", ""),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_coriander_ground", 1, "tsp", ""),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
    ],
    "Fish Moilee (Kerala Fish Curry)": [
        ("PROD_salmon_fillet", 0.4, "kg", "or white fish"),
        ("PROD_coconut_milk", 0.4, "L", ""),
        ("PROD_brown_onion", 1, "pcs", "sliced"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_ginger", 2, "cm", ""),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_chilli", 2, "pcs", "green"),
        ("PROD_curry_powder", 1, "tsp", ""),
        ("PROD_coconut_oil", 2, "tbsp", ""),
    ],
    "Garam Masala from Scratch": [
        ("PROD_cumin", 2, "tbsp", "whole seeds"),
        ("PROD_coriander_ground", 2, "tbsp", "whole seeds preferred"),
        ("PROD_pepper", 1, "tbsp", "whole peppercorns"),
    ],
    "Lamb Nihari": [
        ("PROD_lamb_mince", 0.6, "kg", "or lamb shanks"),
        ("PROD_brown_onion", 3, "pcs", "sliced"),
        ("PROD_garlic", 5, "cloves", ""),
        ("PROD_ginger", 4, "cm", ""),
        ("PROD_plain_flour", 0.03, "kg", "for thickening"),
        ("PROD_cumin", 1, "tsp", ""),
        ("PROD_turmeric", 0.5, "tsp", ""),
        ("PROD_paprika", 2, "tsp", ""),
        ("PROD_coriander_ground", 1, "tsp", ""),
        ("PROD_vegetable_oil", 3, "tbsp", ""),
    ],

    # ═══════════════════════ FRENCH ═══════════════════════
    "French Omelette": [
        ("PROD_eggs", 3, "pcs", ""),
        ("PROD_butter", 0.02, "kg", ""),
        ("PROD_salt", 0.5, "tsp", ""),
        ("PROD_pepper", 0.25, "tsp", ""),
    ],
    "Vinaigrette": [
        ("PROD_olive_oil", 4, "tbsp", ""),
        ("PROD_lemon", 1, "pcs", "or vinegar"),
        ("PROD_salt", 0.5, "tsp", ""),
        ("PROD_pepper", 0.25, "tsp", ""),
    ],
    "Croque Monsieur": [
        ("PROD_bread", 0.2, "kg", "white sliced"),
        ("PROD_cheddar_cheese", 0.15, "kg", "gruyere sub"),
        ("PROD_butter", 0.03, "kg", ""),
        ("PROD_plain_flour", 0.02, "kg", "for bechamel"),
        ("PROD_milk", 0.15, "L", "for bechamel"),
    ],
    "French Onion Soup": [
        ("PROD_brown_onion", 4, "pcs", "sliced"),
        ("PROD_butter", 0.04, "kg", ""),
        ("PROD_chicken_stock", 1, "L", "beef stock preferred"),
        ("PROD_bread", 0.1, "kg", "for croutons"),
        ("PROD_cheddar_cheese", 0.1, "kg", "gruyere sub"),
        ("PROD_plain_flour", 1, "tbsp", ""),
    ],
    "Salade Nicoise": [
        ("PROD_eggs", 4, "pcs", "hard-boiled"),
        ("PROD_potato", 2, "pcs", "boiled"),
        ("PROD_tomato", 2, "pcs", "quartered"),
        ("PROD_olive_oil", 3, "tbsp", ""),
        ("PROD_lemon", 1, "pcs", "for dressing"),
        ("PROD_salt", 0.5, "tsp", ""),
    ],
    "Pan-Fried Sole Meuniere": [
        ("PROD_salmon_fillet", 0.4, "kg", "sub for sole"),
        ("PROD_butter", 0.05, "kg", ""),
        ("PROD_plain_flour", 0.03, "kg", "for dredging"),
        ("PROD_lemon", 1, "pcs", ""),
        ("PROD_salt", 0.5, "tsp", ""),
    ],
    "Coq au Vin": [
        ("PROD_chicken_thigh", 0.6, "kg", ""),
        ("PROD_mushrooms", 0.2, "kg", ""),
        ("PROD_carrot", 2, "pcs", ""),
        ("PROD_brown_onion", 1, "pcs", ""),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_chicken_stock", 0.3, "L", ""),
        ("PROD_butter", 0.03, "kg", ""),
        ("PROD_plain_flour", 0.02, "kg", ""),
        ("PROD_tomato_paste", 1, "tbsp", ""),
    ],
    "Bechamel Sauce": [
        ("PROD_butter", 0.04, "kg", ""),
        ("PROD_plain_flour", 0.04, "kg", ""),
        ("PROD_milk", 0.5, "L", ""),
        ("PROD_salt", 0.5, "tsp", ""),
        ("PROD_pepper", 0.25, "tsp", ""),
    ],
    "Quiche Lorraine": [
        ("PROD_plain_flour", 0.2, "kg", "for pastry"),
        ("PROD_butter", 0.1, "kg", "cold, for pastry"),
        ("PROD_eggs", 4, "pcs", ""),
        ("PROD_cream", 0.2, "L", ""),
        ("PROD_cheddar_cheese", 0.1, "kg", "gruyere sub"),
    ],
    "Ratatouille": [
        ("PROD_zucchini", 2, "pcs", "sliced"),
        ("PROD_red_capsicum", 1, "pcs", "diced"),
        ("PROD_tomato", 3, "pcs", "sliced"),
        ("PROD_brown_onion", 1, "pcs", "diced"),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_olive_oil", 3, "tbsp", ""),
        ("PROD_salt", 0.5, "tsp", ""),
    ],
    "Steak Frites with Bearnaise": [
        ("PROD_beef_mince", 0.5, "kg", "sub for steak"),
        ("PROD_potato", 4, "pcs", "for frites"),
        ("PROD_butter", 0.1, "kg", "for bearnaise"),
        ("PROD_eggs", 3, "pcs", "yolks for bearnaise"),
        ("PROD_lemon", 1, "pcs", "or vinegar"),
        ("PROD_vegetable_oil", 0.5, "L", "for frying"),
        ("PROD_salt", 1, "tsp", ""),
    ],
    "Chicken Fricassee": [
        ("PROD_chicken_thigh", 0.6, "kg", ""),
        ("PROD_mushrooms", 0.2, "kg", ""),
        ("PROD_carrot", 1, "pcs", ""),
        ("PROD_brown_onion", 1, "pcs", ""),
        ("PROD_cream", 0.15, "L", ""),
        ("PROD_chicken_stock", 0.3, "L", ""),
        ("PROD_butter", 0.03, "kg", ""),
        ("PROD_plain_flour", 0.02, "kg", ""),
    ],
    "Beef Bourguignon": [
        ("PROD_beef_mince", 0.8, "kg", "or stewing beef"),
        ("PROD_carrot", 2, "pcs", ""),
        ("PROD_brown_onion", 2, "pcs", ""),
        ("PROD_mushrooms", 0.2, "kg", ""),
        ("PROD_garlic", 3, "cloves", ""),
        ("PROD_tomato_paste", 2, "tbsp", ""),
        ("PROD_chicken_stock", 0.5, "L", ""),
        ("PROD_butter", 0.03, "kg", ""),
        ("PROD_plain_flour", 0.02, "kg", ""),
    ],
    "Souffle (Cheese)": [
        ("PROD_eggs", 4, "pcs", "separated"),
        ("PROD_cheddar_cheese", 0.15, "kg", "grated"),
        ("PROD_butter", 0.04, "kg", ""),
        ("PROD_plain_flour", 0.03, "kg", ""),
        ("PROD_milk", 0.2, "L", ""),
    ],
    "Duck Confit": [
        ("PROD_chicken_thigh", 0.8, "kg", "sub for duck legs"),
        ("PROD_salt", 2, "tbsp", "for curing"),
        ("PROD_garlic", 4, "cloves", ""),
        ("PROD_pepper", 1, "tsp", ""),
        ("PROD_vegetable_oil", 0.5, "L", "sub for duck fat"),
    ],
    "Bouillabaisse": [
        ("PROD_salmon_fillet", 0.3, "kg", ""),
        ("PROD_prawns", 0.2, "kg", ""),
        ("PROD_tomato", 3, "pcs", ""),
        ("PROD_brown_onion", 1, "pcs", ""),
        ("PROD_garlic", 4, "cloves", ""),
        ("PROD_chicken_stock", 0.75, "L", "fish stock preferred"),
        ("PROD_olive_oil", 3, "tbsp", ""),
        ("PROD_lemon", 1, "pcs", ""),
    ],
    "Tarte Tatin": [
        ("PROD_apple", 6, "pcs", "peeled, halved"),
        ("PROD_butter", 0.08, "kg", ""),
        ("PROD_white_sugar", 0.1, "kg", "for caramel"),
        ("PROD_plain_flour", 0.2, "kg", "for pastry"),
    ],
    "Creme Brulee": [
        ("PROD_eggs", 4, "pcs", "yolks only"),
        ("PROD_cream", 0.4, "L", ""),
        ("PROD_white_sugar", 0.08, "kg", ""),
    ],
}


def seed_recipes(data_dir=None):
    """Load cuisine_skill_trees.json and seed all recipes into CSV store."""
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'store')

    store = CSVStore(data_dir)
    base_data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

    # Load skill trees
    with open(os.path.join(base_data, 'cuisine_skill_trees.json'), 'r', encoding='utf-8') as f:
        skill_trees = json.load(f)

    now = datetime.utcnow().isoformat()
    count = 0
    ingredient_count = 0

    for cuisine_key, cuisine_data in skill_trees.items():
        tiers = cuisine_data.get('tiers', {})
        for tier_key, tier_data in tiers.items():
            recipes = tier_data.get('recipes', [])
            for recipe in recipes:
                name = recipe['name']
                recipe_id = slugify(name)

                # Split estimated_time: 40% prep, 60% cook
                est = recipe.get('estimated_time', 30)
                prep_time = max(5, int(est * 0.4))
                cook_time = max(5, est - prep_time)

                # Look up macros
                macros = RECIPE_MACROS.get(name, {"calories": 300, "protein": 15, "carbs": 30, "fat": 12})

                recipe_data = {
                    'id': recipe_id,
                    'name': name,
                    'cuisine': cuisine_key,
                    'difficulty': recipe.get('difficulty', 1),
                    'tier': tier_key,
                    'prep_time': prep_time,
                    'cook_time': cook_time,
                    'servings': 4,
                    'techniques_taught': recipe.get('techniques_taught', []),
                    'key_learnings': recipe.get('key_learnings', ''),
                    'builds_on': recipe.get('builds_on', []),
                    'macros_per_serving': macros,
                    'instructions': [],
                    'video_url': None,
                    'video_timestamps': None,
                    'source': 'skill_tree',
                    'created_at': now,
                }

                # Look up ingredients
                raw_ingredients = RECIPE_INGREDIENTS.get(name, [])
                ingredients = []
                for ing in raw_ingredients:
                    prod_id, qty, unit, notes = ing
                    ingredients.append({
                        'canonical_product_id': prod_id,
                        'quantity': qty,
                        'unit': unit,
                        'notes': notes,
                    })

                upsert_recipe(store, recipe_data, ingredients)
                count += 1
                ingredient_count += len(ingredients)

                if count % 20 == 0:
                    print(f"  Seeded {count} recipes...")

    print(f"Seeded {count} recipes with {ingredient_count} ingredient rows")
    return count


if __name__ == '__main__':
    seed_recipes()

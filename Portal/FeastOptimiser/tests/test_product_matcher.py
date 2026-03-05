"""Tests for the product matching service."""

import pytest
from services.product_matcher import (
    normalize_product_name, extract_metadata,
    find_fuzzy_match
)


def test_normalize_removes_brand():
    assert 'chicken breast' in normalize_product_name("Coles RSPCA Chicken Breast 500g")


def test_normalize_lowercase():
    result = normalize_product_name("RICE")
    assert result == result.lower()


def test_extract_metadata_weight_grams():
    meta = extract_metadata("Chicken Breast 500g")
    assert meta['weight_g'] == 500
    assert meta['weight'] == '500g'


def test_extract_metadata_weight_kg():
    meta = extract_metadata("Rice 2kg")
    assert meta['weight_g'] == 2000  # Converted to grams
    assert meta['weight'] == '2kg'


def test_extract_metadata_volume():
    meta = extract_metadata("Milk 2L")
    assert meta['weight_g'] == 2000  # L treated as proxy
    assert meta['weight'] == '2L'


def test_extract_metadata_no_weight():
    meta = extract_metadata("Fresh Basil")
    assert meta['weight'] is None
    assert meta['weight_g'] is None


def test_fuzzy_match_exact():
    candidates = [
        {'id': 'PROD_chicken', 'name': 'Chicken Breast', 'base_unit': 'kg'},
        {'id': 'PROD_rice', 'name': 'White Rice', 'base_unit': 'kg'},
    ]
    result = find_fuzzy_match({'name': 'Chicken Breast', 'weight': None}, candidates)
    assert result is not None
    assert result['id'] == 'PROD_chicken'


def test_fuzzy_match_close():
    candidates = [
        {'id': 'PROD_chicken', 'name': 'Chicken Breast', 'base_unit': 'kg'},
    ]
    result = find_fuzzy_match({'name': 'chicken breast fillet', 'weight': None}, candidates)
    assert result is not None
    assert result['id'] == 'PROD_chicken'


def test_fuzzy_match_below_threshold():
    candidates = [
        {'id': 'PROD_chicken', 'name': 'Chicken Breast', 'base_unit': 'kg'},
    ]
    result = find_fuzzy_match({'name': 'premium dark chocolate', 'weight': None}, candidates, threshold=80)
    assert result is None

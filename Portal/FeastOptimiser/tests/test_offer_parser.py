"""Tests for the offer parser service."""

import pytest
from services.offer_parser import (
    parse_vision_response, classify_offer, calculate_offer_value
)


def test_parse_valid_json():
    text = '[{"program": "flybuys", "offer_type": "multiplier", "title": "10x points"}]'
    result = parse_vision_response(text)
    assert len(result) == 1
    assert result[0]['program'] == 'flybuys'


def test_parse_with_markdown_fences():
    text = '```json\n[{"program": "flybuys", "offer_type": "multiplier", "title": "10x"}]\n```'
    result = parse_vision_response(text)
    assert len(result) == 1


def test_parse_single_dict():
    text = '{"program": "flybuys", "offer_type": "threshold", "title": "Spend $100"}'
    result = parse_vision_response(text)
    assert len(result) == 1


def test_parse_invalid_json():
    result = parse_vision_response("not json at all")
    assert result == []


def test_parse_missing_required_fields():
    text = '[{"program": "flybuys"}]'
    result = parse_vision_response(text)
    assert len(result) == 0  # Missing offer_type and title


def test_classify_multiplier():
    offer_type, details = classify_offer("10x bonus points on Fresh Produce")
    assert offer_type == 'multiplier'
    assert details['multiplier'] == 10


def test_classify_threshold():
    offer_type, details = classify_offer("Spend $100 and earn 3000 points")
    assert offer_type == 'threshold'
    assert details['spend_threshold'] == 100
    assert details['bonus_points'] == 3000


def test_classify_category_bonus():
    offer_type, details = classify_offer("2000 bonus points on Cadbury products")
    assert offer_type == 'category_bonus'
    assert details['bonus_points'] == 2000


def test_calculate_multiplier_value():
    offer = {'offer_type': 'multiplier', 'details': {'multiplier': 10}}
    value = calculate_offer_value(offer, 50)  # $50 spend
    # (10-1) * 50 * 0.005 = 2.25
    assert value == pytest.approx(2.25)


def test_calculate_threshold_met():
    offer = {'offer_type': 'threshold', 'details': {'spend_threshold': 100, 'bonus_points': 3000}}
    value = calculate_offer_value(offer, 150)
    assert value == pytest.approx(15.0)  # 3000 * 0.005


def test_calculate_threshold_not_met():
    offer = {'offer_type': 'threshold', 'details': {'spend_threshold': 100, 'bonus_points': 3000}}
    value = calculate_offer_value(offer, 50)
    assert value == 0

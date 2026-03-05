"""Tests for the CSVStore data layer."""

import os
import tempfile
import pytest
from models.csv_store import CSVStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield CSVStore(tmpdir)


def test_read_empty_table(store):
    assert store.read_all('nonexistent') == []


def test_write_and_read(store):
    rows = [
        {'id': '1', 'name': 'Alice', 'age': '30'},
        {'id': '2', 'name': 'Bob', 'age': '25'},
    ]
    store.write_all('users', rows)
    result = store.read_all('users')
    assert len(result) == 2
    assert result[0]['name'] == 'Alice'
    assert result[1]['age'] == '25'


def test_append_row(store):
    store.append_row('items', {'id': '1', 'value': 'first'})
    store.append_row('items', {'id': '2', 'value': 'second'})
    result = store.read_all('items')
    assert len(result) == 2


def test_query(store):
    rows = [
        {'id': '1', 'category': 'fruit', 'name': 'apple'},
        {'id': '2', 'category': 'veg', 'name': 'carrot'},
        {'id': '3', 'category': 'fruit', 'name': 'banana'},
    ]
    store.write_all('products', rows)
    fruits = store.query('products', category='fruit')
    assert len(fruits) == 2
    assert all(r['category'] == 'fruit' for r in fruits)


def test_upsert_insert(store):
    store.upsert('items', {'id': '1', 'name': 'first'})
    result = store.read_all('items')
    assert len(result) == 1
    assert result[0]['name'] == 'first'


def test_upsert_update(store):
    store.upsert('items', {'id': '1', 'name': 'first'})
    store.upsert('items', {'id': '1', 'name': 'updated'})
    result = store.read_all('items')
    assert len(result) == 1
    assert result[0]['name'] == 'updated'


def test_delete(store):
    rows = [
        {'id': '1', 'name': 'keep'},
        {'id': '2', 'name': 'delete'},
    ]
    store.write_all('items', rows)
    deleted = store.delete('items', id='2')
    assert deleted == 1
    result = store.read_all('items')
    assert len(result) == 1
    assert result[0]['id'] == '1'


def test_next_id_empty(store):
    assert store.next_id('items') == 1


def test_next_id_existing(store):
    store.append_row('items', {'id': '5', 'name': 'five'})
    store.append_row('items', {'id': '3', 'name': 'three'})
    assert store.next_id('items') == 6


def test_json_field_roundtrip(store):
    import json
    data = {'id': '1', 'meta': json.dumps({'key': 'value', 'nested': [1, 2]})}
    store.upsert('items', data)
    result = store.read_all('items')
    parsed = json.loads(result[0]['meta'])
    assert parsed['key'] == 'value'
    assert parsed['nested'] == [1, 2]

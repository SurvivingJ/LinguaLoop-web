"""routes/payments.py: create-intent is unregistered until a verified Stripe webhook exists
(a completed payment would otherwise never credit tokens); token-packages stays."""

import json


def test_create_intent_route_is_not_registered(app):
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert '/api/payments/create-intent' not in rules
    assert '/api/payments/token-packages' in rules


def test_post_create_intent_answers_with_the_api_404_envelope(client, auth_headers):
    resp = client.post('/api/payments/create-intent', json={'package_id': 'x'}, headers=auth_headers)
    assert resp.status_code == 404
    assert json.loads(resp.data) == {
        'status': 'error', 'error': 'Endpoint not found', 'error_code': 'NOT_FOUND',
    }


def test_token_packages_still_served(client):
    resp = client.get('/api/payments/token-packages')
    assert resp.status_code == 200
    assert 'packages' in json.loads(resp.data)

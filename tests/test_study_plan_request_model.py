"""PUT /api/study-plan request validation (models/study_plan.py).

The model replaced hand-rolled checks in the route; these pin the accepted
inputs, the normalisation and the exact messages the API returns.
"""

import pytest

from models.study_plan import (
    InvalidStudyPlanRequest, StudyPlanTemplateApply, StudyPlanUpdate,
    parse_study_plan_request,
)


def _message(body):
    with pytest.raises(InvalidStudyPlanRequest) as exc:
        parse_study_plan_request(body)
    return str(exc.value)


@pytest.mark.parametrize('body, message', [
    ({}, "language_id (int) required"),
    ([1, 2], "language_id (int) required"),
    ({'language_id': '1', 'daily_minutes': 30}, "language_id (int) required"),
    ({'language_id': 1.0, 'daily_minutes': 30}, "language_id (int) required"),
    ({'language_id': True, 'daily_minutes': 30}, "language_id (int) required"),
    ({'language_id': 1, 'daily_minutes': 9}, "daily_minutes must be int in [10, 180]"),
    ({'language_id': 1, 'daily_minutes': 181}, "daily_minutes must be int in [10, 180]"),
    ({'language_id': 1, 'daily_minutes': 30.0}, "daily_minutes must be int in [10, 180]"),
    ({'language_id': 1, 'daily_minutes': None}, "daily_minutes must be int in [10, 180]"),
    ({'language_id': 1, 'weekday_shape': [1] * 6},
     "weekday_shape must be 7 non-negative floats summing > 0"),
    ({'language_id': 1, 'weekday_shape': [0] * 7},
     "weekday_shape must be 7 non-negative floats summing > 0"),
    ({'language_id': 1, 'weekday_shape': [1, 1, 1, 1, 1, 1, -1]},
     "weekday_shape must be 7 non-negative floats summing > 0"),
    ({'language_id': 1, 'skill_weight_overrides': {'reading': 2.5}},
     "skill_weight_overrides must be {skill: float in [0.5, 2.0]}"),
    ({'language_id': 1, 'skill_weight_overrides': ['reading']},
     "skill_weight_overrides must be {skill: float in [0.5, 2.0]}"),
    ({'language_id': 1, 'template_id': '5', 'daily_minutes': 30}, "template_id must be int"),
    ({'language_id': 1, 'timezone': '  '}, "timezone must be a non-empty string"),
    ({'language_id': 1, 'timezone': 7}, "timezone must be a non-empty string"),
    ({'language_id': 1, 'timezone': 'Mars/Olympus'},
     "timezone must be a valid IANA zone name (e.g. Asia/Tokyo)"),
    ({'language_id': 1, 'prestudy_mode': 'sometimes'}, "prestudy_mode must be 'auto', 'ask' or 'off'"),
    ({'language_id': 1, 'prestudy_mode': ['auto']}, "prestudy_mode must be 'auto', 'ask' or 'off'"),
    ({'language_id': 1, 'budget_scope': 'everything'},
     "budget_scope must be 'tests_and_review' or 'tests_only'"),
    ({'language_id': 1, 'new_words_per_day': 51}, "new_words_per_day must be int in [0, 50]"),
    ({'language_id': 1, 'new_words_per_day': -1}, "new_words_per_day must be int in [0, 50]"),
    ({'language_id': 1, 'new_words_per_day': 5.0}, "new_words_per_day must be int in [0, 50]"),
    ({'language_id': 1, 'new_words_per_day': True}, "new_words_per_day must be int in [0, 50]"),
    ({'language_id': 1, 'excluded_modules': 'reading'}, "excluded_modules must be a list of module codes"),
    ({'language_id': 1, 'excluded_modules': ['reading', 3]},
     "excluded_modules must be a list of module codes"),
])
def test_invalid_bodies_get_the_api_message(body, message):
    assert _message(body) == message


def test_the_first_invalid_field_in_declaration_order_is_reported():
    body = {'language_id': 1, 'excluded_modules': 'x', 'budget_scope': 'x',
            'timezone': 'nope', 'daily_minutes': 5}
    assert _message(body) == "daily_minutes must be int in [10, 180]"
    body.pop('daily_minutes')
    assert _message(body) == "timezone must be a valid IANA zone name (e.g. Asia/Tokyo)"
    body.pop('timezone')
    assert _message(body) == "budget_scope must be 'tests_and_review' or 'tests_only'"


def test_valid_update_is_normalised_and_keeps_only_provided_fields():
    body = parse_study_plan_request({
        'language_id': 1, 'timezone': ' Asia/Tokyo ', 'weekday_shape': [2, 2, 2, 2, 2, 2, 2],
        'skill_weight_overrides': {'reading': '1.23456'}, 'daily_minutes': 45,
        'excluded_modules': ['listening', 'listening'], 'ignored': 'x',
    })
    assert isinstance(body, StudyPlanUpdate)
    assert body.language_id == 1
    assert body.provided() == {
        'daily_minutes': 45,
        'weekday_shape': [1.0] * 7,
        'skill_weight_overrides': {'reading': 1.235},
        'timezone': 'Asia/Tokyo',
        'excluded_modules': ['listening', 'listening'],
    }
    assert list(body.provided()) == [
        'daily_minutes', 'weekday_shape', 'skill_weight_overrides', 'timezone', 'excluded_modules',
    ]


def test_boundary_values_are_accepted():
    body = parse_study_plan_request({
        'language_id': 1, 'daily_minutes': 10, 'new_words_per_day': 0,
        'budget_scope': 'tests_only', 'prestudy_mode': 'off',
    })
    assert body.provided() == {
        'daily_minutes': 10, 'prestudy_mode': 'off', 'budget_scope': 'tests_only',
        'new_words_per_day': 0,
    }
    assert parse_study_plan_request(
        {'language_id': 1, 'daily_minutes': 180, 'new_words_per_day': 50}).provided() == {
        'daily_minutes': 180, 'new_words_per_day': 50}


def test_language_only_body_has_nothing_to_update():
    assert parse_study_plan_request({'language_id': 1}).provided() == {}


def test_template_id_alone_is_a_template_apply():
    body = parse_study_plan_request({'language_id': 1, 'template_id': 5})
    assert isinstance(body, StudyPlanTemplateApply)
    assert (body.language_id, body.template_id) == (1, 5)
    assert _message({'language_id': 1, 'template_id': '5'}) == "template_id (int) required"
    assert _message({'language_id': 1, 'template_id': None}) == "template_id (int) required"


def test_prestudy_mode_does_not_turn_a_template_apply_into_an_update():
    # Sent with only a template_id, prestudy_mode has always been ignored.
    body = parse_study_plan_request({'language_id': 1, 'template_id': 5, 'prestudy_mode': 'bogus'})
    assert isinstance(body, StudyPlanTemplateApply)


def test_template_id_with_another_field_is_an_update():
    body = parse_study_plan_request({'language_id': 1, 'template_id': 5, 'timezone': 'UTC'})
    assert isinstance(body, StudyPlanUpdate)
    assert body.provided() == {'template_id': 5, 'timezone': 'UTC'}

# models/study_plan.py
"""Request models for PUT /api/study-plan.

Two body shapes share the endpoint:

* ``{language_id, template_id}`` alone applies a template (creating the plan
  row when there is none) -> ``StudyPlanTemplateApply``.
* anything else is a partial update of the stored plan -> ``StudyPlanUpdate``.

``parse_study_plan_request`` picks the shape and turns a validation failure
into ``InvalidStudyPlanRequest`` carrying the message the API returns. Rules
that need the database (the template's language, the modules offered for a
language, the merged session settings) are checked by
services.study_plan_settings.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, StrictInt, StrictStr, ValidationError, field_validator

from services.day_boundary import is_valid_timezone

# Present alongside template_id, any of these makes the request a partial
# update instead of a template apply. (prestudy_mode is deliberately absent:
# sent with only a template_id it has always been ignored.)
_UPDATE_ONLY_FIELDS = (
    'daily_minutes', 'weekday_shape', 'skill_weight_overrides', 'timezone',
    'excluded_modules', 'budget_scope', 'new_words_per_day',
)


class InvalidStudyPlanRequest(ValueError):
    """The request body failed validation; ``str()`` is the API message."""


def normalize_weekday_shape(shape: Any) -> Optional[List[float]]:
    """Return a 7-float list normalized to sum=7, or None if invalid."""
    if not isinstance(shape, list) or len(shape) != 7:
        return None
    try:
        floats = [float(x) for x in shape]
    except (TypeError, ValueError):
        return None
    if any(x < 0 for x in floats):
        return None
    s = sum(floats)
    if s <= 0:
        return None
    return [round(7.0 * x / s, 4) for x in floats]


def normalize_skill_weight_overrides(overrides: Any) -> Optional[Dict[str, float]]:
    """Return a dict of {skill_code: float in [0.5, 2.0]}, or None if invalid."""
    if not isinstance(overrides, dict):
        return None
    out: Dict[str, float] = {}
    for k, v in overrides.items():
        if not isinstance(k, str):
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if not (0.5 <= f <= 2.0):
            return None
        out[k] = round(f, 3)
    return out


class StudyPlanTemplateApply(BaseModel):
    """``{language_id, template_id}``: apply a template to the learner's plan."""
    language_id: StrictInt
    template_id: StrictInt


class StudyPlanUpdate(BaseModel):
    """A partial update: only the fields present in the body are changed.

    Fields are declared in the order their errors are reported. A field left
    out keeps its ``None`` default and is absent from ``provided()``; an
    explicit ``null`` is a validation error, as it always was.
    """
    language_id: StrictInt
    daily_minutes: Annotated[StrictInt, Field(ge=10, le=180)] = None
    #: 7 non-negative numbers, normalized to sum 7.
    weekday_shape: List[float] = None
    skill_weight_overrides: Dict[str, float] = None
    template_id: StrictInt = None
    #: A valid IANA zone name (TASK-716); keys the daily load via ADR-022.
    timezone: str = None
    #: Test prestudy trigger (wiki/features/test-prestudy.md).
    prestudy_mode: Literal['auto', 'ask', 'off'] = None
    budget_scope: Literal['tests_and_review', 'tests_only'] = None
    #: An int, not a bool or a float (5.0 is rejected on purpose). > 0 with
    #: Vocabulary review off is allowed: all new words then go to the tail.
    new_words_per_day: Annotated[StrictInt, Field(ge=0, le=50)] = None
    excluded_modules: List[StrictStr] = None

    @field_validator('weekday_shape', mode='plain')
    @classmethod
    def _weekday_shape(cls, value: Any) -> List[float]:
        shape = normalize_weekday_shape(value)
        if shape is None:
            raise ValueError(_MESSAGES['weekday_shape'])
        return shape

    @field_validator('skill_weight_overrides', mode='plain')
    @classmethod
    def _skill_weight_overrides(cls, value: Any) -> Dict[str, float]:
        overrides = normalize_skill_weight_overrides(value)
        if overrides is None:
            raise ValueError(_MESSAGES['skill_weight_overrides'])
        return overrides

    @field_validator('timezone', mode='plain')
    @classmethod
    def _timezone(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("timezone must be a non-empty string")
        if not is_valid_timezone(value):
            raise ValueError("timezone must be a valid IANA zone name (e.g. Asia/Tokyo)")
        return value.strip()

    def provided(self) -> Dict[str, Any]:
        """The editable fields present in the body, in declaration order."""
        return {
            name: getattr(self, name)
            for name in type(self).model_fields
            if name != 'language_id' and name in self.model_fields_set
        }


_MESSAGES = {
    'language_id': "language_id (int) required",
    'daily_minutes': "daily_minutes must be int in [10, 180]",
    'weekday_shape': "weekday_shape must be 7 non-negative floats summing > 0",
    'skill_weight_overrides': "skill_weight_overrides must be {skill: float in [0.5, 2.0]}",
    'template_id': "template_id must be int",
    'prestudy_mode': "prestudy_mode must be 'auto', 'ask' or 'off'",
    'budget_scope': "budget_scope must be 'tests_and_review' or 'tests_only'",
    'new_words_per_day': "new_words_per_day must be int in [0, 50]",
    'excluded_modules': "excluded_modules must be a list of module codes",
}
_TEMPLATE_APPLY_MESSAGES = {**_MESSAGES, 'template_id': "template_id (int) required"}


def _first_message(exc: ValidationError, messages: Dict[str, str]) -> str:
    error = exc.errors()[0]
    if error['type'] == 'value_error':
        return str(error['ctx']['error'])
    field = error['loc'][0] if error['loc'] else None
    return messages.get(field, "invalid request body")


def parse_study_plan_request(data: Any) -> Union[StudyPlanTemplateApply, StudyPlanUpdate]:
    """Validate a PUT /api/study-plan body; raises InvalidStudyPlanRequest."""
    if not isinstance(data, dict):
        data = {}
    template_only = 'template_id' in data and not any(k in data for k in _UPDATE_ONLY_FIELDS)
    model, messages = (
        (StudyPlanTemplateApply, _TEMPLATE_APPLY_MESSAGES) if template_only
        else (StudyPlanUpdate, _MESSAGES)
    )
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise InvalidStudyPlanRequest(_first_message(exc, messages)) from None

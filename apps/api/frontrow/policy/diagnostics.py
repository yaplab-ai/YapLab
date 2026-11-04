"""Fixed validation labels. Never store model values or validator error details."""
from __future__ import annotations

VALIDATION_ISSUES = frozenset({
    'non_text_response', 'response_too_large', 'json_syntax',
    'duplicate_json_keys', 'nonfinite_json_value', 'json_number_limit',
    'schema_extra_fields', 'schema_missing_fields', 'schema_types',
    'schema_limits', 'schema_contract', 'duplicate_action_ids',
    'duplicate_fact_ids', 'duplicate_source_ids', 'duplicate_question_ids',
    'unknown_action_id', 'unknown_fact_id', 'unknown_source_id',
    'unknown_question_id',
})


class InvalidRoleResponse(ValueError):
    """Only a server-defined category crosses the validation boundary."""

    def __init__(self, category: str) -> None:
        if category not in VALIDATION_ISSUES:
            raise ValueError('Unknown validation category')
        self.category = category
        super().__init__(category)

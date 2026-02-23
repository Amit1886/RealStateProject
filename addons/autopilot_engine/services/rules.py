from typing import Any, Dict, Tuple


def rule_matches(rule_conditions: Dict[str, Any], event_payload: Dict[str, Any], branch_code: str) -> Tuple[bool, str]:
    if not rule_conditions:
        return True, "ok"

    allowed_branches = rule_conditions.get("branch_codes")
    if allowed_branches and branch_code not in allowed_branches:
        return False, "branch_mismatch"

    required_keys = rule_conditions.get("required_payload_keys", [])
    for key in required_keys:
        if key not in event_payload:
            return False, f"missing_payload_key:{key}"

    min_amount = rule_conditions.get("min_amount")
    if min_amount is not None:
        try:
            amount = float(event_payload.get("total_amount", 0))
            if amount < float(min_amount):
                return False, "amount_below_min"
        except (TypeError, ValueError):
            return False, "invalid_amount"

    return True, "ok"

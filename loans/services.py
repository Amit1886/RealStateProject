from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def _quantize(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_emi(principal, annual_rate, tenure_years) -> Decimal:
    principal_value = Decimal(str(principal or 0))
    rate_value = Decimal(str(annual_rate or 0))
    tenure_months = int(Decimal(str(tenure_years or 0)) * 12)
    if principal_value <= 0 or tenure_months <= 0:
        return Decimal("0.00")
    monthly_rate = rate_value / Decimal("1200")
    if monthly_rate == 0:
        return _quantize(principal_value / tenure_months)
    growth = (Decimal("1") + monthly_rate) ** tenure_months
    emi = (principal_value * monthly_rate * growth) / (growth - Decimal("1"))
    return _quantize(emi)


def assess_eligibility(monthly_income, existing_emi, emi_amount) -> Decimal:
    income_value = Decimal(str(monthly_income or 0))
    obligations = Decimal(str(existing_emi or 0))
    emi_value = Decimal(str(emi_amount or 0))
    if income_value <= 0:
        return Decimal("0.00")
    disposable = max(income_value - obligations, Decimal("0.00"))
    if disposable <= 0:
        return Decimal("0.00")
    return _quantize((disposable / emi_value) * Decimal("100")) if emi_value > 0 else Decimal("0.00")


def application_status_from_ratio(ratio: Decimal) -> str:
    if ratio >= Decimal("130"):
        return "eligible"
    if ratio >= Decimal("100"):
        return "under_review"
    return "rejected"


def build_application_snapshot(*, requested_amount, interest_rate, tenure_years, monthly_income, existing_emi):
    emi_estimate = calculate_emi(requested_amount, interest_rate, tenure_years)
    ratio = assess_eligibility(monthly_income, existing_emi, emi_estimate)
    return {
        "emi_estimate": emi_estimate,
        "eligibility_ratio": ratio,
        "status": application_status_from_ratio(ratio),
    }


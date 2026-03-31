def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """
    EMI = [P × R × (1+R)^N] / [(1+R)^N – 1]
    R is monthly interest rate (annual_rate / 12 / 100)
    """
    principal = float(principal)
    r = float(annual_rate) / 12 / 100
    n = int(tenure_months)
    if r == 0 or n == 0:
        return round(principal / max(1, n), 2)
    emi = (principal * r * (1 + r) ** n) / ((1 + r) ** n - 1)
    return round(emi, 2)

def detect_barcode_type(raw_code: str):
    if not raw_code:
        return "unknown"
    if raw_code.startswith("http") or len(raw_code) > 20:
        return "qr"
    if raw_code.isdigit() and len(raw_code) in (8, 12, 13, 14):
        return "ean"
    if "-" in raw_code:
        return "code128"
    return "generic"

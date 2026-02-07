from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re
from difflib import get_close_matches
from typing import Iterable, List, Optional, Tuple

from commerce.models import Order, OrderItem, Product


NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "ek": 1,
    "do": 2,
    "teen": 3,
    "char": 4,
    "paanch": 5,
    "chhe": 6,
    "saat": 7,
    "aath": 8,
    "nau": 9,
    "das": 10,
}


@dataclass
class ParsedItem:
    raw_name: str
    quantity: int
    matched_product: Optional[Product]
    match_confidence: float
    status: str


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _split_items(message: str) -> List[str]:
    cleaned = message.replace("\n", ",").replace(";", ",")
    parts = re.split(r",| and | & ", cleaned, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def _extract_qty_and_name(part: str) -> Tuple[int, str]:
    text = _normalize_text(part)
    qty = None

    # Patterns like "2 milk", "2x milk", "milk x2"
    m = re.search(r"(\d+)\s*(x)?\s*([a-zA-Z].*)", text)
    if m:
        qty = int(m.group(1))
        name = m.group(3)
        return max(qty, 1), name.strip()

    m = re.search(r"([a-zA-Z].*?)\s*(x)?\s*(\d+)$", text)
    if m:
        qty = int(m.group(3))
        name = m.group(1)
        return max(qty, 1), name.strip()

    # Number words
    tokens = text.split()
    if tokens and tokens[0] in NUMBER_WORDS:
        qty = NUMBER_WORDS[tokens[0]]
        name = " ".join(tokens[1:]).strip()
        return max(qty, 1), name

    return 1, text


def _build_product_index(products: Iterable[Product]):
    names = []
    name_map = {}
    for p in products:
        normalized = _normalize_text(p.name)
        names.append(normalized)
        name_map[normalized] = p
    return names, name_map


def _match_product(name: str, product_names: List[str], name_map: dict) -> Tuple[Optional[Product], float]:
    if not name:
        return None, 0.0

    normalized = _normalize_text(name)
    # Direct contains match first
    for p_name in product_names:
        if normalized == p_name or normalized in p_name:
            return name_map[p_name], 0.92

    matches = get_close_matches(normalized, product_names, n=1, cutoff=0.6)
    if matches:
        return name_map[matches[0]], 0.75

    return None, 0.0


def parse_whatsapp_order_message(message: str, products: Iterable[Product]) -> List[ParsedItem]:
    product_names, name_map = _build_product_index(products)
    results: List[ParsedItem] = []

    for raw_part in _split_items(message):
        qty, name = _extract_qty_and_name(raw_part)
        product, confidence = _match_product(name, product_names, name_map)
        status = "matched" if product else "manual_review"
        results.append(
            ParsedItem(
                raw_name=name or raw_part,
                quantity=max(qty, 1),
                matched_product=product,
                match_confidence=confidence,
                status=status,
            )
        )

    return results


def create_order_from_parsed_items(
    *,
    owner,
    party,
    parsed_items: List[ParsedItem],
    notes: str,
    order_source: str = "WhatsApp",
) -> Order:
    order = Order.objects.create(
        owner=owner,
        party=party,
        order_type="SALE",
        status="pending",
        notes=notes,
        order_source=order_source,
    )

    for item in parsed_items:
        product = item.matched_product
        price = product.price if product else Decimal("0.00")
        OrderItem.objects.create(
            order=order,
            product=product,
            qty=item.quantity,
            price=price,
            raw_name=item.raw_name if not product else "",
        )

    return order

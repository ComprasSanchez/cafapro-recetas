from __future__ import annotations

from datetime import datetime
from decimal import Decimal


def fmt_money(value) -> str:
    try:
        return f"{Decimal(value):.2f}"
    except Exception:
        return "0.00"


def parse_ddmmyyyy(text: str):
    text = (text or "").strip()
    if not text:
        return None

    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    return None


def fmt_date(value) -> str:
    if not value:
        return ""
    try:
        return value.strftime("%d/%m/%y")
    except Exception:
        return ""

"""Natural-language date parsing."""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

__all__ = ["parse"]

_WEEKDAYS: dict[str, int] = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

_MONTHS: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

_NUMBER_WORDS: dict[str, int] = {
    "a": 1,
    "an": 1,
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
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
}

# Year-first numeric dates: 2025-12-04, 2025/12/04, 2025.12.04
_ISO_RE = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
# Month-first numeric dates: 12/25/2025, 12-25-2025, 12.25.2025
_NUMERIC_DATE_RE = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})$")
_MONTH_NAME_DAY_YEAR_RE = re.compile(
    r"^(?P<month>[a-z]+)\s+"
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)?"
    r"(?:,?\s+(?P<year>\d{4}))?$",
    re.IGNORECASE,
)
_DAY_MONTH_YEAR_RE = re.compile(
    r"^(?:the\s+)?(?P<day>\d{1,2})(?:st|nd|rd|th)?"
    r"(?:\s+of)?\s+(?P<month>[a-z]+)"
    r"(?:,?\s+(?P<year>\d{4}))?$",
    re.IGNORECASE,
)

_WEEKDAY_NAMES = "|".join(sorted(_WEEKDAYS.keys(), key=len, reverse=True))
_UNIT_NAMES = r"years?|yrs?|months?|mos?|weeks?|wks?|days?|fortnights?"
_NUMBER_PATTERN = (
    r"(?:\d+|" + "|".join(sorted(_NUMBER_WORDS.keys(), key=len, reverse=True)) + r")"
)


def parse(s: str, today: date | None = None) -> date:
    """Parse a natural-language date string into a :class:`~datetime.date`.

    Parameters
    ----------
    s:
        A natural-language date expression such as ``"next Tuesday"`` or
        ``"5 days before December 1st, 2025"``.
    today:
        Reference date for relative expressions. Defaults to
        :meth:`datetime.date.today`.

    Returns
    -------
    datetime.date
        The resolved calendar date.

    Raises
    ------
    ValueError
        If ``s`` is empty or not a recognized date expression.
    """
    if today is None:
        today = date.today()

    text = " ".join(s.strip().lower().split())
    if not text:
        raise ValueError(f"Unrecognized date expression: {s!r}")

    # Strip a leading "on " which often appears in calendar phrasing.
    if text.startswith("on "):
        text = text[3:].strip()

    try:
        return _parse_expression(text, today)
    except ValueError as exc:
        raise ValueError(f"Unrecognized date expression: {s!r}") from exc


def _parse_expression(text: str, today: date) -> date:
    # Resolve standalone keywords / absolute dates before relational patterns so
    # phrases like "day before yesterday" are not misread as duration+anchor.
    atom = _parse_atom(text, today)
    if atom is not None:
        return atom

    # "X before/after Y" — duration relative to an anchor expression.
    before_after = re.match(r"^(.+?)\s+(before|after)\s+(.+)$", text)
    if before_after is not None:
        duration_text, direction, anchor_text = before_after.groups()
        anchor = _parse_expression(anchor_text, today)
        delta = _parse_duration(duration_text)
        return _apply_duration(anchor, delta, sign=-1 if direction == "before" else 1)

    # "X from Y" / "X from now"
    from_match = re.match(r"^(.+?)\s+from\s+(.+)$", text)
    if from_match is not None:
        duration_text, anchor_text = from_match.groups()
        if anchor_text in {"now", "today"}:
            anchor = today
        else:
            anchor = _parse_expression(anchor_text, today)
        delta = _parse_duration(duration_text)
        return _apply_duration(anchor, delta, sign=1)

    # "in X"
    in_match = re.match(r"^in\s+(.+)$", text)
    if in_match is not None:
        delta = _parse_duration(in_match.group(1))
        return _apply_duration(today, delta, sign=1)

    # "X ago"
    ago_match = re.match(r"^(.+?)\s+ago$", text)
    if ago_match is not None:
        delta = _parse_duration(ago_match.group(1))
        return _apply_duration(today, delta, sign=-1)

    # Bare duration like "3 days" → treat as future ("in 3 days").
    try:
        delta = _parse_duration(text)
    except ValueError as exc:
        raise ValueError(f"Unrecognized date expression: {text!r}") from exc
    return _apply_duration(today, delta, sign=1)


def _parse_atom(text: str, today: date) -> date | None:
    if text in {"today", "now"}:
        return today
    if text == "tomorrow":
        return today + timedelta(days=1)
    if text == "yesterday":
        return today - timedelta(days=1)
    if text in {"day after tomorrow", "the day after tomorrow"}:
        return today + timedelta(days=2)
    if text in {"day before yesterday", "the day before yesterday"}:
        return today - timedelta(days=2)

    # next/last/this week|month|year
    period = re.match(r"^(next|last|this|previous)\s+(week|month|year)$", text)
    if period is not None:
        return _resolve_period(period.group(1), period.group(2), today)

    # next/last/this weekday
    weekday = re.match(
        rf"^(next|last|this|previous)\s+({_WEEKDAY_NAMES})$",
        text,
    )
    if weekday is not None:
        return _resolve_weekday(weekday.group(1), weekday.group(2), today)

    # bare weekday → this week's occurrence, or next week if already past
    if text in _WEEKDAYS:
        return _resolve_weekday("this", text, today)

    return _parse_absolute(text, today)


def _parse_absolute(text: str, today: date) -> date | None:
    iso = _ISO_RE.match(text)
    if iso is not None:
        year, month, day = int(iso.group(1)), int(iso.group(2)), int(iso.group(3))
        return _make_date(year, month, day)

    numeric = _NUMERIC_DATE_RE.match(text)
    if numeric is not None:
        month = int(numeric.group(1))
        day = int(numeric.group(2))
        year = int(numeric.group(3))
        if year < 100:
            year += 2000
        return _make_date(year, month, day)

    month_first = _MONTH_NAME_DAY_YEAR_RE.match(text)
    if month_first is not None:
        month_name = month_first.group("month").lower()
        if month_name in _MONTHS:
            month = _MONTHS[month_name]
            day = int(month_first.group("day"))
            year_str = month_first.group("year")
            year = int(year_str) if year_str else _infer_year(today, month, day)
            return _make_date(year, month, day)

    day_first = _DAY_MONTH_YEAR_RE.match(text)
    if day_first is not None:
        month_name = day_first.group("month").lower()
        if month_name in _MONTHS:
            month = _MONTHS[month_name]
            day = int(day_first.group("day"))
            year_str = day_first.group("year")
            year = int(year_str) if year_str else _infer_year(today, month, day)
            return _make_date(year, month, day)

    return None


def _infer_year(today: date, month: int, day: int) -> int:
    """Prefer the current year; if that date has already passed, use next year."""
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        # e.g. Feb 29 in a non-leap year — try next year
        return today.year + 1
    if candidate < today:
        return today.year + 1
    return today.year


def _make_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError(f"Invalid calendar date: {year}-{month}-{day}") from exc


def _resolve_weekday(modifier: str, weekday_name: str, today: date) -> date:
    target = _WEEKDAYS[weekday_name]
    current = today.weekday()
    days_ahead = (target - current) % 7
    days_behind = (current - target) % 7

    if modifier == "next":
        # Always at least one day in the future; if today is that weekday, +7.
        return today + timedelta(days=7 if days_ahead == 0 else days_ahead)
    if modifier in {"last", "previous"}:
        # Always at least one day in the past; if today is that weekday, -7.
        return today - timedelta(days=7 if days_behind == 0 else days_behind)
    # "this" / bare: today if it matches, otherwise the next occurrence.
    if days_ahead == 0:
        return today
    return today + timedelta(days=days_ahead)


def _resolve_period(modifier: str, unit: str, today: date) -> date:
    """Resolve ``next/last/this week|month|year`` relative to ``today``.

    These keep the same day-of-week / day-of-month / month-day as ``today``,
    shifting by one unit (e.g. ``next week`` is ``today + 7 days``).
    """
    if modifier in {"this"}:
        return today

    sign = 1 if modifier == "next" else -1
    if unit == "week":
        return today + timedelta(days=7 * sign)
    if unit == "month":
        return _add_months(today, sign)
    return _add_years(today, sign)


def _parse_number(token: str) -> int:
    token = token.lower()
    if token.isdigit():
        return int(token)
    if token in _NUMBER_WORDS:
        return _NUMBER_WORDS[token]
    raise ValueError(f"Unrecognized number: {token!r}")


def _normalize_unit(unit: str) -> str:
    unit = unit.lower()
    aliases = {
        "yr": "year",
        "yrs": "year",
        "year": "year",
        "years": "year",
        "mo": "month",
        "mos": "month",
        "month": "month",
        "months": "month",
        "wk": "week",
        "wks": "week",
        "week": "week",
        "weeks": "week",
        "day": "day",
        "days": "day",
        "fortnight": "fortnight",
        "fortnights": "fortnight",
    }
    if unit not in aliases:
        raise ValueError(f"Unrecognized time unit: {unit!r}")
    return aliases[unit]


def _parse_duration(text: str) -> list[tuple[int, str]]:
    """Parse a duration like ``'1 year and 2 months'`` into component pairs."""
    text = text.strip()
    if not text:
        raise ValueError("Empty duration")

    # Allow a leading "the " for phrases like "the day after ...".
    if text.startswith("the "):
        text = text[4:]

    parts = re.split(r"\s*(?:,\s*|\band\b)\s*", text)
    components: list[tuple[int, str]] = []

    part_re = re.compile(
        rf"^(?:({_NUMBER_PATTERN})\s+)?({_UNIT_NAMES})$",
        re.IGNORECASE,
    )

    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = part_re.match(part)
        if match is None:
            raise ValueError(f"Unrecognized duration component: {part!r}")
        amount_token = match.group(1)
        amount = 1 if amount_token is None else _parse_number(amount_token)
        unit = _normalize_unit(match.group(2))
        components.append((amount, unit))

    if not components:
        raise ValueError(f"Unrecognized duration: {text!r}")
    return components


def _apply_duration(
    base: date,
    components: list[tuple[int, str]],
    *,
    sign: int,
) -> date:
    result = base
    for amount, unit in components:
        n = sign * amount
        if unit == "day":
            result = result + timedelta(days=n)
        elif unit == "week":
            result = result + timedelta(days=7 * n)
        elif unit == "fortnight":
            result = result + timedelta(days=14 * n)
        elif unit == "month":
            result = _add_months(result, n)
        elif unit == "year":
            result = _add_years(result, n)
        else:
            raise ValueError(f"Unsupported unit: {unit!r}")
    return result


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(d: date, years: int) -> date:
    year = d.year + years
    day = d.day
    if d.month == 2 and day == 29 and not calendar.isleap(year):
        day = 28
    return date(year, d.month, day)

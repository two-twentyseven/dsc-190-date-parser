"""Tests for :func:`nldate.parse`."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from nldate import parse

TODAY = date(2025, 11, 5)  # a Wednesday


def p(s: str, today: date = TODAY) -> date:
    return parse(s, today=today)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("December 1st, 2025", date(2025, 12, 1)),
        ("December 1 2025", date(2025, 12, 1)),
        ("Dec 1, 2025", date(2025, 12, 1)),
        ("1 December 2025", date(2025, 12, 1)),
        ("2025-12-01", date(2025, 12, 1)),
        ("12/25/2025", date(2025, 12, 25)),
        ("March 3rd, 2024", date(2024, 3, 3)),
        ("February 29, 2024", date(2024, 2, 29)),
    ],
)
def test_absolute_dates(text: str, expected: date) -> None:
    assert p(text) == expected


@pytest.mark.parametrize(
    "text",
    ["december 1st, 2025", "DECEMBER 1ST, 2025", "  December   1st,  2025\n"],
)
def test_case_and_whitespace_insensitive(text: str) -> None:
    assert p(text) == date(2025, 12, 1)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("today", date(2025, 11, 5)),
        ("tomorrow", date(2025, 11, 6)),
        ("yesterday", date(2025, 11, 4)),
        ("the day after tomorrow", date(2025, 11, 7)),
        ("the day before yesterday", date(2025, 11, 3)),
    ],
)
def test_keywords(text: str, expected: date) -> None:
    assert p(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("in 3 days", date(2025, 11, 8)),
        ("3 days from now", date(2025, 11, 8)),
        ("3 days ago", date(2025, 11, 2)),
        ("in 2 weeks", date(2025, 11, 19)),
        ("2 weeks ago", date(2025, 10, 22)),
        ("in 2 months", date(2026, 1, 5)),
        ("in 1 year", date(2026, 11, 5)),
        ("next week", date(2025, 11, 12)),
        ("last month", date(2025, 10, 5)),
        ("next year", date(2026, 11, 5)),
    ],
)
def test_relative_to_today(text: str, expected: date) -> None:
    assert p(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5 days before December 1st, 2025", date(2025, 11, 26)),
        ("5 days after December 1st, 2025", date(2025, 12, 6)),
        ("2 weeks before December 1st, 2025", date(2025, 11, 17)),
        ("3 months before December 1st, 2025", date(2025, 9, 1)),
        ("1 day before January 1, 2025", date(2024, 12, 31)),
        ("10 days before tomorrow", date(2025, 10, 27)),
        ("two weeks from tomorrow", date(2025, 11, 20)),
    ],
)
def test_before_after_anchor(text: str, expected: date) -> None:
    assert p(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 year and 2 months after yesterday", date(2027, 1, 4)),
        ("2 weeks and 3 days before December 1st, 2025", date(2025, 11, 14)),
        ("1 year, 2 months and 3 days after December 1st, 2025", date(2027, 2, 4)),
        ("in 1 week and 2 days", date(2025, 11, 14)),
    ],
)
def test_compound_durations(text: str, expected: date) -> None:
    assert p(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("in three days", date(2025, 11, 8)),
        ("five days ago", date(2025, 10, 31)),
        ("a week from today", date(2025, 11, 12)),
        ("five days before December 1st, 2025", date(2025, 11, 26)),
    ],
)
def test_number_words(text: str, expected: date) -> None:
    assert p(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 month after January 31, 2025", date(2025, 2, 28)),
        ("1 month after January 31, 2024", date(2024, 2, 29)),
        ("1 year after February 29, 2024", date(2025, 2, 28)),
        ("1 day after February 28, 2024", date(2024, 2, 29)),
        ("1 day after February 28, 2025", date(2025, 3, 1)),
        ("3 days after December 30, 2025", date(2026, 1, 2)),
    ],
)
def test_calendar_edge_cases(text: str, expected: date) -> None:
    assert p(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("next Monday", date(2025, 11, 10)),
        ("next Tuesday", date(2025, 11, 11)),
        ("next Wednesday", date(2025, 11, 12)),
        ("next Friday", date(2025, 11, 7)),
        ("last Monday", date(2025, 11, 3)),
        ("last Wednesday", date(2025, 10, 29)),
        ("last Friday", date(2025, 10, 31)),
        ("this Friday", date(2025, 11, 7)),
        ("NEXT tue", date(2025, 11, 11)),
    ],
)
def test_weekdays(text: str, expected: date) -> None:
    assert p(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "banana",
        "not a date",
        "February 30, 2025",
        "December 32nd, 2025",
        "2025-13-01",
        "next Blursday",
        "5 days before",
        "before December 1st, 2025",
        "5 bananas after tomorrow",
        "December 1st, 2025 banana",
    ],
)
def test_invalid_input_raises_value_error(text: str) -> None:
    with pytest.raises(ValueError):
        p(text)


def test_default_today_is_current_date() -> None:
    before = date.today()
    result = parse("tomorrow")
    after = date.today()
    assert before + timedelta(days=1) <= result <= after + timedelta(days=1)
    assert type(result) is date


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("the 4th of July, 2026", date(2026, 7, 4)),
        ("Sept 9, 2025", date(2025, 9, 9)),
        ("December 25th", date(2025, 12, 25)),
        ("a month from today", date(2025, 12, 5)),
        ("a year ago", date(2024, 11, 5)),
        ("a week before tomorrow", date(2025, 10, 30)),
        ("6 months after June 30, 2025", date(2025, 12, 30)),
        ("1 month before December 31, 2025", date(2025, 11, 30)),
        ("2 years before February 29, 2024", date(2022, 2, 28)),
        ("last Saturday", date(2025, 11, 1)),
    ],
)
def test_more_examples(text: str, expected: date) -> None:
    assert p(text) == expected

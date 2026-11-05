"""Source-derived reporting periods and financial-table column selection."""

import calendar
import re
from datetime import date


MONTHS = {name.casefold(): number for number in range(1, 13)
          for name in (calendar.month_name[number], calendar.month_abbr[number])}
MONTH_PATTERN = "(?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + ")"
DATE_PATTERN = rf"({MONTH_PATTERN})\.?\s+(\d{{1,2}}),?\s+((?:19|20)\d{{2}})"


def reporting_date(statement: str) -> date | None:
    match = re.search(r"\b(?:as\s+(?:of|at)|on|year\s+ended)\s+" + DATE_PATTERN,
                      statement, re.IGNORECASE)
    if not match:
        return None
    month, day, year = match.groups()
    try:
        return date(int(year), MONTHS[month.casefold()], int(day))
    except ValueError:
        return None


def fiscal_year(statement: str) -> int | None:
    if re.search(r"\b(?:quarter|Q[1-4]|YTD|year.to.date|(?:three|six|nine).months?)\b",
                 statement, re.IGNORECASE):
        return None
    match = re.search(r"\b(?:fiscal(?:\s+year)?|FY)\s*((?:19|20)\d{2})\b", statement, re.I)
    return int(match.group(1)) if match else None


def future_annual_period(statement: str, filings) -> tuple[date, date] | None:
    """Earlier filings cannot establish a completed future annual actual."""
    if re.search(r"\b(?:forecasts?|guidance|expects?|expected|projects?|projected|"
                 r"estimates?|estimated|will|plans?|planned)\b", statement, re.I):
        return None
    if re.search(r"\b(?:quarter|Q[1-4]|YTD|year.to.date|(?:three|six|nine).months?)\b",
                 statement, re.IGNORECASE):
        return None
    annual = [f for f in filings if getattr(f, "form", None) == "10-K"]
    dates = [f.filed_at for f in filings if getattr(f, "filed_at", None)]
    if not annual or not dates:
        return None
    year = fiscal_year(statement)
    explicit = reporting_date(statement) if re.search(r"\byear\s+ended\b", statement, re.I) else None
    if not year and not explicit:
        return None
    anchor = max(f.period_end for f in annual)
    try:
        target = explicit or date(year, anchor.month, anchor.day)
    except ValueError:
        return None
    cutoff = max(dates)
    return (target, cutoff) if target > cutoff else None


def table_column(statement: str, prefix: str, period_end: date, form: str) -> int | None:
    """Bind the requested year/date to the closest preceding year-header row."""
    year = fiscal_year(statement)
    target_date = reporting_date(statement)
    if year is None and (target_date is None or target_date == period_end):
        return 0
    if year is not None and form != "10-K":
        return None
    lines = prefix.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index].strip()
        if not re.fullmatch(r"(?:(?:19|20)\d{2}[\s,$%]*){2,}", line):
            continue
        years = [int(value) for value in re.findall(r"(?:19|20)\d{2}", line)]
        if year is not None:
            choices = [i for i, value in enumerate(years) if value == year]
        else:
            heading = "\n".join(lines[max(0, index - 4):index])
            months = re.findall(rf"\b({MONTH_PATTERN})\.?\s+(\d{{1,2}})", heading, re.I)
            if len(months) == 1:
                months *= len(years)
            if len(months) != len(years):
                return None
            try:
                columns = [date(y, MONTHS[m.casefold()], int(d)) for y, (m, d) in zip(years, months)]
            except ValueError:
                return None
            choices = [i for i, value in enumerate(columns) if value == target_date]
        return choices[0] if len(choices) == 1 else None
    if year is not None:
        return 0 if year == period_end.year else None
    return None

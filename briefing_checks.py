"""Grounding checks for the AI market briefing.

The briefing is written by a language model from a structured metrics dict, then
published to the dashboard. That dict is the ground truth, and it is already in
memory at generation time -- so the briefing can be checked against it without a
second model call, without a judge, and without a labelled dataset.

Four deterministic checks run over the generated markdown:

1. Numeric grounding -- every figure in the prose must trace back to a number the
   model was actually given (or to one of a small set of derivations an analyst
   would reasonably compute). An unmatched figure is a fabricated one.
2. Attribution -- in a sentence about a single ticker, a figure must be one of
   that ticker's own values or a market-wide one, not another ticker's.
3. Superlatives -- if the text names a top gainer or worst performer, that ticker
   must actually be the extreme.
4. Direction -- if the text says a ticker rose or fell, the sign must agree.

An empty response fails outright.

What this does NOT do: judge whether the analysis is any good, catch a wrong
claim stated without numbers ("sentiment is deteriorating"), or tell which of a
ticker's own metrics a figure belongs to (a volatility quoted as a return
passes). It establishes that the figures in the text came from the data.
"""

import re
from dataclasses import dataclass

# Figures written to fewer decimal places than the source are matched by
# tolerance, so "up 2.1%" is accepted for a true value of 2.145.
_EPSILON = 1e-9

# Dates are prose, and an ISO one reads as arithmetic if left in place:
# "2026-08-14" extracts as 2026, -8 and -14. Stripped first, and to a different
# placeholder than labels, so a date never reads as a 52-week horizon.
_DATE_PATTERNS = [
    r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
    r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,?\s+\d{4})?\b",
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?(?:,?\s+\d{4})?\b",
]

# Phrases where a digit is part of a label, not a claim. Stripped before any
# number is extracted, otherwise "the 52-week high" reports 52 as unverified.
# This is the tuning surface: a new stock label here means a false positive.
_LABEL_PATTERNS = [
    r"\b52[-\s]?(?:week|wk|w)\b",
    r"\b20[-\s]?(?:day|d)\b",
    r"\b50[-\s]?(?:day|d)\b",
    r"\b200[-\s]?(?:day|d|sma)\b",
    r"\b(?:2|5|10|30)[-\s]?(?:year|yr|y)\b",
    r"\b12[-\s]?month\b",
    r"\bS&P\s*500\b",
    r"\bNasdaq\s*100\b",
    r"\bRussell\s*2000\b",
    r"\bDow\s*30\b",
    r"\bVIX\b",
    r"\bQ[1-4]\b",
]

_NUMBER_RE = re.compile(
    r"(?P<sign>[+-])?\$?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
)

_RISE_WORDS = {
    "rose", "gained", "advanced", "climbed", "rallied", "jumped", "surged",
    "added", "up", "higher", "rising", "outperformed", "led",
}
_FALL_WORDS = {
    "fell", "dropped", "declined", "slipped", "lost", "sank", "tumbled",
    "down", "lower", "falling", "underperformed", "lagged", "retreated",
}

_BEST_PHRASES = [
    "top gainer", "best performer", "best-performing", "biggest gainer",
    "top performer", "biggest winner", "strongest performer", "led the",
    "biggest advance",
]
_WORST_PHRASES = [
    "top loser", "worst performer", "worst-performing", "biggest loser",
    "biggest decliner", "weakest performer", "biggest laggard", "laggard",
    "biggest decline",
]


@dataclass(frozen=True)
class Violation:
    """A single failed check. `kind` groups them; `detail` is human-readable."""
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.detail}"


@dataclass
class CheckResult:
    violations: list[Violation]
    numbers_checked: int

    @property
    def ok(self) -> bool:
        return not self.violations

    def summary(self) -> str:
        if self.ok:
            return f"grounding OK ({self.numbers_checked} figures traced to source data)"
        return f"{len(self.violations)} violation(s) across {self.numbers_checked} figures"


# ── Fact collection ───────────────────────────────────────────────────────────

def collect_facts(data: dict) -> set[float]:
    """Every number the model was given, plus the derivations it may compute.

    Deliberately built from what the *prompt* contains rather than from every
    column queried: a figure is grounded only if the model could have read it.
    """
    facts: set[float] = set()

    def add(value) -> None:
        if value is None or isinstance(value, bool):
            return
        try:
            number = float(value)
        except (TypeError, ValueError):
            return
        facts.add(number)
        facts.add(abs(number))  # "fell 0.42%" states the magnitude, not the sign

    daily = data.get("daily") or []
    for row in daily:
        for key in ("close_price", "daily_return_pct", "vol_20d_pct", "position_52w_pct"):
            add(row.get(key))

    for row in data.get("performance_52w") or []:
        add(row.get("return_52w_pct"))

    sectors = data.get("sectors") or []
    for row in sectors:
        add(row.get("avg_return"))
        add(row.get("avg_vol"))

    macro = data.get("macro") or {}
    macro_values: list[float] = []
    for value in macro.values():
        add(value)
        try:
            macro_values.append(float(value))
        except (TypeError, ValueError):
            continue

    # Spreads between rates are the one derivation an analyst always writes --
    # "a real yield of X against a breakeven of Y" -- quoted either in points or
    # in basis points. Nothing else is derived, so an invented figure stays caught.
    for i, first in enumerate(macro_values):
        for second in macro_values[i + 1:]:
            spread = abs(first - second)
            facts.add(round(spread, 6))
            facts.add(round(spread * 100, 4))

    gainers = sum(1 for row in daily if (row.get("daily_return_pct") or 0) > 0)
    losers = sum(1 for row in daily if (row.get("daily_return_pct") or 0) < 0)
    for count in (len(daily), gainers, losers, len(sectors)):
        facts.add(float(count))

    return facts


# ── Number extraction ─────────────────────────────────────────────────────────

def _strip_non_claims(text: str) -> str:
    """Blank out digits that are part of a date, a name, or list numbering."""
    cleaned = re.sub(r"(?m)^\s{0,3}\d+[.)]\s", "- ", text)
    cleaned = re.sub(r"(?m)^#+\s*\d+[.)]?\s", "## ", cleaned)
    for pattern in _DATE_PATTERNS:
        cleaned = re.sub(pattern, "<date>", cleaned, flags=re.IGNORECASE)
    for pattern in _LABEL_PATTERNS:
        cleaned = re.sub(pattern, "<label>", cleaned, flags=re.IGNORECASE)
    return cleaned


def extract_numbers(text: str) -> list[tuple[float, int, str]]:
    """Return (value, decimal places as written, raw text) for each figure."""
    found: list[tuple[float, int, str]] = []
    for match in _NUMBER_RE.finditer(_strip_non_claims(text)):
        raw_number = match.group("num")
        value = float(raw_number.replace(",", ""))
        if match.group("sign") == "-":
            value = -value
        decimals = len(raw_number.split(".")[1]) if "." in raw_number else 0
        found.append((value, decimals, match.group(0)))
    return found


def _is_grounded(value: float, decimals: int, facts: set[float]) -> bool:
    """True if some fact rounds to the stated figure at the stated precision."""
    tolerance = 0.5 * (10 ** -decimals) + _EPSILON
    return any(abs(fact - value) <= tolerance for fact in facts)


def check_numbers(text: str, facts: set[float]) -> tuple[list[Violation], int]:
    violations: list[Violation] = []
    numbers = extract_numbers(text)
    for value, decimals, raw in numbers:
        # A bare year is prose, not a metric, and never appears in the data.
        if decimals == 0 and 1900 <= value <= 2100:
            continue
        if not _is_grounded(value, decimals, facts):
            violations.append(
                Violation("unverified_number", f"{raw!r} traces to no figure in the source data")
            )
    return violations, len(numbers)


# ── Claim checks ──────────────────────────────────────────────────────────────

_TICKER_KEYS = ("close_price", "daily_return_pct", "vol_20d_pct", "position_52w_pct")


def _own_facts(data: dict, ticker: str) -> set[float]:
    """The figures the prompt showed for one ticker, with their magnitudes."""
    values = []
    for row in data.get("daily") or []:
        if str(row.get("ticker")) == ticker:
            values += [row.get(key) for key in _TICKER_KEYS]
    for row in data.get("performance_52w") or []:
        if str(row.get("ticker")) == ticker:
            values.append(row.get("return_52w_pct"))

    facts: set[float] = set()
    for value in values:
        if value is None or isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        facts.add(number)
        facts.add(abs(number))
    return facts


def _shared_facts(data: dict) -> set[float]:
    """Figures that belong to no single ticker: sectors, macro, spreads, counts."""
    daily = data.get("daily") or []
    facts = collect_facts({**data, "daily": [], "performance_52w": []})
    gainers = sum(1 for row in daily if (row.get("daily_return_pct") or 0) > 0)
    losers = sum(1 for row in daily if (row.get("daily_return_pct") or 0) < 0)
    for count in (len(daily), gainers, losers):
        facts.add(float(count))
    return facts


def _company_words(data: dict) -> dict[str, str]:
    """Ticker -> first word of its company name, lower-cased ('NVDA' -> 'nvidia')."""
    words: dict[str, str] = {}
    for row in data.get("daily") or []:
        found = re.findall(r"[A-Za-z]+", str(row.get("company_name") or ""))
        if row.get("ticker") and found:
            words[str(row["ticker"])] = found[0].lower()
    return words


def check_attribution(text: str, data: dict) -> list[Violation]:
    """A figure in a sentence about one ticker must not be another ticker's.

    Only sentences that name exactly one ticker symbol, and no other tracked
    company by name, are checked. A figure that matches nothing at all is left
    to check_numbers, so it is reported once.
    """
    daily = data.get("daily") or []
    known = {str(r["ticker"]) for r in daily if r.get("ticker")}
    if not known:
        return []

    pooled = collect_facts(data)
    shared = _shared_facts(data)
    company_words = _company_words(data)

    violations: list[Violation] = []
    for sentence in _sentences(text):
        mentioned = _tickers_in(sentence, known)
        if len(mentioned) != 1:
            continue
        ticker = mentioned[0]
        words = _words(sentence)
        if any(word in words for other, word in company_words.items() if other != ticker):
            continue

        allowed = _own_facts(data, ticker) | shared
        for value, decimals, raw in extract_numbers(sentence):
            if decimals == 0 and 1900 <= value <= 2100:
                continue
            if _is_grounded(value, decimals, pooled) and not _is_grounded(value, decimals, allowed):
                violations.append(Violation(
                    "misattributed_number",
                    f"{raw!r} is not one of {ticker}'s figures: {sentence[:120]!r}",
                ))
    return violations


def _sentences(text: str) -> list[str]:
    plain = re.sub(r"[*_`#>]", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", plain) if s.strip()]


def _tickers_in(sentence: str, known: set[str]) -> list[str]:
    return [t for t in known if re.search(rf"\b{re.escape(t)}\b", sentence)]


def _words(sentence: str) -> set[str]:
    return set(re.findall(r"[a-z]+", sentence.lower()))


def check_superlatives(text: str, data: dict) -> list[Violation]:
    """A named best/worst performer must actually be the extreme."""
    daily = [r for r in (data.get("daily") or []) if r.get("daily_return_pct") is not None]
    perf = [r for r in (data.get("performance_52w") or []) if r.get("return_52w_pct") is not None]
    if not daily:
        return []

    known = {str(r["ticker"]) for r in daily if r.get("ticker")}
    best_day = max(daily, key=lambda r: r["daily_return_pct"])["ticker"]
    worst_day = min(daily, key=lambda r: r["daily_return_pct"])["ticker"]
    best_year = max(perf, key=lambda r: r["return_52w_pct"])["ticker"] if perf else None
    worst_year = min(perf, key=lambda r: r["return_52w_pct"])["ticker"] if perf else None

    violations: list[Violation] = []
    for sentence in _sentences(text):
        lowered = sentence.lower()
        mentioned = _tickers_in(sentence, known)
        if not mentioned:
            continue
        # "<label>" is what a 52-week/12-month phrase was replaced with, so the
        # horizon survives label stripping.
        yearly = "<label>" in _strip_non_claims(sentence).lower() or "year" in lowered

        for phrases, daily_pick, yearly_pick, name in (
            (_BEST_PHRASES, best_day, best_year, "best"),
            (_WORST_PHRASES, worst_day, worst_year, "worst"),
        ):
            if not any(p in lowered for p in phrases):
                continue
            expected = yearly_pick if (yearly and yearly_pick) else daily_pick
            if expected and expected not in mentioned:
                horizon = "52-week" if (yearly and yearly_pick) else "daily"
                violations.append(Violation(
                    "wrong_superlative",
                    f"names {'/'.join(mentioned)} as the {horizon} {name} performer, "
                    f"but the data says {expected}: {sentence[:120]!r}",
                ))
    return violations


def check_directions(text: str, data: dict) -> list[Violation]:
    """A ticker described as rising must have risen.

    Only sentences naming exactly one ticker with one direction are checked --
    "X rose while Y fell" is common and splitting clauses reliably is not worth
    the false positives it would cost.
    """
    daily = [r for r in (data.get("daily") or []) if r.get("daily_return_pct") is not None]
    returns = {str(r["ticker"]): float(r["daily_return_pct"]) for r in daily if r.get("ticker")}
    known = set(returns)

    violations: list[Violation] = []
    for sentence in _sentences(text):
        mentioned = _tickers_in(sentence, known)
        if len(mentioned) != 1:
            continue
        words = _words(sentence)
        rising, falling = words & _RISE_WORDS, words & _FALL_WORDS
        if bool(rising) == bool(falling):
            continue

        ticker = mentioned[0]
        actual = returns[ticker]
        if rising and actual < 0:
            violations.append(Violation(
                "wrong_direction",
                f"describes {ticker} as rising, but it returned {actual:+.3f}%: {sentence[:120]!r}",
            ))
        elif falling and actual > 0:
            violations.append(Violation(
                "wrong_direction",
                f"describes {ticker} as falling, but it returned {actual:+.3f}%: {sentence[:120]!r}",
            ))
    return violations


def check_briefing(text: str, data: dict) -> CheckResult:
    """Run every check against the generated briefing."""
    if not text or not text.strip():
        return CheckResult(
            violations=[Violation("empty_briefing", "the model returned no text")],
            numbers_checked=0,
        )
    number_violations, counted = check_numbers(text, collect_facts(data))
    return CheckResult(
        violations=(
            number_violations
            + check_attribution(text, data)
            + check_superlatives(text, data)
            + check_directions(text, data)
        ),
        numbers_checked=counted,
    )


def format_violations(violations: list[Violation]) -> str:
    """Render violations as prompt feedback for a correction attempt."""
    return "\n".join(f"- {v}" for v in violations)


# ── Deterministic fallback ────────────────────────────────────────────────────

def render_fallback_briefing(data: dict) -> str:
    """A briefing built straight from the data, correct by construction.

    Published when the model's output cannot be verified, so the dashboard stays
    current without carrying a claim the data does not support.
    """
    daily = [r for r in (data.get("daily") or []) if r.get("daily_return_pct") is not None]
    macro = data.get("macro") or {}
    sectors = data.get("sectors") or []

    if not daily:
        return "## Market Briefing\n\nNo trading data available for this date.\n"

    best = max(daily, key=lambda r: r["daily_return_pct"])
    worst = min(daily, key=lambda r: r["daily_return_pct"])
    gainers = sum(1 for r in daily if r["daily_return_pct"] > 0)
    losers = sum(1 for r in daily if r["daily_return_pct"] < 0)

    lines = [
        "## Market Overview",
        "",
        f"{gainers} of {len(daily)} tracked names advanced and {losers} declined "
        f"on {data.get('as_of_date', 'the latest session')}.",
        "",
        "## Today's Movers",
        "",
        f"- **{best['ticker']}** ({best.get('company_name', '')}) "
        f"{best['daily_return_pct']:+.3f}%, closing at ${best['close_price']}",
        f"- **{worst['ticker']}** ({worst.get('company_name', '')}) "
        f"{worst['daily_return_pct']:+.3f}%, closing at ${worst['close_price']}",
    ]

    if sectors:
        leader = sectors[0]
        lines += [
            "",
            "## Sector Snapshot",
            "",
            f"{leader['sector']} led with an average return of {leader['avg_return']:+.3f}%.",
        ]

    if macro:
        lines += [
            "",
            "## Macro Environment",
            "",
            f"- Fed Funds Rate: {macro.get('fed_funds_rate')}%",
            f"- 10Y Treasury Yield: {macro.get('treasury_yield_10y')}%",
            f"- Real Yield (10Y): {macro.get('real_yield_10y')}%",
            f"- Breakeven Inflation (10Y): {macro.get('breakeven_inflation_10y')}%",
            f"- Unemployment Rate: {macro.get('unemployment_rate')}%",
        ]

    lines += [
        "",
        "---",
        "",
        "*This briefing was generated directly from the warehouse. The model-written "
        "version failed its grounding checks and was withheld.*",
    ]
    return "\n".join(lines)

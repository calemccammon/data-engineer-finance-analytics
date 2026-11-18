"""Unit tests for the briefing grounding checks.

No warehouse, no API key, no network -- the checks take a metrics dict and a
string, which is the whole point of keeping them separate from generation.
"""

import pytest

from briefing_checks import (
    check_attribution,
    check_briefing,
    check_directions,
    check_numbers,
    check_superlatives,
    collect_facts,
    extract_numbers,
    render_fallback_briefing,
)


@pytest.fixture
def data():
    """A small but realistically shaped metrics dict."""
    return {
        "as_of_date": "2026-08-14",
        "daily": [
            {"ticker": "NVDA", "company_name": "NVIDIA", "sector": "Technology",
             "close_price": 178.32, "daily_return_pct": 2.145,
             "vol_20d_pct": 41.2, "position_52w_pct": 87.4},
            {"ticker": "AAPL", "company_name": "Apple", "sector": "Technology",
             "close_price": 231.08, "daily_return_pct": 0.512,
             "vol_20d_pct": 22.7, "position_52w_pct": 71.0},
            {"ticker": "XOM", "company_name": "Exxon Mobil", "sector": "Energy",
             "close_price": 118.44, "daily_return_pct": -1.230,
             "vol_20d_pct": 18.9, "position_52w_pct": 44.3},
        ],
        "performance_52w": [
            {"ticker": "NVDA", "company_name": "NVIDIA", "return_52w_pct": 64.3},
            {"ticker": "AAPL", "company_name": "Apple", "return_52w_pct": 12.8},
            {"ticker": "XOM", "company_name": "Exxon Mobil", "return_52w_pct": -7.5},
        ],
        "macro": {
            "fed_funds_rate": 4.50, "treasury_yield_10y": 4.25,
            "real_yield_10y": 1.95, "unemployment_rate": 4.1,
            "breakeven_inflation_10y": 2.30, "gdp_growth_rate": 2.8,
        },
        "sectors": [
            {"sector": "Technology", "avg_return": 1.329, "avg_vol": 31.9},
            {"sector": "Energy", "avg_return": -1.230, "avg_vol": 18.9},
        ],
    }


# ── Fact collection ───────────────────────────────────────────────────────────

def test_collects_every_figure_the_prompt_contains(data):
    facts = collect_facts(data)
    assert 178.32 in facts        # close price
    assert 2.145 in facts         # daily return
    assert 41.2 in facts          # 20-day volatility
    assert 64.3 in facts          # 52-week return
    assert 4.50 in facts          # macro rate
    assert 1.329 in facts         # sector average


def test_collects_magnitudes_so_a_loss_can_be_stated_without_its_sign(data):
    facts = collect_facts(data)
    assert -1.230 in facts and 1.230 in facts


def test_collects_counts_used_in_the_prompt(data):
    facts = collect_facts(data)
    assert 3.0 in facts   # three tickers
    assert 2.0 in facts   # two gainers
    assert 1.0 in facts   # one loser


def test_collects_rate_spreads_in_points_and_basis_points(data):
    facts = collect_facts(data)
    # 4.25 ten-year less 2.30 breakeven
    assert any(abs(f - 1.95) < 1e-9 for f in facts)
    assert any(abs(f - 195.0) < 1e-9 for f in facts)


def test_ignores_columns_the_prompt_never_shows(data):
    """pct_vs_200sma is queried but not sent, so citing it is not grounded."""
    data["daily"][0]["pct_vs_200sma"] = 0.913
    assert 0.913 not in collect_facts(data)


# ── Number extraction ─────────────────────────────────────────────────────────

def test_extracts_values_with_their_written_precision():
    assert extract_numbers("up 2.1% to $178.32")[:2] == [(2.1, 1, "2.1"), (178.32, 2, "$178.32")]


def test_handles_signs_and_thousands_separators():
    values = [v for v, _, _ in extract_numbers("-1.23% on volume of 1,240,000")]
    assert values == [-1.23, 1240000.0]


def test_ignores_digits_that_are_part_of_a_label():
    """'52-week high' and '10-year yield' are names, not claims."""
    assert extract_numbers("the 52-week high and the 10-year yield and the 200-day SMA") == []


def test_ignores_markdown_list_numbering():
    assert extract_numbers("1. Market Overview\n2. Movers") == []


def test_ignores_dates():
    """An ISO date otherwise extracts as 2026, -8 and -14 -- two of them bogus."""
    assert extract_numbers("As of 2026-08-14 the session closed.") == []
    assert extract_numbers("On August 14, 2026 markets rallied.") == []
    assert extract_numbers("Trading on 08/14/2026 was thin.") == []


def test_a_date_is_not_mistaken_for_a_52_week_horizon(data):
    """Dates and labels use different placeholders, so a date in a sentence
    cannot flip a daily superlative into a 52-week one."""
    assert check_superlatives("On 2026-08-14, NVDA was the top gainer.", data) == []


# ── Numeric grounding ─────────────────────────────────────────────────────────

def test_accepts_a_figure_rounded_to_fewer_decimals(data):
    """The model writes 2.1%; the source says 2.145%."""
    violations, counted = check_numbers("NVDA gained 2.1% today.", collect_facts(data))
    assert violations == []
    assert counted == 1


def test_accepts_a_figure_rounded_up_or_down(data):
    facts = collect_facts(data)
    assert check_numbers("NVDA rose 2%.", facts)[0] == []
    assert check_numbers("volatility near 41%.", facts)[0] == []


def test_flags_a_fabricated_figure(data):
    violations, _ = check_numbers("NVDA gained 7.8% today.", collect_facts(data))
    assert len(violations) == 1
    assert violations[0].kind == "unverified_number"
    assert "7.8" in violations[0].detail


def test_ignores_bare_years(data):
    assert check_numbers("Since 2024 the trend has held.", collect_facts(data))[0] == []


# ── Superlatives ──────────────────────────────────────────────────────────────

def test_accepts_the_correct_top_gainer(data):
    assert check_superlatives("NVDA was the top gainer on the day.", data) == []


def test_flags_the_wrong_top_gainer(data):
    violations = check_superlatives("AAPL was the top gainer on the day.", data)
    assert len(violations) == 1
    assert violations[0].kind == "wrong_superlative"
    assert "NVDA" in violations[0].detail


def test_flags_the_wrong_worst_performer(data):
    violations = check_superlatives("AAPL was the biggest decliner.", data)
    assert len(violations) == 1
    assert "XOM" in violations[0].detail


def test_reads_a_52_week_superlative_against_the_52_week_data(data):
    """Make AAPL the worst over 52 weeks while XOM stays the worst on the day,
    so the two horizons give different answers."""
    data["performance_52w"][1]["return_52w_pct"] = -20.0
    assert check_superlatives("Over the 52-week period AAPL was the worst performer.", data) == []

    violations = check_superlatives("Over the 52-week period XOM was the worst performer.", data)
    assert len(violations) == 1
    assert "52-week" in violations[0].detail and "AAPL" in violations[0].detail

    assert check_superlatives("XOM was the worst performer on the day.", data) == []


# ── Attribution ───────────────────────────────────────────────────────────────

def test_accepts_a_tickers_own_figures(data):
    text = "NVDA rose 2.145% to $178.32, with volatility at 41.2% and a 64.3% gain over the year."
    assert check_attribution(text, data) == []


def test_flags_another_tickers_figure(data):
    """$178.32 is NVDA's close, so it is grounded but does not belong to AAPL."""
    violations = check_attribution("AAPL closed at $178.32.", data)
    assert len(violations) == 1
    assert violations[0].kind == "misattributed_number"
    assert "AAPL" in violations[0].detail and "178.32" in violations[0].detail


def test_attribution_accepts_market_wide_figures_beside_a_ticker(data):
    text = "NVDA led as 2 of 3 names advanced, with the Fed funds rate at 4.5% and Technology up 1.329%."
    assert check_attribution(text, data) == []


def test_attribution_skips_sentences_naming_two_tickers(data):
    assert check_attribution("NVDA rose 2.145% while XOM fell 1.23%.", data) == []


def test_attribution_skips_sentences_naming_another_company(data):
    """The 1.23% belongs to Exxon, which is named without its ticker."""
    assert check_attribution("NVDA was the top gainer while Exxon fell 1.23%.", data) == []


def test_attribution_leaves_ungrounded_figures_to_the_numeric_check(data):
    assert check_attribution("NVDA gained 7.8% today.", data) == []
    result = check_briefing("NVDA gained 7.8% today.", data)
    assert [v.kind for v in result.violations] == ["unverified_number"]


def test_a_misattributed_figure_fails_the_briefing(data):
    result = check_briefing("AAPL closed at $178.32.", data)
    assert not result.ok
    assert [v.kind for v in result.violations] == ["misattributed_number"]


# ── Direction ─────────────────────────────────────────────────────────────────

def test_accepts_a_correct_direction(data):
    assert check_directions("NVDA rose on heavy volume.", data) == []


def test_flags_an_inverted_direction(data):
    violations = check_directions("XOM climbed on the session.", data)
    assert len(violations) == 1
    assert violations[0].kind == "wrong_direction"
    assert "XOM" in violations[0].detail


def test_skips_sentences_naming_more_than_one_ticker(data):
    """'NVDA rose while XOM fell' is correct but not worth parsing clauses for."""
    assert check_directions("NVDA rose while XOM fell.", data) == []


def test_skips_sentences_with_mixed_direction_words(data):
    assert check_directions("NVDA gave up earlier losses to finish higher.", data) == []


# ── End to end ────────────────────────────────────────────────────────────────

def test_a_faithful_briefing_passes(data):
    briefing = (
        "## Market Overview\n\n"
        "2 of 3 tracked names advanced. NVDA was the top gainer, rising 2.145% "
        "to close at $178.32, while XOM fell 1.23% to $118.44.\n\n"
        "## Macro Environment\n\n"
        "The Fed funds rate stands at 4.5% with the 10-year yield at 4.25%."
    )
    result = check_briefing(briefing, data)
    assert result.ok, [str(v) for v in result.violations]
    assert result.numbers_checked > 0


def test_a_briefing_with_a_fabricated_number_and_a_wrong_leader_fails(data):
    briefing = "AAPL was the top gainer, surging 9.9% on the session."
    result = check_briefing(briefing, data)
    kinds = {v.kind for v in result.violations}
    assert "unverified_number" in kinds
    assert "wrong_superlative" in kinds
    assert not result.ok


def test_an_empty_response_fails(data):
    """A blank or missing response must not be published as verified."""
    for text in ("", "   \n", None):
        result = check_briefing(text, data)
        assert not result.ok
        assert result.violations[0].kind == "empty_briefing"


def test_summary_reads_differently_either_way(data):
    assert "OK" in check_briefing("NVDA rose 2.145%.", data).summary()
    assert "violation" in check_briefing("NVDA rose 99.9%.", data).summary()


# ── Fallback ──────────────────────────────────────────────────────────────────

def test_fallback_briefing_is_itself_grounded(data):
    """The fallback must pass the same checks it exists to satisfy."""
    result = check_briefing(render_fallback_briefing(data), data)
    assert result.ok, [str(v) for v in result.violations]


def test_fallback_names_the_real_movers(data):
    text = render_fallback_briefing(data)
    assert "NVDA" in text and "XOM" in text
    assert "withheld" in text


def test_fallback_survives_an_empty_dataset():
    assert "No trading data" in render_fallback_briefing({"daily": [], "as_of_date": "2026-08-14"})

"""
Static mock data for Analyst Arena V1.
Single ticker: NVDA.
"""

NVDA_PACKET = {
    "ticker": "NVDA",
    "name": "NVIDIA Corporation",
    "overview": (
        "NVIDIA designs and manufactures GPUs for gaming, professional visualization, "
        "data center, and automotive markets. The company has pivoted heavily into AI "
        "compute, with data center revenue now the dominant segment."
    ),
    "business_model": (
        "Four segments: Data Center (~80% of revenue), Gaming (~15%), Professional "
        "Visualization (~3%), Automotive (~2%). Data Center growth driven by AI training "
        "and inference demand. Recurring software revenue via CUDA ecosystem and AI Enterprise."
    ),
    "key_metrics": {
        "revenue_ttm": 60.9,  # $B
        "revenue_growth_yoy": 0.22,
        "gross_margin": 0.73,
        "operating_margin": 0.55,
        "net_margin": 0.49,
        "fcf_ttm": 28.2,  # $B
        "capex_ttm": 2.1,  # $B
    },
    "valuation_snapshot": {
        "price": 142.50,
        "market_cap": 3_520,  # $B
        "ev": 3_480,
        "pe_ttm": 72,
        "ev_revenue": 57,
        "ev_ebitda": 65,
        "fcf_yield": 0.008,
    },
}

NVDA_EARNINGS_PACKET = {
    "ticker": "NVDA",
    "period": "Q4 FY25",
    "release_date": "2025-02-26",
    "headline": "Record Data Center revenue; guidance above consensus",
    "results": {
        "revenue": 22.1,  # $B, +22% yoy
        "data_center_revenue": 18.4,  # $B, +27% yoy
        "gaming_revenue": 2.9,  # $B, flat yoy
        "gross_margin": 0.76,  # up 180bp yoy
        "operating_income": 14.8,  # $B
        "eps_diluted": 0.82,  # +26% yoy
    },
    "guidance": {
        "q1_fy26_revenue": "~$24.0B (midpoint)",
        "fy26_revenue_growth": "low-to-mid twenties %",
    },
    "management_commentary": (
        "Hopper demand remains strong; Blackwell ramp on track for Q2. "
        "Operating leverage improving as software mix increases."
    ),
}

NVDA_NEWS = [
    {
        "date": "2025-03-15",
        "headline": "NVIDIA announces new AI chip partnership with major cloud provider",
        "summary": "Multi-year supply agreement for Blackwell GPUs; terms not disclosed.",
    },
    {
        "date": "2025-03-10",
        "headline": "SEC filing: Insider selling by executives",
        "summary": "Form 4 filings show routine 10b5-1 plan sales; no material change to ownership.",
    },
    {
        "date": "2025-03-05",
        "headline": "Data center demand normalization concerns from analyst note",
        "summary": "One sell-side firm flags risk of order pull-forward and inventory build.",
    },
]

NVDA_FINANCIALS = {
    "income_statement": {
        "revenue": 60.9,
        "cogs": 16.4,
        "gross_profit": 44.5,
        "operating_expenses": 7.2,
        "operating_income": 37.3,
        "net_income": 29.8,
        "eps_diluted": 1.21,
    },
    "balance_sheet": {
        "cash": 31.2,
        "total_assets": 77.1,
        "total_debt": 9.7,
        "shareholders_equity": 54.2,
    },
    "cash_flow": {
        "operating_cf": 32.1,
        "capex": -2.1,
        "fcf": 30.0,
        "buybacks": -15.2,
    },
}

NVDA_PRICE_CHART = {
    "ticker": "NVDA",
    "timeframe": "1Y",
    "summary": (
        "1Y: +180%. Strong uptrend with volatility. Key levels: support ~$120 (Aug 2024), "
        "resistance ~$150. 50-day MA at $138. Volume elevated on earnings and product announcements."
    ),
    "high_52w": 150.20,
    "low_52w": 68.50,
    "current": 142.50,
}

# Supported ticker for V1
SUPPORTED_TICKERS = ["NVDA"]


def get_company_packet(ticker: str) -> dict | None:
    """Return company packet for ticker. V1: NVDA only."""
    if ticker.upper() != "NVDA":
        return None
    return NVDA_PACKET.copy()


def get_earnings_packet(ticker: str) -> dict | None:
    """Return earnings packet for ticker. V1: NVDA only."""
    if ticker.upper() != "NVDA":
        return None
    return NVDA_EARNINGS_PACKET.copy()


def get_recent_news(ticker: str) -> list[dict]:
    """Return recent news for ticker. V1: static mock."""
    if ticker.upper() != "NVDA":
        return []
    return [n.copy() for n in NVDA_NEWS]


def get_financials(ticker: str, period: str = "TTM") -> dict | None:
    """Return financials for ticker. V1: static mock, period ignored."""
    if ticker.upper() != "NVDA":
        return None
    return {k: v.copy() for k, v in NVDA_FINANCIALS.items()}


def get_price_chart(ticker: str, timeframe: str = "1Y") -> dict | None:
    """Return chart summary for ticker. V1: text summary, not image."""
    if ticker.upper() != "NVDA":
        return None
    out = NVDA_PRICE_CHART.copy()
    out["timeframe"] = timeframe
    return out

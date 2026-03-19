"""
Scoring rubric for Analyst Arena.
Base: 100 points. Penalties applied separately.
"""

from dataclasses import dataclass, field


@dataclass
class CategoryScore:
    """Single category score with max points."""
    name: str
    points: float
    max_points: float
    notes: str = ""


@dataclass
class Penalty:
    """Applied penalty."""
    name: str
    points: float  # negative
    notes: str = ""


@dataclass
class ThesisScore:
    """Full thesis score result."""
    total_score: float = 0.0
    hallucination_count: int = 0
    rebuttal_score: float = 0.0
    categories: list[CategoryScore] = field(default_factory=list)
    penalties: list[Penalty] = field(default_factory=list)

    @property
    def display_metrics(self) -> dict:
        """Three display metrics for UI."""
        return {
            "total_score": round(self.total_score, 1),
            "hallucination_count": self.hallucination_count,
            "rebuttal_score": round(self.rebuttal_score, 1),
        }


# Category definitions (max points)
CATEGORIES = [
    ("thesis_quality", 15),
    ("evidence_grounding", 20),
    ("financial_reasoning", 20),
    ("valuation_rigor", 15),
    ("risk_recognition", 10),
    ("rebuttal_strength", 15),
    ("calibration", 5),
]

PENALTIES = [
    ("hallucination", -15),
    ("internal_inconsistency", -10),
    ("genericness", -5),
]


def score_thesis(
    thesis_text: str,
    rebuttal_text: str | None = None,
    packet_facts: set[str] | None = None,
) -> ThesisScore:
    """
    V1: Deterministic placeholder scoring.
    Returns structured score. In production, replace with LLM judge or trained scorer.
    """
    result = ThesisScore()
    packet_facts = packet_facts or set()

    # V1: Simple heuristic scoring for demo
    # Thesis quality: length + stance clarity
    has_stance = any(w in thesis_text.lower() for w in ["bull", "bear", "long", "short", "buy", "sell"])
    thesis_len = len(thesis_text.split())
    result.categories.append(CategoryScore(
        "thesis_quality",
        min(15, 5 + (10 if has_stance else 0) + min(5, thesis_len // 50)),
        15,
        "V1 heuristic",
    ))

    # Evidence grounding: keyword overlap with packet
    evidence_score = 10.0 if thesis_len > 100 else 5.0
    result.categories.append(CategoryScore("evidence_grounding", evidence_score, 20, "V1 heuristic"))

    # Financial reasoning
    fin_terms = ["margin", "revenue", "cash", "multiple", "valuation", "eps", "growth", "leverage"]
    fin_count = sum(1 for t in fin_terms if t in thesis_text.lower())
    result.categories.append(CategoryScore(
        "financial_reasoning",
        min(20, 5 + fin_count * 2),
        20,
        "V1 heuristic",
    ))

    # Valuation rigor
    val_terms = ["multiple", "valuation", "price", "target", "ev", "pe", "fcf"]
    val_count = sum(1 for t in val_terms if t in thesis_text.lower())
    result.categories.append(CategoryScore(
        "valuation_rigor",
        min(15, 3 + val_count * 2),
        15,
        "V1 heuristic",
    ))

    # Risk recognition
    risk_terms = ["risk", "bear", "downside", "uncertainty", "could", "if", "however"]
    risk_count = sum(1 for t in risk_terms if t in thesis_text.lower())
    result.categories.append(CategoryScore(
        "risk_recognition",
        min(10, risk_count * 2),
        10,
        "V1 heuristic",
    ))

    # Rebuttal strength
    if rebuttal_text:
        rebut_terms = ["however", "but", "opponent", "argument", "assumption", "wrong", "incorrect"]
        rebut_count = sum(1 for t in rebut_terms if t in rebuttal_text.lower())
        rebut_score = min(15, 3 + rebut_count * 2)
    else:
        rebut_score = 0.0
    result.rebuttal_score = rebut_score
    result.categories.append(CategoryScore("rebuttal_strength", rebut_score, 15, "V1 heuristic"))

    # Calibration
    result.categories.append(CategoryScore("calibration", 3.0, 5, "V1 default"))

    # Total from categories
    result.total_score = sum(c.points for c in result.categories)

    # V1: No penalties by default (deterministic demo)
    result.hallucination_count = 0

    return result


def score_pm_decision(
    thesis_a_text: str,
    thesis_b_text: str,
    winner: str,
    rationale: str,
) -> dict:
    """
    Score the PM/judge decision round.
    V1: Returns structured result for display.
    """
    return {
        "winner": winner,
        "rationale": rationale,
        "thesis_a_preview": thesis_a_text[:200] + "..." if len(thesis_a_text) > 200 else thesis_a_text,
        "thesis_b_preview": thesis_b_text[:200] + "..." if len(thesis_b_text) > 200 else thesis_b_text,
    }

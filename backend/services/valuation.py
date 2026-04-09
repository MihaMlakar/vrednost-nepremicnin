"""Valuation logic: Truth Score, Negotiation Lever, confidence."""

from typing import Optional

from backend.models.schemas import (
    GURSTransaction,
    ListingData,
    TrendPoint,
    ValuationReport,
)


def _calc_score(comps, asking_price_per_m2):
    """Calculate truth score and confidence from a set of comps."""
    if not comps:
        return 0.0, 0.0, "low"

    avg_gurs = sum(c.price_per_m2 for c in comps) / len(comps)
    truth_score = round(((asking_price_per_m2 - avg_gurs) / avg_gurs) * 100, 1)

    if len(comps) >= 8:
        confidence = "high"
    elif len(comps) >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return truth_score, avg_gurs, confidence


def calculate_valuation(
    listing: ListingData,
    comps: list,
    trend: list,
    cached: bool = False,
    wider_comps: Optional[list] = None,
    wider_neighborhoods: Optional[list] = None,
) -> ValuationReport:
    """
    Calculate the full valuation report with neighborhood and wider area scores.
    """
    asking_price_per_m2 = listing.price_eur / listing.size_m2

    # Neighborhood score (primary)
    truth_score, avg_gurs, confidence = _calc_score(comps, asking_price_per_m2)
    negotiation_lever = _generate_lever(
        truth_score, listing.neighborhood, len(comps), avg_gurs, asking_price_per_m2
    )

    # Wider area score (secondary)
    wider_truth_score = None
    wider_negotiation_lever = None
    wider_avg_gurs = None
    wider_confidence = None
    wider_num_comps = None

    if wider_comps is not None:
        wider_truth_score, wider_avg_gurs_val, wider_confidence = _calc_score(
            wider_comps, asking_price_per_m2
        )
        wider_avg_gurs = round(wider_avg_gurs_val, 0) if wider_avg_gurs_val else 0
        wider_num_comps = len(wider_comps)
        wider_negotiation_lever = _generate_wider_lever(
            wider_truth_score, wider_num_comps, wider_avg_gurs_val, asking_price_per_m2
        )

    return ValuationReport(
        listing=listing,
        truth_score=truth_score,
        negotiation_lever=negotiation_lever,
        avg_gurs_price_per_m2=round(avg_gurs, 0),
        asking_price_per_m2=round(asking_price_per_m2, 0),
        num_comps=len(comps),
        confidence=confidence,
        comps=comps,
        trend=trend,
        cached=cached,
        wider_truth_score=wider_truth_score,
        wider_negotiation_lever=wider_negotiation_lever,
        wider_avg_gurs_price_per_m2=wider_avg_gurs,
        wider_num_comps=wider_num_comps,
        wider_confidence=wider_confidence,
        wider_comps=wider_comps,
        wider_neighborhoods=wider_neighborhoods,
    )


def _generate_lever(
    truth_score: float,
    neighborhood: str,
    num_comps: int,
    avg_gurs: float,
    asking: float,
) -> str:
    """Generate negotiation lever text for neighborhood score."""
    abs_score = abs(truth_score)

    if num_comps == 0:
        return f"Premalo podatkov o transakcijah za {neighborhood} za določitev poštene vrednosti."

    if truth_score > 15:
        return (
            f"Ta nepremičnina je {abs_score:.0f}% nad povprečjem transakcij za "
            f"{neighborhood}. Na podlagi {num_comps} nedavnih prodaj je povprečna zaključna "
            f"cena {avg_gurs:,.0f} EUR/m² v primerjavi z oglaševano ceno {asking:,.0f} EUR/m². "
            f"Močna pogajalska pozicija."
        )
    elif truth_score > 5:
        return (
            f"Ta nepremičnina je {abs_score:.0f}% nad povprečjem transakcij za "
            f"{neighborhood}. Na podlagi {num_comps} nedavnih prodaj pri {avg_gurs:,.0f} EUR/m² "
            f"obstaja prostor za pogajanje."
        )
    elif truth_score > -5:
        return (
            f"Ta nepremičnina je v okviru povprečja transakcij za {neighborhood}. "
            f"Na podlagi {num_comps} nedavnih prodaj pri {avg_gurs:,.0f} EUR/m² "
            f"se oglaševana cena {asking:,.0f} EUR/m² zdi poštena."
        )
    elif truth_score > -15:
        return (
            f"Ta nepremičnina je {abs_score:.0f}% pod povprečjem transakcij za "
            f"{neighborhood}. Pri {asking:,.0f} EUR/m² v primerjavi s povprečjem {avg_gurs:,.0f} EUR/m² "
            f"gre za ugoden nakup."
        )
    else:
        return (
            f"Ta nepremičnina je {abs_score:.0f}% pod povprečjem transakcij za "
            f"{neighborhood}. Pri {asking:,.0f} EUR/m² v primerjavi s povprečjem {avg_gurs:,.0f} EUR/m² "
            f"je cena izrazito pod tržno vrednostjo. Preverite zakaj."
        )


def _generate_wider_lever(
    truth_score: float,
    num_comps: int,
    avg_gurs: float,
    asking: float,
) -> str:
    """Generate negotiation lever text for wider area score."""
    abs_score = abs(truth_score)

    if num_comps == 0:
        return "Premalo podatkov o transakcijah v širšem območju za primerjavo."

    if truth_score > 5:
        return (
            f"V primerjavi s širšim območjem ({num_comps} prodaj, "
            f"povprečje {avg_gurs:,.0f} EUR/m²) je oglaševana cena "
            f"{abs_score:.0f}% nad povprečjem."
        )
    elif truth_score > -5:
        return (
            f"V primerjavi s širšim območjem ({num_comps} prodaj, "
            f"povprečje {avg_gurs:,.0f} EUR/m²) je oglaševana cena "
            f"v okviru povprečja."
        )
    else:
        return (
            f"V primerjavi s širšim območjem ({num_comps} prodaj, "
            f"povprečje {avg_gurs:,.0f} EUR/m²) je oglaševana cena "
            f"{abs_score:.0f}% pod povprečjem."
        )

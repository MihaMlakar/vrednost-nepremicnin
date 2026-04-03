"""Valuation logic: Truth Score, Negotiation Lever, confidence."""

from backend.models.schemas import (
    GURSTransaction,
    ListingData,
    TrendPoint,
    ValuationReport,
)


def calculate_valuation(
    listing: ListingData,
    comps: list[GURSTransaction],
    trend: list[TrendPoint],
    cached: bool = False,
) -> ValuationReport:
    """
    Calculate the full valuation report from listing data and comparable transactions.

    Truth Score = ((asking_price_per_m2 - avg_gurs_price_per_m2) / avg_gurs_price_per_m2) * 100
    Positive = overpriced, Negative = underpriced
    """
    asking_price_per_m2 = listing.price_eur / listing.size_m2

    # Calculate average from comps
    if not comps:
        avg_gurs = 0.0
        truth_score = 0.0
    else:
        avg_gurs = sum(c.price_per_m2 for c in comps) / len(comps)
        truth_score = round(((asking_price_per_m2 - avg_gurs) / avg_gurs) * 100, 1)

    # Confidence based on number of comps
    if len(comps) >= 8:
        confidence = "high"
    elif len(comps) >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    # Generate negotiation lever text
    negotiation_lever = _generate_lever(
        truth_score, listing.neighborhood, len(comps), avg_gurs, asking_price_per_m2
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
    )


def _generate_lever(
    truth_score: float,
    neighborhood: str,
    num_comps: int,
    avg_gurs: float,
    asking: float,
) -> str:
    """Generate a human-readable negotiation lever string."""
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

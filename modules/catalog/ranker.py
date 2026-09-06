"""
Cult Ranking Engine for Science Fiction Literature.
Calculates the multidimensional 'Cult Index' for works and authors.
"""

from typing import List, Dict, Any

AWARD_WEIGHTS = {
    "hugo_win": 12.0,
    "hugo_nom": 4.0,
    "nebula_win": 11.0,
    "nebula_nom": 4.0,
    "locus_win": 9.0,
    "locus_nom": 3.0,
    "clarke_win": 9.0,
    "clarke_nom": 3.0,
    "bsfa_win": 7.0,
    "bsfa_nom": 2.5,
    "pkd_win": 8.0,
    "pkd_nom": 3.0,
    "campbell_win": 7.0,
    "seiun_win": 6.0,
    "sturgeon_win": 8.0,
    "world_fantasy_win": 8.0
}

CANON_WEIGHTS = {
    "SF Masterworks": 18.0,
    "Locus All-Time Best": 16.0,
    "NPR Top 100 SF": 14.0,
    "r/printSF Top Tier": 12.0,
    "ISFDB Top Ranked": 10.0,
    "Porges Century Canon": 15.0
}

HISTORIC_MULTIPLIERS = {
    # Early eras predating awards get a foundational boost to recognize trope-makers
    "proto_sf": 2.2,     # Pre-1926 (Shelley, Verne, Wells, Čapek, Stapledon)
    "pulp_golden": 1.6,   # 1926-1950 (Campbell era, early Asimov/Heinlein/van Vogt)
    "classic_mid": 1.2,   # 1951-1964 (Fifties boom, early Dick, Clarke)
    "new_wave": 1.0,      # 1965-1979 (Hugo & Nebula fully mature)
    "cyberpunk_80s": 1.0, # 1980-1989
    "modern": 1.0         # 1990+
}


class CultRanker:
    """Calculates scientific cult index scores for works and authors."""

    @staticmethod
    def get_era_key(year: int) -> str:
        if year < 1926:
            return "proto_sf"
        elif year <= 1950:
            return "pulp_golden"
        elif year <= 1964:
            return "classic_mid"
        elif year <= 1979:
            return "new_wave"
        elif year <= 1989:
            return "cyberpunk_80s"
        return "modern"

    @classmethod
    def calculate_work_cult_score(
        cls,
        year: int,
        awards: List[str],
        canon_inclusions: List[str],
        trope_maker: bool = False,
        community_votes: int = 100,
        avg_rating: float = 4.2
    ) -> float:
        """
        Computes Cult Score for a work. Scale typically spans 50.0 to 100.0 for cult classics.
        """
        base_score = 40.0

        # Awards component
        award_score = 0.0
        for aw in awards:
            aw_clean = aw.lower().replace(" ", "_")
            if "hugo" in aw_clean and "win" in aw_clean:
                award_score += AWARD_WEIGHTS["hugo_win"]
            elif "hugo" in aw_clean:
                award_score += AWARD_WEIGHTS["hugo_nom"]
            elif "nebula" in aw_clean and "win" in aw_clean:
                award_score += AWARD_WEIGHTS["nebula_win"]
            elif "nebula" in aw_clean:
                award_score += AWARD_WEIGHTS["nebula_nom"]
            elif "locus" in aw_clean and "win" in aw_clean:
                award_score += AWARD_WEIGHTS["locus_win"]
            elif "locus" in aw_clean:
                award_score += AWARD_WEIGHTS["locus_nom"]
            elif "clarke" in aw_clean:
                award_score += AWARD_WEIGHTS["clarke_win"]
            elif "pkd" in aw_clean or "philip k. dick" in aw_clean:
                award_score += AWARD_WEIGHTS["pkd_win"]
            elif "bsfa" in aw_clean:
                award_score += AWARD_WEIGHTS["bsfa_win"]
            else:
                award_score += 4.0

        # Canon inclusions component
        canon_score = 0.0
        for canon in canon_inclusions:
            for c_key, c_val in CANON_WEIGHTS.items():
                if c_key.lower() in canon.lower():
                    canon_score += c_val
                    break

        # Trope Maker / Historical Breakthrough
        trope_score = 15.0 if trope_maker else 0.0

        # Raw composite
        raw = base_score + award_score + canon_score + trope_score

        # Apply Era Multiplier for pre-award classics
        era = cls.get_era_key(year)
        multiplier = HISTORIC_MULTIPLIERS.get(era, 1.0)
        
        # If pre-award era had no awards, don't let it suffer
        if era in ("proto_sf", "pulp_golden") and award_score == 0:
            raw = (raw + 25.0) * multiplier
        else:
            raw = raw * (1.0 + (multiplier - 1.0) * 0.3)

        # Normalize score into 0 - 100 scale (with exceptional masterpieces approaching 98-100)
        normalized = min(99.8, round(raw * 0.72, 2))
        return max(50.0, normalized)

    @classmethod
    def calculate_author_cult_score(
        cls,
        tier: int,
        works_cult_scores: List[float],
        coined_concepts_count: int = 0
    ) -> float:
        """
        Computes Author Cult Score based on their top works, tier, and conceptual impact.
        """
        if not works_cult_scores:
            base = 65.0 if tier == 3 else (80.0 if tier == 2 else 90.0)
            return base + min(10.0, coined_concepts_count * 2.0)

        # Weighted average favoring top 3 magnum opuses
        sorted_scores = sorted(works_cult_scores, reverse=True)
        top_works = sorted_scores[:3]
        avg_top = sum(top_works) / len(top_works)

        tier_bonus = {1: 8.0, 2: 4.0, 3: 1.0}.get(tier, 0.0)
        concepts_bonus = min(7.0, coined_concepts_count * 1.5)

        final_score = min(100.0, round(avg_top * 0.90 + tier_bonus + concepts_bonus, 2))
        return final_score

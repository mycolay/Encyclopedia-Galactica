"""
The Critic / Evaluator for the Karpathy AutoResearch Loop.
Evaluates candidate Sci-Fi terms against academic rigor, attestation fidelity,
and Hrinchenko morphological validity.
"""

from typing import Dict, Any, Tuple
from modules.lexicography.grinchenko_engine import GrinchenkoEngine


class KarpathyCritic:
    """Evaluates candidates using a multi-metric objective function."""

    ACCEPTANCE_THRESHOLD = 0.85

    @classmethod
    def evaluate_candidate(cls, candidate: Dict[str, Any], source_text: str) -> Tuple[float, bool, Dict[str, Any]]:
        scores = {}
        penalties = []

        # 1. Structural Completeness Check (weight: 0.25)
        required_keys = [
            "term_orig", "scientific_definition", "original_context",
            "ukr_grinchenko_neologisms", "morphological_rationale",
            "ukr_translated_context"
        ]
        missing = [k for k in required_keys if not candidate.get(k)]
        if missing:
            completeness = max(0.0, 1.0 - len(missing) * 0.25)
            penalties.append(f"Відсутні обов'язкові поля: {', '.join(missing)}")
        else:
            completeness = 1.0
        scores["completeness"] = completeness

        # 2. Text Attestation Fidelity (weight: 0.30)
        # Term must appear in original context, and context must be present in source text
        term = str(candidate.get("term_orig", "")).strip().lower()
        orig_context = str(candidate.get("original_context", "")).strip()

        if not term or not orig_context:
            attestation = 0.0
            penalties.append("Порожній термін або контекст")
        else:
            term_in_context = term in orig_context.lower()
            context_in_source = True
            if source_text:
                # Check fuzzy inclusion of at least a 30-char slice of context in source
                ctx_slice = orig_context[:min(40, len(orig_context))].lower()
                context_in_source = ctx_slice in source_text.lower()

            if term_in_context and context_in_source:
                attestation = 1.0
            elif term_in_context:
                attestation = 0.85  # term is in context, but slight formatting mismatch in source
            else:
                attestation = 0.30
                penalties.append(f"Термін '{term}' не знайдено в наведеному контексті")
        scores["attestation"] = attestation

        # 3. Grinchenko Morphological Validity (weight: 0.30)
        neologisms = candidate.get("ukr_grinchenko_neologisms", [])
        if not neologisms:
            morphology = 0.2
            penalties.append("Не згенеровано жодного українського неологізму")
        else:
            variant_scores = []
            for n in neologisms:
                var_text = n.get("variant", "")
                rat_text = n.get("morphemes", "") + " " + candidate.get("morphological_rationale", "")
                res = GrinchenkoEngine.evaluate_ukrainian_neologism(var_text, rat_text)
                variant_scores.append(res["score"])
                if not res["is_acceptable"]:
                    penalties.extend(res.get("issues", []))
            morphology = sum(variant_scores) / len(variant_scores) if variant_scores else 0.5
        scores["morphology"] = morphology

        # 4. Definition Depth & Translation Coherence (weight: 0.15)
        definition = str(candidate.get("scientific_definition", ""))
        trans_context = str(candidate.get("ukr_translated_context", ""))

        if len(definition) > 30 and len(trans_context) > 20:
            depth = 1.0
        else:
            depth = 0.6
            penalties.append("Занадто коротке визначення або переклад контексту")
        scores["depth"] = depth

        # Calculate Final Composite Loss / Quality Metric
        final_score = (
            scores["completeness"] * 0.25 +
            scores["attestation"] * 0.30 +
            scores["morphology"] * 0.30 +
            scores["depth"] * 0.15
        )
        final_score = round(min(0.99, max(0.0, final_score)), 2)
        passed = (final_score >= cls.ACCEPTANCE_THRESHOLD)

        details = {
            "component_scores": scores,
            "penalties": penalties,
            "threshold": cls.ACCEPTANCE_THRESHOLD,
            "passed": passed
        }
        return final_score, passed, details

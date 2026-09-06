"""
LLM Client for AutoSciFi & Lexicon («Космослов»).
Communicates with local Ollama on NVIDIA RTX 3090 (Qwen 3.5:27b / Qwen 3.6:35b).
Supports JSON structured outputs and custom lexicographical prompting.
"""

import json
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("AutoResearch.LLM")


class LocalLLMClient:
    def __init__(self, model_name: str = "qwen3.5:27b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def is_available(self) -> bool:
        """Checks if Ollama service is reachable."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def list_available_models(self) -> list:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if r.status_code == 200:
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []

    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False, temperature: float = 0.3) -> Dict[str, Any]:
        """Generates completion from local Ollama instance."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_predict": 2000
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["format"] = "json"

        try:
            response = requests.post(url, json=payload, timeout=600)
            response.raise_for_status()
            data = response.json()
            raw_text = data.get("response", "").strip()
            # In Ollama 0.24.0, reasoning models may place output into 'thinking'
            if not raw_text and data.get("thinking"):
                raw_text = data.get("thinking", "").strip()

            result = {
                "text": raw_text,
                "prompt_eval_count": data.get("prompt_eval_count", 0),
                "eval_count": data.get("eval_count", 0),
                "total_duration_ms": data.get("total_duration", 0) // 1_000_000
            }

            if json_mode:
                cleaned = raw_text
                # Strip reasoning <think>...</think> if present
                if "</think>" in cleaned:
                    cleaned = cleaned.split("</think>")[-1].strip()

                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()

                # Extract content between outer braces
                start_idx = cleaned.find("{")
                end_idx = cleaned.rfind("}")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    cleaned = cleaned[start_idx:end_idx + 1]

                try:
                    result["json"] = json.loads(cleaned)
                except Exception as parse_err:
                    import re
                    sanitized = re.sub(r",\s*([\]}])", r"\1", cleaned)
                    result["json"] = json.loads(sanitized)

            return result
        except Exception as e:
            logger.error(f"LLM request error ({self.model_name}): {e}")
            raise

    def analyze_sci_fi_text(self, author_name: str, work_title: str, year: int, excerpt_text: str) -> Dict[str, Any]:
        """
        Specialized prompt for extracting Sci-Fi neologisms and crafting
        Grinchenko-based Ukrainian interpretations.
        """
        system_prompt = (
            "Ти — провідний учений-філолог, дослідник наукової фантастики та академічний укладач Словника науково-фантастичних неологізмів. "
            "Твоя мета — знайти в тексті оригінальні авторські терміни, технології, фантастичні концепції та створити для них органічні, "
            "вишукані українські відповідники за моделями 'Словаря української мови' Бориса Грінченка (1907-1909), "
            "уникаючи механічних англійських кальок та росіянізмів. Відповідай ВИКЛЮЧНО валідним JSON-об'єктом."
        )

        prompt = f"""
Проаналізуй поданий оригінальний фрагмент науково-фантастичного твору:
Автор: {author_name}
Твір: {work_title} ({year} рік)

ОРИГІНАЛЬНИЙ ТЕКСТ:
\"\"\"
{excerpt_text}
\"\"\"

Знайди ключовий науково-фантастичний концепт або авторський термін (наприклад, неологізм, винайдена технологія, філософське явище).
Згенеруй структурований JSON за таким форматом:
{{
  "term_orig": "термін_англійською_або_мовою_оригіналу",
  "ipa": "[фонетична транскрипція]",
  "concept_category": "Категорія (наприклад: Штучний інтелект, Релятивістський зв'язок, Квантова фізика, Мегаструктури, Соціологія)",
  "scientific_definition": "Чітке наукове пояснення концепту у всесвіті твору",
  "original_context": "Точна цитата з фрагмента, де термін вжито",
  "context_source_locator": "Сцена або розділ",
  "ukr_traditional": "Як це слово перекладали раніше (або 'вперше вводиться')",
  "ukr_grinchenko_neologisms": [
    {{
      "variant": "Український_неологізм_з_наголосом",
      "morphemes": "корінь + префікс + суфікс (детальний розбір)",
      "grinchenko_model": "Словарь Грінченка, вказівка на аналогічну продуктивну модель",
      "semantic_nuance": "Чому саме цей варіант найкраще передає дух оригіналу"
    }},
    {{
      "variant": "Другий_варіант_неологізму",
      "morphemes": "розбір",
      "grinchenko_model": "модель",
      "semantic_nuance": "нюанс"
    }}
  ],
  "morphological_rationale": "Академічне лінгвістичне обґрунтування вибору моделі словотвору",
  "ukr_translated_context": "Художній переклад оригінальної цитати українською мовою з використанням першого варіанта неологізму"
}}
"""
        return self.generate(prompt=prompt, system_prompt=system_prompt, json_mode=True)

    def propose_candidates(self, excerpt_text: str, work_title: str = "", author_name: str = "") -> list:
        """
        КРОК 1 (Т12): Пропозиція кандидатів.
        LLM читає шматок тексту і називає лише список слів-кандидатів.
        Жодних цитат, жодних галюцинацій.
        """
        system_prompt = (
            "Ти — дослідник історії наукової фантастики. Прочитай фрагмент тексту та виділи "
            "ключові фантастичні терміни, назви вигаданих технологій, неологізми, раси або спекулятивні концепти. "
            "Відповідай ВИКЛЮЧНО JSON-об'єктом формату: {\"candidates\": [\"term1\", \"term2\", ...]}."
        )
        prompt = f"""
Твір: {work_title} ({author_name})

ФРАГМЕНТ ТЕКСТУ:
\"\"\"
{excerpt_text}
\"\"\"

Знайди до 5 найважливіших спекулятивних термінів або неологізмів із цього фрагмента.
Поверни JSON:
{{"candidates": ["термін1", "термін2"]}}
"""
        res = self.generate(prompt=prompt, system_prompt=system_prompt, json_mode=True, temperature=0.2)
        payload = res.get("json")
        if not isinstance(payload, dict) or not isinstance(payload.get("candidates"), list):
            raise ValueError("invalid_candidates_schema")
        cands = payload["candidates"]
        if any(not isinstance(c, str) or not c.strip() for c in cands):
            raise ValueError("invalid_candidate_item")
        # Transport/JSON failures propagate: only an explicit empty array means no candidates.
        return list(dict.fromkeys(c.strip() for c in cands))

    def derive_ukrainian_neologism(
        self,
        term: str,
        verified_quote: str,
        work_title: str = "",
        author_name: str = ""
    ) -> Dict[str, Any]:
        """
        КРОК 3 (Т12): Деривація.
        LLM отримує ВЖЕ ЗНАЙДЕНУ справжню цитату і пропонує український відповідник
        за моделями словника Грінченка. Регістр 'proposed'.
        """
        system_prompt = (
            "Ти — академічний лексикограф та перекладач наукової фантастики. "
            "Тобі надано СПРАВЖНЮ верифіковану цитату з першоджерела. "
            "Твоє завдання — створити питомий, органічний український неологізм за моделями "
            "живої української мови (словник Б. Грінченка 1907-1909), без механічних кальок та русизмів. "
            "Відповідай ВИКЛЮЧНО валідним JSON-об'єктом."
        )
        prompt = f"""
Термін: {term}
Твір: {work_title} ({author_name})

АВТЕНТИЧНА ЦИТАТА З КНИГИ (КООРДИНАТА ПІДТВЕРДЖЕНА):
\"\"\"
{verified_quote}
\"\"\"

Створи для цього терміна українську пропозицію (регістр 'proposed').
Поверни JSON строго за такою структурою:
{{
  "proposed_ukr_term": "Українське_слово_з_наголосом",
  "grinchenko_root": "базовий_український_корінь (наприклад: плин-, роб-, віст-, літ-)",
  "derivation_model": "формула словотвору (наприклад: корінь + сполучний о + суфікс -ник)",
  "stylistic_note": "філологічне пояснення, чому ця форма найкраще розкриває суть поняття",
  "scientific_definition": "стисле визначення концепту у всесвіті твору",
  "concept_category": "категорія концепту (наприклад: Хрононавтика, Робототехніка, Космоплавання, Астроінженерія)"
}}
"""
        return self.generate(prompt=prompt, system_prompt=system_prompt, json_mode=True, temperature=0.3)

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
                "top_p": 0.9
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["format"] = "json"

        try:
            response = requests.post(url, json=payload, timeout=240)
            response.raise_for_status()
            data = response.json()
            raw_text = data.get("response", "").strip()

            result = {
                "text": raw_text,
                "prompt_eval_count": data.get("prompt_eval_count", 0),
                "eval_count": data.get("eval_count", 0),
                "total_duration_ms": data.get("total_duration", 0) // 1_000_000
            }

            if json_mode:
                try:
                    result["json"] = json.loads(raw_text)
                except Exception as e:
                    # Try extracting json snippet if wrapped in markdown
                    cleaned = raw_text
                    if "```json" in cleaned:
                        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                    elif "```" in cleaned:
                        cleaned = cleaned.split("```")[1].split("```")[0].strip()
                    result["json"] = json.loads(cleaned)

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

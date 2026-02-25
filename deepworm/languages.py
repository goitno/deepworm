"""Multi-language support for research output.

Provides language-specific prompts and output formatting
so research reports can be generated in the user's preferred language.

Usage:
    deepworm "quantum computing" --lang tr
    deepworm "machine learning" --lang de
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Language:
    """Language definition with display info and prompt instructions."""
    code: str
    name: str
    native_name: str
    prompt_instruction: str


# Supported languages
LANGUAGES: Dict[str, Language] = {
    "en": Language(
        code="en",
        name="English",
        native_name="English",
        prompt_instruction="Write the response in English.",
    ),
    "tr": Language(
        code="tr",
        name="Turkish",
        native_name="Türkçe",
        prompt_instruction="Yanıtı Türkçe olarak yaz. Tüm başlıklar, açıklamalar ve içerik Türkçe olmalıdır.",
    ),
    "de": Language(
        code="de",
        name="German",
        native_name="Deutsch",
        prompt_instruction="Schreibe die Antwort auf Deutsch. Alle Überschriften, Beschreibungen und Inhalte sollen auf Deutsch sein.",
    ),
    "fr": Language(
        code="fr",
        name="French",
        native_name="Français",
        prompt_instruction="Écris la réponse en français. Tous les titres, descriptions et contenus doivent être en français.",
    ),
    "es": Language(
        code="es",
        name="Spanish",
        native_name="Español",
        prompt_instruction="Escribe la respuesta en español. Todos los títulos, descripciones y contenido deben estar en español.",
    ),
    "pt": Language(
        code="pt",
        name="Portuguese",
        native_name="Português",
        prompt_instruction="Escreva a resposta em português. Todos os títulos, descrições e conteúdo devem estar em português.",
    ),
    "it": Language(
        code="it",
        name="Italian",
        native_name="Italiano",
        prompt_instruction="Scrivi la risposta in italiano. Tutti i titoli, le descrizioni e i contenuti devono essere in italiano.",
    ),
    "ru": Language(
        code="ru",
        name="Russian",
        native_name="Русский",
        prompt_instruction="Напиши ответ на русском языке. Все заголовки, описания и содержание должны быть на русском.",
    ),
    "zh": Language(
        code="zh",
        name="Chinese",
        native_name="中文",
        prompt_instruction="请用中文撰写回复。所有标题、描述和内容都应该用中文。",
    ),
    "ja": Language(
        code="ja",
        name="Japanese",
        native_name="日本語",
        prompt_instruction="日本語で回答を書いてください。すべての見出し、説明、内容は日本語で記述してください。",
    ),
    "ko": Language(
        code="ko",
        name="Korean",
        native_name="한국어",
        prompt_instruction="한국어로 답변을 작성하세요. 모든 제목, 설명 및 내용은 한국어로 작성해야 합니다.",
    ),
    "ar": Language(
        code="ar",
        name="Arabic",
        native_name="العربية",
        prompt_instruction="اكتب الرد باللغة العربية. يجب أن تكون جميع العناوين والأوصاف والمحتوى باللغة العربية.",
    ),
    "hi": Language(
        code="hi",
        name="Hindi",
        native_name="हिन्दी",
        prompt_instruction="कृपया हिन्दी में उत्तर लिखें। सभी शीर्षक, विवरण और सामग्री हिन्दी में होनी चाहिए।",
    ),
    "nl": Language(
        code="nl",
        name="Dutch",
        native_name="Nederlands",
        prompt_instruction="Schrijf het antwoord in het Nederlands. Alle titels, beschrijvingen en inhoud moeten in het Nederlands zijn.",
    ),
    "pl": Language(
        code="pl",
        name="Polish",
        native_name="Polski",
        prompt_instruction="Napisz odpowiedź po polsku. Wszystkie tytuły, opisy i treść powinny być po polsku.",
    ),
    "sv": Language(
        code="sv",
        name="Swedish",
        native_name="Svenska",
        prompt_instruction="Skriv svaret på svenska. Alla rubriker, beskrivningar och innehåll ska vara på svenska.",
    ),
    "uk": Language(
        code="uk",
        name="Ukrainian",
        native_name="Українська",
        prompt_instruction="Напишіть відповідь українською мовою. Усі заголовки, описи та вміст мають бути українською.",
    ),
}


def get_language(code: str) -> Optional[Language]:
    """Get a language by its code.

    Args:
        code: ISO 639-1 language code (e.g. 'en', 'tr', 'de').

    Returns:
        Language object or None if not found.
    """
    return LANGUAGES.get(code.lower())


def list_languages() -> list[Language]:
    """Return all supported languages, sorted by code."""
    return sorted(LANGUAGES.values(), key=lambda l: l.code)


def get_language_instruction(code: str) -> str:
    """Get the prompt instruction for a language code.

    Returns empty string if language not found (falls back to model default).
    """
    lang = get_language(code)
    return lang.prompt_instruction if lang else ""

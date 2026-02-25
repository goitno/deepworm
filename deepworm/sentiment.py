"""Sentiment and tone analysis for research reports.

Analyze text sentiment (positive/negative/neutral), detect tone
and bias patterns, and provide section-level sentiment breakdowns.
Uses lexicon-based approach — no external dependencies required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Sentiment lexicons (curated for research/analytical text)
_POSITIVE_WORDS = {
    "good", "great", "excellent", "best", "better", "improved", "improvement",
    "effective", "efficient", "success", "successful", "beneficial", "benefit",
    "advantage", "innovative", "innovation", "promising", "progress",
    "significant", "notable", "remarkable", "outstanding", "superior",
    "optimal", "robust", "reliable", "accurate", "precise", "strong",
    "powerful", "advanced", "comprehensive", "thorough", "valuable",
    "important", "essential", "crucial", "vital", "key", "positive",
    "increase", "increased", "growth", "growing", "enhance", "enhanced",
    "well", "proven", "recommended", "solution", "solved", "achieve",
    "achieved", "accomplish", "breakthrough", "revolutionary", "transformative",
    "leading", "pioneer", "pioneering", "elegant", "intuitive", "flexible",
    "scalable", "popular", "widely", "adopted", "trusted", "award",
    "winning", "outperform", "surpass", "exceed", "exceeded",
}

_NEGATIVE_WORDS = {
    "bad", "poor", "worst", "worse", "fail", "failed", "failure",
    "problem", "issue", "error", "bug", "flaw", "weakness", "limitation",
    "disadvantage", "risk", "risky", "danger", "dangerous", "threat",
    "concern", "concerning", "alarming", "critical", "severe", "serious",
    "difficult", "complex", "complicated", "confusing", "unclear",
    "insufficient", "inadequate", "lack", "lacking", "missing", "absent",
    "decline", "decreased", "decrease", "loss", "lost", "reduce", "reduced",
    "slow", "slower", "slowest", "expensive", "costly", "overhead",
    "vulnerable", "vulnerability", "insecure", "unstable", "unreliable",
    "inaccurate", "imprecise", "outdated", "deprecated", "obsolete",
    "broken", "crash", "crashes", "corrupt", "corrupted", "malicious",
    "attack", "exploit", "breach", "leak", "leaked", "compromise",
    "negative", "harmful", "toxic", "bias", "biased", "unfair",
    "controversy", "controversial", "dispute", "disputed",
}

_INTENSIFIERS = {
    "very", "extremely", "highly", "incredibly", "remarkably",
    "particularly", "especially", "significantly", "substantially",
    "considerably", "dramatically", "enormously", "absolutely",
    "completely", "entirely", "totally", "utterly", "thoroughly",
}

_NEGATORS = {
    "not", "no", "never", "neither", "nor", "none", "nothing",
    "nowhere", "hardly", "barely", "scarcely", "rarely", "seldom",
    "without", "lack", "lacking", "absence", "cannot", "can't",
    "don't", "doesn't", "didn't", "won't", "wouldn't", "shouldn't",
    "isn't", "aren't", "wasn't", "weren't",
}

# Bias indicators in research text
_BIAS_PATTERNS = [
    (r"\b(?:obviously|clearly|undoubtedly|undeniably)\b", "certainty_bias"),
    (r"\b(?:everyone|nobody|always|never)\b", "absolute_language"),
    (r"\b(?:simply|just|merely|only)\b", "minimizing_language"),
    (r"\b(?:must|should|need to|have to)\b", "prescriptive_language"),
    (r"\b(?:unfortunately|sadly|alarmingly)\b", "emotional_language"),
    (r"\b(?:so-called|alleged|supposed|questionable)\b", "skeptical_language"),
]


@dataclass
class SentimentScore:
    """Sentiment analysis result for a text segment."""

    positive: float = 0.0
    negative: float = 0.0
    neutral: float = 0.0
    compound: float = 0.0  # combined score -1 to +1
    label: str = "neutral"  # positive, negative, neutral, mixed
    confidence: float = 0.0
    word_count: int = 0
    positive_words: List[str] = field(default_factory=list)
    negative_words: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "positive": round(self.positive, 3),
            "negative": round(self.negative, 3),
            "neutral": round(self.neutral, 3),
            "compound": round(self.compound, 3),
            "label": self.label,
            "confidence": round(self.confidence, 3),
            "word_count": self.word_count,
        }


@dataclass
class ToneAnalysis:
    """Tone and style analysis result."""

    formality: float = 0.0  # 0 (informal) to 1 (formal)
    objectivity: float = 0.0  # 0 (subjective) to 1 (objective)
    bias_indicators: List[Dict[str, Any]] = field(default_factory=list)
    tone_label: str = "neutral"  # academic, persuasive, neutral, informal
    hedging_count: int = 0  # "might", "perhaps", "possibly"
    assertion_count: int = 0  # definitive statements

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "formality": round(self.formality, 3),
            "objectivity": round(self.objectivity, 3),
            "tone_label": self.tone_label,
            "hedging_count": self.hedging_count,
            "assertion_count": self.assertion_count,
            "bias_count": len(self.bias_indicators),
            "bias_indicators": self.bias_indicators,
        }


@dataclass
class SentimentReport:
    """Complete sentiment analysis report."""

    overall: SentimentScore = field(default_factory=SentimentScore)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    tone: ToneAnalysis = field(default_factory=ToneAnalysis)
    sentence_sentiments: List[SentimentScore] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render as markdown report."""
        lines = ["## Sentiment Analysis\n"]

        # Overall
        icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪", "mixed": "🟡"}
        label_icon = icon.get(self.overall.label, "⚪")
        lines.append(f"**Overall Sentiment**: {label_icon} {self.overall.label.title()} "
                      f"(compound: {self.overall.compound:+.3f})\n")

        lines.append(f"- Positive: {self.overall.positive:.1%}")
        lines.append(f"- Negative: {self.overall.negative:.1%}")
        lines.append(f"- Neutral: {self.overall.neutral:.1%}")
        lines.append(f"- Confidence: {self.overall.confidence:.1%}")
        lines.append("")

        # Tone
        lines.append(f"**Tone**: {self.tone.tone_label.title()}")
        lines.append(f"- Formality: {self.tone.formality:.1%}")
        lines.append(f"- Objectivity: {self.tone.objectivity:.1%}")
        if self.tone.hedging_count:
            lines.append(f"- Hedging phrases: {self.tone.hedging_count}")
        if self.tone.bias_indicators:
            lines.append(f"- Bias indicators: {len(self.tone.bias_indicators)}")
        lines.append("")

        # Sections
        if self.sections:
            lines.append("### Section Breakdown\n")
            lines.append("| Section | Sentiment | Compound |")
            lines.append("|---------|-----------|----------|")
            for sec in self.sections:
                s_icon = icon.get(sec["label"], "⚪")
                lines.append(
                    f"| {sec['section']} | {s_icon} {sec['label']} | "
                    f"{sec['compound']:+.3f} |"
                )
            lines.append("")

        # Key words
        if self.overall.positive_words:
            top_positive = self.overall.positive_words[:10]
            lines.append(f"**Positive terms**: {', '.join(top_positive)}")
        if self.overall.negative_words:
            top_negative = self.overall.negative_words[:10]
            lines.append(f"**Negative terms**: {', '.join(top_negative)}")

        return "\n".join(lines) + "\n"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall": self.overall.to_dict(),
            "tone": self.tone.to_dict(),
            "sections": self.sections,
            "sentence_count": len(self.sentence_sentiments),
        }


def analyze_sentiment(text: str) -> SentimentScore:
    """Analyze sentiment of text.

    Uses lexicon-based approach with negation handling and
    intensifier detection.

    Args:
        text: Input text.

    Returns:
        SentimentScore with positive/negative/neutral ratios.
    """
    words = _tokenize(text)
    if not words:
        return SentimentScore(neutral=1.0, label="neutral", confidence=0.0)

    pos_score = 0.0
    neg_score = 0.0
    pos_words: List[str] = []
    neg_words: List[str] = []

    for i, word in enumerate(words):
        # Check for negation in previous 2 words
        negated = _is_negated(words, i)
        # Check for intensifier
        intensity = _get_intensity(words, i)

        if word in _POSITIVE_WORDS:
            if negated:
                neg_score += intensity
                neg_words.append(word)
            else:
                pos_score += intensity
                pos_words.append(word)
        elif word in _NEGATIVE_WORDS:
            if negated:
                pos_score += intensity * 0.5  # negated negative is weakly positive
                pos_words.append(word)
            else:
                neg_score += intensity
                neg_words.append(word)

    total = pos_score + neg_score
    word_count = len(words)

    if total == 0:
        return SentimentScore(
            neutral=1.0,
            label="neutral",
            confidence=0.5,
            word_count=word_count,
        )

    positive = pos_score / max(total, 1)
    negative = neg_score / max(total, 1)
    neutral_ratio = max(0, 1.0 - (total / max(word_count, 1)))
    neutral_ratio = min(neutral_ratio, 1.0)

    # Compound: -1 to +1
    compound = (pos_score - neg_score) / (pos_score + neg_score + 1)
    compound = max(-1.0, min(1.0, compound))

    # Determine label
    if abs(compound) < 0.1:
        label = "neutral"
    elif compound > 0:
        if negative > 0.3:
            label = "mixed"
        else:
            label = "positive"
    else:
        if positive > 0.3:
            label = "mixed"
        else:
            label = "negative"

    # Confidence based on signal strength
    confidence = min(1.0, total / max(word_count * 0.1, 1))

    return SentimentScore(
        positive=positive,
        negative=negative,
        neutral=neutral_ratio,
        compound=compound,
        label=label,
        confidence=confidence,
        word_count=word_count,
        positive_words=pos_words,
        negative_words=neg_words,
    )


def analyze_tone(text: str) -> ToneAnalysis:
    """Analyze the tone and style of text.

    Detects formality level, objectivity, bias indicators,
    hedging, and assertions.

    Args:
        text: Input text.

    Returns:
        ToneAnalysis with formality, objectivity, bias details.
    """
    words = _tokenize(text)
    text_lower = text.lower()

    if not words:
        return ToneAnalysis()

    # Formality indicators
    formal_markers = {
        "furthermore", "moreover", "consequently", "therefore",
        "nevertheless", "nonetheless", "however", "thus", "hence",
        "whereby", "whereas", "notwithstanding", "aforementioned",
        "hitherto", "subsequently", "accordingly", "additionally",
    }
    informal_markers = {
        "gonna", "wanna", "gotta", "kinda", "sorta", "yeah",
        "hey", "cool", "awesome", "stuff", "thing", "things",
        "pretty", "really", "basically", "literally", "actually",
        "super", "totally", "huge", "crazy", "insane",
    }

    formal_count = sum(1 for w in words if w in formal_markers)
    informal_count = sum(1 for w in words if w in informal_markers)
    formality = (formal_count + 1) / (formal_count + informal_count + 2)

    # Objectivity: first-person pronouns and emotional language reduce it
    first_person = sum(1 for w in words if w in {"i", "my", "me", "we", "our", "us"})
    opinion_words = sum(1 for w in words if w in {
        "think", "believe", "feel", "opinion", "personally",
        "seems", "appears", "guess", "suppose",
    })
    subjectivity = (first_person + opinion_words) / max(len(words) * 0.05, 1)
    objectivity = max(0.0, min(1.0, 1.0 - subjectivity))

    # Bias detection
    bias_indicators: List[Dict[str, Any]] = []
    for pattern, bias_type in _BIAS_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            bias_indicators.append({
                "type": bias_type,
                "text": match,
            })

    # Hedging language
    hedging_words = {
        "might", "may", "perhaps", "possibly", "potentially",
        "likely", "unlikely", "probably", "could", "would",
        "suggest", "suggests", "appear", "appears", "seem", "seems",
        "tend", "tends", "approximate", "approximately", "roughly",
    }
    hedging_count = sum(1 for w in words if w in hedging_words)

    # Assertion language
    assertion_words = {
        "is", "are", "was", "were", "will", "must", "shall",
        "demonstrates", "proves", "shows", "confirms", "establishes",
        "reveals", "indicates", "determines",
    }
    assertion_count = sum(1 for w in words if w in assertion_words)

    # Determine tone label
    if formality > 0.7 and objectivity > 0.7:
        tone_label = "academic"
    elif objectivity < 0.4:
        tone_label = "persuasive"
    elif formality < 0.4:
        tone_label = "informal"
    else:
        tone_label = "neutral"

    return ToneAnalysis(
        formality=formality,
        objectivity=objectivity,
        bias_indicators=bias_indicators,
        tone_label=tone_label,
        hedging_count=hedging_count,
        assertion_count=assertion_count,
    )


def analyze_report_sentiment(text: str) -> SentimentReport:
    """Full sentiment analysis of a research report.

    Analyzes overall sentiment, section-level breakdown,
    sentence-level sentiments, and tone.

    Args:
        text: Full report text (markdown supported).

    Returns:
        SentimentReport with complete analysis.
    """
    report = SentimentReport()

    # Overall sentiment
    report.overall = analyze_sentiment(text)

    # Tone analysis
    report.tone = analyze_tone(text)

    # Section-level analysis
    sections = _split_sections(text)
    for section_title, section_text in sections:
        score = analyze_sentiment(section_text)
        report.sections.append({
            "section": section_title,
            "label": score.label,
            "compound": score.compound,
            "positive": score.positive,
            "negative": score.negative,
        })

    # Sentence-level
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if len(sentence.split()) >= 5:
            score = analyze_sentiment(sentence)
            report.sentence_sentiments.append(score)

    return report


def sentiment_diff(
    text_a: str, text_b: str
) -> Dict[str, Any]:
    """Compare sentiment between two texts.

    Args:
        text_a: First text.
        text_b: Second text.

    Returns:
        Dict with sentiment comparison metrics.
    """
    score_a = analyze_sentiment(text_a)
    score_b = analyze_sentiment(text_b)

    return {
        "text_a": {
            "label": score_a.label,
            "compound": round(score_a.compound, 3),
        },
        "text_b": {
            "label": score_b.label,
            "compound": round(score_b.compound, 3),
        },
        "compound_diff": round(score_b.compound - score_a.compound, 3),
        "shifted": score_a.label != score_b.label,
        "shift_direction": _shift_direction(score_a.compound, score_b.compound),
    }


def _shift_direction(a: float, b: float) -> str:
    """Determine sentiment shift direction."""
    diff = b - a
    if abs(diff) < 0.05:
        return "stable"
    return "more_positive" if diff > 0 else "more_negative"


def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    # Strip markdown
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # Extract words
    words = re.findall(r"[a-z']+", text.lower())
    return words


def _is_negated(words: List[str], index: int) -> bool:
    """Check if word at index is negated by a preceding negator."""
    for i in range(max(0, index - 3), index):
        if words[i] in _NEGATORS:
            return True
    return False


def _get_intensity(words: List[str], index: int) -> float:
    """Get intensity multiplier based on preceding intensifiers."""
    for i in range(max(0, index - 2), index):
        if words[i] in _INTENSIFIERS:
            return 1.5
    return 1.0


def _split_sections(text: str) -> List[Tuple[str, str]]:
    """Split markdown text into sections by headings."""
    sections: List[Tuple[str, str]] = []
    current_title = "Introduction"
    current_text: List[str] = []

    for line in text.split("\n"):
        heading = re.match(r"^#{1,3}\s+(.+)$", line)
        if heading:
            if current_text:
                sections.append((current_title, "\n".join(current_text)))
            current_title = heading.group(1).strip()
            current_text = []
        else:
            current_text.append(line)

    if current_text:
        sections.append((current_title, "\n".join(current_text)))

    return sections

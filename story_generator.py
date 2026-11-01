
"""Core logic: call Groq, parse the story, check readability and safety."""

import os
import re

from prompts import (
    LEVELS,
    SAFETY_CHECK_PROMPT,
    SYSTEM_PROMPT,
    build_user_prompt,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# ------------------------------------------------------------------
# Groq model configuration
# ------------------------------------------------------------------

MODEL = os.environ.get("STORY_MODEL", "openai/gpt-oss-120b")

MAX_TOPIC_CHARS = 200
MAX_FIELD_CHARS = 300


# Words that trigger an extra safety review (whole-word match).
FLAGGED_WORDS = [
    "kill", "killed", "murder", "suicide", "blood", "gun", "guns", "weapon",
    "sex", "sexual", "porn", "naked", "drug", "drugs", "alcohol", "beer",
    "wine", "cigarette", "terror", "torture", "stupid", "idiot", "hate",
]


class StoryError(Exception):
    """Any error that should be shown to the user in plain words."""


# ------------------------------------------------------------------
# Groq API call
# ------------------------------------------------------------------

def _import_groq():
    try:
        from groq import Groq
    except ImportError as e:
        raise StoryError(
            "The 'groq' package is missing. "
            "Run: pip install groq"
        ) from e

    return Groq


def call_model(system, user, max_tokens=4000):
    """Send one request to Groq and return the generated text."""

    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        raise StoryError(
            "GROQ_API_KEY is not set. "
            "Create a key in the Groq Console and put it in your .env file."
        )

    Groq = _import_groq()
    client = Groq(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_completion_tokens=max_tokens,
            reasoning_effort="low",
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": user,
                },
            ],
        )

    except Exception as e:
        from groq import (
            AuthenticationError,
            RateLimitError,
            APIConnectionError,
            APIStatusError,
        )

        if isinstance(e, AuthenticationError):
            raise StoryError(
                "Groq API key rejected. Check GROQ_API_KEY."
            ) from e

        if isinstance(e, RateLimitError):
            raise StoryError(
                "Groq rate limit reached. Please wait and try again."
            ) from e

        if isinstance(e, APIConnectionError):
            raise StoryError(
                "Could not connect to Groq. Check your internet connection."
            ) from e

        if isinstance(e, APIStatusError):
            raise StoryError(
                f"Groq API error ({e.status_code}): {e.message}"
            ) from e

        raise StoryError(
            f"Unexpected Groq error: {e}"
        ) from e

    # Check whether the model returned any choices.
    if not response.choices:
        raise StoryError(
            "Groq returned no choices. Please try again."
        )

    choice = response.choices[0]
    message = choice.message
    content = message.content

    # Check whether the model returned actual text.
    if not content or not content.strip():
        finish_reason = choice.finish_reason

        raise StoryError(
            f"Groq returned empty content. "
            f"Finish reason: {finish_reason}. "
            f"Model: {MODEL}. Please try again."
        )

    return content.strip()


# ------------------------------------------------------------------
# Story parsing
# ------------------------------------------------------------------

_HEADING = re.compile(
    r"^\s*(TITLE|STORY|KEY IDEA|QUESTIONS)\s*:",
    re.I | re.M,
)


def parse_story(raw):
    """Split the model reply into title, story, key idea and questions."""

    text = raw.replace("**", "").replace("##", "").replace("# ", "")

    matches = list(_HEADING.finditer(text))
    sections = {}

    for i, match in enumerate(matches):
        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(text)
        )

        sections[match.group(1).upper()] = (
            text[match.end():end].strip()
        )

    story = sections.get("STORY", "")

    if not story:
        raise StoryError(
            "The model reply could not be read. Please try again."
        )

    questions = []

    for line in sections.get("QUESTIONS", "").splitlines():
        line = re.sub(
            r"^\s*(\d+[.)]|[-*•])\s*",
            "",
            line,
        ).strip()

        if line:
            questions.append(line)

    title = sections.get("TITLE", "Untitled story")

    return {
        "title": (
            title.splitlines()[0].strip()
            or "Untitled story"
        ),
        "story": story,
        "key_idea": sections.get("KEY IDEA", ""),
        "questions": questions[:3],
    }


# ------------------------------------------------------------------
# Readability analysis
# ------------------------------------------------------------------

def split_sentences(text):
    parts = re.split(
        r'(?<=[.!?])[\s"\')\]]+',
        text.strip(),
    )

    return [
        part
        for part in parts
        if re.search(r"\w", part)
    ]


def count_words(text):
    return len(
        re.findall(
            r"[A-Za-z0-9À-￿']+",
            text,
        )
    )


def count_syllables(word):
    word = re.sub(
        r"[^a-z]",
        "",
        word.lower(),
    )

    if not word:
        return 0

    groups = re.findall(
        r"[aeiouy]+",
        word,
    )

    n = len(groups)

    if (
        word.endswith("e")
        and not word.endswith(("le", "ee"))
        and n > 1
    ):
        n -= 1

    return max(n, 1)


def analyze_readability(story, level):
    """Estimate story difficulty and compare with level targets."""

    profile = LEVELS[level]

    sentences = split_sentences(story)

    words = re.findall(
        r"[A-Za-z']+",
        story,
    )

    n_words = count_words(story)

    n_sent = max(
        len(sentences),
        1,
    )

    avg_sentence = n_words / n_sent

    syllables = (
        sum(count_syllables(word) for word in words)
        or 1
    )

    wc = max(
        len(words),
        1,
    )

    reading_ease = (
        206.835
        - 1.015 * avg_sentence
        - 84.6 * (syllables / wc)
    )

    grade = (
        0.39 * avg_sentence
        + 11.8 * (syllables / wc)
        - 15.59
    )

    return {
        "word_count": n_words,
        "sentence_count": len(sentences),
        "avg_sentence_length": round(avg_sentence, 1),
        "target_avg_sentence": profile["max_avg_sentence"],
        "target_words": (
            f"{profile['min_words']}-{profile['max_words']}"
        ),
        "reading_ease": round(reading_ease, 1),
        "grade_estimate": round(max(grade, 0), 1),
        "sentence_ok": (
            avg_sentence
            <= profile["max_avg_sentence"] * 1.1
        ),
    }


# ------------------------------------------------------------------
# Safety checking
# ------------------------------------------------------------------

def keyword_flags(text):
    low = text.lower()

    return sorted({
        word
        for word in FLAGGED_WORDS
        if re.search(
            rf"\b{re.escape(word)}\b",
            low,
        )
    })


def check_safety(parsed, level, use_ai=True):
    """Keyword filter, then optionally a second AI safety review."""

    full = "\n".join([
        parsed["title"],
        parsed["story"],
        parsed["key_idea"],
        *parsed["questions"],
    ])

    flags = keyword_flags(full)

    result = {
        "passed": True,
        "flags": flags,
        "method": "keyword",
        "note": "",
    }

    # Run AI safety review only when needed.
    if use_ai == "always" or (use_ai and flags):

        prompt = SAFETY_CHECK_PROMPT.format(
            ages=LEVELS[level]["ages"],
            text=full,
        )

        try:
            verdict = call_model(
                "You review children's content.",
                prompt,
                max_tokens=100,
            )

        except StoryError as e:
            result.update(
                passed=not flags,
                method="keyword",
                note=f"AI review unavailable: {e}",
            )

            return result

        first = (
            verdict.strip().splitlines()[0].upper()
            if verdict.strip()
            else ""
        )

        result.update(
            passed=first.startswith("SAFE"),
            method="keyword+ai",
            note=verdict.strip(),
        )

    elif flags:
        result["passed"] = False

        result["note"] = (
            "Flagged words found; AI review was turned off."
        )

    return result


# ------------------------------------------------------------------
# Story generation
# ------------------------------------------------------------------

def _clean(value, limit):
    return re.sub(
        r"\s+",
        " ",
        (value or ""),
    ).strip()[:limit]


def generate_story(
    topic,
    level="3-5",
    goal="",
    name="",
    interest="",
    language="English",
    max_retries=2,
    ai_safety=True,
):
    """Full pipeline: validate -> prompt -> call -> parse -> readability -> safety."""

    topic = _clean(
        topic,
        MAX_TOPIC_CHARS,
    )

    if not topic:
        raise StoryError(
            "Please enter a topic."
        )

    if level not in LEVELS:
        raise StoryError(
            f"Level must be one of: {', '.join(LEVELS)}."
        )

    goal = _clean(
        goal,
        MAX_FIELD_CHARS,
    )

    name = _clean(
        name,
        40,
    )

    interest = _clean(
        interest,
        80,
    )

    language = _clean(
        language,
        30,
    ) or "English"

    base_prompt = build_user_prompt(
        topic,
        level,
        goal,
        name,
        interest,
        language,
    )

    prompt = base_prompt

    attempts = 0

    while True:
        attempts += 1

        raw_story = call_model(
            SYSTEM_PROMPT,
            prompt,
        )

        parsed = parse_story(
            raw_story
        )

        metrics = analyze_readability(
            parsed["story"],
            level,
        )

        # Readability heuristics only make sense for English.
        if (
            language.lower() != "english"
            or metrics["sentence_ok"]
            or attempts > max_retries
        ):
            break

        prompt = (
            base_prompt
            + f"\n\nIMPORTANT: your previous draft averaged "
            f"{metrics['avg_sentence_length']} words "
            f"per sentence, but the limit is "
            f"{metrics['target_avg_sentence']}. "
            "Rewrite the whole story using shorter, simpler sentences."
        )

    safety = check_safety(
        parsed,
        level,
        use_ai=ai_safety,
    )

    return {
        **parsed,
        "topic": topic,
        "level": level,
        "level_label": LEVELS[level]["label"],
        "goal": goal,
        "name": name,
        "interest": interest,
        "language": language,
        "readability": metrics,
        "safety": safety,
        "attempts": attempts,
    }


# ------------------------------------------------------------------
# Story export
# ------------------------------------------------------------------

def story_to_text(s):
    """Plain-text version of a story, for downloads and the CLI."""

    qs = "\n".join(
        f"{i}. {q}"
        for i, q in enumerate(
            s["questions"],
            1,
        )
    )

    return (
        f"{s['title']}\n"
        f"{'=' * len(s['title'])}\n\n"
        f"{s['story']}\n\n"
        f"KEY IDEA\n"
        f"{s['key_idea']}\n\n"
        f"QUESTIONS\n"
        f"{qs}\n"
    )

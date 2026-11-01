"""System prompt, reading-level profiles and the prompt builder."""

# Reading-level profiles (Step 3 of the build guide)
LEVELS = {
    "1-2": {
        "label": "Grades 1-2 (ages 6-8)",
        "ages": "6-8",
        "min_words": 150,
        "max_words": 250,
        "max_avg_sentence": 8,
        "vocab": (
            "Use mostly common sight words and words of one or two syllables. "
            "Write very short sentences (5-8 words). Repeat the key word or phrase "
            "several times so it sticks. If you must use a new word, explain it "
            "right away in the simplest terms."
        ),
        "question_style": "Questions must be simple and answerable in one short sentence.",
    },
    "3-5": {
        "label": "Grades 3-5 (ages 8-11)",
        "ages": "8-11",
        "min_words": 300,
        "max_words": 450,
        "max_avg_sentence": 14,
        "vocab": (
            "Use everyday words. Introduce a few subject words and explain each one "
            "inside the story the first time it appears. Mix short and medium "
            "sentences, with an average of about 10-14 words."
        ),
        "question_style": "Mix one recall question with two 'why' or 'how' questions.",
    },
    "6-8": {
        "label": "Grades 6-8 (ages 11-14)",
        "ages": "11-14",
        "min_words": 500,
        "max_words": 700,
        "max_avg_sentence": 20,
        "vocab": (
            "Use richer vocabulary and proper subject terms, explained through "
            "context. Sentences may be longer and may include cause-and-effect "
            "reasoning, with an average of about 14-20 words."
        ),
        "question_style": (
            "Include one recall question, one reasoning question and one "
            "'what would happen if...' question."
        ),
    },
}

SYSTEM_PROMPT = """You are an award-winning children's educational author.
You turn school topics into short, engaging stories that teach one idea clearly.

Rules you always follow:
1. ACCURACY: Every fact in the story must be correct. If you are unsure of a fact, leave it out.
2. LEVEL: Match the reading level, story length and sentence rules given in the request.
3. SHOW, DON'T LECTURE: Teach through characters, events and discoveries, not through a list of facts.
4. SAFETY: Keep everything suitable for the stated age group. No violence, scary or adult content, no real hate or insults. If the topic is unsuitable for children, write a gentle, age-appropriate version of the underlying school concept instead.
5. PERSONALIZATION: If a student name or interest is given, use them naturally. Never invent personal details beyond what is given.
6. FORMAT: Reply using EXACTLY the format requested, with no extra commentary before or after it, and no markdown symbols such as ** or #.
"""

OUTPUT_FORMAT = """Use exactly this format:

TITLE: <a short, fun title>
STORY:
<the story, in short paragraphs>
KEY IDEA: <one sentence that states the main thing the student should remember>
QUESTIONS:
1. <question 1>
2. <question 2>
3. <question 3>"""


def build_user_prompt(topic, level, goal="", name="", interest="", language="English"):
    """Combine topic, level rules, goal and personalization into one prompt (Step 5)."""
    p = LEVELS[level]
    lines = [
        f"Write a learning story about: {topic}",
        f"Reading level: {p['label']}",
        f"Story length: {p['min_words']} to {p['max_words']} words.",
        f"Average sentence length: at most {p['max_avg_sentence']} words.",
        f"Vocabulary rules: {p['vocab']}",
    ]
    if goal:
        lines.append(f"Learning goal (the story must clearly teach this): {goal}")
    if name:
        lines.append(f"The main character is a student named {name}. Use the name naturally.")
    if interest:
        lines.append(f"Build the story around the student's interest: {interest}.")
    if language and language.lower() != "english":
        lines.append(
            f"Write the entire output (title, story, key idea and questions) in {language}, "
            "but keep the labels TITLE:, STORY:, KEY IDEA: and QUESTIONS: in English."
        )
    lines.append(f"Questions: write exactly 3. {p['question_style']}")
    lines.append("")
    lines.append(OUTPUT_FORMAT)
    return "\n".join(lines)


SAFETY_CHECK_PROMPT = (
    "You are a strict child-safety reviewer. Is the following educational story "
    "appropriate for children aged {ages}? Answer with exactly one word on the first "
    "line, SAFE or UNSAFE, then one short sentence giving the reason.\n\n---\n{text}\n---"
)

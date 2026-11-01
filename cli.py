"""Command-line version.

Examples:
    python cli.py                      (asks you questions)
    python cli.py -t "water cycle" -l 3-5 -g "explain evaporation" -n Asha -i cricket
"""

import argparse

from prompts import LEVELS
from story_generator import StoryError, generate_story, story_to_text


def ask(prompt, default=""):
    value = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return value or default


def main():
    ap = argparse.ArgumentParser(description="AI-Powered Personalized Learning Story Generator")
    ap.add_argument("-t", "--topic")
    ap.add_argument("-l", "--level", choices=list(LEVELS))
    ap.add_argument("-g", "--goal", default=None)
    ap.add_argument("-n", "--name", default=None)
    ap.add_argument("-i", "--interest", default=None)
    ap.add_argument("--language", default="English")
    ap.add_argument("-o", "--output", help="save the story to this text file")
    args = ap.parse_args()

    topic = args.topic or ask("Topic (e.g. fractions)")
    level = args.level or ask("Level (1-2, 3-5, 6-8)", "3-5")
    goal = args.goal if args.goal is not None else ask("Learning goal (optional)")
    name = args.name if args.name is not None else ask("Student name (optional)")
    interest = args.interest if args.interest is not None else ask("Interest (optional)")

    print("\nWriting your story...\n")
    try:
        s = generate_story(topic, level, goal, name, interest, args.language)
    except StoryError as e:
        raise SystemExit(f"Error: {e}")

    text = story_to_text(s)
    print(text)
    r = s["readability"]
    print(f"[{r['word_count']} words | avg sentence {r['avg_sentence_length']} (target <= {r['target_avg_sentence']}) "
          f"| grade ~{r['grade_estimate']} | safety: {'OK' if s['safety']['passed'] else 'REVIEW NEEDED'}]")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()

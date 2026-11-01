"""Streamlit UI.  Run:  streamlit run app.py"""

import streamlit as st

import storage
from prompts import LEVELS
from story_generator import StoryError, generate_story, story_to_text

st.set_page_config(page_title="Learning Story Generator", page_icon="📖", layout="centered")
st.title("📖 AI-Powered Personalized Learning Story Generator")
st.caption("Turn any topic into a short story that matches the student's reading level.")


def show_story(s):
    st.subheader(s["title"])
    st.write(s["story"])
    st.success(f"**Key idea:** {s['key_idea']}")
    st.markdown("**Check your understanding**")
    for i, q in enumerate(s["questions"], 1):
        st.write(f"{i}. {q}")
    r = s["readability"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Words", r["word_count"], help=f"Target {r['target_words']}")
    c2.metric("Avg sentence", r["avg_sentence_length"], help=f"Target <= {r['target_avg_sentence']}")
    c3.metric("Grade estimate", r["grade_estimate"])
    if s["safety"]["passed"]:
        st.caption("✅ Safety check passed")
    else:
        st.warning("⚠️ Safety check flagged this story. A teacher should review it. " + s["safety"].get("note", ""))
    st.download_button("Download as .txt", story_to_text(s), file_name="story.txt")


tab_new, tab_saved = st.tabs(["Create a story", "Saved stories"])

with tab_new:
    with st.form("story_form"):
        topic = st.text_input("Topic *", placeholder="e.g. fractions, water cycle, gravity")
        level = st.selectbox("Reading level", list(LEVELS), index=1, format_func=lambda k: LEVELS[k]["label"])
        goal = st.text_area("Learning goal (optional)", placeholder="e.g. explain evaporation and rain", height=70)
        c1, c2 = st.columns(2)
        name = c1.text_input("Student name (optional)")
        interest = c2.text_input("Interest (optional)", placeholder="e.g. cricket")
        language = st.selectbox("Language", ["English", "Hindi", "Telugu", "Tamil", "Spanish"])
        submitted = st.form_submit_button("Generate story")

    if submitted:
        with st.spinner("Writing your story..."):
            try:
                st.session_state["story"] = generate_story(topic, level, goal, name, interest, language)
            except StoryError as e:
                st.session_state.pop("story", None)
                st.error(str(e))

    if "story" in st.session_state:
        story = st.session_state["story"]
        show_story(story)
        if st.button("💾 Save this story"):
            storage.save_story(story)
            st.toast("Saved!")

with tab_saved:
    rows = storage.list_stories()
    if not rows:
        st.info("No saved stories yet.")
    for row in rows:
        with st.expander(f"{row['title']}  ·  {row['topic']}  ·  Grades {row['level']}"):
            s = storage.get_story(row["id"])
            show_story(s)
            if st.button("Delete", key=f"del{row['id']}"):
                storage.delete_story(row["id"])
                st.rerun()

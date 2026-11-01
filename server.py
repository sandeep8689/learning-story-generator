"""Flask backend + web UI.  Run:  python server.py   then open http://127.0.0.1:5000"""

from flask import Flask, jsonify, render_template, request

import storage
from prompts import LEVELS
from story_generator import StoryError, generate_story


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/levels")
    def levels():
        return jsonify({k: v["label"] for k, v in LEVELS.items()})

    @app.post("/api/generate")
    def generate():
        data = request.get_json(silent=True) or {}
        try:
            story = generate_story(
                topic=data.get("topic", ""),
                level=data.get("level", "3-5"),
                goal=data.get("goal", ""),
                name=data.get("name", ""),
                interest=data.get("interest", ""),
                language=data.get("language", "English"),
            )
        except StoryError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify(story)

    @app.post("/api/stories")
    def save():
        story = request.get_json(silent=True) or {}
        if not story.get("story") or not story.get("title"):
            return jsonify({"error": "Nothing to save."}), 400
        story_id = storage.save_story(story)
        return jsonify({"id": story_id}), 201

    @app.get("/api/stories")
    def list_all():
        return jsonify(storage.list_stories())

    @app.get("/api/stories/<int:story_id>")
    def get_one(story_id):
        story = storage.get_story(story_id)
        if not story:
            return jsonify({"error": "Story not found."}), 404
        return jsonify(story)

    @app.delete("/api/stories/<int:story_id>")
    def delete_one(story_id):
        if not storage.delete_story(story_id):
            return jsonify({"error": "Story not found."}), 404
        return jsonify({"deleted": story_id})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

"""
DeckMaster Web - Main Application Entry Point

Creates the Flask app and registers all route blueprints.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
app.py
"""

import os
from flask import Flask

from web.routes.collection import collection_bp
from web.routes.commander import commander_bp


def create_app():
    # Explicit template/static paths so running from repo root works.
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ── Config ────────────────────────────────────────────────────────────────
    app.config["BASE_DIR"] = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(app.config["BASE_DIR"])
    app.config["COMMANDERS_DIR"] = os.environ.get(
        "COMMANDERS_DIR",
        os.path.join(project_root, "commanders"),
    )
    app.config["COLLECTION_DB"]  = os.environ.get(
        "COLLECTION_DB",
        os.path.join(project_root, "collection.db"),
    )

    # ── Register Blueprints ───────────────────────────────────────────────────
    app.register_blueprint(collection_bp)
    app.register_blueprint(commander_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
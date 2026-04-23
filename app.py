"""
DeckMaster Web - Main Application Entry Point

Creates the Flask app and registers all route blueprints.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
app.py
"""

import os
from flask import Flask

from routes.collection import collection_bp
from routes.commander import commander_bp


def create_app():
    app = Flask(__name__)

    # ── Config ────────────────────────────────────────────────────────────────
    app.config["BASE_DIR"]       = os.path.dirname(os.path.abspath(__file__))
    app.config["COMMANDERS_DIR"] = os.path.join(app.config["BASE_DIR"], "commanders")
    app.config["COLLECTION_DB"]  = os.path.join(app.config["BASE_DIR"], "collection.db")

    # ── Register Blueprints ───────────────────────────────────────────────────
    app.register_blueprint(collection_bp)
    app.register_blueprint(commander_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
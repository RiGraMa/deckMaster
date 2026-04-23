"""
DeckMaster Web - Commander Blueprint

Routes for scraping and managing commander decklists from EDHREC.
Scraper logic will be integrated from deckmaster.py in Phase 2.

Author: Ricardo Martins
Repository: https://github.com/RiGraMa/deckMaster
routes/commander.py
"""

from flask import Blueprint, render_template

commander_bp = Blueprint("commander", __name__)


# ── Routes ────────────────────────────────────────────────────────────────────
@commander_bp.route("/scrape")
def scrape():
    """
    Scrape a commander decklist from EDHREC.
    Phase 2 — not yet implemented.
    """
    return render_template("commander.html")
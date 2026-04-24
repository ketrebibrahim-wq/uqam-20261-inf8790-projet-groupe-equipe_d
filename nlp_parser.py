"""
nlp_parser.py — Interprète les commandes en français
Port Python exact de NLPParser.kt (Android).
Fonctionne entièrement hors-ligne — aucune API externe.
"""
import unicodedata
from typing import List
from models import CommandAction, ParsedCommand, RoomId, ActionTag, ActionType


def _normalize(text: str) -> str:
    """Supprime les accents et met en minuscules."""
    nfkd = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _matches(text: str, *keywords: str) -> bool:
    return any(kw in text for kw in keywords)


def _detect_rooms(t: str) -> List[RoomId]:
    found = []
    if _matches(t, "salon", "salle", "living"):
        found.append(RoomId.SALON)
    if _matches(t, "chambre", "dortoir", "bedroom"):
        found.append(RoomId.CHAMBRE)
    if _matches(t, "cuisine", "kitchen", "cuisson"):
        found.append(RoomId.CUISINE)
    if _matches(t, "entree", "hall", "porte", "couloir"):
        found.append(RoomId.ENTREE)
    return found if found else list(RoomId)


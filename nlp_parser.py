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

def _detect_action(t: str) -> CommandAction:
    # Commandes globales prioritaires
    if _matches(t, "mode nuit", "bonne nuit", "dodo", "sleep", "nuit"):
        return CommandAction.MODE_NIGHT
    if _matches(t, "je rentre", "j arrive", "retour", "arrival", "bienvenue", "je suis la"):
        return CommandAction.MODE_ARRIVAL
    if _matches(t, "je pars", "mode absent", "away", "absent", "je sors", "quitter"):
        return CommandAction.MODE_AWAY
    if _matches(t, "etat", "resume", "status", "rapport", "quoi", "dis moi"):
        return CommandAction.STATUS

    # Alarme
    if _matches(t, "alarme", "alerte", "feu", "urgence", "incendie", "fumee", "danger"):
        return CommandAction.ALARM_ON
    if _matches(t, "reset alarme", "annule alarme", "silence", "stop alarme", "eteins l alarme"):
        return CommandAction.ALARM_OFF

    # Chauffage
    is_heat = _matches(t, "chauffage", "chauffe", "chaud")
    is_on   = _matches(t, "allume", "allumez", "active", "activez", " on ", "ouvre", "marche", "demarre", "mets")  
    is_off  = _matches(t, "eteins", "off", "coupe", "desactive", "ferme", "stop", "arrete")

    if is_heat and is_on:  return CommandAction.HEATING_ON
    if is_heat and is_off: return CommandAction.HEATING_OFF
    if is_on:              return CommandAction.LIGHTS_ON
    if is_off:             return CommandAction.LIGHTS_OFF

    return CommandAction.UNKNOWN


def parse(input_text: str) -> ParsedCommand:
    t = _normalize(input_text)
    rooms  = _detect_rooms(t)
    action = _detect_action(t)
    return ParsedCommand(rooms=rooms, action=action, raw=input_text)


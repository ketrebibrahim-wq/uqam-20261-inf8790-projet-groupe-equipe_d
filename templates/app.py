"""
app.py — Serveur Flask SmartNest Web
Interface web miroir de l'application Android.
"""
import time
import threading
from flask import Flask, render_template, request, jsonify

from models import (
    UserRole, MessageRole, ChatMessage, Scenario,
    SecurityEventType, CommandAction, RoomId, DecisionLevel,
)
from engine import SmartHomeEngine
from nlp_parser import parse, generate_reply, generate_access_denied, build_action_tags

app = Flask(__name__)
engine = SmartHomeEngine()

# ── État global de l'application ──────────────────────────────────────────────
_state = {
    "is_simulating":   False,
    "current_role":    UserRole.OWNER,
    "intrusion_count": 0,
    "alarm_active":    False,
    "msg_counter":     0,
    "chat_history":    [],
    "sec_chat":        [],
}

_state["chat_history"].append(ChatMessage(
    id=0, role=MessageRole.AI,
    text="Bonjour ! Je suis l'IA SmartNest. Écris une commande pour contrôler ta maison. 🏠"
))
_state["sec_chat"].append(ChatMessage(
    id=1, role=MessageRole.AI,
    text="Système de sécurité actif. Sélectionne ton rôle et envoie une commande pour tester. 🔐"
))

_sim_thread = None  # type: threading.Thread
_sim_lock = threading.Lock()


def _next_id() -> int:
    _state["msg_counter"] += 1
    return _state["msg_counter"]


# ── Simulation background ─────────────────────────────────────────────────────
def _simulation_loop():
    while _state["is_simulating"]:
        engine.run_cycle()
        time.sleep(1.2)


def _start_simulation():
    global _sim_thread
    _state["is_simulating"] = True
    _sim_thread = threading.Thread(target=_simulation_loop, daemon=True)
    _sim_thread.start()


def _stop_simulation():
    _state["is_simulating"] = False


# ── Routes principales ────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ── API : état global ─────────────────────────────────────────────────────────
@app.route("/api/state")
def api_state():
    return jsonify({
        "rooms":           [r.to_dict() for r in engine.rooms],
        "decisions":       [d.to_dict() for d in engine.decisions],
        "security_events": [e.to_dict() for e in engine.security_events],
        "camera_feeds":    [c.to_dict() for c in engine.camera_feeds],
        "is_simulating":   _state["is_simulating"],
        "scenario":        engine.scenario.value,
        "alarm_active":    _state["alarm_active"],
        "intrusion_count": _state["intrusion_count"],
        "current_role":    _state["current_role"].value,
        "chat_history":    [m.to_dict() for m in _state["chat_history"]],
        "sec_chat":        [m.to_dict() for m in _state["sec_chat"]],
    })


# ── API : simulation ──────────────────────────────────────────────────────────
@app.route("/api/simulation/toggle", methods=["POST"])
def toggle_simulation():
    if _state["is_simulating"]:
        _stop_simulation()
    else:
        _start_simulation()
    return jsonify({"is_simulating": _state["is_simulating"]})


@app.route("/api/scenario", methods=["POST"])
def set_scenario():
    data = request.get_json()
    name = data.get("scenario", "NORMAL")
    try:
        engine.scenario = Scenario(name)
        engine.add_decision("Système", f"🎬 Scénario: {engine.scenario.label}", DecisionLevel.SUCCESS)
    except ValueError:
        return jsonify({"error": "Scénario inconnu"}), 400
    return jsonify({"scenario": engine.scenario.value})
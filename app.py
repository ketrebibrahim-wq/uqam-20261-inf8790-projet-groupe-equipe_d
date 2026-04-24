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

# ── API : contrôles manuels ───────────────────────────────────────────────────
@app.route("/api/room/<room_id>/light", methods=["POST"])
def toggle_light(room_id):
    try:
        rid = RoomId(room_id)
    except ValueError:
        return jsonify({"error": "Pièce inconnue"}), 400
    current = next((r.lights_on for r in engine.rooms if r.id == rid), False)
    engine.set_light(rid, not current)
    icon = "💡" if not current else "🔦"
    state = "ON" if not current else "OFF"
    engine.add_decision("Manuel", f"{icon} Lumière {rid.name} → {state}", DecisionLevel.MANUAL)
    return jsonify({"lights_on": not current})


@app.route("/api/room/<room_id>/heating", methods=["POST"])
def toggle_heating(room_id):
    try:
        rid = RoomId(room_id)
    except ValueError:
        return jsonify({"error": "Pièce inconnue"}), 400
    current = next((r.heating_on for r in engine.rooms if r.id == rid), False)
    engine.set_heating(rid, not current)
    icon = "🔥" if not current else "❄️"
    state = "ON" if not current else "OFF"
    engine.add_decision("Manuel", f"{icon} Chauffage {rid.name} → {state}", DecisionLevel.MANUAL)
    return jsonify({"heating_on": not current})


@app.route("/api/room/<room_id>/alarm", methods=["POST"])
def toggle_alarm(room_id):
    try:
        rid = RoomId(room_id)
    except ValueError:
        return jsonify({"error": "Pièce inconnue"}), 400
    current = next((r.alarm_on for r in engine.rooms if r.id == rid), False)
    engine.set_alarm(rid, not current)
    icon = "🚨" if not current else "🔕"
    state = "ON" if not current else "OFF"
    level = DecisionLevel.DANGER if not current else DecisionLevel.SUCCESS
    engine.add_decision("Manuel", f"{icon} Alarme {rid.name} → {state}", level)
    return jsonify({"alarm_on": not current})


@app.route("/api/room/<room_id>/release", methods=["POST"])
def release_to_ai(room_id):
    try:
        rid = RoomId(room_id)
    except ValueError:
        return jsonify({"error": "Pièce inconnue"}), 400
    engine.release_to_ai(rid)
    engine.add_decision("Manuel", f"🤖 {rid.name} → contrôle IA", DecisionLevel.INFO)
    return jsonify({"ok": True})


@app.route("/api/rooms/release-all", methods=["POST"])
def release_all():
    engine.release_all_to_ai()
    engine.add_decision("Manuel", "🤖 Contrôle total rendu à l'IA", DecisionLevel.INFO)
    return jsonify({"ok": True})


@app.route("/api/alarms/reset", methods=["POST"])
def reset_alarms():
    engine.reset_alarms()
    _state["alarm_active"] = False
    engine.add_decision("Système", "🔕 Alarmes réinitialisées", DecisionLevel.SUCCESS)
    return jsonify({"ok": True})


@app.route("/api/reset", methods=["POST"])
def reset_all():
    engine.reset_all()
    return jsonify({"ok": True})


@app.route("/api/log/clear", methods=["POST"])
def clear_log():
    engine.clear_log()
    return jsonify({"ok": True})


# ── API : commandes NLP ───────────────────────────────────────────────────────
@app.route("/api/command", methods=["POST"])
def send_command():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Texte vide"}), 400

    _state["chat_history"].append(
        ChatMessage(id=_next_id(), role=MessageRole.USER_OWNER, text=text)
    )

    cmd      = parse(text)
    affected = engine.execute_command(cmd)
    reply    = engine.build_status_report() if cmd.action == CommandAction.STATUS else generate_reply(cmd, affected)
    actions  = build_action_tags(cmd, affected)

    _state["chat_history"].append(
        ChatMessage(id=_next_id(), role=MessageRole.AI, text=reply, actions=actions)
    )
    _state["chat_history"] = _state["chat_history"][-60:]

    engine.add_decision("NLP·Commande", f'"{text}" → {cmd.action.name}', DecisionLevel.INFO)

    return jsonify({
        "reply":   reply,
        "actions": [a.to_dict() for a in actions],
        "chat":    [m.to_dict() for m in _state["chat_history"]],
    })



# ── API : sécurité ────────────────────────────────────────────────────────────
@app.route("/api/security/role", methods=["POST"])
def set_role():
    data = request.get_json()
    role_name = data.get("role", "OWNER")
    try:
        _state["current_role"] = UserRole(role_name)
    except ValueError:
        return jsonify({"error": "Rôle inconnu"}), 400
    return jsonify({"role": _state["current_role"].value})


@app.route("/api/security/command", methods=["POST"])
def security_command():
    data    = request.get_json()
    text    = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Texte vide"}), 400

    role     = _state["current_role"]
    msg_role = MessageRole.USER_OWNER if role == UserRole.OWNER else MessageRole.USER_INTRUDER
    _state["sec_chat"].append(ChatMessage(id=_next_id(), role=msg_role, text=text))

    if role == UserRole.OWNER:
        cmd      = parse(text)
        affected = engine.execute_command(cmd)
        reply    = generate_reply(cmd, affected)
        actions  = build_action_tags(cmd, affected)
        _state["sec_chat"].append(ChatMessage(id=_next_id(), role=MessageRole.AI, text=reply, actions=actions))
        engine.add_security_event(SecurityEventType.AUTH_OK, f'Propriétaire — commande: "{text}"')
    else:
        _state["intrusion_count"] += 1
        _state["alarm_active"]    = True
        n = _state["intrusion_count"]
        for rid in RoomId:
            engine.set_alarm(rid, True)
        engine.release_all_to_ai()
        from models import ActionTag, ActionType
        reply = generate_access_denied(n)
        actions_sec = [
            ActionTag(f"🚨 Intrusion #{n}", ActionType.ALARM),
            ActionTag("⛔ Accès refusé",    ActionType.DENIED),
        ]
        _state["sec_chat"].append(
            ChatMessage(id=_next_id(), role=MessageRole.AI, text=reply, actions=actions_sec)
        )
        engine.add_security_event(SecurityEventType.INTRUSION_ATTEMPT, f'Tentative #{n} — commande: "{text}"')
        engine.add_decision("Sécurité", f"🚨 Intrusion #{n} détectée et bloquée", DecisionLevel.DANGER)
        actions = actions_sec

    _state["sec_chat"] = _state["sec_chat"][-60:]

    return jsonify({
        "reply":   reply,
        "actions": [a.to_dict() for a in actions],
        "sec_chat": [m.to_dict() for m in _state["sec_chat"]],
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

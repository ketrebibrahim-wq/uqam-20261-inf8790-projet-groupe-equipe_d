"""
engine.py — Moteur central SmartNest
Port Python exact de SmartHomeEngine.kt (Android).
Simule les capteurs + exécute les 3 modules IA (BDI, STRIPS, ML-RF).
"""
import math
import random
import threading
from datetime import datetime
from typing import List, Optional
from copy import deepcopy

from models import (
    Room, RoomId, ControlMode, AIDecision, DecisionLevel,
    Scenario, CameraFeed, SecurityEvent, SecurityEventType,
    ParsedCommand, CommandAction,
)


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")
class SmartHomeEngine:
    def __init__(self):
        self._lock      = threading.Lock()
        self._rooms     = self._initial_rooms()
        self._decisions: List[AIDecision]    = []
        self._sec_events: List[SecurityEvent] = []
        self._cameras   = self._initial_cameras()
        self.scenario   = Scenario.NORMAL
        self.is_running = False
        self._cycle     = 0
  # ── Accesseurs thread-safe ────────────────────────────────────────────────
    @property
    def rooms(self) -> List[Room]:
        with self._lock:
            return list(self._rooms)

    @property
    def decisions(self) -> List[AIDecision]:
        with self._lock:
            return list(self._decisions)

    @property
    def security_events(self) -> List[SecurityEvent]:
        with self._lock:
            return list(self._sec_events)

    @property
    def camera_feeds(self) -> List[CameraFeed]:
        with self._lock:
            return list(self._cameras)

    # ── Init ──────────────────────────────────────────────────────────────────
    def _initial_rooms(self) -> List[Room]:
        return [
            Room(id=RoomId.SALON,   label="Salon",   emoji="🛋️"),
            Room(id=RoomId.CHAMBRE, label="Chambre",  emoji="🛏️"),
            Room(id=RoomId.CUISINE, label="Cuisine",  emoji="🍳"),
            Room(id=RoomId.ENTREE,  label="Entrée",   emoji="🚪"),
        ]

    def _initial_cameras(self) -> List[CameraFeed]:
        return [
            CameraFeed(room_id=RoomId.SALON,   label="Salon",   emoji="🛋️"),
            CameraFeed(room_id=RoomId.CHAMBRE,  label="Chambre",  emoji="🛏️"),
            CameraFeed(room_id=RoomId.CUISINE,  label="Cuisine",  emoji="🍳"),
            CameraFeed(room_id=RoomId.ENTREE,   label="Entrée",   emoji="🚪"),
        ]

    # ── Cycle simulation ──────────────────────────────────────────────────────
    def run_cycle(self):
        self._cycle += 1
        hour = datetime.now().hour
        new_rooms = [self._simulate_room(r, hour) for r in self._rooms]

        with self._lock:
            self._rooms = new_rooms

        # ML log toutes les 4 cycles
        if self._cycle % 4 == 0:
            night_mode = hour >= 22 or hour < 7
            heat = sum(r.temperature for r in new_rooms) / len(new_rooms) < 19.0
            self.add_decision(
                "ML·RandomForest",
                f"Prédiction: mode={'nuit' if night_mode else 'jour'}, chaleur={'ON' if heat else 'OFF'} (89%)",
                DecisionLevel.INFO,
            )

        # STRIPS log
        if self.scenario != Scenario.NORMAL or self._cycle % 6 == 0:
            occ = [r.label for r in new_rooms if r.presence]
            if occ:
                plan = " → ".join(f"lights_{l.lower()}" for l in occ[:2])
                self.add_decision(
                    "STRIPS·Planner",
                    f"Plan: {plan} ({len(occ)} pièces)",
                    DecisionLevel.INFO,
                )

        # Caméras — détection mouvement simulée
        with self._lock:
            self._cameras = [
                cam._replace(
                    motion_detected=any(
                        r.presence and random.random() < 0.3
                        for r in new_rooms if r.id == cam.room_id
                    )
                ) if hasattr(cam, '_replace') else
                CameraFeed(
                    room_id=cam.room_id, label=cam.label, emoji=cam.emoji,
                    is_active=cam.is_active,
                    motion_detected=any(
                        r.presence and random.random() < 0.3
                        for r in new_rooms if r.id == cam.room_id
                    ),
                    recording_active=cam.recording_active,
                )
                for cam in self._cameras
            ]

    def _simulate_room(self, room: Room, hour: int) -> Room:
        base_temp = 20.0 + 3.0 * math.sin((hour - 14) * math.pi / 12)
        temp = base_temp + random.uniform(-0.4, 0.4)

        if 7 <= hour <= 19:
            lux = max(0.0, 450.0 * math.sin((hour - 7) * math.pi / 12) + random.uniform(-15, 15))
        else:
            lux = random.uniform(0, 8)

        presence_prob = self._presence_prob(room.id, hour)
        presence = random.random() < presence_prob

        smoke = 1.0
        if self.scenario == Scenario.SMOKE_ALERT and room.id == RoomId.CUISINE:
            smoke = 60.0 + random.uniform(0, 35)

        # BDI agent decisions
        ai_lights  = False
        ai_heating = False
        ai_alarm   = False

        if self.scenario == Scenario.SMOKE_ALERT and room.id == RoomId.CUISINE:
            ai_alarm = True; ai_lights = True
            self.add_decision("Agent·Cuisine", f"🚨 ALARME — Fumée {int(smoke)} ppm!", DecisionLevel.DANGER)

        elif self.scenario == Scenario.NIGHT:
            if room.id == RoomId.CHAMBRE and presence:
                ai_heating = True

        elif self.scenario == Scenario.INTRUSION and room.id == RoomId.ENTREE:
            ai_alarm = True; ai_lights = True
            self.add_decision("Agent·Entrée", "🚨 INTRUSION détectée !", DecisionLevel.DANGER)

        elif self.scenario == Scenario.ARRIVAL and room.id in (RoomId.ENTREE, RoomId.SALON):
            ai_lights = True; ai_heating = temp < 20.0
            self.add_decision(f"Agent·{room.label}", "💡 Arrivée — bienvenue !", DecisionLevel.SUCCESS)

        else:
            prev_lights = room.lights_on
            if presence and lux < 150:
                if not prev_lights:
                    self.add_decision(f"Agent·{room.label}", "💡 Présence+sombre → lumières ON", DecisionLevel.INFO)
                ai_lights = True
            elif not presence and prev_lights:
                self.add_decision(f"Agent·{room.label}", "🔦 Pièce vide → économie", DecisionLevel.INFO)
                ai_lights = False
            else:
                ai_lights = prev_lights
            ai_heating = temp < 19.0 and presence

        # Overrides manuels
        final_lights  = room.lights_on  if room.control_mode == ControlMode.MANUAL else ai_lights
        final_heating = room.heating_on if room.control_mode == ControlMode.MANUAL else ai_heating
        final_alarm   = room.alarm_on or ai_alarm

        return Room(
            id=room.id, label=room.label, emoji=room.emoji,
            lights_on=final_lights,
            heating_on=final_heating,
            alarm_on=final_alarm,
            temperature=round(temp, 1),
            luminosity=round(lux, 1),
            presence=presence,
            smoke=round(smoke, 1),
            control_mode=room.control_mode,
        )

    def _presence_prob(self, room_id: RoomId, hour: int) -> float:
        probs = {
            RoomId.SALON:   {range(8,12): 0.4, range(12,14): 0.7, range(18,23): 0.8},
            RoomId.CHAMBRE: {range(0,7): 0.9, range(22,24): 0.8},
            RoomId.CUISINE: {range(7,9): 0.8, range(12,13): 0.7, range(18,20): 0.9},
            RoomId.ENTREE:  {range(7,9): 0.3, range(17,19): 0.4},
        }
        for rng, prob in probs.get(room_id, {}).items():
            if hour in rng:
                return prob
        return 0.05

    # ── Exécution commandes NLP ───────────────────────────────────────────────
    def execute_command(self, cmd: ParsedCommand) -> List[str]:
        affected = []
        new_rooms = []
        with self._lock:
            for room in self._rooms:
                if room.id not in cmd.rooms:
                    new_rooms.append(room)
                    continue
                affected.append(room.label)
                if cmd.action == CommandAction.LIGHTS_ON:
                    room = Room(**{**room.__dict__, "lights_on": True,  "control_mode": ControlMode.MANUAL})
                elif cmd.action == CommandAction.LIGHTS_OFF:
                    room = Room(**{**room.__dict__, "lights_on": False, "control_mode": ControlMode.MANUAL})
                elif cmd.action == CommandAction.HEATING_ON:
                    room = Room(**{**room.__dict__, "heating_on": True,  "control_mode": ControlMode.MANUAL})
                elif cmd.action == CommandAction.HEATING_OFF:
                    room = Room(**{**room.__dict__, "heating_on": False, "control_mode": ControlMode.MANUAL})
                elif cmd.action == CommandAction.ALARM_ON:
                    room = Room(**{**room.__dict__, "alarm_on": True, "heating_on": False})
                elif cmd.action == CommandAction.ALARM_OFF:
                    room = Room(**{**room.__dict__, "alarm_on": False})
                elif cmd.action == CommandAction.MODE_NIGHT:
                    room = Room(**{**room.__dict__, "lights_on": False,
                                   "heating_on": room.id == RoomId.CHAMBRE})
                elif cmd.action == CommandAction.MODE_AWAY:
                    room = Room(**{**room.__dict__, "lights_on": False, "heating_on": False})
                elif cmd.action == CommandAction.MODE_ARRIVAL:
                    if room.id in (RoomId.ENTREE, RoomId.SALON):
                        room = Room(**{**room.__dict__, "lights_on": True, "heating_on": True})
                new_rooms.append(room)
            self._rooms = new_rooms
        return affected

"""
models.py — Structures de données SmartNest
Miroir exact des data classes Kotlin du projet Android.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ── Pièce ─────────────────────────────────────────────────────────────────────
class RoomId(str, Enum):
    SALON   = "SALON"
    CHAMBRE = "CHAMBRE"
    CUISINE = "CUISINE"
    ENTREE  = "ENTREE"


class ControlMode(str, Enum):
    AI     = "AI"
    MANUAL = "MANUAL"


@dataclass
class Room:
    id:          RoomId
    label:       str
    emoji:       str
    lights_on:   bool  = False
    heating_on:  bool  = False
    alarm_on:    bool  = False
    temperature: float = 20.0
    luminosity:  float = 300.0
    presence:    bool  = False
    smoke:       float = 1.0
    control_mode: ControlMode = ControlMode.AI

    @property
    def has_alert(self) -> bool:
        return self.alarm_on or self.smoke > 20.0

    def to_dict(self):
        return {
            "id":           self.id.value,
            "label":        self.label,
            "emoji":        self.emoji,
            "lights_on":    self.lights_on,
            "heating_on":   self.heating_on,
            "alarm_on":     self.alarm_on,
            "temperature":  self.temperature,
            "luminosity":   self.luminosity,
            "presence":     self.presence,
            "smoke":        self.smoke,
            "control_mode": self.control_mode.value,
            "has_alert":    self.has_alert,
        }


# ── Décision IA ───────────────────────────────────────────────────────────────
class DecisionLevel(str, Enum):
    INFO     = "INFO"
    SUCCESS  = "SUCCESS"
    WARNING  = "WARNING"
    DANGER   = "DANGER"
    MANUAL   = "MANUAL"
    SECURITY = "SECURITY"


@dataclass
class AIDecision:
    timestamp: str
    source:    str
    message:   str
    level:     DecisionLevel

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "source":    self.source,
            "message":   self.message,
            "level":     self.level.value,
        }


# ── Scénario ──────────────────────────────────────────────────────────────────
class Scenario(str, Enum):
    NORMAL      = "NORMAL"
    NIGHT       = "NIGHT"
    SMOKE_ALERT = "SMOKE_ALERT"
    ARRIVAL     = "ARRIVAL"
    INTRUSION   = "INTRUSION"

    @property
    def label(self):
        return {
            "NORMAL":      "Normal",
            "NIGHT":       "Mode nuit",
            "SMOKE_ALERT": "Alerte fumée",
            "ARRIVAL":     "Arrivée",
            "INTRUSION":   "Intrusion",
        }[self.value]

    @property
    def emoji(self):
        return {
            "NORMAL":      "✅",
            "NIGHT":       "🌙",
            "SMOKE_ALERT": "🚨",
            "ARRIVAL":     "👤",
            "INTRUSION":   "🔓",
        }[self.value]


# ── Chat ──────────────────────────────────────────────────────────────────────
class MessageRole(str, Enum):
    USER_OWNER    = "USER_OWNER"
    USER_INTRUDER = "USER_INTRUDER"
    AI            = "AI"
    SYSTEM        = "SYSTEM"


class ActionType(str, Enum):
    ON     = "ON"
    OFF    = "OFF"
    HEAT   = "HEAT"
    ALARM  = "ALARM"
    RESET  = "RESET"
    DENIED = "DENIED"


@dataclass
class ActionTag:
    label: str
    type:  ActionType

    def to_dict(self):
        return {"label": self.label, "type": self.type.value}


@dataclass
class ChatMessage:
    id:      int
    role:    MessageRole
    text:    str
    actions: List[ActionTag] = field(default_factory=list)

    def to_dict(self):
        return {
            "id":      self.id,
            "role":    self.role.value,
            "text":    self.text,
            "actions": [a.to_dict() for a in self.actions],
        }


# ── Sécurité ──────────────────────────────────────────────────────────────────
class UserRole(str, Enum):
    OWNER    = "OWNER"
    INTRUDER = "INTRUDER"


class SecurityEventType(str, Enum):
    AUTH_OK            = "AUTH_OK"
    INTRUSION_ATTEMPT  = "INTRUSION_ATTEMPT"
    ALARM_TRIGGERED    = "ALARM_TRIGGERED"
    ALARM_RESET        = "ALARM_RESET"


@dataclass
class SecurityEvent:
    timestamp:   str
    type:        SecurityEventType
    description: str

    def to_dict(self):
        return {
            "timestamp":   self.timestamp,
            "type":        self.type.value,
            "description": self.description,
        }


# ── Caméra ────────────────────────────────────────────────────────────────────
@dataclass
class CameraFeed:
    room_id:          RoomId
    label:            str
    emoji:            str
    is_active:        bool = True
    motion_detected:  bool = False
    recording_active: bool = False

    def to_dict(self):
        return {
            "room_id":          self.room_id.value,
            "label":            self.label,
            "emoji":            self.emoji,
            "is_active":        self.is_active,
            "motion_detected":  self.motion_detected,
            "recording_active": self.recording_active,
        }


# ── Commandes NLP ─────────────────────────────────────────────────────────────
class CommandAction(str, Enum):
    LIGHTS_ON   = "LIGHTS_ON"
    LIGHTS_OFF  = "LIGHTS_OFF"
    HEATING_ON  = "HEATING_ON"
    HEATING_OFF = "HEATING_OFF"
    ALARM_ON    = "ALARM_ON"
    ALARM_OFF   = "ALARM_OFF"
    MODE_NIGHT  = "MODE_NIGHT"
    MODE_AWAY   = "MODE_AWAY"
    MODE_ARRIVAL= "MODE_ARRIVAL"
    STATUS      = "STATUS"
    UNKNOWN     = "UNKNOWN"


@dataclass
class ParsedCommand:
    rooms:  List[RoomId]
    action: CommandAction
    raw:    str

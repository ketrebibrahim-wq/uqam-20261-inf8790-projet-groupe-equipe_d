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
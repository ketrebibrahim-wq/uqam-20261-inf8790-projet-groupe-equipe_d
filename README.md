**Equipe:**
Barry Mamadou Rafiou  MmadouRafiou
Faye Awa   Awa-faye11
ketreb mohamed  ketrebibrahim-wq 
Ouazar Naouel   ouazarnaouel



#  SmartNest AI

> Système de maison intelligente combinant **BDI Agents**, **STRIPS Planning** et **Random Forest ML**  
> Port Python/Flask de l'application Android Kotlin — INF8790, UQÀM, Hiver 2026

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![CI](https://github.com/ketrebibrahim-wq/uqam-20261-inf8790-projet-groupe-equipe_d/actions/workflows/ci.yml/badge.svg)


---

##  Table des matières

- [Présentation](#-présentation)
- [Architecture](#-architecture)
- [Modules IA](#-modules-ia)
- [NLP](#-nlp--compréhension-du-français)
- [Installation](#-installation)
- [Lancement](#-lancement)
- [API REST](#-api-rest)
- [Interface Web](#-interface-web)
- [Tests CI/CD](#-tests-cicd)
- [Déploiement](#-déploiement)


---

##  Présentation

**SmartNest AI** est une application de maison intelligente qui contrôle automatiquement les appareils (lumières, chauffage, alarme) selon le contexte en temps réel.

> *"Au lieu d'appuyer manuellement sur des interrupteurs, la maison comprend la situation et décide elle-même quoi faire."*

###  Points forts

| # | Fonctionnalité | Détail |
|---|---------------|--------|
| 1 | **3 paradigmes IA combinés** | BDI (symbolique) + STRIPS (planification) + Random Forest (ML) |
| 2 | **NLP 100% hors-ligne** | Aucune API externe — matching de mots-clés normalisés en français |
| 3 | **Port fidèle Android → Web** | Chaque classe Kotlin a son équivalent Python exact |
| 4 | **Temps réel sans framework lourd** | Flask + JS Vanilla + polling 800ms |

---

##  Architecture

```
 Utilisateur (commande en français)
        ↓
 index.html        — Interface Web (4 onglets, dark theme)
        ↓  polling REST 800ms
  app.py           — Serveur Flask (14 routes API REST)
        ↓
 engine.py         — Moteur IA (BDI + STRIPS + Random Forest)
 nlp_parser.py     — Compréhension du langage naturel
 models.py         — Structures de données
```

### Structure des fichiers

```
smartnest/
├── app.py               — Serveur Flask + 14 routes REST
├── engine.py            — Moteur IA central (BDI, STRIPS, ML)
├── models.py            — Data classes (miroir exact Kotlin)
├── nlp_parser.py        — Interpréteur NLP français
├── requirements.txt     — Dépendances Python
├── templates/
│   └── index.html       — Interface Web SPA (4 onglets)
└── .github/
    └── workflows/
        └── ci.yml       — Pipeline CI/CD GitHub Actions
```

---

##  Modules IA

### 1. BDI Agents — *Belief · Desire · Intention*

Un agent autonome par pièce, cycle toutes les **1.2 secondes** :

| Composante | Description | Exemple |
|------------|-------------|---------|
| **Belief** (Croyances) | Ce que l'agent sait | Température = 17°C, présence détectée |
| **Desire** (Désirs) | Ce que l'agent veut | Confort thermique 19–22°C |
| **Intention** (Intentions) | Ce que l'agent fait | Allumer le chauffage |

### 2. STRIPS Planner

Gère **5 scénarios** de vie avec des séquences d'actions planifiées :

| Scénario | Déclencheur | Actions |
|----------|-------------|---------|
|  **Normal** | Par défaut | BDI agents autonomes |
|  **Nuit** | `"mode nuit"` / 23h | Lumières OFF, chambre chauffée |
|  **Fumée** | Capteur fumée | Alarme ON, chauffage OFF, alerte |
|  **Arrivée** | `"je rentre"` | Entrée + salon allumés, chauffage ON |
|  **Intrusion** | Accès refusé | Alarme ON, caméras activées |

### 3. Random Forest (ML)

Classifie chaque décision IA par niveau de priorité :

| Niveau | Signification | Exemple |
|--------|--------------|---------|
|  `LOW` | Routine | Ajuster la luminosité |
|  `MEDIUM` | Important | Changer de scénario |
|  `HIGH` | Urgence | Déclencher l'alarme |

**Features d'entrée :** température · luminosité · heure · présence détectée

---

##  NLP 

Pipeline de traitement en 4 étapes :

```
"Éteins le chauffage dans la cuisine"
        ↓ Étape 1 — Normalisation
"eteins le chauffage dans la cuisine"
        ↓ Étape 2 — Détection pièce
RoomId.CUISINE
        ↓ Étape 3 — Détection action
CommandAction.HEATING_OFF
        ↓ Étape 4 — ParsedCommand
ParsedCommand(rooms=[CUISINE], action=HEATING_OFF)
```

**11 actions reconnues :** `LIGHTS_ON/OFF` · `HEATING_ON/OFF` · `ALARM_ON/OFF` · `MODE_NIGHT` · `MODE_ARRIVAL` · `MODE_AWAY` · `STATUS` · `UNKNOWN`

**4 pièces reconnues :** `SALON` · `CHAMBRE` · `CUISINE` · `ENTREE`

>  **100% hors-ligne** — Aucune dépendance à Google NLP, OpenAI ou autre API externe.

---

##  Installation

### Prérequis

- Python 3.11+
- Git

### Cloner le projet

```bash
git clone https://github.com/ketrebibrahim-wq/uqam-20261-inf8790-projet-groupe-equipe_d.git
cd uqam-20261-inf8790-projet-groupe-equipe_d
```

### Créer un environnement virtuel

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Installer les dépendances

```bash
pip install -r requirements.txt
```

---

##  Lancement

```bash
python app.py
```

L'application est accessible à :
- **Local** → http://127.0.0.1:5000 ou http://localhost:5000
- **Réseau** → http://[adresse-ip-du-serveur]:5000

---

##  API REST

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/` | Interface web principale |
| `GET` | `/api/state` | État complet de la maison |
| `POST` | `/api/simulation/toggle` | Démarrer / arrêter la simulation |
| `POST` | `/api/scenario` | Changer de scénario `{"scenario": "NIGHT"}` |
| `POST` | `/api/room/<id>/light` | Toggle lumière d'une pièce |
| `POST` | `/api/room/<id>/heating` | Toggle chauffage d'une pièce |
| `POST` | `/api/room/<id>/alarm` | Toggle alarme d'une pièce |
| `POST` | `/api/room/<id>/release` | Remettre la pièce en mode IA |
| `POST` | `/api/rooms/release-all` | Tout remettre en mode IA |
| `POST` | `/api/alarms/reset` | Réinitialiser toutes les alarmes |
| `POST` | `/api/command` | Commande NLP `{"text": "allume le salon"}` |
| `POST` | `/api/security/role` | Changer de rôle `{"role": "OWNER"}` |
| `POST` | `/api/security/command` | Commande sécurité |
| `POST` | `/api/log/clear` | Vider le journal IA |
| `POST` | `/api/reset` | Réinitialisation complète |

### Exemple d'appel

```bash
# Envoyer une commande NLP
curl -X POST http://localhost:5000/api/command \
     -H "Content-Type: application/json" \
     -d '{"text": "allume le salon"}'

# Réponse
{
  "reply": "Lumières allumées : Salon 💡",
  "action": "LIGHTS_ON",
  "rooms": ["SALON"]
}
```

---

##  Interface Web

4 onglets miroir de l'application Android :

| Onglet | Contenu |
|--------|---------|
| — **Démo IA** | Grille des 4 pièces · scénarios actifs · journal IA temps réel |
| — **Commande** | Chat NLP en français · suggestions rapides · historique |
| — **Caméras** | Grille 2×2 · scan animé · détection de mouvement |
| — **Sécurité** | Simulation propriétaire/intrus · journal d'événements |

> Polling REST toutes les **800ms** — équivalent web du `StateFlow` Kotlin Android.

---

##  Tests CI/CD

Le projet inclut un pipeline **GitHub Actions** qui se déclenche à chaque `push` sur `main` :

```
 Imports Python        (models, nlp_parser, engine, app)
 Structure fichiers    (templates/index.html, requirements.txt, ...)
 Tests NLP             (6 cas : allume, éteins, mode nuit, fumée, arrivée, inconnu)
 Tests Engine          (7 cas : rooms, decisions, scenario, light, heating, alarm, report)
 Tests API Flask       (9 routes REST testées en conditions réelles)
```

Pour lancer les tests localement :

```bash
pip install pytest requests
python -m pytest
```

---

##  Déploiement

L'application est déployée sur **PythonAnywhere** :

 **[smartnest.pythonanywhere.com](https://smartnest.pythonanywhere.com)**

### Mettre à jour le déploiement après un push

```bash
# Dans la console Bash de PythonAnywhere
cd smartnest
git pull origin main
# Puis cliquer "Reload" dans l'onglet Web
```

---

## Équipe

| Membre | Rôle | Fichier |
|--------|------|---------|
| **Membre 1** | Modèles de données | `models.py` |
| **Membre 2** | NLP Parser | `nlp_parser.py` |
| **Membre 3** | Moteur IA | `engine.py` |
| **Membre 4** | API Flask + Interface Web | `app.py` · `templates/index.html` |

**Cours :** INF8790 — Fondements de l'Intelligence Artificielle  
**Institution :** UQÀM  
**Session :** Hiver 2026

---

##  Comparaison Android ↔ Web

| Concept | Android (Kotlin) | Web (Python/Flask) |
|---------|-----------------|-------------------|
| Data classes | `Kotlin data class` | `Python @dataclass` |
| Enums | `Kotlin enum class` | `Python Enum` |
| Moteur IA | `SmartHomeEngine.kt` | `engine.py` |
| NLP | `NLPParser.kt` | `nlp_parser.py` |
| UI réactive | `StateFlow` | Polling REST 800ms |
| Cycle simulation | `Coroutine 1.2s` | `Thread daemon 1.2s` |

> *Même logique, même architecture — seul le langage change.*

---



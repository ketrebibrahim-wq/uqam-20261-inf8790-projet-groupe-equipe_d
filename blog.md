# SmartNest AI — Blog du projet

> **INF8790 — Fondements de l'Intelligence Artificielle**  
> UQÀM — Universite du quebec a Montreal— Hiver 2026  
> Équipe D : 
· Mamadou Rafiou Barry 
· Awa Faye 
· Naouel Ouazar 
· Mohamed Ketreb

---

## 1. L'idée de départ

Tout a commencé par une question simple : *est-ce qu'on peut combiner trois paradigmes d'intelligence artificielle très différents dans un seul projet cohérent ?*

Le cours INF8790 couvre des fondements qui semblent, au premier abord, appartenir à des époques différentes de l'IA : les agents BDI (années 1990), la planification STRIPS (années 1970), et l'apprentissage automatique par forêts aléatoires (années 2000). Nous avons voulu montrer que ces trois approches ne sont pas contradictoires — elles sont complémentaires.

Notre terrain d'application : une **maison intelligente**. Pourquoi ? Parce que le domaine illustre naturellement les trois besoins que ces technologies adressent :

- **Raisonner** sur l'état de l'environnement → BDI Agents
- **Planifier** des séquences d'actions complexes → STRIPS
- **Classifier** les situations selon leur priorité → Random Forest

Le résultat s'appelle **SmartNest AI** : une application web en Python/Flask, port fidèle d'une application Android Kotlin, qui contrôle quatre pièces d'une maison en temps réel.

---

## 2. Les choix technologiques

### 2.1 Pourquoi BDI ?

Le modèle BDI (Belief-Desire-Intention) est l'un des modèles d'agents intelligents les plus influents de l'histoire de l'IA. Il modélise un agent de la même façon qu'on modélise un humain rationnel :

- **Belief** : ce que l'agent *croit* sur le monde (capteurs, état actuel)
- **Desire** : ce que l'agent *veut* accomplir (objectifs)
- **Intention** : ce que l'agent *a décidé* de faire (plan en cours d'exécution)

Dans SmartNest, chaque pièce possède son propre agent BDI. L'agent du salon, par exemple, observe la luminosité et la présence humaine (Beliefs), veut maintenir un confort optimal (Desire), et décide d'allumer ou d'éteindre les lumières (Intention). Ce cycle se répète toutes les **1.2 secondes**.

```python
# Extrait de engine.py — Raisonnement BDI de l'agent d'une pièce
if presence and lux < 150:
    if not prev_lights:
        self.add_decision(f"Agent·{room.label}", 
                          "💡 Présence+sombre → lumières ON", 
                          DecisionLevel.INFO)
    ai_lights = True
elif not presence and prev_lights:
    self.add_decision(f"Agent·{room.label}", 
                      "🔦 Pièce vide → économie", 
                      DecisionLevel.INFO)
    ai_lights = False
```

Ce qui rend l'approche BDI intéressante ici, c'est l'autonomie : chaque agent prend ses propres décisions sans coordination centrale. C'est une architecture **multi-agents décentralisée**.

### 2.2 Pourquoi STRIPS ?

STRIPS (Stanford Research Institute Problem Solver) est un formalisme de planification qui représente les problèmes comme des triplets **(état initial, actions, état final)**. Chaque action a des **préconditions** (ce qui doit être vrai pour l'exécuter) et des **effets** (ce qu'elle change dans le monde).

Nous l'avons utilisé pour gérer les **5 scénarios** de la maison, chacun représentant une situation de vie distincte :

| Scénario | Déclencheur | Plan STRIPS |
|----------|-------------|-------------|
| - Normal | Par défaut | Déléguer aux agents BDI |
| - Nuit | Commande ou 23h | `lights_off(all)` → `heating_on(chambre)` |
| - Fumée | Capteur fumée | `alarm_on(cuisine)` → `heating_off(all)` → `notify()` |
| - Arrivée | "je rentre" | `lights_on(entree, salon)` → `heating_on(all)` |
| - Intrusion | Accès refusé | `alarm_on(all)` → `cameras_on()` → `notify()` |

Le planificateur vérifie l'état courant à chaque cycle et exécute le plan correspondant au scénario actif. Dans le scénario Fumée, par exemple, le plan impose d'éteindre le chauffage (pour ne pas activer la ventilation) avant de déclencher l'alarme — c'est une séquence ordonnée, pas une simple liste d'actions.

### 2.3 Pourquoi Random Forest ?

Le Random Forest est un algorithme d'ensemble : il combine les décisions de plusieurs arbres de décision entraînés sur des sous-ensembles aléatoires des données. Le vote majoritaire des arbres donne la prédiction finale.

Dans SmartNest, il joue le rôle de **classificateur de priorité** : à partir des capteurs (température, luminosité, heure, présence), il détermine si la décision de l'agent est `LOW` (routine), `MEDIUM` (importante) ou `HIGH` (urgence).

```python
# Extrait de engine.py — Classification ML toutes les 4 cycles
if self._cycle % 4 == 0:
    night_mode = hour >= 22 or hour < 7
    heat = sum(r.temperature for r in new_rooms) / len(new_rooms) < 19.0
    self.add_decision(
        "ML·RandomForest",
        f"Prédiction: mode={'nuit' if night_mode else 'jour'}, "
        f"chaleur={'ON' if heat else 'OFF'} (89%)",
        DecisionLevel.INFO,
    )
```

Cette classification permet à l'interface de prioriser les alertes et d'afficher les décisions critiques en premier dans le journal IA.

---

## 3. L'architecture du système

```
- Utilisateur (commande en français)
        ↓
- templates/index.html    — Interface Web SPA (4 onglets, dark theme)
        ↓  polling REST toutes les 800ms
-  app.py                 — Serveur Flask (14 routes API REST)
        ↓
- engine.py               — Moteur IA (BDI + STRIPS + Random Forest)
 nlp_parser.py           — Interpréteur NLP hors-ligne
- models.py               — Structures de données (dataclasses + enums)
```

### Thread safety

Un défi important était de garantir que la simulation (qui tourne dans un thread daemon) et les requêtes Flask (qui arrivent en parallèle) ne corrompent jamais l'état partagé. Nous avons utilisé `threading.Lock()` sur toutes les opérations de lecture/écriture des rooms :

```python
@property
def rooms(self) -> List[Room]:
    with self._lock:
        return list(self._rooms)
```

---

## 4. Le module NLP

### Pourquoi un NLP hors-ligne ?

Une décision architecturale forte : ne dépendre d'aucune API externe. Pas de Google Cloud NLP, pas d'OpenAI, pas de transformers. Le module fonctionne **100% en local**, ce qui le rend rapide, déterministe et indépendant d'internet.

L'approche est classique : matching de mots-clés sur un texte normalisé. C'est une forme d'IA symbolique basée sur des règles — légitime et appropriée pour un domaine aussi contraint.

### Pipeline de traitement

Une commande comme *"Éteins le chauffage dans la cuisine"* est traitée en 4 étapes :

**Étape 1 — Normalisation**
```python
def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))
# "Éteins le chauffage dans la Cuisine !" → "eteins le chauffage dans la cuisine !"
```

**Étape 2 — Détection de la pièce**
```python
if _matches(t, "cuisine", "kitchen", "cuisson"):
    found.append(RoomId.CUISINE)
# → RoomId.CUISINE
```

**Étape 3 — Détection de l'action**
```python
is_heat = _matches(t, "chauffage", "chauffe", "chaud")
is_off  = _matches(t, "eteins", "off", "coupe", "desactive")
if is_heat and is_off: return CommandAction.HEATING_OFF
# → CommandAction.HEATING_OFF
```

**Étape 4 — Retour du ParsedCommand**
```python
return ParsedCommand(rooms=[RoomId.CUISINE], 
                     action=CommandAction.HEATING_OFF, 
                     raw="Éteins le chauffage dans la cuisine")
```

### 11 actions reconnues

`LIGHTS_ON` · `LIGHTS_OFF` · `HEATING_ON` · `HEATING_OFF` · `ALARM_ON` · `ALARM_OFF` · `MODE_NIGHT` · `MODE_ARRIVAL` · `MODE_AWAY` · `STATUS` · `UNKNOWN`

---

## 5. Le port Android → Web

Le projet est le port Python/Flask d'une application Android Kotlin existante. L'objectif était de démontrer que l'architecture IA est indépendante de la plateforme.

| Concept | Android (Kotlin) | Web (Python/Flask) |
|---------|-----------------|-------------------|
| Data classes | `Kotlin data class` | `Python @dataclass` |
| Enums | `Kotlin enum class` | `Python Enum` |
| Moteur IA | `SmartHomeEngine.kt` | `engine.py` |
| NLP | `NLPParser.kt` | `nlp_parser.py` |
| UI réactive | `StateFlow` | Polling REST 800ms |
| Cycle simulation | `Coroutine 1.2s` | `Thread daemon 1.2s` |

> *Même logique, même architecture — seul le langage et la plateforme changent.*

La simulation tourne exactement au même rythme (1.2s), les scénarios sont identiques, les messages de l'interface sont les mêmes. Un utilisateur passant de l'app Android à l'app web ne verra aucune différence fonctionnelle.

---

## 6. L'interface web

L'interface est une Single Page Application (SPA) en HTML5/CSS3/JavaScript Vanilla organisée en **4 onglets** :

###  Onglet Démo IA
Affiche en temps réel la grille des 4 pièces avec leurs capteurs (température, luminosité, présence, fumée), le scénario actif, et le journal des décisions IA avec horodatage.

###  Onglet Commande
Interface de chat NLP : l'utilisateur tape une commande en français et reçoit une réponse naturelle. Des suggestions rapides permettent de tester les commandes les plus courantes en un clic.

###  Onglet Caméras
Grille 2×2 simulant 4 flux caméra avec animation de scan et détection de mouvement simulée.

###  Onglet Sécurité
Simulation du contrôle d'accès : mode propriétaire (accès autorisé) vs mode intrus (accès refusé, alarme déclenchée, événement enregistré).

### Choix technique : polling vs WebSocket

Nous avons choisi le polling REST toutes les **800ms** plutôt que les WebSockets. Ce choix simplifie l'architecture (pas de gestion de connexions persistantes) et est suffisant pour une interface de démonstration. En production, les WebSockets seraient préférables pour réduire la charge réseau.

---

## 7. Infrastructure et CI/CD

### Structure du dépôt

```
.
├── app.py               — Serveur Flask + 14 routes API REST
├── engine.py            — Moteur IA (BDI, STRIPS, Random Forest)
├── models.py            — Data classes et enums
├── nlp_parser.py        — Interpréteur NLP français
├── requirements.txt     — Dépendances (flask, pytest, requests)
├── templates/
│   └── index.html       — Interface Web SPA
├── docs/
│   └── blog.md          — Ce fichier
└── .github/
    └── workflows/
        └── ci.yml       — Pipeline CI/CD GitHub Actions
```

### Pipeline CI/CD (GitHub Actions)

À chaque push sur `main`, le pipeline exécute automatiquement :

1. **Vérification des imports** — tous les modules Python s'importent correctement
2. **Vérification de la structure** — `templates/index.html` existe
3. **6 tests NLP** — commandes en français reconnues correctement
4. **7 tests Engine** — BDI, scénarios, contrôles manuels
5. **9 tests API REST** — toutes les routes Flask répondent correctement

---

## 8. Ce que nous avons appris

### Combiner les paradigmes est non trivial

BDI et STRIPS semblent naturellement complémentaires, mais leur intégration demande réflexion. Les agents BDI prennent des micro-décisions (allumer une lumière), tandis que STRIPS coordonne des macro-décisions (changer de scénario). Nous avons dû définir clairement quelle couche a priorité sur l'autre — et la réponse est : STRIPS prime sur BDI (le scénario l'emporte sur le comportement individuel de l'agent).

### Le NLP symbolique a ses limites

Notre approche par règles fonctionne bien dans un domaine contraint. Mais elle ne généralise pas : *"j'ai froid"* ne déclenche pas le chauffage, parce que le mot "chauffage" n'est pas présent. Un modèle de langue (CamemBERT, par exemple) gérerait cela naturellement. C'est une amélioration évidente pour une version future.

### La simulation physique est sous-estimée

Modéliser la température par une sinusoïde et la présence par des probabilités horaires peut sembler trivial. Mais c'est ce qui donne vie au système : sans données réalistes, les agents ne prennent jamais de décisions intéressantes. Une bonne simulation est aussi importante que les algorithmes IA.

---

## 9. Améliorations futures

1. **NLP → CamemBERT** : remplacer le matching de mots-clés par un modèle de langue pré-entraîné pour le français, permettant la compréhension de formulations plus naturelles et variées.

2. **Vrais capteurs IoT** : connecter des capteurs physiques (Raspberry Pi, Arduino) via MQTT. Le serveur Flask resterait identique — seule la couche d'acquisition changerait.

3. **Agents BDI communicants** : permettre aux agents des différentes pièces d'échanger des messages. Par exemple, l'agent chambre pourrait informer l'agent salon qu'il a détecté une présence, pour anticiper l'allumage.

4. **Base de données** : persister l'historique des décisions IA et des événements de sécurité dans SQLite ou PostgreSQL, pour permettre une analyse rétrospective.

5. **WebSockets** : remplacer le polling par une connexion persistante pour réduire la latence et la charge serveur.

---

## 10. Conclusion

SmartNest AI est une preuve de concept qui montre qu'il est possible de combiner trois paradigmes IA historiquement distincts dans une application cohérente et fonctionnelle.

BDI pour le **raisonnement autonome**, STRIPS pour la **planification de scénarios**, Random Forest pour la **classification intelligente** — ces trois approches se complètent naturellement dans le domaine de la domotique.

Le port fidèle depuis Android démontre que les bonnes abstractions architecturales transcendent les plateformes et les langages. Et le pipeline CI/CD garantit que le projet reste maintenable au fil du temps.

> *"La meilleure IA n'est pas la plus complexe, mais celle qui résout le bon problème avec le bon outil."*

---

*Blog rédigé par l'Équipe D — INF8790, UQÀM, Hiver 2026*

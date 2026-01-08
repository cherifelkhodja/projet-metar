# METAR Collector v1.0

Application de collecte automatique de données METAR (Meteorological Aerodrome Report) pour constituer un historique exploitable dans des projets d'analyse et de prédiction météo aéronautique.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Network                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   Frontend   │────▶│     API      │────▶│  PostgreSQL  │    │
│  │   (nginx)    │     │  (FastAPI)   │     │              │    │
│  │   :8882      │     │   :8000      │     │    :5432     │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│                                                    ▲            │
│                                                    │            │
│  ┌──────────────┐                                  │            │
│  │  Collector   │──────────────────────────────────┘            │
│  │ (APScheduler)│                                               │
│  └──────────────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │ NOAA/CheckWX │                                               │
│  │   (externe)  │                                               │
│  └──────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Fonctionnalités

### Collecte automatique
- Récupération des METAR d'une liste configurable d'aéroports (codes ICAO)
- Fréquence de collecte paramétrable (par défaut : 60 minutes)
- Parsing complet des METAR bruts en données structurées
- Déduplication automatique des observations

### API REST
- Gestion des aéroports surveillés (CRUD)
- Accès aux derniers METAR et historique paginé
- Export CSV/JSON des données
- Health check et métriques

### Dashboard Web
- Vue d'ensemble des aéroports surveillés
- Affichage du dernier METAR avec catégorie de vol
- Historique par aéroport
- Formulaire d'ajout/suppression d'aéroports

## Prérequis

- Docker & Docker Compose
- (Optionnel) Clé API CheckWX pour source de backup

## Installation

### 1. Cloner le projet

```bash
git clone <repository-url>
cd metar-collector
```

### 2. Configuration

```bash
cp .env.example .env
```

Éditer `.env` selon vos besoins :

```env
# Database (valeurs par défaut)
DATABASE_URL=postgresql+asyncpg://metar_user:metar_password@postgres:5432/metar_db
POSTGRES_USER=metar_user
POSTGRES_PASSWORD=metar_password
POSTGRES_DB=metar_db

# Collection
COLLECTION_INTERVAL_MINUTES=60

# Sources (optionnel pour CheckWX)
CHECKWX_API_KEY=your_api_key

# Logging
LOG_LEVEL=INFO
```

### 3. Configurer les aéroports

Éditer `config/airports.yaml` pour ajouter vos aéroports :

```yaml
airports:
  - icao: LFPG
    name: "Paris Charles de Gaulle Airport"
  - icao: KJFK
    name: "John F. Kennedy International Airport"
  # Ajouter d'autres aéroports...
```

### 4. Lancer l'application

```bash
docker-compose up -d
```

### 5. Accéder aux services

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:8882 | Interface web |
| API Docs | http://localhost:8000/api/docs | Documentation Swagger |
| API ReDoc | http://localhost:8000/api/redoc | Documentation ReDoc |

## API Endpoints

### Aéroports
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/airports` | Liste des aéroports |
| POST | `/api/v1/airports` | Ajouter un aéroport |
| GET | `/api/v1/airports/{icao}` | Détails d'un aéroport |
| DELETE | `/api/v1/airports/{icao}` | Supprimer un aéroport |

### METAR
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/metar/{icao}/latest` | Dernier METAR |
| GET | `/api/v1/metar/{icao}/history` | Historique paginé |
| GET | `/api/v1/metar/bulk/latest` | Derniers METAR (tous) |

### Export
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/export/csv` | Export CSV |
| GET | `/api/v1/export/json` | Export JSON |

### Administration
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/metrics` | Métriques |
| GET | `/api/v1/collection/status` | Statut de collecte |

## Structure du projet

```
metar-collector/
├── docker-compose.yml
├── .env.example
├── README.md
├── config/
│   └── airports.yaml          # Configuration des aéroports
├── services/
│   ├── collector/             # Service de collecte
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── domain/        # Entités et value objects
│   │   │   ├── application/   # Services et use cases
│   │   │   ├── infrastructure/# Sources, parsers, persistence
│   │   │   └── main.py
│   │   └── tests/
│   ├── api/                   # Service API REST
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   ├── presentation/  # Routes et schemas
│   │   │   ├── infrastructure/# Database
│   │   │   └── main.py
│   │   └── tests/
│   └── frontend/              # Dashboard web
│       ├── Dockerfile
│       ├── nginx.conf
│       ├── index.html
│       ├── css/
│       └── js/
└── shared/
    └── database/
        └── migrations/
            └── init.sql       # Schema initial
```

## Développement

### Lancer les tests

```bash
# Tests du collector
cd services/collector
pip install -e ".[dev]"
pytest

# Tests de l'API
cd services/api
pip install -e ".[dev]"
pytest
```

### Linting et formatage

```bash
# Linting
ruff check .

# Formatage
black .

# Type checking
mypy src
```

### Logs

```bash
# Voir les logs de tous les services
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f collector
docker-compose logs -f api
```

## Sources de données METAR

### NOAA Aviation Weather Center (Principal)
- URL : https://aviationweather.gov/api/data/metar
- Gratuit, pas de clé API requise
- Couverture mondiale

### CheckWX (Backup)
- URL : https://www.checkwx.com/api
- Clé API gratuite requise
- Utilisé automatiquement si NOAA indisponible

## Données parsées

Les METAR bruts sont parsés en données structurées :

| Champ | Type | Description |
|-------|------|-------------|
| `icao_code` | string | Code ICAO de l'aéroport |
| `observation_time` | datetime | Heure d'observation UTC |
| `raw_metar` | string | METAR brut original |
| `wind_direction_degrees` | int | Direction du vent (degrés) |
| `wind_speed_kt` | int | Vitesse du vent (nœuds) |
| `wind_gust_kt` | int | Rafales (nœuds) |
| `visibility_statute_mi` | decimal | Visibilité (miles) |
| `visibility_meters` | int | Visibilité (mètres) |
| `weather_phenomena` | json | Phénomènes météo |
| `cloud_layers` | json | Couches nuageuses |
| `ceiling_ft` | int | Plafond (pieds) |
| `temperature_c` | decimal | Température (°C) |
| `dewpoint_c` | decimal | Point de rosée (°C) |
| `altimeter_inhg` | decimal | QNH (inHg) |
| `altimeter_hpa` | int | QNH (hPa) |
| `flight_category` | string | VFR/MVFR/IFR/LIFR |

## Catégories de vol

| Catégorie | Visibilité | Plafond | Couleur |
|-----------|------------|---------|---------|
| VFR | > 5 SM | > 3000 ft | Vert |
| MVFR | 3-5 SM | 1000-3000 ft | Bleu |
| IFR | 1-3 SM | 500-1000 ft | Rouge |
| LIFR | < 1 SM | < 500 ft | Violet |

## Maintenance

### Sauvegarde de la base

```bash
docker-compose exec postgres pg_dump -U metar_user metar_db > backup.sql
```

### Restauration

```bash
cat backup.sql | docker-compose exec -T postgres psql -U metar_user metar_db
```

### Nettoyage des données anciennes

La rétention est illimitée par défaut. Pour nettoyer manuellement :

```sql
DELETE FROM metar_observations
WHERE observation_time < NOW() - INTERVAL '1 year';
```

## Évolutions futures

- [ ] Support TAF (prévisions)
- [ ] Intégration FlightAware AeroAPI
- [ ] Alertes météo personnalisées
- [ ] Visualisation cartographique
- [ ] Analytics et tendances
- [ ] API GraphQL

## Licence

MIT License

## Support

Pour signaler un bug ou demander une fonctionnalité :
- Ouvrir une issue sur le repository

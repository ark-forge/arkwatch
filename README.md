# ArkWatch - Service de Veille IA

## Description
Service de veille automatisée qui surveille des sites web et génère des rapports IA quotidiens.

## Fonctionnalités
- 🔍 Surveillance de pages web (détection de changements)
- 🤖 Analyse IA des modifications (Ollama/Mistral)
- 📧 Rapports par email automatiques
- 📊 Dashboard de suivi

## Stack technique
- **Backend** : Python 3.11 + FastAPI
- **Scraping** : Crawl4ai
- **IA** : Ollama (Mistral)
- **Base de données** : PostgreSQL 17 + Qdrant
- **Cache** : Redis
- **Emails** : msmtp

## Installation

```bash
# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'environnement
cp config/.env.example config/.env

# Lancer l'API
uvicorn src.api.main:app --reload
```

## Structure

```
arkwatch/
├── src/
│   ├── api/          # Endpoints FastAPI
│   ├── scraper/      # Module de scraping
│   ├── analyzer/     # Analyse IA avec Ollama
│   ├── storage/      # PostgreSQL + Qdrant
│   └── notifications/# Emails et alertes
├── tests/            # Tests unitaires
├── config/           # Configuration
└── docker/           # Dockerfiles
```

## API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | /watches | Créer une surveillance |
| GET | /watches | Lister les surveillances |
| GET | /watches/{id} | Détails d'une surveillance |
| DELETE | /watches/{id} | Supprimer une surveillance |
| GET | /reports | Lister les rapports |
| GET | /reports/{id} | Détail d'un rapport |

## Développé par
Claude CEO - Entreprise IA autonome

## License
Propriétaire - ArkForge

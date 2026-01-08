# METAR Collector - Makefile
# Commandes pour la gestion du projet

.PHONY: help build up down restart logs clean test lint format

# Variables
COMPOSE = docker-compose
COMPOSE_FILE = docker-compose.yml

# Couleurs pour l'affichage
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m

##@ Général

help: ## Afficher cette aide
	@awk 'BEGIN {FS = ":.*##"; printf "\n${BLUE}METAR Collector${NC} - Commandes disponibles:\n\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  ${GREEN}%-15s${NC} %s\n", $$1, $$2 } /^##@/ { printf "\n${YELLOW}%s${NC}\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Docker

build: ## Construire les images Docker
	@echo "${BLUE}Construction des images...${NC}"
	$(COMPOSE) build

build-no-cache: ## Construire sans cache
	@echo "${BLUE}Construction des images (sans cache)...${NC}"
	$(COMPOSE) build --no-cache

up: ## Démarrer tous les services
	@echo "${GREEN}Démarrage des services...${NC}"
	$(COMPOSE) up -d
	@echo "${GREEN}Services démarrés !${NC}"
	@echo "  Dashboard: http://localhost:8882"
	@echo "  API Docs:  http://localhost:8000/api/docs"

down: ## Arrêter tous les services
	@echo "${YELLOW}Arrêt des services...${NC}"
	$(COMPOSE) down

stop: ## Arrêter sans supprimer les conteneurs
	@echo "${YELLOW}Arrêt des conteneurs...${NC}"
	$(COMPOSE) stop

restart: down up ## Redémarrer tous les services

##@ Logs & Monitoring

logs: ## Voir les logs de tous les services
	$(COMPOSE) logs -f

logs-collector: ## Logs du service collector
	$(COMPOSE) logs -f collector

logs-api: ## Logs du service API
	$(COMPOSE) logs -f api

logs-db: ## Logs de PostgreSQL
	$(COMPOSE) logs -f postgres

ps: ## Afficher l'état des services
	$(COMPOSE) ps

health: ## Vérifier la santé des services
	@echo "${BLUE}Vérification de la santé...${NC}"
	@curl -s http://localhost:8000/api/v1/health | python3 -m json.tool 2>/dev/null || echo "${RED}API non disponible${NC}"

metrics: ## Afficher les métriques
	@curl -s http://localhost:8000/api/v1/metrics | python3 -m json.tool 2>/dev/null || echo "${RED}API non disponible${NC}"

##@ Base de données

db-shell: ## Ouvrir un shell PostgreSQL
	$(COMPOSE) exec postgres psql -U metar_user -d metar_db

db-backup: ## Sauvegarder la base de données
	@echo "${BLUE}Sauvegarde de la base...${NC}"
	@mkdir -p backups
	$(COMPOSE) exec -T postgres pg_dump -U metar_user metar_db > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "${GREEN}Sauvegarde terminée dans backups/${NC}"

db-restore: ## Restaurer depuis le dernier backup (usage: make db-restore FILE=backups/backup.sql)
	@if [ -z "$(FILE)" ]; then echo "${RED}Usage: make db-restore FILE=backups/backup.sql${NC}"; exit 1; fi
	@echo "${YELLOW}Restauration depuis $(FILE)...${NC}"
	cat $(FILE) | $(COMPOSE) exec -T postgres psql -U metar_user -d metar_db
	@echo "${GREEN}Restauration terminée${NC}"

db-reset: ## Réinitialiser la base de données (ATTENTION: perte de données)
	@echo "${RED}ATTENTION: Cette action supprimera toutes les données !${NC}"
	@read -p "Continuer ? [y/N] " confirm && [ "$$confirm" = "y" ]
	$(COMPOSE) down -v
	$(COMPOSE) up -d postgres
	@sleep 5
	$(COMPOSE) up -d

##@ Développement

shell-collector: ## Shell dans le conteneur collector
	$(COMPOSE) exec collector /bin/bash

shell-api: ## Shell dans le conteneur API
	$(COMPOSE) exec api /bin/bash

##@ Tests

test: ## Lancer tous les tests
	@echo "${BLUE}Lancement des tests...${NC}"
	cd services/collector && pip install -q -e ".[dev]" && pytest -v
	cd services/api && pip install -q -e ".[dev]" && pytest -v

test-collector: ## Tests du service collector
	@echo "${BLUE}Tests du collector...${NC}"
	cd services/collector && pip install -q -e ".[dev]" && pytest -v

test-api: ## Tests du service API
	@echo "${BLUE}Tests de l'API...${NC}"
	cd services/api && pip install -q -e ".[dev]" && pytest -v

test-cov: ## Tests avec couverture
	cd services/collector && pip install -q -e ".[dev]" && pytest --cov=src --cov-report=html

##@ Qualité de code

lint: ## Vérifier le code (ruff)
	@echo "${BLUE}Vérification du code...${NC}"
	cd services/collector && ruff check src tests
	cd services/api && ruff check src tests

format: ## Formater le code (black)
	@echo "${BLUE}Formatage du code...${NC}"
	cd services/collector && black src tests
	cd services/api && black src tests

typecheck: ## Vérification des types (mypy)
	@echo "${BLUE}Vérification des types...${NC}"
	cd services/collector && mypy src
	cd services/api && mypy src

check: lint typecheck ## Toutes les vérifications

##@ Nettoyage

clean: ## Nettoyer les fichiers temporaires
	@echo "${YELLOW}Nettoyage...${NC}"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "${GREEN}Nettoyage terminé${NC}"

clean-docker: ## Nettoyer les images et volumes Docker
	@echo "${RED}Nettoyage Docker...${NC}"
	$(COMPOSE) down -v --rmi local
	@echo "${GREEN}Nettoyage Docker terminé${NC}"

clean-all: clean clean-docker ## Tout nettoyer

##@ Installation

install: ## Installer les dépendances de développement
	@echo "${BLUE}Installation des dépendances...${NC}"
	cd services/collector && pip install -e ".[dev]"
	cd services/api && pip install -e ".[dev]"
	@echo "${GREEN}Installation terminée${NC}"

setup: ## Configuration initiale du projet
	@echo "${BLUE}Configuration du projet...${NC}"
	@if [ ! -f .env ]; then cp .env.example .env; echo "${GREEN}.env créé${NC}"; fi
	@echo "${GREEN}Configuration terminée${NC}"
	@echo "Lancez 'make build up' pour démarrer"

##@ Production

prod-up: ## Démarrer en mode production
	$(COMPOSE) -f docker-compose.yml up -d

prod-down: ## Arrêter le mode production
	$(COMPOSE) -f docker-compose.yml down

# Cibles par défaut
.DEFAULT_GOAL := help

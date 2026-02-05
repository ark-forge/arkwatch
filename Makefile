# ArkWatch Makefile
# Commandes de développement et déploiement

VENV = venv/bin
PYTHON = $(VENV)/python
PYTEST = $(VENV)/pytest

.PHONY: help test test-verbose deploy validate install clean

help:
	@echo "ArkWatch - Commandes disponibles"
	@echo "================================"
	@echo "make test          - Exécuter les tests"
	@echo "make test-verbose  - Tests avec détails"
	@echo "make validate      - Validation pré-déploiement"
	@echo "make deploy        - Déploiement complet"
	@echo "make install       - Installer les dépendances"
	@echo "make clean         - Nettoyer les fichiers temporaires"

# Tests
test:
	$(PYTEST) tests/ -v --tb=short

test-verbose:
	$(PYTEST) tests/ -v --tb=long -s

test-quick:
	$(PYTEST) tests/ -x --tb=line

# Validation et déploiement
validate:
	$(PYTHON) scripts/pre_deploy_check.py --skip-health

deploy:
	./scripts/deploy.sh

deploy-force:
	./scripts/deploy.sh --force

# Installation
install:
	pip install -r requirements.txt

# Nettoyage
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

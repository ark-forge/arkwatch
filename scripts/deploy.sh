#!/bin/bash
#
# ArkWatch Deployment Script with Rollback
# RULE: No deployment without passing tests
#
# Usage: ./deploy.sh [--force]
#

set -e

ARKWATCH_DIR="/opt/claude-ceo/workspace/arkwatch"
BACKUP_DIR="/opt/claude-ceo/backups/arkwatch"
VENV_PYTHON="$ARKWATCH_DIR/venv/bin/python"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/opt/claude-ceo/logs/deploy_${TIMESTAMP}.log"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[OK] $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARN] $1${NC}" | tee -a "$LOG_FILE"
}

# Créer les répertoires nécessaires
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname $LOG_FILE)"

log "╔════════════════════════════════════════════════════╗"
log "║  ARKWATCH DEPLOYMENT SCRIPT                        ║"
log "║  Timestamp: $TIMESTAMP                        ║"
log "╚════════════════════════════════════════════════════╝"

# Check si --force est passé
FORCE=false
if [[ "$1" == "--force" ]]; then
    FORCE=true
    warning "Mode FORCE activé - tests contournés (non recommandé)"
fi

# ============================================
# ÉTAPE 1: Pré-validation (tests)
# ============================================
log ""
log "ÉTAPE 1: Pré-validation"
log "━━━━━━━━━━━━━━━━━━━━━━━"

if [[ "$FORCE" == false ]]; then
    log "Exécution des tests de validation..."

    if $VENV_PYTHON "$ARKWATCH_DIR/scripts/pre_deploy_check.py" --skip-health 2>&1 | tee -a "$LOG_FILE"; then
        success "Validation réussie"
    else
        error "Validation échouée - Déploiement annulé"
        error "Règle: Aucun déploiement sans test passé"
        exit 1
    fi
else
    warning "Tests contournés (--force)"
fi

# ============================================
# ÉTAPE 2: Backup
# ============================================
log ""
log "ÉTAPE 2: Backup"
log "━━━━━━━━━━━━━━━"

BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"
log "Création du backup: $BACKUP_PATH"

# Backup des fichiers critiques
mkdir -p "$BACKUP_PATH"
cp -r "$ARKWATCH_DIR/src" "$BACKUP_PATH/" 2>/dev/null || true
cp -r "$ARKWATCH_DIR/data" "$BACKUP_PATH/" 2>/dev/null || true
cp "$ARKWATCH_DIR/requirements.txt" "$BACKUP_PATH/" 2>/dev/null || true

# Sauvegarder l'état des services
systemctl is-active arkwatch-api > "$BACKUP_PATH/api_status.txt" 2>/dev/null || echo "unknown" > "$BACKUP_PATH/api_status.txt"
systemctl is-active arkwatch-worker > "$BACKUP_PATH/worker_status.txt" 2>/dev/null || echo "unknown" > "$BACKUP_PATH/worker_status.txt"

success "Backup créé"

# ============================================
# ÉTAPE 3: Mise à jour des dépendances
# ============================================
log ""
log "ÉTAPE 3: Dépendances"
log "━━━━━━━━━━━━━━━━━━━"

cd "$ARKWATCH_DIR"
if $VENV_PYTHON -m pip install -r requirements.txt -q 2>&1 | tee -a "$LOG_FILE"; then
    success "Dépendances installées"
else
    warning "Erreur dépendances (peut être OK)"
fi

# ============================================
# ÉTAPE 4: Redémarrage des services
# ============================================
log ""
log "ÉTAPE 4: Redémarrage services"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

restart_service() {
    local service=$1
    log "Redémarrage $service..."

    if sudo systemctl restart "$service" 2>&1 | tee -a "$LOG_FILE"; then
        sleep 2
        if systemctl is-active --quiet "$service"; then
            success "$service redémarré"
            return 0
        else
            error "$service n'a pas démarré"
            return 1
        fi
    else
        error "Échec redémarrage $service"
        return 1
    fi
}

API_OK=false
WORKER_OK=false

if restart_service "arkwatch-api"; then
    API_OK=true
fi

if restart_service "arkwatch-worker"; then
    WORKER_OK=true
fi

# ============================================
# ÉTAPE 5: Health check post-déploiement
# ============================================
log ""
log "ÉTAPE 5: Health check post-déploiement"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sleep 3  # Attendre que l'API soit prête

HEALTH_OK=false
for i in {1..5}; do
    log "Tentative $i/5..."

    if curl -s -f "http://localhost:8080/health" > /dev/null 2>&1; then
        HEALTH_OK=true
        success "Health check OK"
        break
    fi

    sleep 2
done

if [[ "$HEALTH_OK" == false ]]; then
    error "Health check échoué après 5 tentatives"
fi

# ============================================
# ÉTAPE 6: Rollback si nécessaire
# ============================================
if [[ "$API_OK" == false || "$HEALTH_OK" == false ]]; then
    log ""
    log "ROLLBACK AUTOMATIQUE"
    log "━━━━━━━━━━━━━━━━━━━━"

    error "Déploiement échoué - Rollback en cours..."

    # Restaurer les fichiers
    if [[ -d "$BACKUP_PATH/src" ]]; then
        rm -rf "$ARKWATCH_DIR/src"
        cp -r "$BACKUP_PATH/src" "$ARKWATCH_DIR/"
        log "Fichiers restaurés"
    fi

    # Redémarrer les services
    sudo systemctl restart arkwatch-api 2>/dev/null || true
    sudo systemctl restart arkwatch-worker 2>/dev/null || true

    sleep 3

    # Vérifier après rollback
    if curl -s -f "http://localhost:8080/health" > /dev/null 2>&1; then
        warning "Rollback réussi - Service restauré"
    else
        error "CRITIQUE: Rollback échoué - Intervention manuelle requise"
    fi

    exit 1
fi

# ============================================
# Résumé
# ============================================
log ""
log "╔════════════════════════════════════════════════════╗"
log "║  DÉPLOIEMENT TERMINÉ                               ║"
log "╠════════════════════════════════════════════════════╣"
log "║  API:        $(if $API_OK; then echo '✓ OK'; else echo '✗ FAIL'; fi)                                  ║"
log "║  Worker:     $(if $WORKER_OK; then echo '✓ OK'; else echo '✗ FAIL'; fi)                                  ║"
log "║  Health:     $(if $HEALTH_OK; then echo '✓ OK'; else echo '✗ FAIL'; fi)                                  ║"
log "║  Backup:     $BACKUP_PATH"
log "║  Log:        $LOG_FILE"
log "╚════════════════════════════════════════════════════╝"

# Nettoyer les vieux backups (garder les 5 derniers)
log ""
log "Nettoyage des anciens backups..."
ls -dt "$BACKUP_DIR"/backup_* 2>/dev/null | tail -n +6 | xargs rm -rf 2>/dev/null || true
success "Terminé"

exit 0

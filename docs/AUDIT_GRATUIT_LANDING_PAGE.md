# Landing Page Audit Gratuit - Documentation Technique

## Vue d'ensemble

Landing page pour offre audit gratuit monitoring avec:
- Timer compte à rebours 24h (localStorage)
- Badge slots dynamiques (3/5 places restantes)
- Formulaire capture leads (nom, email, stack, URL, pain point)
- Tracking pixel conversion
- Intégration API complète

## URLs

### Page publique
- **Production**: https://arkforge.fr/audit-gratuit-monitoring.html
- **Fichier source**: `/opt/claude-ceo/workspace/arkwatch/site/audit-gratuit-monitoring.html`
- **Déployé**: `/var/www/arkforge/audit-gratuit-monitoring.html`

### API Endpoints
- **Slots**: `GET https://watch.arkforge.fr/audit-gratuit/slots`
- **Stats**: `GET https://watch.arkforge.fr/audit-gratuit/stats`
- **Submit**: `POST https://watch.arkforge.fr/audit-gratuit/submit`

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Landing Page (audit-gratuit-monitoring.html)  │
│  - Timer 24h (localStorage)                     │
│  - Badge slots (fetch API)                      │
│  - Form (nom, email, stack, URL)                │
└──────────────────┬──────────────────────────────┘
                   │
                   │ POST /audit-gratuit/submit
                   ▼
┌─────────────────────────────────────────────────┐
│  ArkWatch API (audit_gratuit.py router)         │
│  - Validation Pydantic                          │
│  - Anti-duplicate (email)                       │
│  - Slots management (5 max)                     │
│  - Email confirmation → lead                    │
│  - Email notification → actionnaire             │
└──────────────────┬──────────────────────────────┘
                   │
                   │ Save JSON
                   ▼
┌─────────────────────────────────────────────────┐
│  Tracking Data (audit_gratuit_tracking.json)    │
│  - Submissions list                             │
│  - Metrics (slots, confirmations, reports)      │
└─────────────────────────────────────────────────┘
```

## Fonctionnalités

### 1. Timer Compte à Rebours (24h)
- **Technologie**: JavaScript + localStorage
- **Clé**: `arkwatch_audit_deadline`
- **Comportement**:
  - Premier visit → crée deadline (now + 24h)
  - Retours suivants → affiche temps restant
  - Expiration → overlay "Offre expirée" + redirect /trial-14d.html
- **Affichage**: Format HH:MM:SS avec animation

### 2. Badge Slots Dynamiques
- **Affichage**: "3/5 places restantes"
- **Source**: API `GET /audit-gratuit/slots`
- **Fallback**: localStorage `arkwatch_audit_slots`
- **Comportement**:
  - Fetch slots au chargement
  - Update après soumission
  - Si 0 slots → bouton disabled + "Offre complète"
- **Animation**: CSS pulse (2s infinite)

### 3. Formulaire Capture Leads

#### Champs
| Champ | Type | Validation | Requis |
|-------|------|------------|--------|
| Nom | text | 2-100 chars | ✓ |
| Email | email | EmailStr | ✓ |
| Stack | select | Options fixes | ✓ |
| URL | url | URL valide | ✓ |

#### Options Stack
- AWS (CloudWatch, X-Ray...)
- Google Cloud (Stackdriver...)
- Azure (Monitor, App Insights...)
- Datadog
- New Relic
- Grafana / Prometheus
- Solution custom / maison
- Pas de monitoring en place
- Autre

#### Soumission
- **Method**: POST
- **Endpoint**: `https://watch.arkforge.fr/audit-gratuit/submit`
- **Content-Type**: application/json
- **Tracking**: submission_id généré client-side

### 4. Tracking Conversion

#### Tracking Pixel
```html
<img src="https://watch.arkforge.fr/api/track-email-open/page_audit_gratuit"
     width="1" height="1" style="display:none;" alt="" />
```

#### Analytics Plausible
- Event: `AuditGratuit`
- Props: `{ stack: "datadog" }`

#### Données collectées
- Soumission: name, email, stack, url
- Attribution: utm_source, utm_campaign, referrer
- Timestamps: submitted_at, confirmation_sent_at
- Tracking: email_opened, report_delivered

## API Router (audit_gratuit.py)

### Configuration
```python
router = APIRouter(prefix="/audit-gratuit")
MAX_SLOTS = 5
NOTIFY_EMAIL = "apps.desiorac@gmail.com"
AUDIT_TRACKING_FILE = "/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_tracking.json"
```

### Endpoints

#### POST /audit-gratuit/submit
Soumission formulaire audit.

**Request Body**:
```json
{
  "name": "Jean Dupont",
  "email": "jean@entreprise.com",
  "stack": "datadog",
  "url": "https://www.entreprise.com",
  "submission_id": "audit_1234567890_abc123",
  "source": "landing_page",
  "utm_source": null,
  "utm_campaign": null,
  "referrer": null,
  "timestamp": "2026-02-10T20:00:00Z"
}
```

**Response Success (200)**:
```json
{
  "success": true,
  "message": "Audit reserve ! Consultez votre email pour la confirmation.",
  "slots_remaining": 4,
  "submission_id": "audit_1234567890_abc123"
}
```

**Response Duplicate (200)**:
```json
{
  "success": true,
  "message": "Vous etes deja inscrit ! Votre rapport arrive sous 48h.",
  "slots_remaining": 4,
  "submission_id": "audit_previous_id"
}
```

**Response Slots Full (409)**:
```json
{
  "detail": "Offre complete. Les 5 places ont ete prises."
}
```

**Actions déclenchées**:
1. Validation Pydantic
2. Check slots disponibles
3. Check duplicate email
4. Envoi email confirmation → lead
5. Envoi email notification → actionnaire
6. Save tracking data
7. Return response avec slots mis à jour

#### GET /audit-gratuit/slots
Récupère disponibilité slots.

**Response**:
```json
{
  "slots_remaining": 3,
  "slots_total": 5,
  "slots_used": 2
}
```

#### GET /audit-gratuit/stats
Statistiques campagne audit.

**Response**:
```json
{
  "total_submissions": 2,
  "slots_remaining": 3,
  "confirmations_sent": 2,
  "reports_delivered": 0,
  "last_submission": "2026-02-10T20:00:00Z"
}
```

### Email Confirmation (Lead)

**Destinataire**: lead email
**Subject**: "Votre audit monitoring gratuit est en cours"
**Contenu**:
- Confirmation réception demande
- Rappel URL + stack analysée
- Liste des livrables (4 points)
- Timeline: rapport PDF sous 48h
- Tracking pixel: `audit_gratuit_{submission_id}`

### Email Notification (Actionnaire)

**Destinataire**: apps.desiorac@gmail.com
**Subject**: "[AUDIT GRATUIT] Nouveau lead: {name} ({stack})"
**Contenu**:
- Tableau infos lead (nom, email, stack, URL, source, date)
- Action requise: Livrer rapport PDF sous 48h
- Reply-to: email du lead

## Données de Tracking

### Structure fichier JSON
```json
{
  "campaign": "audit_gratuit_monitoring",
  "created_at": "2026-02-10T20:00:00Z",
  "last_updated": "2026-02-10T20:30:00Z",
  "max_slots": 5,
  "submissions": [
    {
      "submission_id": "audit_1234567890_abc123",
      "name": "Jean Dupont",
      "email": "jean@entreprise.com",
      "stack": "datadog",
      "url": "https://www.entreprise.com",
      "source": "landing_page",
      "utm_source": null,
      "utm_campaign": null,
      "referrer": null,
      "submitted_at": "2026-02-10T20:15:00Z",
      "confirmation_sent": true,
      "notification_sent": true,
      "report_delivered": false,
      "report_delivered_at": null
    }
  ]
}
```

### Localisation
- **Fichier**: `/opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_tracking.json`
- **Permissions**: rw-r--r-- ubuntu:ubuntu
- **Backup**: Atomique via .tmp file + replace

## Tests

### Test Suite End-to-End
**Fichier**: `/opt/claude-ceo/workspace/arkwatch/tests/test_audit_gratuit_e2e.sh`

**Tests exécutés**:
1. ✓ Page accessible (HTTP 200)
2. ✓ Éléments critiques présents (timer, slots, form)
3. ✓ API Slots endpoint
4. ✓ API Stats endpoint
5. ✓ Form submission complète
6. ✓ Duplicate protection

**Exécution**:
```bash
/opt/claude-ceo/workspace/arkwatch/tests/test_audit_gratuit_e2e.sh
```

**Output attendu**: "STATUS: READY FOR PRODUCTION ✓"

## Déploiement

### Fichiers déployés
```
/var/www/arkforge/
  └── audit-gratuit-monitoring.html  (25K)

/opt/claude-ceo/workspace/arkwatch/
  ├── site/audit-gratuit-monitoring.html  (source)
  ├── src/api/routers/audit_gratuit.py   (API)
  ├── data/audit_gratuit_tracking.json    (tracking)
  └── tests/test_audit_gratuit_e2e.sh     (tests)
```

### Service API
```bash
# Status
systemctl status arkwatch-api

# Redémarrage (si modifs code)
sudo systemctl restart arkwatch-api

# Logs
journalctl -u arkwatch-api -f
```

### Déploiement page
```bash
# Copie fichier HTML
cp /opt/claude-ceo/workspace/arkwatch/site/audit-gratuit-monitoring.html \
   /var/www/arkforge/audit-gratuit-monitoring.html

# Vérification
curl -I https://arkforge.fr/audit-gratuit-monitoring.html
```

## Monitoring & Maintenance

### Vérifier slots restants
```bash
curl -s https://watch.arkforge.fr/audit-gratuit/slots | jq
```

### Vérifier statistiques
```bash
curl -s https://watch.arkforge.fr/audit-gratuit/stats | jq
```

### Reset campagne (nouveau cycle)
```bash
# Backup ancien cycle
cp /opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_tracking.json \
   /opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_tracking_backup_$(date +%Y%m%d).json

# Reset slots
cat > /opt/claude-ceo/workspace/arkwatch/data/audit_gratuit_tracking.json <<'EOF'
{
  "campaign": "audit_gratuit_monitoring",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "last_updated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "max_slots": 5,
  "submissions": []
}
EOF
```

### Livraison rapport audit

Quand un lead a été audité et rapport PDF prêt:

```bash
# Marquer rapport livré (via API future ou manuel)
# TODO: Ajouter endpoint PATCH /audit-gratuit/submissions/{id}/deliver
```

## Optimisations Futures

### Phase 2: Automation
- [ ] Script génération automatique rapport PDF (Playwright screenshots + analysis)
- [ ] Cron job delivery automatique sous 48h
- [ ] Email relance J+3 si pas de réponse
- [ ] Nurturing sequence leads audit → trial

### Phase 3: Analytics
- [ ] Dashboard admin stats campagne
- [ ] A/B testing CTA variants
- [ ] Heatmap visitor behavior
- [ ] Conversion funnel audit → trial → payant

### Phase 4: Scale
- [ ] Multi-campagnes (différentes stacks)
- [ ] Dynamic slots (variable MAX_SLOTS)
- [ ] Webhook Zapier pour intégration CRM
- [ ] Export CSV leads pour cold outreach

## Sécurité

### Protection CSRF
- CORS configuré: `allow_origins=["https://arkforge.fr"]`
- Content-Type validation: `application/json`

### Rate Limiting
- TODO: Ajouter rate limit 10 req/min par IP sur `/submit`

### Validation Email
- Pydantic EmailStr (regex RFC 5322)
- Anti-duplicate par email exact match

### Sanitization
- Toutes inputs sanitized via Pydantic
- URL validation (scheme http/https)
- Stack validation (enum strict)

## Contact

**Actionnaire**: apps.desiorac@gmail.com
**Notifications**: Toutes les soumissions audit gratuit
**Livraison**: Rapport PDF manuel sous 48h (automatisation future)

---

**Status**: ✅ DEPLOYED & TESTED
**Date**: 2026-02-10
**Version**: 1.0.0
**Tâche**: #70

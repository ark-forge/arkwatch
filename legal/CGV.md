# Conditions Générales de Vente - ArkWatch

*Dernière mise à jour : 6 février 2026*

---

## Article 1 - Objet du service

Les présentes Conditions Générales de Vente (ci-après « CGV ») régissent l'utilisation du service **ArkWatch**, édité par **ArkForge** (ci-après « le Prestataire »).

ArkWatch est un service de veille web automatisée par intelligence artificielle accessible via une API REST. Il permet à ses utilisateurs (ci-après « le Client ») de :

- Configurer des alertes de surveillance sur des pages web publiques ;
- Recevoir des notifications automatiques (email, webhook) lorsqu'un changement significatif est détecté ;
- Consulter l'historique des changements détectés via l'API ;
- Paramétrer des seuils de détection personnalisés.

Le service est fourni « en l'état » (*as is*). Le Client reconnaît que les résultats de la veille dépendent de facteurs externes (accessibilité des sites surveillés, structure HTML, etc.) sur lesquels le Prestataire n'a aucun contrôle.

---

## Article 2 - Tarifs et paiement

### 2.1 Plans et tarification

Les prix sont indiqués en euros TTC. TVA non applicable, article 293 B du Code Général des Impôts.

| Plan | Prix | URLs surveillées | Fréquence min. | Accès API |
|------|------|-----------------|----------------|-----------|
| **Free** | Gratuit | 3 | 1 fois / 24h | 1 000 appels/jour |
| **Starter** | Sur demande | 10 | 1 fois / heure | Illimité |
| **Pro** | 9 €/mois | 50 | Toutes les 5 min | Illimité |
| **Business** | 29 €/mois | 1 000 | Toutes les minutes | Illimité |

Le plan Free est disponible sans engagement ni moyen de paiement.

### 2.2 Modalités de paiement

Le paiement des abonnements payants s'effectue exclusivement par carte bancaire via le prestataire de paiement sécurisé **Stripe**. Le Client autorise le prélèvement mensuel automatique à la date anniversaire de souscription.

### 2.3 Modification des tarifs

Le Prestataire se réserve le droit de modifier ses tarifs. Toute modification sera notifiée au Client par email au moins **30 jours** avant sa prise d'effet. En l'absence de résiliation dans ce délai, le Client sera réputé avoir accepté les nouveaux tarifs.

Les tarifs en vigueur au moment de la souscription restent applicables jusqu'à la fin de la période d'abonnement en cours.

### 2.4 Facturation

Une facture est mise à disposition du Client pour chaque paiement. Le Client peut accéder à son historique de facturation via le portail Stripe.

---

## Article 3 - Limitation de responsabilité

### 3.1 Obligations de moyens

Le Prestataire s'engage à fournir le service avec diligence et conformément aux règles de l'art. Il s'agit d'une **obligation de moyens** et non de résultat.

### 3.2 Exclusions de responsabilité

Le Prestataire **ne saurait être tenu responsable** :

- De l'exactitude, l'exhaustivité ou la pertinence des informations collectées lors de la veille ;
- Des décisions prises par le Client sur la base des alertes ou rapports générés par le service ;
- Des interruptions temporaires du service pour maintenance préventive ou corrective ;
- De l'indisponibilité des sites web tiers surveillés par le Client ;
- Des modifications de structure ou de contenu des sites surveillés rendant la détection inopérante ;
- Des dommages indirects, y compris perte de chiffre d'affaires, perte de données, perte de chance, préjudice commercial ou atteinte à l'image ;
- Des dysfonctionnements résultant d'un cas de force majeure au sens de l'article 1218 du Code civil.

### 3.3 Plafond d'indemnisation

En tout état de cause, la responsabilité totale du Prestataire est limitée au montant des sommes effectivement versées par le Client au cours des **12 derniers mois** précédant le fait générateur du dommage.

Pour les utilisateurs du plan Free, la responsabilité du Prestataire est expressément exclue dans la mesure permise par la loi.

### 3.4 Non-garantie des résultats

Le service utilise des techniques d'analyse automatisée (comparaison de contenu, hachage, IA). Le Prestataire **ne garantit pas** :

- La détection de 100 % des changements survenus sur les pages surveillées ;
- L'absence de faux positifs (alertes pour des changements non significatifs) ;
- Un délai précis entre le changement effectif et la notification.

---

## Article 4 - Disponibilité et niveau de service (SLA)

### 4.1 Disponibilité cible

Le Prestataire s'efforce de maintenir une disponibilité du service de **99 %** sur une base mensuelle, hors périodes de maintenance programmée.

### 4.2 Maintenance

Le Prestataire se réserve le droit d'interrompre temporairement le service pour des opérations de maintenance. Dans la mesure du possible, les opérations de maintenance programmée seront effectuées en dehors des heures ouvrées (fuseau Europe/Paris) et notifiées au préalable.

### 4.3 Incidents

En cas d'incident majeur affectant le service, le Prestataire s'engage à mettre en œuvre les moyens raisonnables pour rétablir le service dans les meilleurs délais. Le Client sera informé par email.

### 4.4 Absence de garantie contractuelle d'uptime

Le taux de disponibilité mentionné à l'article 4.1 constitue un **objectif** et non un engagement contractuel. Aucune compensation ou pénalité n'est due en cas de non-atteinte de cet objectif, sauf accord spécifique conclu par écrit entre les parties.

---

## Article 5 - Résiliation et remboursement

### 5.1 Résiliation par le Client

Le Client peut résilier son abonnement à tout moment :
- Via le portail de gestion Stripe ;
- Par email à contact@arkforge.fr.

La résiliation prend effet à la **fin de la période d'abonnement en cours**. Le Client conserve l'accès au service jusqu'à cette date.

### 5.2 Absence de remboursement

Aucun remboursement au prorata ne sera effectué en cas de résiliation en cours de période. Le Client ayant accepté l'exécution immédiate du service, le droit de rétractation prévu aux articles L221-18 et suivants du Code de la consommation ne s'applique pas, conformément à l'article L221-28.

### 5.3 Résiliation par le Prestataire

Le Prestataire se réserve le droit de suspendre ou résilier l'accès au service, sans préavis ni indemnité, en cas de :

- Violation des présentes CGV ;
- Utilisation abusive du service (surcharge volontaire, scraping de données protégées, etc.) ;
- Non-paiement après relance ;
- Activité illicite ou contraire à l'ordre public.

En cas de résiliation pour non-paiement, le Prestataire procédera à une relance par email avant toute suspension.

### 5.4 Conséquences de la résiliation

À l'expiration de l'abonnement :
- L'accès API est désactivé ;
- Les données de surveillance sont conservées pendant **30 jours** puis supprimées ;
- Les données de facturation sont conservées conformément aux obligations légales (10 ans).

Le Client peut exercer son droit à la portabilité des données (article 20 du RGPD) avant la suppression, via l'endpoint `GET /api/v1/auth/account/data`.

---

## Article 6 - Données personnelles

Le traitement des données personnelles du Client est régi par la **Politique de Confidentialité** d'ArkWatch, accessible à l'adresse : [https://arkforge.fr/privacy](https://arkforge.fr/privacy).

Le Prestataire s'engage à traiter les données conformément au Règlement Général sur la Protection des Données (RGPD - Règlement UE 2016/679) et à la loi Informatique et Libertés.

### Résumé des droits du Client (RGPD) :

| Droit | Article RGPD | Exercice |
|-------|-------------|----------|
| Accès | Art. 15 | `GET /api/v1/auth/account/data` |
| Rectification | Art. 16 | `PATCH /api/v1/auth/account` |
| Suppression | Art. 17 | `DELETE /api/v1/auth/account` |
| Portabilité | Art. 20 | `GET /api/v1/auth/account/data` (JSON) |
| Opposition | Art. 21 | Lien de désinscription dans chaque email |

Contact DPO : contact@arkforge.fr

Pour toute réclamation, le Client peut saisir la CNIL : [www.cnil.fr](https://www.cnil.fr).

---

## Article 7 - Droit applicable et litiges

### 7.1 Droit applicable

Les présentes CGV sont régies par le **droit français**.

### 7.2 Résolution amiable

En cas de différend relatif à l'exécution ou à l'interprétation des présentes CGV, les parties s'engagent à rechercher une solution amiable avant toute action judiciaire.

### 7.3 Médiation (consommateurs)

Conformément aux articles L611-1 et suivants du Code de la consommation, le Client consommateur peut recourir gratuitement à un médiateur de la consommation. Le Prestataire communiquera les coordonnées du médiateur compétent sur demande adressée à contact@arkforge.fr.

### 7.4 Juridiction compétente

À défaut de résolution amiable, les litiges entre professionnels relèvent de la compétence exclusive des **tribunaux du ressort du siège social du Prestataire**. Pour les litiges impliquant un consommateur, les règles de compétence territoriale de droit commun s'appliquent.

---

## Article 8 - Dispositions diverses

### 8.1 Intégralité

Les présentes CGV constituent l'intégralité de l'accord entre le Client et le Prestataire concernant l'utilisation du service ArkWatch. Elles annulent et remplacent toute version antérieure.

### 8.2 Nullité partielle

Si une clause des présentes CGV est déclarée nulle ou inapplicable, les autres clauses restent en vigueur.

### 8.3 Modification des CGV

Le Prestataire se réserve le droit de modifier les présentes CGV. Les modifications seront notifiées au Client par email au moins **15 jours** avant leur entrée en vigueur. La poursuite de l'utilisation du service vaut acceptation des nouvelles CGV.

---

## Article 9 - Identification du Prestataire

**ArkForge**
Entrepreneur individuel
M. Dubourg
SIRET : 488 010 331 00020
TVA : Non applicable (art. 293 B du CGI)
Email : contact@arkforge.fr
Site web : https://arkforge.fr

Support : contact@arkforge.fr (délai de réponse : 48h ouvrées)

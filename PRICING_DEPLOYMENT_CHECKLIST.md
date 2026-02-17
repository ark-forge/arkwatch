# Pricing V2 - Deployment Checklist

**Task**: #20260887
**Date**: 2026-02-09
**Worker**: Fondations

## Pre-Deployment Verification ✅

- [x] pricing-v2.html created and tested
- [x] All 3 plans present (Starter €29, Pro €99, Enterprise custom)
- [x] 4x trial CTAs implemented
- [x] Demo.html integration complete
- [x] Analytics tracking enabled
- [x] Mobile-responsive design
- [x] All tests passed (100%)

## Deployment Steps

### 1. File Transfer

**Source file**: `/opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html`

**Deploy to**:
```bash
# Option A: Local web root (if hosting locally)
cp /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html /var/www/html/arkwatch/

# Option B: Remote server (if hosting remotely)
scp /opt/claude-ceo/workspace/arkwatch/site/pricing-v2.html user@server:/var/www/html/arkwatch/

# Option C: Already deployed (if site/ folder is served directly)
# No action needed - file is already in site/ folder
```

### 2. Verify URLs

After deployment, verify these URLs are accessible:

- **Pricing page**: https://arkforge.fr/arkwatch/pricing-v2.html (or /site/pricing-v2.html)
- **Demo page**: https://arkforge.fr/arkwatch/demo.html (or /site/demo.html)
- **Trial page**: https://arkforge.fr/arkwatch/free-trial.html (or /site/free-trial.html)

**Test each CTA link manually**:
- [ ] Demo header "Pricing" link → pricing-v2.html
- [ ] Demo CTA "View Pricing" button → pricing-v2.html
- [ ] Pricing Starter CTA → free-trial.html?plan=starter
- [ ] Pricing Pro CTA → free-trial.html?plan=pro
- [ ] Pricing Enterprise CTA → mailto:contact@arkforge.fr

### 3. Server Configuration

If using Nginx, ensure this location block exists:

```nginx
location /arkwatch/ {
    alias /opt/claude-ceo/workspace/arkwatch/site/;
    try_files $uri $uri/ =404;
}
```

Or for Apache:

```apache
Alias /arkwatch /opt/claude-ceo/workspace/arkwatch/site
<Directory /opt/claude-ceo/workspace/arkwatch/site>
    Options Indexes FollowSymLinks
    AllowOverride None
    Require all granted
</Directory>
```

### 4. DNS & SSL

Verify:
- [ ] Domain resolves correctly: `nslookup arkforge.fr`
- [ ] SSL certificate valid: `curl -I https://arkforge.fr`
- [ ] HTTPS redirect enabled (HTTP → HTTPS)

### 5. Analytics Verification

After deployment, verify analytics tracking:

```bash
# Test pageview tracking
curl "https://arkforge.fr/arkwatch/pricing-v2.html" -I

# Check analytics endpoint responds
curl "https://watch.arkforge.fr/t.gif?e=pricing_pageview&p=/pricing-v2.html&s=direct" -I
```

Expected: 200 OK or 204 No Content

### 6. Cross-Browser Testing

Test on:
- [ ] Chrome/Edge (Desktop)
- [ ] Firefox (Desktop)
- [ ] Safari (Desktop)
- [ ] Mobile (iOS Safari)
- [ ] Mobile (Android Chrome)

### 7. Navigation Updates

**Update these pages to link to pricing-v2.html**:

- [ ] Main landing page: `arkwatch.html` or `index.html`
- [ ] Header navigation (if global)
- [ ] Footer navigation (if exists)
- [ ] Sitemap.xml (add /arkwatch/pricing-v2.html)

Example for main landing page:

```html
<nav>
  <a href="/arkwatch/demo.html">Demo</a>
  <a href="/arkwatch/pricing-v2.html">Pricing</a>
  <a href="/arkwatch/free-trial.html">Free Trial</a>
</nav>
```

## Post-Deployment Monitoring

### Day 1 (0-24h)
- [ ] Monitor server logs for 404 errors
- [ ] Verify analytics: pricing_pageview events
- [ ] Check page load time (target: < 2s)
- [ ] Verify all CTAs clickable

### Day 2 (24-48h)
- [ ] Monitor analytics: pricing_cta_click events
- [ ] Track free-trial.html signups from pricing page
- [ ] Monitor bounce rate (target: < 50%)

### Day 3-14 (48h-2 weeks)
- [ ] Track trial signups by plan (starter/pro/enterprise)
- [ ] Monitor trial → paid conversion (14-day cycle)
- [ ] First revenue expected: 48-72h after first trial signup

## Analytics Queries

**To monitor conversion funnel**:

```sql
-- Pageviews
SELECT COUNT(*) FROM analytics WHERE event = 'pricing_pageview';

-- CTA clicks
SELECT COUNT(*) FROM analytics WHERE event LIKE 'pricing_cta_click_%';

-- Conversion rate
SELECT
  (COUNT(CASE WHEN event LIKE 'pricing_cta_click_%' THEN 1 END) * 100.0 /
   COUNT(CASE WHEN event = 'pricing_pageview' THEN 1 END)) AS conversion_rate
FROM analytics
WHERE event IN ('pricing_pageview', 'pricing_cta_click_starter', 'pricing_cta_click_pro', 'pricing_cta_click_enterprise');
```

## Rollback Plan

If issues occur:

1. **Revert demo.html**:
```bash
git checkout /opt/claude-ceo/workspace/arkwatch/site/demo.html
```

2. **Remove pricing-v2.html**:
```bash
rm /var/www/html/arkwatch/pricing-v2.html
```

3. **Restore old pricing** (if exists):
```bash
cp /opt/claude-ceo/workspace/arkwatch/site/pricing.html /var/www/html/arkwatch/
```

## Success Metrics

**Week 1 targets**:
- Pricing pageviews: > 50
- Pricing → Trial conversion: > 30%
- Trial signups from pricing: > 15

**Week 2 targets**:
- First paid customer: 1+
- MRR: €29-99 (depending on plan chosen)
- Churn: 0% (too early)

## Contact

**Issues or questions**: Report to CEO via task queue

**Emergency rollback**: Contact Fondations worker

---

**Status**: ✅ READY FOR DEPLOYMENT
**Risk**: Low
**Estimated deployment time**: 15 minutes
**Estimated time to first revenue**: 48-72h after deployment

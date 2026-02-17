# Quick Start - Trial Signup Deployment

**Time to deploy**: ~5 minutes
**Difficulty**: Easy

---

## What Was Built

Landing page `/trial-signup` with:
- ✅ Form: name + email + usecase
- ✅ Tracking pixel (conversion monitoring)
- ✅ Auto-email confirmation
- ✅ Redirect to /try page
- ✅ Email open tracking

---

## Deploy in 3 Steps

### Step 1: Upload HTML Page (2 min)

```bash
# Copy page to production site
sudo cp /opt/claude-ceo/workspace/arkwatch/site/trial-signup.html \
        /var/www/arkforge.fr/trial-signup.html

# Set permissions
sudo chown www-data:www-data /var/www/arkforge.fr/trial-signup.html
sudo chmod 644 /var/www/arkforge.fr/trial-signup.html
```

**Verify**: Visit https://arkforge.fr/trial-signup.html
→ Should see form with 3 fields

---

### Step 2: Restart API Service (1 min)

```bash
# Restart to load new router
sudo systemctl restart arkwatch-api

# Check status
sudo systemctl status arkwatch-api
```

**Verify**:
```bash
curl https://watch.arkforge.fr/api/trial-signup/stats
# Should return: {"total_submissions": 0, ...}
```

---

### Step 3: Test Submission (2 min)

1. Go to https://arkforge.fr/trial-signup.html
2. Fill form:
   - Name: Your Name
   - Email: Your email
   - Usecase: "Test submission to verify system works"
3. Submit
4. Check your email inbox
5. Click link in email
6. Verify redirect to /try page

**Check tracking**:
```bash
cat /opt/claude-ceo/workspace/arkwatch/data/trial_signups_tracking.json | jq '.metrics'
```

Should show:
```json
{
  "total_submissions": 1,
  "total_emails_sent": 1,
  "email_send_rate": 100.0,
  ...
}
```

---

## Done! 🎉

Page is live at: **https://arkforge.fr/trial-signup.html**

---

## Monitor Performance

### Get stats anytime:
```bash
curl https://watch.arkforge.fr/api/trial-signup/stats
```

### Check recent submissions:
```bash
cat /opt/claude-ceo/workspace/arkwatch/data/trial_signups_tracking.json | \
  jq '.submissions | sort_by(.submitted_at) | reverse | .[0:3]'
```

### Track email opens:
```bash
cat /opt/claude-ceo/workspace/arkwatch/data/trial_signups_tracking.json | \
  jq '.submissions | map(select(.email_opened == true)) | length'
```

---

## Troubleshooting

### Page not loading?
```bash
# Check file exists
ls -lh /var/www/arkforge.fr/trial-signup.html

# Check nginx config
sudo nginx -t
sudo systemctl reload nginx
```

### Form submission fails?
```bash
# Check API logs
sudo journalctl -u arkwatch-api -f

# Check API is running
curl https://watch.arkforge.fr/health
```

### Email not received?
```bash
# Check SMTP logs
tail -f /var/log/mail.log

# Check email_sender config
python3 /opt/claude-ceo/automation/email_sender.py --test
```

---

## Next Steps

After deployment:
1. Share link on LinkedIn/Twitter
2. Add to marketing emails
3. Monitor conversion rate daily
4. A/B test different headlines

---

**Questions?** Check full documentation:
`/opt/claude-ceo/workspace/arkwatch/docs/TRIAL_SIGNUP_SYSTEM_20260963.md`

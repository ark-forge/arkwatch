<p align="center">
  <h1 align="center">ArkWatch</h1>
  <p align="center"><strong>AI-powered website monitoring. Get notified when what matters changes.</strong></p>
  <p align="center">
    <a href="https://watch.arkforge.fr"><img src="https://img.shields.io/badge/API-live-brightgreen" alt="API Status"></a>
    <a href="#quick-start"><img src="https://img.shields.io/badge/deploy-one--click-blue" alt="One-click deploy"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-orange" alt="License"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-yellow" alt="Python 3.11+"></a>
  </p>
</p>

---

Track **price changes**, **competitor moves**, **content updates**, and **outages** across any website — with AI-powered summaries delivered to your inbox.

```
You:      "Watch https://competitor.com/pricing"
ArkWatch: *checks every 5 minutes*
ArkWatch: "Competitor raised their Pro plan from $49 to $79. Enterprise tier removed."
```

## Why ArkWatch?

| Problem | ArkWatch Solution |
|---------|-------------------|
| Manually checking competitor websites | Automated monitoring with configurable intervals |
| Drowning in irrelevant change alerts | AI filters noise — only meaningful changes trigger alerts |
| Expensive monitoring tools ($50+/mo) | **Free tier** (3 monitors) or **self-host for $0** |
| Vendor lock-in | Open source — run it on your own server |

## Features

- **Smart Change Detection** — Content hashing + configurable change thresholds (ignore < 5% changes)
- **AI-Powered Summaries** — Mistral AI analyzes what changed and why it matters
- **Email Alerts** — Get notified instantly when significant changes happen
- **REST API** — Full CRUD API with API key auth for programmatic access
- **Stripe Billing** — Built-in subscription management (free, starter, pro, business tiers)
- **GDPR Compliant** — PII encryption at rest, data export, account deletion, unsubscribe
- **SSRF Protected** — Blocks private IPs, dangerous ports, DNS rebinding attacks

## Quick Start

### Option 1: Docker (recommended)

```bash
git clone https://github.com/desiorac/arkwatch.git
cd arkwatch
cp config/.env.example config/.env
# Edit config/.env with your settings (at minimum: MISTRAL_API_KEY, SMTP credentials)
docker compose up -d
```

ArkWatch is now running at `http://localhost:8080`.

### Option 2: Local install

```bash
git clone https://github.com/desiorac/arkwatch.git
cd arkwatch
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env
# Edit config/.env

# Start the API server
python run_api.py

# In another terminal — start the monitoring worker
python run_worker.py
```

### Option 3: Hosted (zero setup)

Use the managed version at **[arkforge.fr/arkwatch](https://arkforge.fr/arkwatch.html)** — free tier includes 3 monitors with daily checks.

## Usage

### 1. Register and get your API key

```bash
curl -X POST https://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "name": "Your Name", "privacy_accepted": true}'
```

Response:
```json
{
  "api_key": "ak_...",
  "message": "Welcome! A verification code has been sent to your email."
}
```

### 2. Create a watch

```bash
curl -X POST https://localhost:8080/api/v1/watches \
  -H "X-API-Key: ak_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://competitor.com/pricing",
    "name": "Competitor pricing",
    "check_interval": 3600,
    "notify_email": "you@example.com"
  }'
```

### 3. Get change reports

```bash
curl -H "X-API-Key: ak_your_key" https://localhost:8080/api/v1/reports
```

Each report includes:
- **Diff** — exactly what changed on the page
- **AI Summary** — plain-English explanation of the changes
- **Importance Score** — AI-rated significance level

## API Reference

### Core Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | No | Register & get API key |
| POST | `/api/v1/auth/verify-email` | No | Verify email (6-digit code) |
| POST | `/api/v1/watches` | API Key | Create a monitor |
| GET | `/api/v1/watches` | API Key | List monitors |
| PATCH | `/api/v1/watches/{id}` | API Key | Update a monitor |
| DELETE | `/api/v1/watches/{id}` | API Key | Delete a monitor |
| GET | `/api/v1/reports` | API Key | List change reports |
| GET | `/api/v1/reports/{id}` | API Key | Get report detail |
| GET | `/health` | No | Health check |

### Billing Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/billing/checkout` | API Key | Create Stripe checkout |
| GET | `/api/v1/billing/subscription` | API Key | Subscription status |
| GET | `/api/v1/billing/usage` | API Key | Usage vs. plan limits |

Full API docs: [docs/03-api-reference.md](docs/03-api-reference.md)

## Pricing (Hosted)

| Plan | Monitors | Check Interval | Price |
|------|----------|----------------|-------|
| Free | 3 | Daily | $0 |
| Starter | 10 | Hourly | $9/mo |
| Pro | 50 | 5 minutes | $29/mo |
| Business | 1000 | 1 minute | Custom |

Self-hosted: **unlimited monitors, unlimited checks, $0.**

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  FastAPI     │     │  Worker      │     │  Mistral AI  │
│  REST API    │────▶│  (async)     │────▶│  Analysis    │
│  port 8080   │     │  5min cycle  │     │              │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  Email       │
                    │  Alerts      │
                    └──────────────┘
```

**Stack:** Python 3.11+ / FastAPI / httpx / BeautifulSoup4 / Mistral AI / Stripe

## Configuration

Copy `config/.env.example` to `config/.env` and set:

| Variable | Required | Description |
|----------|----------|-------------|
| `MISTRAL_API_KEY` | For AI summaries | Mistral API key ([console.mistral.ai](https://console.mistral.ai)) |
| `SMTP_HOST` | For email alerts | SMTP server hostname |
| `SMTP_PORT` | For email alerts | SMTP port (usually 587) |
| `SMTP_USER` | For email alerts | SMTP username |
| `SMTP_FROM` | For email alerts | Sender email address |
| `SECRET_KEY` | Yes | App secret key (generate a random string) |
| `STRIPE_*` | For billing | Stripe API keys (optional for self-hosted) |

## Development

```bash
# Run tests
make test

# Run tests with full output
make test-verbose

# Pre-deploy validation
make validate

# Clean temp files
make clean
```

## Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

## License

[AGPL-3.0](LICENSE) — Free to self-host and modify. If you distribute a modified version, share your changes.

## Links

- **Hosted version:** [arkforge.fr/arkwatch](https://arkforge.fr/arkwatch.html)
- **API:** [watch.arkforge.fr](https://watch.arkforge.fr)
- **Documentation:** [docs/](docs/)

---

<p align="center">Built by <a href="https://arkforge.fr">ArkForge</a></p>

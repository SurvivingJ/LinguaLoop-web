# Environment Setup Guide

**Purpose**: Complete guide to setting up development and production environments for the LinguaLoop/LinguaDojo project.

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.11+ | Backend runtime |
| **pip** | Latest | Python package manager |
| **Git** | 2.x+ | Version control |
| **Node.js** | 16+ (optional) | For any frontend tooling |
| **PostgreSQL Client** | 14+ (optional) | Direct database access |

### Required Accounts

1. **Supabase**
   - Create project at [supabase.com](https://supabase.com)
   - Obtain: URL, anon key, service role key

2. **OpenAI**
   - Create account at [platform.openai.com](https://platform.openai.com)
   - Generate API key with GPT-4 access
   - Note: Used for test generation

3. **OpenRouter** (optional for topic generation)
   - Create account at [openrouter.ai](https://openrouter.ai)
   - Generate API key
   - Note: Alternative LLM provider

4. **Azure Cognitive Services**
   - Create Speech service in Azure Portal
   - Obtain: subscription key, region

5. **Cloudflare R2**
   - Create R2 bucket in Cloudflare dashboard
   - Generate access credentials (Access Key ID, Secret Access Key)
   - Note: Used for audio storage

6. **Stripe** (for payments)
   - Create account at [stripe.com](https://stripe.com)
   - Get test mode keys: publishable key, secret key, webhook secret
   - Switch to production keys when ready

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd LinguaLoop/WebApp
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key Dependencies** (from requirements.txt):
- Flask 3.0.3
- supabase 2.6.0
- openai 1.99.3
- azure-cognitiveservices-speech 1.40.0
- boto3 1.37.38 (for R2)
- stripe 12.4.0
- python-dotenv 1.0.0

### 4. Configure Environment Variables

Create `.env` file in project root:

```bash
# Copy from template
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

**Required Variables**: See [Environment Variables](./04-environment-variables.md) for complete list.

**Minimal `.env` for local development**:
```env
# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-change-me

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# Azure Speech (for audio generation)
AZURE_SPEECH_KEY=your-azure-key
AZURE_SPEECH_REGION=eastus

# Cloudflare R2 (for audio storage)
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=linguadojo-audio
R2_PUBLIC_URL=https://your-bucket.r2.dev

# Stripe (use test keys for development)
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Optional
OPENROUTER_API_KEY=your-openrouter-key
```

### 5. Setup Database

#### Create Supabase Project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. Create new project
3. Wait for provisioning (2-3 minutes)
4. Copy URL and keys to `.env`

#### Run Migrations

Execute migrations manually in Supabase SQL Editor:

```sql
-- 1. Execute test_generation_tables.sql
-- Creates dimension tables, prompt templates, config tables

-- 2. Execute elo_functions.sql
-- Creates ELO calculation functions

-- 3. Execute process_test_submission_v2.sql
-- Creates main test submission RPC

-- 4. Create remaining tables (if not auto-created)
-- See migrations/ folder for additional SQL files
```

**Note**: No automated migration tool. Migrations executed manually via Supabase dashboard.

#### Verify Tables

```sql
-- Check tables exist
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- Should see: tests, questions, users, test_results, topics, etc.
```

### 6. Seed Data (Optional)

Create initial dimension data:

```sql
-- Languages
INSERT INTO dim_languages (id, code, name) VALUES
(1, 'cn', 'Chinese'),
(2, 'en', 'English'),
(3, 'jp', 'Japanese');

-- Test Types
INSERT INTO dim_test_types (type_code, requires_audio, is_active) VALUES
('reading', false, true),
('listening', true, true),
('dictation', true, true);

-- Categories (examples)
INSERT INTO dim_categories (name, description, is_active) VALUES
('Daily Life', 'Everyday activities and routines', true),
('Technology', 'Computers, internet, and digital life', true),
('Culture', 'Cultural traditions and customs', true);

-- Lenses
INSERT INTO dim_lenses (name, description) VALUES
('Personal Experience', 'First-person perspective'),
('How-to Guide', 'Instructional approach'),
('News Report', 'Journalistic style');
```

### 7. Run Development Server

```bash
python app.py
```

Visit: [http://localhost:5000](http://localhost:5000)

**Expected output**:
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

---

## Running AI Pipelines

### Test Generation Pipeline

```bash
# Ensure .env is configured
# Run from project root
python scripts/run_test_generation.py
```

**Requires**:
- Topics in `production_queue` table
- All API keys configured (OpenAI, Azure, R2)
- Service role Supabase key

**Output**: Tests inserted into `tests` and `questions` tables

### Topic Generation Pipeline

```bash
python scripts/run_topic_generation.py
```

**Requires**:
- Categories in `dim_categories` table
- OpenRouter or OpenAI key
- Service role Supabase key

**Output**: Topics inserted into `topics` table, queued to `production_queue`

---

## Testing

### Manual Testing

No automated test suite currently. Testing is manual via:

1. **Login Flow**: Test OTP email delivery and verification
2. **Test Taking**: Take tests in all 3 modes
3. **Test Generation**: Run pipeline and verify output
4. **Payments**: Use Stripe test card (4242 4242 4242 4242)

### Test Stripe Payments

```
Card Number: 4242 4242 4242 4242
Expiry: Any future date (e.g., 12/34)
CVC: Any 3 digits (e.g., 123)
ZIP: Any 5 digits (e.g., 12345)
```

---

## Production Deployment

### Environment Differences

| Aspect | Development | Production |
|--------|-------------|------------|
| **FLASK_ENV** | development | production |
| **FLASK_DEBUG** | True | False |
| **Stripe Keys** | Test mode | Live mode |
| **Domain** | localhost:5000 | your-domain.com |
| **HTTPS** | Optional | Required |

### Deployment Checklist

- [ ] Set `FLASK_ENV=production` and `FLASK_DEBUG=False`
- [ ] Use production Supabase project
- [ ] Switch to Stripe live keys
- [ ] Configure custom domain with HTTPS
- [ ] Set strong `SECRET_KEY` (generate via `os.urandom(24)`)
- [ ] Configure CORS for production domain only
- [ ] Setup error logging and monitoring
- [ ] Configure R2 bucket CORS for production domain
- [ ] Setup database backups
- [ ] Configure rate limiting on auth endpoints
- [ ] Review and tighten RLS policies

### Deployment Options

#### Option 1: Traditional Server (e.g., DigitalOcean, AWS EC2)

```bash
# Install dependencies
pip install -r requirements.txt

# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

**Nginx reverse proxy** (recommended):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Option 2: Platform-as-a-Service (e.g., Heroku, Render)

**Procfile**:
```
web: gunicorn app:app
```

**Environment Variables**: Set via platform dashboard

#### Option 3: Serverless (e.g., Vercel, AWS Lambda)

**Note**: Flask not optimal for serverless. Consider refactoring to FastAPI or Next.js for serverless deployment.

---

## Troubleshooting

### Common Issues

#### 1. Supabase Connection Errors

**Error**: `Could not connect to Supabase`

**Solutions**:
- Verify `SUPABASE_URL` is correct (check for typos)
- Ensure API keys are valid (regenerate if needed)
- Check network/firewall rules

#### 2. OpenAI API Errors

**Error**: `Authentication failed` or `Insufficient quota`

**Solutions**:
- Verify `OPENAI_API_KEY` is correct
- Check OpenAI account has available credits
- Ensure GPT-4 access is enabled

#### 3. Azure TTS Errors

**Error**: `Speech synthesis failed`

**Solutions**:
- Verify `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`
- Check Azure subscription is active
- Ensure region matches your Speech resource region

#### 4. R2 Upload Errors

**Error**: `Failed to upload audio to R2`

**Solutions**:
- Verify R2 credentials (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`)
- Check bucket name is correct
- Ensure bucket CORS is configured

#### 5. Database Migration Errors

**Error**: `Relation does not exist`

**Solutions**:
- Verify all migrations have been executed
- Check table names for typos
- Ensure using correct Supabase project

#### 6. Import Errors

**Error**: `ModuleNotFoundError: No module named 'xyz'`

**Solutions**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### 7. Port Already in Use

**Error**: `Address already in use`

**Solutions**:
```bash
# Find process using port 5000
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Kill process or use different port
python app.py --port 5001
```

---

## Environment Variables Reference

See [Environment Variables](./04-environment-variables.md) for complete documentation of all 30+ environment variables.

**Critical Variables** (must be set):
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OPENAI_API_KEY`
- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `STRIPE_SECRET_KEY`
- `SECRET_KEY`

---

## Development Workflow

### Typical Development Cycle

1. **Pull latest changes**: `git pull origin main`
2. **Activate virtual environment**: `source venv/bin/activate`
3. **Install new dependencies** (if requirements.txt changed): `pip install -r requirements.txt`
4. **Run migrations** (if any new SQL files): Execute in Supabase SQL Editor
5. **Start development server**: `python app.py`
6. **Make changes**: Edit Python/HTML/JS files
7. **Test locally**: Reload browser (Flask auto-reloads on code changes if `FLASK_DEBUG=True`)
8. **Commit changes**: `git add .`, `git commit -m "..."`
9. **Push to remote**: `git push origin branch-name`

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push branch
git push origin feature/new-feature

# Create pull request (via GitHub/GitLab)

# After merge, update main
git checkout main
git pull origin main
```

---

## Security Best Practices

1. **Never commit `.env`**: Add to `.gitignore`
2. **Rotate API keys regularly**: Especially service role key
3. **Use environment-specific keys**: Test keys for dev, live keys for prod
4. **Enable 2FA**: On all service accounts (Supabase, OpenAI, Azure, Stripe)
5. **Monitor API usage**: Set up alerts for unusual activity
6. **Backup database**: Regular automated backups via Supabase
7. **Use HTTPS in production**: Required for JWT security
8. **Sanitize user input**: Escape HTML, validate on backend

---

## Performance Optimization

### Development

- Use Flask debug mode for auto-reload
- Use browser DevTools to debug frontend
- Monitor Supabase logs for slow queries

### Production

- Enable Supabase connection pooling
- Use CDN for static assets
- Enable gzip compression (Nginx/Cloudflare)
- Cache audio files on R2 with long TTL
- Monitor with APM tools (e.g., Sentry, DataDog)

---

## Related Documents

- [Environment Variables](./04-environment-variables.md)
- [Coding Conventions](./01-coding-conventions.md)
- [Error Handling](./02-error-handling.md)
- [Project Overview](../01-Overview/01-project-overview.md)
- [Tech Stack](../01-Overview/02-tech-stack.md)

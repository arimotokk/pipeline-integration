# VAT Pipeline Deployment Guide

## Phase 1 Complete: Code Ready ✓

Your deployment files are ready:
- `requirements-deploy.txt` - Updated dependencies with PostgreSQL + R2
- `database-deploy.py` - Works with both SQLite (local) and PostgreSQL (cloud)
- `app-deploy.py` - Main app with R2 file storage support
- `render.yaml` - Render deployment configuration
- `.env.example` - Environment variables template

## What Changed?

### 1. Database (SQLite → PostgreSQL)
- **Local**: Still uses SQLite (vat_invoices.db) for testing
- **Production**: Auto-switches to PostgreSQL when DATABASE_URL env var exists
- No code changes needed - same functions work for both!

### 2. File Storage (Local → Cloudflare R2)
- **Local**: Saves files to `uploads/` folder
- **Production**: Uploads to Cloudflare R2 (cloud storage)
- Files identified by `r2://` prefix in database

### 3. New Dependencies
- `psycopg2-binary` - PostgreSQL driver
- `boto3` - S3-compatible API for R2
- `gunicorn` - Production web server

## Next Steps

### Phase 2: Set Up Cloudflare R2 (15 mins)

1. **Create Cloudflare Account**
   - Go to https://dash.cloudflare.com/sign-up
   - Free tier includes 10GB storage

2. **Create R2 Bucket**
   - Dashboard → R2 → Create bucket
   - Name: `vat-invoices`
   - Location: Automatic

3. **Get API Credentials**
   - R2 → Manage R2 API Tokens → Create API Token
   - Permissions: Edit (read/write)
   - Copy these 3 values:
     * Access Key ID
     * Secret Access Key
     * Endpoint URL (looks like: https://xxxxx.r2.cloudflarestorage.com)

### Phase 3: Deploy to Render (20 mins)

1. **Prepare Your Repo**
   ```bash
   cd /Users/arimotosaki/Documents/GitHub/pipeline-integration
   
   # Copy new deployment files
   cp requirements-deploy.txt requirements.txt
   cp database-deploy.py database.py
   cp app-deploy.py app.py
   cp render.yaml render.yaml
   
   # Commit changes
   git add .
   git commit -m "Add deployment configuration"
   git push origin main
   ```

2. **Create Render Account**
   - Go to https://render.com/register
   - Sign up with GitHub

3. **Create New Web Service**
   - Dashboard → New + → Web Service
   - Connect your GitHub repo: `pipeline-integration`
   - Render auto-detects `render.yaml` ✓

4. **Set Environment Variables**
   - In Render dashboard, go to Environment tab
   - Add these secrets:
     * `ANTHROPIC_API_KEY` = (your existing API key)
     * `R2_ENDPOINT_URL` = (from Cloudflare R2)
     * `R2_ACCESS_KEY_ID` = (from Cloudflare R2)
     * `R2_SECRET_ACCESS_KEY` = (from Cloudflare R2)
     * `R2_BUCKET_NAME` = vat-invoices
   
   Note: DATABASE_URL is auto-set by Render ✓

5. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for first deployment
   - Your URL: `https://vat-pipeline-xxxx.onrender.com`

### Phase 4: Test Online (10 mins)

1. **Open Your App**
   - Go to your Render URL
   - Should see upload page

2. **Upload Test Invoice**
   - Upload one of your sample invoices
   - Verify extraction works
   - Check invoice appears in history

3. **Verify Persistence**
   - Close browser
   - Reopen your URL
   - Invoice should still be there ✓

4. **Share Demo Link**
   - Copy your Render URL
   - Share with potential employers
   - Works 24/7 with your data persisted

## Testing Locally First (Recommended)

Before deploying, test the new code locally:

```bash
cd /Users/arimotosaki/Documents/GitHub/pipeline-integration

# Backup current working files
cp app.py app-backup.py
cp database.py database-backup.py
cp requirements.txt requirements-backup.txt

# Use deployment versions locally
cp app-deploy.py app.py
cp database-deploy.py database.py

# Install new dependencies
source venv/bin/activate
pip install psycopg2-binary boto3 gunicorn

# Run locally (still uses SQLite)
python3 app.py
```

Open http://localhost:5002 - should work exactly as before!

## Troubleshooting

### "ModuleNotFoundError: psycopg2"
```bash
pip install psycopg2-binary
```

### "Connection refused" on Render
- Check Environment Variables are set correctly
- Check Logs in Render dashboard
- DATABASE_URL should auto-populate

### Files not uploading to R2
- Verify R2 credentials in Environment Variables
- Check bucket name matches: `vat-invoices`
- Endpoint URL must include https://

### Database not persisting
- Make sure DATABASE_URL is set (Render does this automatically)
- Check Render database is created and connected

## Cost Breakdown

- **Render Web Service**: Free tier (750 hours/month)
- **Render PostgreSQL**: Free tier (90 days, then $7/month)
- **Cloudflare R2**: Free tier (10GB storage, unlimited downloads)

Total monthly cost after 90 days: ~$7/month (or stay free by creating new Render account)

## What You'll Get

✓ Public demo URL: `https://vat-pipeline-xxxx.onrender.com`
✓ Works 24/7 with no maintenance
✓ Data persists across restarts
✓ Professional deployment for job applications
✓ Can share link with employers

## Need Help?

Just ask! I'll guide you through any step.

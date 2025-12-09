# HTTP Basic Authentication Setup

This document describes the HTTP Basic Authentication implementation for the VAT Integration Pipeline.

## Overview

The application uses Flask-HTTPAuth to implement HTTP Basic Authentication. All routes except `/health` require authentication.

## Implementation Details

### Protected Routes (14 total)

All application routes require authentication:
- `/` - Index/Upload form
- `/upload` - File upload processing
- `/history` - Invoice history
- `/vat-summary` - VAT summary
- `/download-excel` - Excel export
- `/download-pdf` - PDF export
- `/errors` - Error dashboard
- `/error-review` - Error review
- `/manual-entry/<id>` - Manual entry form
- `/manual-entry/submit` - Submit manual entry
- `/delete/<id>` - Delete invoice
- `/flag-error/<id>` - Flag error
- `/edit/<id>` - Edit invoice
- `/edit/submit` - Submit edit

### Unauthenticated Routes

- `/health` - Health check endpoint (returns `{"status": "healthy"}`)

## Local Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export AUTH_USERNAME="your_username"
   export AUTH_PASSWORD="your_password"
   ```

3. **Run the application:**
   ```bash
   python3 app.py
   ```

4. **Test authentication:**
   - Visit `http://localhost:5002/` - should prompt for login
   - Visit `http://localhost:5002/health` - should return JSON without authentication
   - Enter correct credentials - should grant access
   - Enter wrong credentials - should return 401 Unauthorized

5. **Run automated tests:**
   ```bash
   export AUTH_USERNAME="demo"
   export AUTH_PASSWORD="demo123"
   python3 test_auth.py
   ```

## Render Deployment

1. **Add environment variables in Render Dashboard:**
   - Navigate to: https://dashboard.render.com/
   - Select your service: `pipeline-integration`
   - Go to **Environment** tab
   - Add two new environment variables:
     - `AUTH_USERNAME` = your_chosen_username
     - `AUTH_PASSWORD` = your_chosen_password
   - Click **Save Changes**

2. **Deploy to Render:**
   ```bash
   git add .
   git commit -m "Add HTTP Basic Authentication"
   git push origin your-branch-name
   ```

3. **Verify deployment:**
   - Visit: https://pipeline-integration-mm0d.onrender.com/
   - Browser should show authentication prompt
   - Enter credentials from Render environment variables
   - Visit: https://pipeline-integration-mm0d.onrender.com/health
   - Should return `{"status": "healthy"}` without authentication

## Security Notes

- Credentials are transmitted securely over HTTPS on Render
- Passwords are stored in environment variables, not in code
- Default 401 response for unauthorized access
- No custom error pages or branded messages
- Health check endpoint allows monitoring without credentials

## Testing Checklist

- [ ] Flask-HTTPAuth installed (`flask-httpauth==4.8.0`)
- [ ] All 14 routes protected with `@auth.login_required`
- [ ] Health endpoint `/health` accessible without authentication
- [ ] Environment variables `AUTH_USERNAME` and `AUTH_PASSWORD` set
- [ ] Browser shows authentication prompt on main site
- [ ] Correct credentials grant access to all pages
- [ ] Wrong credentials return 401 Unauthorized
- [ ] No `.env` file with real credentials in repository

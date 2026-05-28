# Deployment Guide - Railway + Vercel

This guide walks through deploying the Breathe ESG application with:
- **Backend (Django)**: Railway + PostgreSQL
- **Frontend (React)**: Vercel

---

## Prerequisites

- GitHub account
- Railway account (sign up at [railway.app](https://railway.app))
- Vercel account (sign up at [vercel.com](https://vercel.com))
- Code pushed to GitHub repository

---

## Part 1: Deploy Backend to Railway

### Step 1: Create New Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `breathe` repository
5. Railway auto-detects Django ✅

### Step 2: Add PostgreSQL Database

1. In project dashboard, click "New"
2. Select "Database" → "Add PostgreSQL"
3. Railway automatically creates `DATABASE_URL` environment variable

### Step 3: Configure Service Settings

1. Click on your Django service (not the database)
2. Go to "Settings" tab
3. Under "Service Settings":
   - **Root Directory**: `backend`
   - **Start Command**: (leave empty, uses Procfile)

### Step 4: Add Environment Variables

Click "Variables" tab and add:

```env
SECRET_KEY=<generate-from-https://djecrety.ir/>
DEBUG=False
ALLOWED_HOSTS=<your-service>.up.railway.app
CSRF_TRUSTED_ORIGINS=https://<your-service>.up.railway.app
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

**Note:** You'll update `CORS_ALLOWED_ORIGINS` after deploying frontend.

### Step 5: Deploy

1. Railway starts deploying automatically
2. Wait for "Success" status (~2-3 minutes)
3. Copy your backend URL from the "Deployments" tab
   - Example: `https://breathe-backend-production.up.railway.app`

### Step 6: Run Database Migrations

1. Click your service → Top right menu (•••) → "New Shell"
2. Run these commands:
   ```bash
   python manage.py migrate
   python manage.py seed_clean_demo
   ```
3. Wait for "Command completed successfully"

### Step 7: Test Backend

Visit: `https://your-backend.up.railway.app/api/`

Should see:
```json
{
  "activities": "https://...",
  "source-files": "https://...",
  ...
}
```

✅ **Backend deployed!**

---

## Part 2: Deploy Frontend to Vercel

### Step 8: Create New Project

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New..." → "Project"
3. Import your `breathe` repository

### Step 9: Configure Build Settings

- **Framework Preset**: Vite
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### Step 10: Add Environment Variable

Under "Environment Variables", add:

**Name**: `VITE_API_BASE_URL`  
**Value**: `https://your-backend.up.railway.app/api`

(Use your actual Railway backend URL from Step 5)

### Step 11: Deploy

1. Click "Deploy"
2. Wait for deployment (~2-3 minutes)
3. Copy your frontend URL
   - Example: `https://breathe-esg.vercel.app`

✅ **Frontend deployed!**

---

## Part 3: Update CORS Settings

### Step 12: Update Railway Environment Variables

1. Go back to Railway dashboard
2. Click your Django service → "Variables"
3. Update these variables:

```env
CORS_ALLOWED_ORIGINS=https://your-app.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-backend.up.railway.app,https://your-app.vercel.app
ALLOWED_HOSTS=your-backend.up.railway.app,your-app.vercel.app
```

(Replace with your actual URLs)

4. Railway will auto-redeploy (~1 minute)

---

## Testing Deployment

### ✅ Test Checklist

1. **Backend API**
   - Visit: `https://your-backend.up.railway.app/api/`
   - Should return JSON with endpoints

2. **Frontend Loads**
   - Visit: `https://your-app.vercel.app`
   - Should see login page

3. **Login Works**
   - Username: `acme_admin`
   - Password: `admin123`
   - Should redirect to dashboard

4. **File Upload**
   - Upload a SAP CSV file
   - Check for emissions calculation
   - Verify no CORS errors in browser console

5. **Review Queue**
   - Should show uploaded activities
   - Emissions should be populated (not 0)

---

## Demo Credentials

After running `seed_clean_demo`, use these credentials:

**Organization 1: Acme Manufacturing**
- Admin: `acme_admin` / `admin123`
- Analyst: `acme_analyst` / `analyst123`

**Organization 2: TechCorp Industries**
- Admin: `tech_admin` / `admin123`
- Analyst: `tech_analyst` / `analyst123`

---

## Troubleshooting

### "CORS error" in browser console

**Fix:** Update Railway environment variables:
```env
CORS_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-backend.up.railway.app,https://your-vercel-app.vercel.app
```

### "502 Bad Gateway" on Railway

**Check:**
1. Railway dashboard → Logs tab
2. Look for errors in deployment logs

**Common fixes:**
- Ensure `gunicorn` is in `requirements.txt` ✅
- Check `Procfile` exists ✅
- Verify `runtime.txt` has correct Python version ✅

### "Network Error" when uploading files

**Check:**
1. Vercel environment variable `VITE_API_BASE_URL` is correct
2. Make sure URL ends with `/api` (no trailing slash)
3. Check Railway logs for backend errors

### "Database connection failed"

**Fix:** Railway provides `DATABASE_URL` automatically. If missing:
1. Railway dashboard → Database service
2. Copy "Internal Database URL"
3. Add as `DATABASE_URL` variable to Django service

### Static files not loading

**Fix:**
```bash
# In Railway shell
python manage.py collectstatic --noinput
```

---

## Monitoring

### Railway

- **Logs**: Service → "Logs" tab
- **Metrics**: Service → "Metrics" tab (CPU, memory, requests)
- **Database**: Database service → "Metrics" (storage, connections)

### Vercel

- **Analytics**: Project → "Analytics" tab
- **Logs**: Project → "Deployments" → Click deployment → "Function Logs"

---

## Updating Deployment

### Backend Updates

1. Push changes to GitHub
2. Railway auto-deploys
3. If migrations added, run in Railway shell:
   ```bash
   python manage.py migrate
   ```

### Frontend Updates

1. Push changes to GitHub
2. Vercel auto-deploys

### Environment Variable Updates

**Railway:**
- Dashboard → Service → Variables → Edit → Save
- Service auto-redeploys

**Vercel:**
- Dashboard → Project → Settings → Environment Variables → Edit → Save
- Click "Redeploy" on latest deployment

---

## URLs to Submit

After deployment, submit these in your assignment:

1. **Live Frontend URL**: `https://your-app.vercel.app`
2. **Live Backend URL**: `https://your-backend.up.railway.app`
3. **GitHub Repository**: `https://github.com/your-username/breathe`

**Demo Credentials**: `acme_admin` / `admin123`

---

## Cost

Both Railway and Vercel offer **free tiers** suitable for this prototype:

- **Railway Free**: $5 credit/month (enough for prototype)
- **Vercel Free**: Unlimited personal projects
- **PostgreSQL**: Included in Railway

---

## Support

If deployment fails:
1. Check Railway logs: Dashboard → Service → Logs
2. Check Vercel logs: Dashboard → Deployments → Click deployment
3. Check browser console for frontend errors (F12)

---

**Deployment complete! 🚀**

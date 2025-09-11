# 🚀 NHP Analyzer - Render Deployment Guide

## ✅ Issues Fixed

### 1. **Hardcoded Windows Paths** - FIXED ✅
- Removed hardcoded Tesseract path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Removed hardcoded Poppler path: `D:\NHP models\poppler-25.07.0\Library\bin`
- Added dynamic path detection for Linux environments

### 2. **Corrupted Requirements File** - FIXED ✅
- Replaced corrupted 200+ dependency file with clean 16 essential dependencies
- Removed duplicate and unnecessary packages

### 3. **Missing Render Configuration** - FIXED ✅
- Created `render.yaml` with proper system dependencies
- Added `Procfile` for alternative deployment
- Created `install_dependencies.sh` script

### 4. **Production Configuration** - FIXED ✅
- Updated app.py to use environment PORT variable
- Added proper debug mode detection
- Updated frontend to handle production URLs

## 🚀 How to Deploy to Render

### Step 1: Prepare Your Repository
1. Commit all the changes I made:
```bash
git add .
git commit -m "Fix Render deployment issues"
git push origin main
```

### Step 2: Deploy to Render
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:

**Basic Settings:**
- **Name**: `nhp-analyzer-backend`
- **Environment**: `Python 3`
- **Region**: `Oregon (US West)`
- **Branch**: `main`

**Build & Deploy:**
- **Root Directory**: Leave empty (uses root)
- **Build Command**: 
```bash
apt-get update && apt-get install -y tesseract-ocr poppler-utils && pip install -r backend/requirements.txt
```
- **Start Command**: 
```bash
cd backend && python app.py
```

**Environment Variables:**
- `GEMINI_API_KEY`: Your Google Gemini API key
- `CHROMA_DB_PATH`: `./data/embeddings`
- `UPLOAD_FOLDER`: `./uploads`
- `FLASK_ENV`: `production`

### Step 3: Update Frontend
1. After deployment, get your Render URL (e.g., `https://nhp-analyzer-backend.onrender.com`)
2. Update `frontend/script.js` line 6:
```javascript
this.backendUrl = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000' 
    : 'https://YOUR-ACTUAL-RENDER-URL.onrender.com';
```
3. Redeploy your frontend to Vercel

## 🔧 Alternative: Using render.yaml

If you prefer, you can use the `render.yaml` file I created:

1. In Render dashboard, select "New +" → "Blueprint"
2. Connect your repository
3. Render will automatically detect and use the `render.yaml` configuration

## 🐛 Common Issues & Solutions

### Issue: "Tesseract not found"
**Solution**: The build command installs tesseract-ocr, but if it fails:
- Add this to your build command: `apt-get install -y tesseract-ocr`

### Issue: "Poppler not found" 
**Solution**: The build command installs poppler-utils, but if it fails:
- Add this to your build command: `apt-get install -y poppler-utils`

### Issue: "Port binding error"
**Solution**: The app now uses `os.environ.get('PORT', 5000)` which Render sets automatically

### Issue: "CORS errors"
**Solution**: Flask-CORS is configured, but make sure your frontend URL is correct

## 📋 Pre-Deployment Checklist

- [ ] All hardcoded paths removed ✅
- [ ] Requirements.txt cleaned up ✅
- [ ] Environment variables configured ✅
- [ ] Build command includes system dependencies ✅
- [ ] Frontend URL updated with actual Render URL
- [ ] GEMINI_API_KEY set in Render environment variables

## 🎯 Expected Deployment Time
- **Build**: 5-10 minutes (installing system dependencies)
- **Startup**: 1-2 minutes (loading ML models)

## 📞 Support
If you still get errors, check:
1. Render build logs for specific error messages
2. Make sure your GEMINI_API_KEY is valid
3. Verify the frontend URL matches your actual Render URL

# Signal & Scale - Local Deployment Instructions

## 🚀 Quick Deployment Steps

### Step 1: Navigate to your local Signal & Scale repository
```bash
cd "~/Signal & Scale"  # Note the quotes for spaces in folder name
```

### Step 2: Create and switch to feature branch
```bash
git checkout -b feat/signal-scale-core
```

### Step 3: Copy the enhanced files
1. **Replace `src/api/main.py`** with the `main.py` from this package
2. **Add `README-BRAND.md`** to your repository root
3. **Replace `requirements.txt`** with the enhanced version from this package

### Step 4: Update .gitignore (append these lines)
```
# Signal & Scale Cache and Data
__pycache__/
.venv/
.env
node_modules/
dist/
*.log
data/cache/
```

### Step 5: Commit and push
```bash
git add src/api/main.py README-BRAND.md requirements.txt .gitignore
git commit -m "feat(core): add real data integration, API routes, and brand intelligence"
git push -u origin feat/signal-scale-core
```

### Step 6: Create Pull Request
1. Go to https://github.com/Jillian-ignited/Signal-Scale
2. Click "Compare & pull request" for feat/signal-scale-core
3. Title: "Signal & Scale core bundle"
4. Description: "Real data integration with YouTube API, PageSpeed Insights, web scraping, and enhanced brand intelligence"

## 🔧 Environment Variables to Set After Deployment

```bash
PYTHON_VERSION=3.11
PSI_API_KEY=YOUR_GOOGLE_PAGESPEED_API_KEY
YOUTUBE_API_KEY=YOUR_YOUTUBE_DATA_API_KEY
ALLOW_MOCK=false
CACHE_DIR=./data/cache
```

## ✅ Features Added

- **YouTube Data API v3**: Real subscriber counts and channel analytics
- **Google PageSpeed Insights API**: Website performance analysis  
- **Web Scraping**: Twitter profile discovery and metrics
- **Enhanced Intelligence Database**: Comprehensive brand financial data
- **Confidence Scoring**: 60-95% based on data source quality
- **Professional PDF Reports**: Enterprise-ready documentation

## 🎯 Result

Your Signal & Scale platform will have legitimate real data integration that justifies premium pricing with verifiable social media metrics and strategic insights.

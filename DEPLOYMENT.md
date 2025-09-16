# 🚀 Signal & Scale - Deployment Guide

## GitHub + Render Deployment

### Step 1: Upload to GitHub

1. **Extract the zip file** to your local machine
2. **Create a new GitHub repository** (or use existing)
3. **Push the code to GitHub:**

```bash
# Navigate to your extracted project
cd signal-scale

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial Signal & Scale platform"

# Add your GitHub repo as remote
git remote add origin https://github.com/yourusername/signal-scale.git
git push -u origin main
```

### Step 2: Deploy on Render

1. **Go to [Render.com](https://render.com)** and sign in
2. **Click "New +" → "Web Service"**
3. **Connect your GitHub repository**
4. **Configure deployment settings:**

   **Basic Settings:**
   - **Name**: `signal-scale` (or your preferred name)
   - **Environment**: `Python 3`
   - **Region**: Choose closest to your users
   - **Branch**: `main`

   **Build & Deploy:**
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt && cd frontend && npm install && npm run build
     ```
   - **Start Command**: 
     ```bash
     cd src && uvicorn api.main:app --host 0.0.0.0 --port $PORT
     ```

   **Advanced Settings:**
   - **Auto-Deploy**: `Yes` (deploys automatically on git push)

5. **Set Environment Variables** (if needed):
   - `MANUS_API_KEY`: Your Manus API key
   - `PYTHON_VERSION`: `3.11.0`
   - Any other API keys for data sources

6. **Click "Create Web Service"**

### Step 3: Verify Deployment

Once deployed, Render will give you a URL like `https://signal-scale.onrender.com`

**Test these endpoints:**
- **Dashboard**: `https://your-app.onrender.com/`
- **Health Check**: `https://your-app.onrender.com/health`
- **API Docs**: `https://your-app.onrender.com/docs`
- **Demo Data**: `https://your-app.onrender.com/api/demo-data`

## 🔧 Configuration Options

### Environment Variables

Set these in Render's dashboard under "Environment":

```bash
# Required for some data sources
MANUS_API_KEY=your_manus_api_key_here

# Optional: Custom configuration
PYTHON_VERSION=3.11.0
NODE_VERSION=18
```

### Custom Domain (Optional)

1. In Render dashboard, go to your service
2. Click "Settings" → "Custom Domains"
3. Add your domain (e.g., `app.yourdomain.com`)
4. Update your DNS to point to Render

## 📊 Monitoring & Logs

### Health Monitoring
- **Health Endpoint**: `/health`
- **Status**: Returns `{"status": "healthy", "service": "signal-scale-api"}`

### Viewing Logs
1. Go to your Render service dashboard
2. Click "Logs" tab
3. Monitor real-time application logs

### Performance Monitoring
- Render provides built-in metrics
- Monitor response times and error rates
- Set up alerts for downtime

## 🔄 Updates & Maintenance

### Automatic Deployments
- Push to `main` branch triggers automatic deployment
- Build takes ~3-5 minutes
- Zero-downtime deployments

### Manual Deployment
1. Go to Render dashboard
2. Click "Manual Deploy" → "Deploy latest commit"

### Rollback
1. Go to "Deployments" tab
2. Click "Rollback" on any previous deployment

## 🛡️ Security Best Practices

### API Keys
- Store all API keys as environment variables
- Never commit API keys to git
- Rotate keys regularly

### CORS Configuration
- Currently set to allow all origins (`*`)
- For production, restrict to your domains:
  ```python
  allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"]
  ```

### HTTPS
- Render provides free SSL certificates
- All traffic is automatically encrypted

## 💰 Pricing Considerations

### Render Pricing
- **Starter**: Free tier (limited resources)
- **Starter**: $7/month (basic production)
- **Standard**: $25/month (recommended for production)
- **Pro**: $85/month (high performance)

### Scaling
- Render auto-scales based on traffic
- Monitor usage in dashboard
- Upgrade plan as needed

## 🚨 Troubleshooting

### Common Issues

**Build Fails:**
- Check that `requirements.txt` is in root directory
- Verify Node.js version compatibility
- Check build logs for specific errors

**Frontend Not Loading:**
- Ensure `npm run build` completed successfully
- Check that `dist/` folder exists in frontend
- Verify static file serving in FastAPI

**API Errors:**
- Check environment variables are set
- Monitor logs for Python errors
- Test endpoints individually

### Getting Help

1. **Check Render logs** for error details
2. **Test locally** to isolate issues
3. **Check GitHub issues** for known problems
4. **Contact support** if deployment-specific

## 📈 Performance Optimization

### Frontend Optimization
- React app is pre-built and minified
- Static assets served efficiently
- Gzip compression enabled

### Backend Optimization
- FastAPI with async/await
- Efficient data processing
- Proper error handling

### Database Considerations
- Currently uses in-memory data
- For production, consider adding Redis/PostgreSQL
- Render offers managed databases

---

## 🎉 You're Live!

Once deployed, your Signal & Scale platform will be accessible to customers worldwide. The sophisticated dashboard and powerful API are ready to generate revenue from fashion and consumer brands.

**Next Steps:**
1. Test all functionality on your live URL
2. Set up custom domain (optional)
3. Configure monitoring and alerts
4. Start onboarding customers!

**Your platform is now ready to compete with enterprise-level solutions at a fraction of the cost.**


# Signal & Scale - Brand Intelligence Platform

A premium competitive intelligence platform designed for fashion and consumer product brands. Built with a sophisticated React frontend and powerful Python backend.

## 🎯 Target Market

- **Fashion Brands**: Streetwear, luxury, contemporary fashion
- **Consumer Product Brands**: Lifestyle, beauty, accessories
- **Agencies**: Marketing agencies serving fashion/consumer brands
- **Pricing Tiers**: $499 / $999 / $2500 monthly subscriptions

## ✨ Key Features

### 📊 Weekly Reports
- Brand mention tracking and sentiment analysis
- Engagement highlights across social platforms
- Streetwear trend identification
- Competitive mention analysis
- Opportunities and risk assessment

### 🎭 Cultural Radar
- Emerging creator discovery (under 100K followers)
- Influence scoring and engagement analysis
- Creator recommendation engine (seed/collab/monitor)
- Platform-specific insights (TikTok, Instagram, YouTube)

### 🏆 Peer Tracker
- DTC website competitive analysis
- Multi-dimensional scoring (Homepage, PDP, Checkout, etc.)
- Strengths and gaps identification
- Priority improvement recommendations

## 🚀 Quick Start

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <your-repo-url>
   cd signal-scale
   pip install -r requirements.txt
   ```

2. **Build frontend:**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

3. **Run the application:**
   ```bash
   cd src
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Access the platform:**
   - Dashboard: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

### Render Deployment

1. **Connect your GitHub repo to Render**

2. **Create a new Web Service with these settings:**
   - **Build Command**: `pip install -r requirements.txt && cd frontend && npm install && npm run build`
   - **Start Command**: `cd src && uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3.11

3. **Set environment variables** (if needed):
   - `MANUS_API_KEY`: Your Manus API key
   - Any other API keys for data sources

4. **Deploy!** Render will automatically build and deploy your app.

## 🏗️ Architecture

```
signal-scale/
├── src/                    # Python backend
│   ├── api/               # FastAPI routes
│   ├── models/            # Pydantic data models
│   ├── orchestrator/      # Main analysis engine
│   ├── collectors/        # Data collection modules
│   ├── analyzers/         # Analysis algorithms
│   └── validators/        # JSON schema validation
├── frontend/              # React dashboard
│   ├── src/
│   │   ├── components/    # UI components
│   │   └── App.jsx       # Main dashboard
│   └── dist/             # Built frontend (served by FastAPI)
├── docs/                  # Documentation
├── tests/                 # Test suites
└── config/               # Configuration files
```

## 🎨 Design Philosophy

Inspired by Sara Blakely's approach to Spanx - sophisticated, empowering, and accessible. The design uses:

- **Sophisticated color palette**: Warm stones, creams, strategic accents
- **Premium typography**: Clean, approachable, authoritative
- **Data-rich visualizations**: Beautiful but actionable
- **Empowering language**: Makes users feel like industry insiders

## 📡 API Endpoints

### Core Analysis
- `POST /api/analyze` - Run competitive intelligence analysis
- `GET /api/demo-data` - Get demo data for testing
- `GET /api/modes` - Get available analysis modes

### Health & Monitoring
- `GET /health` - Health check endpoint
- `GET /` - Serve React dashboard

### Legacy Support
- `POST /analyze` - Legacy analysis endpoint
- `GET /modes` - Legacy modes endpoint

## 🧪 Testing

```bash
# Run the brand-neutral test suite
python test_brand_neutral.py

# Run basic functionality tests
python test_simple.py

# Run pytest suite
pytest
```

## 🔧 Configuration

The platform is designed to be brand-neutral and configurable:

- **Brand Information**: Name, URL, metadata (aliases, hashtags, etc.)
- **Competitor Sets**: Flexible competitor definitions
- **Analysis Modes**: weekly_report, cultural_radar, peer_tracker, or all
- **Time Windows**: Configurable analysis periods
- **Result Limits**: Configurable result set sizes

## 💰 Revenue Features

### Subscription Tiers
- **Starter ($499)**: Basic reports, 3 competitors, monthly analysis
- **Professional ($999)**: Advanced insights, 8 competitors, weekly analysis, PDF exports
- **Enterprise ($2500)**: Real-time monitoring, unlimited competitors, white-label reports

### Export & Reporting
- Professional PDF reports
- Data export capabilities
- White-label options for agencies
- API access for enterprise clients

## 🛡️ Security & Performance

- **CORS enabled** for cross-origin requests
- **Health monitoring** with dedicated endpoints
- **Error handling** with graceful degradation
- **Performance optimized** for 90-120 second analysis cycles
- **Scalable architecture** ready for high-volume usage

## 📈 Competitive Advantage

1. **Fashion-Focused**: Built specifically for fashion/streetwear brands
2. **Creator Discovery**: Unique focus on emerging influencers
3. **Actionable Insights**: Clear next steps, not just data
4. **Premium UX**: Enterprise-level design and experience
5. **Brand-Neutral**: Works with any brand, not hardcoded

## 🤝 Support

For technical support, feature requests, or business inquiries:
- Create an issue in this repository
- Contact: [your-email@domain.com]

---

**Built with ❤️ for the fashion industry**


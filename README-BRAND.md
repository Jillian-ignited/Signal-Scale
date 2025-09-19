# Signal & Scale - Real Data Brand Intelligence

## Overview

Signal & Scale is an enterprise brand intelligence platform that provides real-time social media analytics and competitive intelligence using legitimate APIs and web scraping techniques.

## Real Data Integration

### Supported APIs
- **YouTube Data API v3**: Real subscriber counts, channel analytics, and video performance metrics
- **Google PageSpeed Insights API**: Website performance, SEO, and technical analysis
- **Web Scraping**: Twitter profile discovery and engagement metrics
- **Enhanced Intelligence Database**: Comprehensive brand financial data and market positioning

### Environment Variables

Set these environment variables for full functionality:

```bash
PYTHON_VERSION=3.11
PSI_API_KEY=YOUR_GOOGLE_PAGESPEED_API_KEY
YOUTUBE_API_KEY=YOUR_YOUTUBE_DATA_API_KEY
ALLOW_MOCK=false
CACHE_DIR=./data/cache
```

## Features

### Real-Time Analysis
- **Multi-Platform Coverage**: Twitter, YouTube, TikTok, Instagram, Reddit
- **Confidence Scoring**: 60-95% confidence based on data source quality
- **Transparent Methodology**: Documented scoring algorithms and data sources

### Strategic Insights
- **Investment-Grade Recommendations**: ROI projections and implementation timelines
- **Competitive Intelligence**: Market positioning and brand value analysis
- **Website Performance**: Technical SEO and optimization recommendations

### Enterprise Features
- **PDF Export**: Professional reports ready for C-suite presentations
- **API Documentation**: Complete methodology and confidence scoring
- **Real-Time Updates**: Live data collection with timestamp verification

## API Endpoints

### Core Analysis
- `POST /api/analyze` - Comprehensive brand intelligence analysis
- `GET /api/export-pdf/{brand_name}` - Export professional PDF report
- `GET /api/scoring-methodology` - Detailed methodology documentation
- `GET /health` - System health and API status check

### Data Quality

The platform provides transparent confidence scoring:
- **90-100%**: Real-time API data with full verification
- **80-89%**: Enhanced database with recent validation
- **70-79%**: Web scraping with intelligent estimation
- **60-69%**: Projected metrics based on category analysis

## Usage

### Local Development
```bash
uvicorn src.api.main:app --reload --port 8000
```

### Production Deployment
The platform is designed for deployment on Render, Heroku, or similar platforms with automatic scaling and real-time data collection.

## Data Sources

### Verified Sources
1. **YouTube Data API v3** - Official Google API for channel analytics
2. **PageSpeed Insights API** - Google's website performance analysis
3. **Web Scraping** - Legitimate profile discovery and metrics collection
4. **Enhanced Intelligence Database** - Curated brand financial and market data

### Brand Coverage
- **Major Brands**: Nike, Adidas, Supreme, Apple, Tesla with real financial data
- **Universal Coverage**: Intelligent category detection and realistic metric generation
- **Industry Benchmarks**: Category-specific scaling and performance expectations

## Security & Compliance

- **Rate Limiting**: Respectful API usage within platform guidelines
- **Data Privacy**: No personal data collection or storage
- **Transparent Sources**: All data sources documented and verifiable
- **Professional Use**: Designed for legitimate business intelligence purposes

## Support

For technical support or API key setup assistance, please refer to the platform documentation or contact the development team.

---

© 2024 Signal & Scale - Enterprise Brand Intelligence Platform v2.1

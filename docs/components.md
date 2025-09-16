# CI Orchestrator Components

## Core Architecture

### 1. Data Collectors (`src/collectors/`)
- **SocialMediaCollector**: Instagram, TikTok, X/Twitter, Reddit, YouTube data
- **EcommerceCollector**: Amazon, eBay, StockX, Grailed, Depop, Farfetch, SSENSE
- **WebsiteCollector**: Brand and competitor website analysis
- **TrendCollector**: Cultural and fashion trend monitoring

### 2. Analyzers (`src/analyzers/`)
- **SentimentAnalyzer**: Customer sentiment analysis
- **EngagementAnalyzer**: Social media engagement metrics
- **InfluenceScorer**: Cultural radar influence scoring algorithm
- **PeerScorer**: Website comparison and scoring
- **TrendAnalyzer**: Streetwear trend detection and analysis

### 3. Validators (`src/validators/`)
- **JSONValidator**: Output schema validation
- **DataValidator**: Input parameter validation
- **QualityValidator**: Data quality checks

### 4. API Interface (`src/api/`)
- **FastAPI Router**: REST API endpoints
- **RequestHandler**: Input processing and validation
- **ResponseFormatter**: JSON output formatting
- **ErrorHandler**: Error handling and fallbacks

## Key Dependencies

### Data Collection
- **requests**: HTTP requests for web scraping
- **beautifulsoup4**: HTML parsing
- **selenium/playwright**: Dynamic content scraping
- **aiohttp**: Async HTTP requests
- **tweepy**: Twitter API integration
- **instaloader**: Instagram data collection

### Analysis & Processing
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **textblob/vaderSentiment**: Sentiment analysis
- **python-dateutil**: Date/time processing

### Validation & Configuration
- **jsonschema**: JSON schema validation
- **pydantic**: Data models and validation
- **python-dotenv**: Environment configuration
- **pyyaml**: YAML configuration files

### API & Infrastructure
- **fastapi**: REST API framework
- **uvicorn**: ASGI server
- **ratelimit**: Rate limiting
- **structlog**: Structured logging

## Workflow Components

### 1. Router Module
- Mode detection (weekly_report, cultural_radar, peer_tracker, all)
- Input validation and parameter processing
- Workflow orchestration

### 2. Collection Pipeline
- Parallel data collection across platforms
- Rate limiting and timeout management
- Data normalization and cleaning

### 3. Analysis Pipeline
- Platform-specific analysis algorithms
- Scoring and ranking systems
- Trend detection and sentiment analysis

### 4. Output Pipeline
- JSON schema validation
- Response formatting
- Error handling and fallbacks

## Scoring Algorithms

### Cultural Radar Influence Score
```
influence_score = round(
    (engagement_rate * 0.5) + 
    (content_relevancy * 0.3) + 
    (trend_alignment * 0.2)
) # 0-100 scale
```

### Peer Tracker Scoring
- **Homepage**: Hero clarity (2), new/drop surfacing (2), load performance (2), nav clarity (2), merchandising (2)
- **PDP**: Media richness (2), details depth (2), reviews/UGC (2), size/fit (2), cross-sell (2)
- **Checkout**: Express pay options, guest checkout, steps, clarity
- **Content & Community**: UGC blocks, collabs, editorial cadence
- **Mobile UX**: Performance, tap targets, navigation ease
- **Price Presentation**: Entry price clarity, hero price anchoring, promo visibility

## Error Handling Strategy

1. **Graceful Degradation**: Return valid JSON even with missing data
2. **Source Fallbacks**: Alternative data sources when primary fails
3. **Timeout Management**: Configurable timeouts for each collector
4. **Rate Limiting**: Respect platform rate limits
5. **Data Quality Checks**: Validate data before analysis


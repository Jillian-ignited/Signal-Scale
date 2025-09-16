# CI Orchestrator Agent

A comprehensive competitive intelligence agent for fashion/streetwear brands that analyzes brand mentions, cultural trends, and peer performance across multiple platforms.

## Features

- **Weekly Report**: Track brand mentions, sentiment, engagement highlights, and competitive analysis
- **Cultural Radar**: Identify emerging creators and influencers in your target market
- **Peer Tracker**: Audit your DTC site against competitors across key dimensions
- **Multi-Platform Analysis**: Instagram, TikTok, X/Twitter, Reddit, YouTube, eCommerce platforms
- **Structured JSON Output**: Clean, validated data ready for integration

## Modes

1. **weekly_report**: Brand monitoring and trend analysis
2. **cultural_radar**: Creator discovery and influence scoring
3. **peer_tracker**: Competitive website analysis
4. **all**: Combined analysis across all modes

## Quick Start

```python
from ci_orchestrator import CIOrchestrator

# Initialize the agent
agent = CIOrchestrator()

# Run analysis
result = agent.analyze({
    "brand": {"name": "Crooks & Castles", "url": "https://crooksncastles.com"},
    "competitors": [
        {"name": "Paper Planes", "url": "https://paperplane.shop"},
        {"name": "Stüssy", "url": "https://stussy.com"}
    ],
    "mode": "all",
    "window_days": 7
})

print(result)
```

## Project Structure

```
ci_orchestrator/
├── src/
│   ├── collectors/     # Data collection modules
│   ├── analyzers/      # Analysis and scoring algorithms
│   ├── validators/     # JSON schema validation
│   └── api/           # API interface
├── config/            # Configuration files
├── docs/              # Documentation
├── tests/             # Test files
└── examples/          # Usage examples
```

## Installation

```bash
pip install -r requirements.txt
```

## API Usage

The agent exposes a REST API for integration:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "brand": {"name": "Crooks & Castles", "url": "https://crooksncastles.com"},
    "competitors": [{"name": "Paper Planes", "url": "https://paperplane.shop"}],
    "mode": "weekly_report",
    "window_days": 7
  }'
```

## Documentation

- [Requirements](docs/requirements.md)
- [API Reference](docs/api.md)
- [Configuration](docs/configuration.md)
- [Examples](examples/)

## License

MIT License


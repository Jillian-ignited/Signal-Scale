# CI Orchestrator Agent Requirements

## Overview
The CI Orchestrator is a competitive intelligence agent for fashion/streetwear brands that analyzes brand mentions, cultural trends, and peer performance across multiple platforms.

## Input Parameters

### Required Inputs
- **brand** (object): `{ "name": "string", "url": "string?" }`
- **competitors** (array): `{ "name": "string", "url": "string?" }[]`
- **mode** (enum): `weekly_report | cultural_radar | peer_tracker | all` (default: all)
- **window_days** (int): Analysis time window in days (default: 7)

### Optional Inputs
- **influencer_max_followers** (int): Maximum follower count for cultural radar (default: 100000)
- **min_engagement_rate** (float): Minimum engagement rate threshold (default: 0.05)
- **price_band** (string): Target price range (default: "$40–$150")
- **max_competitors** (int): Maximum number of competitors to analyze (default: 8)
- **max_results_per_section** (int): Maximum results per output section (default: 10)

## Output Modes

### 1. Weekly Report
Tracks brand mentions, sentiment, engagement highlights, streetwear trends, competitive mentions, and opportunities/risks over the specified time window across:
- Instagram, TikTok, X/Twitter, Reddit, YouTube, Facebook groups
- eCommerce platforms: Amazon, eBay, StockX, Grailed, Depop, Farfetch, SSENSE

### 2. Cultural Radar
Finds emerging creators with high engagement in the target price band:
- Tier 1: Already posting about the brand
- Tier 2: Relevant but not yet posting
- Influence score: engagement rate + content relevancy + trend alignment (0–100)

### 3. Peer Tracker
Audits brand's DTC site vs peers across:
- Homepage, PDP, Checkout, Content & Community, Mobile UX, Price Presentation
- Scores each dimension 1–10 with detailed notes

## Data Sources
- Social Media: Instagram, TikTok, X/Twitter, Reddit, YouTube, Facebook
- eCommerce: Amazon, eBay, StockX, Grailed, Depop, Farfetch, SSENSE
- Brand websites and DTC platforms
- Cultural trend monitoring across platforms

## Technical Requirements
- Return strict JSON only (no Markdown or prose)
- Handle inaccessible sources gracefully
- Implement rate limiting and timeout guards
- Support concurrent data collection
- Validate output against defined schema


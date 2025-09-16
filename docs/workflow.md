_# CI Orchestrator Workflow Architecture

## 1. Input Processing
- The API receives a POST request with the `CIOrchestratorInput` data.
- The input data is validated against the Pydantic model.
- The `mode` parameter determines which analysis modules to run.

## 2. Orchestration Layer
- The `Orchestrator` class manages the overall workflow.
- It initializes the necessary data collectors and analyzers based on the selected `mode`.
- It runs the analysis modules in parallel where possible (e.g., collecting data from multiple sources).

## 3. Data Collection
- **Weekly Report**: 
    - `SocialMediaCollector` fetches brand mentions, sentiment, and engagement data from Instagram, TikTok, X/Twitter, Reddit, and YouTube.
    - `EcommerceCollector` scrapes competitive mentions and pricing data from e-commerce platforms.
- **Cultural Radar**:
    - `SocialMediaCollector` searches for emerging creators based on follower count, engagement rate, and keywords.
- **Peer Tracker**:
    - `WebsiteCollector` crawls the brand's and competitors' websites to analyze homepage, PDP, checkout, etc.

## 4. Analysis and Scoring
- **Weekly Report**:
    - `SentimentAnalyzer` processes text data to determine positive, negative, and neutral sentiment.
    - `EngagementAnalyzer` calculates engagement metrics and identifies highlights.
    - `TrendAnalyzer` identifies emerging streetwear trends.
- **Cultural Radar**:
    - `InfluenceScorer` calculates the influence score for each creator.
    - Creators are tiered based on their relevance and brand mentions.
- **Peer Tracker**:
    - `PeerScorer` scores each brand across the defined dimensions.
    - Strengths, gaps, and priority fixes are identified.

## 5. Output Generation
- The results from the analysis modules are aggregated.
- The final output is formatted according to the `CIOrchestratorOutput` model.
- The JSON output is validated against the schema before being returned.

## 6. Error Handling
- If a data source is unavailable, the corresponding section in the output will be populated with a note indicating the source was unavailable.
- Timeouts and rate limits are handled gracefully to prevent the agent from failing.
- Invalid input data will result in a 422 HTTP error with a descriptive message.
_


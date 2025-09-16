# CI Orchestrator - Manus Agent Integration Specification

This document outlines the API specification for the CI Orchestrator, a brand-neutral competitive intelligence agent designed to work with the Manus platform.

## Goal

The primary goal is to provide a single, API-runnable agent that works for any brand, covering three distinct analysis workflows:

- **weekly_report**: Tracks brand mentions, customer sentiment, engagement highlights, streetwear trends, competitive mentions, and identifies opportunities and risks.
- **cultural_radar**: Identifies emerging creators and influencers with under 100,000 followers and an engagement rate greater than or equal to a specified threshold.
- **peer_tracker**: Audits a brand's direct-to-consumer (DTC) website against its competitors across a set of key dimensions.

## API Endpoint

### Trigger & Authentication

- **HTTP Method**: `POST`
- **Endpoint**: `{BASE_URL}{RUN_PATH}` (The specific URL will be provided by the Manus platform)
- **Authentication**: `Authorization: Bearer {MANUS_API_KEY}`
- **Content-Type**: `application/json`

### Latency Target

The agent aims for a response time of **≤ 90–120 seconds** per request. It is designed to degrade gracefully by returning partial results and warnings if certain data sources are slow or unavailable.

## Request Body

The request body must be a JSON object with the following structure. All input field names must match exactly.

```json
{
  "agent_id": "AGENT_ID_FROM_MANUS",
  "brand": {
    "name": "Crooks & Castles",
    "url": "https://crooksncastles.com",
    "meta": {
      "aliases": ["C&C"],
      "hashtags": ["#crooksncastles"]
    }
  },
  "competitors": [
    {
      "name": "Paper Planes",
      "url": "https://paperplane.shop"
    },
    {
      "name": "Stüssy",
      "url": "https://stussy.com"
    }
  ],
  "mode": "all",
  "window_days": 7,
  "influencer_max_followers": 100000,
  "min_engagement_rate": 0.05,
  "price_band": "$40–$150",
  "max_competitors": 8,
  "max_results_per_section": 10,
  "context": {
    "source": "signal-scale",
    "version": "v1"
  }
}
```

### Request Parameters

| Field                      | Type     | Description                                                                                                                                      |
| -------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `agent_id`                 | `string` | The unique identifier of the agent, provided by the Manus platform.                                                                              |
| `brand`                    | `object` | An object containing information about the target brand.                                                                                         |
| `brand.name`               | `string` | The name of the brand.                                                                                                                           |
| `brand.url`                | `string` | (Optional) The URL of the brand's website.                                                                                                       |
| `brand.meta`               | `object` | (Optional) A dictionary for brand-specific metadata, such as `aliases`, `hashtags`, `priority_platforms`, and `blocked_domains`.                  |
| `competitors`              | `array`  | An array of competitor objects.                                                                                                                  |
| `mode`                     | `string` | The analysis mode. Must be one of `weekly_report`, `cultural_radar`, `peer_tracker`, or `all`.                                                    |
| `window_days`              | `integer`| (Optional) The number of days to look back for data collection. Defaults to `7`.                                                                 |
| `influencer_max_followers` | `integer`| (Optional) The maximum number of followers for an influencer to be considered in the cultural radar. Defaults to `100000`.                         |
| `min_engagement_rate`      | `float`  | (Optional) The minimum engagement rate for an influencer to be considered. Defaults to `0.05` (5%).                                               |
| `price_band`               | `string` | (Optional) The price band to focus on for creator and trend analysis. Defaults to `"$40–$150"`.                                                  |
| `max_competitors`          | `integer`| (Optional) The maximum number of competitors to analyze in the peer tracker. Used to cap the volume of work. Defaults to `8`.                     |
| `max_results_per_section`  | `integer`| (Optional) The maximum number of results to return in each section of the output. Used to cap the size of the result. Defaults to `10`.          |
| `context`                  | `object` | (Optional) An object for passing contextual information, such as the source of the request and the API version.                                  |

## Response Body

The agent will return a strict JSON response with no Markdown. If a section is not requested (based on the `mode`), it will be omitted from the response. If data is unavailable for a particular section, the agent will return empty arrays and a `warnings` array with details.

```json
{
  "weekly_report": {
    "brand_mentions_overview": { "this_window": 0, "prev_window": 0, "delta_pct": 0 },
    "customer_sentiment": { "positive": "", "negative": "", "neutral": "" },
    "engagement_highlights": [
      { "platform": "instagram", "link": "https://...", "why_it_matters": "..." }
    ],
    "streetwear_trends": [
      { "theme": "utility cargos", "evidence": "…", "hashtags": ["#streetwear", "#gorpcore"] }
    ],
    "competitive_mentions": [
      { "competitor": "Stüssy", "context": "compared on fit/price", "link": "https://..." }
    ],
    "opportunities_risks": [
      { "type": "opportunity", "insight": "…", "action": "…", "impact": "high" }
    ]
  },
  "cultural_radar": {
    "creators": [
      {
        "creator": "@handle",
        "platform": "tiktok",
        "profile": "https://tiktok.com/@handle",
        "followers": 42000,
        "engagement_rate": 0.067,
        "brand_mentioned": true,
        "content_focus": "ootd, techwear",
        "recommendation": "seed",
        "influence_score": 78
      }
    ],
    "top_3_to_activate": [
      { "creator": "@handle", "why": "Tier 1, high ER", "action": "seed" }
    ]
  },
  "peer_tracker": {
    "scorecard": {
      "dimensions": ["Homepage","PDP","Checkout","ContentCommunity","MobileUX","PricePresentation"],
      "brands": ["Crooks & Castles","Paper Planes","Stüssy"],
      "scores": [
        { "dimension": "Homepage", "brand": "Crooks & Castles", "score": 7, "notes": ["New arrivals visible", "Hero loads fast"] },
        { "dimension": "Homepage", "brand": "Stüssy", "score": 9, "notes": ["Stronger editorial", "Clear drop CTA"] }
      ]
    },
    "strengths": ["Media richness on PDPs"],
    "gaps": ["Fewer express pay options on checkout"],
    "priority_fixes": [
      { "fix": "Add Apple Pay + Klarna", "impact": "high", "why": "Reduce abandonment" }
    ]
  },
  "warnings": ["instagram blocked for some queries"],
  "provenance": {
    "sources": ["https://instagram.com/p/...","https://stussy.com/..."]
  }
}
```

### Response Fields

- **`weekly_report`**: Contains the weekly competitive intelligence analysis.
- **`cultural_radar`**: Contains the analysis of emerging creators and influencers.
- **`peer_tracker`**: Contains the DTC website audit and competitive scorecard.
- **`warnings`**: An array of strings containing any warnings or non-critical errors that occurred during the analysis (e.g., a platform blocking access).
- **`provenance`**: An object containing an array of source URLs for the data used in the analysis.

## Rules and Constraints

- **No free-text outside JSON**: The response must be a valid JSON object. No Markdown tables or other non-JSON content.
- **Graceful degradation**: If a platform blocks access, the agent will still return the relevant section with empty arrays and add a meaningful warning to the `warnings` array.
- **`influence_score`**: An integer between 0 and 100, computed from engagement rate, content relevancy, and trend alignment.
- **`peer_tracker.scores[*].score`**: An integer between 1 and 10, with one or two notes explaining the score.
- **Provenance**: The `provenance` section should include source URLs whenever possible.

## Error Handling

- **422 Unprocessable Entity**: If the input schema is invalid, the agent will return a 422 status code with a JSON response containing validation details.
- **200 OK with Warnings**: For data access issues or timeouts, the agent will return a 200 status code with partial results and a `warnings` array.
- **Hard Failures**: If the agent must fail hard, it will return a JSON response with an `error` object containing the error `type` and `message`.

## Performance and Limits

- The agent will respect the `max_competitors` and `max_results_per_section` parameters to control the volume of work and the size of the response.
- The overall timeout for each request is **≤ 120 seconds**. The agent will not block the entire run on a single slow source; it will skip the source and add a warning.

## Versioning

The agent will accept a `context.version` string in the request and include a `version` field in the response to allow for future evolution without breaking existing integrations.

## Acceptance Criteria

- The agent works with any brand and set of competitors (no hardcoded brand names).
- The agent returns the specified JSON contract for each of the `mode` options (`weekly_report`, `cultural_radar`, `peer_tracker`, and `all`).
- The agent returns partial results and a `warnings` array when encountering source limits, instead of failing.
- A round-trip test with the specified inputs completes in under 120 seconds.



_# CI Orchestrator Scoring Algorithms

## 1. Cultural Radar: Influence Score

The influence score is a metric from 0 to 100 that quantifies a creator's potential impact and relevance to the brand. It is calculated as a weighted average of three key factors:

- **Engagement Rate (50%)**: The creator's average engagement rate on their primary platform.
- **Content Relevancy (30%)**: How well the creator's content aligns with the brand's niche and target audience.
- **Trend Alignment (20%)**: How well the creator's content reflects current streetwear trends.

**Formula:**
```
influence_score = round(
    (engagement_rate * 0.5) + 
    (content_relevancy * 0.3) + 
    (trend_alignment * 0.2)
)
```

## 2. Peer Tracker: Website Scoring

The peer tracker scores each brand's website on a scale of 1 to 10 across six key dimensions. Each dimension is scored based on a set of heuristics, and the final score is the sum of the points awarded for each heuristic.

### Scoring Dimensions & Heuristics:

- **Homepage (10 points)**:
    - Hero clarity (2 pts)
    - New/drop surfacing (2 pts)
    - Load performance (LCP) (2 pts)
    - Navigation clarity (2 pts)
    - Merchandising (2 pts)

- **Product Detail Page (PDP) (10 points)**:
    - Media richness (2 pts)
    - Details depth (2 pts)
    - Reviews/UGC (2 pts)
    - Size/fit information (2 pts)
    - Cross-sell/up-sell (2 pts)

- **Checkout (10 points)**:
    - Express pay options (e.g., Apple Pay, Shop Pay) (3 pts)
    - Guest checkout option (3 pts)
    - Number of steps to complete checkout (2 pts)
    - Clarity of pricing and fees (2 pts)

- **Content & Community (10 points)**:
    - User-generated content (UGC) integration (3 pts)
    - Collaborations and partnerships showcased (3 pts)
    - Editorial content and blog (2 pts)
    - Community engagement features (2 pts)

- **Mobile UX (10 points)**:
    - Responsive design and mobile-first layout (3 pts)
    - Tap target size and spacing (3 pts)
    - Navigation ease on mobile (2 pts)
    - Page load speed on mobile (2 pts)

- **Price Presentation (10 points)**:
    - Clarity of entry-level pricing (3 pts)
    - Hero product price anchoring (3 pts)
    - Visibility of promotions and discounts (2 pts)
    - Transparency of shipping costs (2 pts)
_


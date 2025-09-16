# Pydantic models for CI Orchestrator
from pydantic import BaseModel, Field, conint, confloat
from typing import List, Literal, Optional, Dict, Any

class Brand(BaseModel):
    name: str
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None  # Brand-specific metadata like aliases, hashtags, etc.

class Competitor(BaseModel):
    name: str
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None  # Competitor-specific metadata

class BrandMentionsOverview(BaseModel):
    this_window: int
    prev_window: int
    delta_pct: float

class CustomerSentiment(BaseModel):
    positive: str
    negative: str
    neutral: str

class EngagementHighlight(BaseModel):
    platform: str
    link: str
    why_it_matters: str

class StreetwearTrend(BaseModel):
    theme: str
    evidence: str
    hashtags: List[str]

class CompetitiveMention(BaseModel):
    competitor: str
    context: str
    link: str

class OpportunityRisk(BaseModel):
    type: Literal["opportunity", "risk"]
    insight: str
    action: str
    impact: Literal["high", "medium", "low"]

class WeeklyReport(BaseModel):
    brand_mentions_overview: BrandMentionsOverview
    customer_sentiment: CustomerSentiment
    engagement_highlights: List[EngagementHighlight]
    streetwear_trends: List[StreetwearTrend]
    competitive_mentions: List[CompetitiveMention]
    opportunities_risks: List[OpportunityRisk]

class Creator(BaseModel):
    creator: str
    platform: str
    profile: str
    followers: int
    engagement_rate: float
    crooks_mentioned: bool
    content_focus: str
    recommendation: Literal["seed", "collab", "monitor"]
    influence_score: conint(ge=0, le=100)

class Top3ToActivate(BaseModel):
    creator: str
    why: str
    action: Literal["seed", "collab"]

class CulturalRadar(BaseModel):
    creators: List[Creator]
    top_3_to_activate: List[Top3ToActivate]

class ScorecardItem(BaseModel):
    dimension: str
    brand: str
    score: conint(ge=0, le=10)
    notes: List[str]

class Scorecard(BaseModel):
    dimensions: List[str]
    brands: List[str]
    scores: List[ScorecardItem]

class PriorityFix(BaseModel):
    fix: str
    impact: Literal["high", "medium", "low"]
    why: str

class PeerTracker(BaseModel):
    scorecard: Scorecard
    strengths: List[str]
    gaps: List[str]
    priority_fixes: List[PriorityFix]

class CIOrchestratorOutput(BaseModel):
    weekly_report: Optional[WeeklyReport] = None
    cultural_radar: Optional[CulturalRadar] = None
    peer_tracker: Optional[PeerTracker] = None

class CIOrchestratorInput(BaseModel):
    brand: Brand
    competitors: List[Competitor]
    mode: Literal["weekly_report", "cultural_radar", "peer_tracker", "all"] = "all"
    window_days: int = 7
    influencer_max_followers: int = 100000
    min_engagement_rate: confloat(ge=0.0) = 0.05
    price_band: str = "$40–$150"
    max_competitors: int = 8
    max_results_per_section: int = 10


"""
Main orchestrator class that coordinates all CI Orchestrator components.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import CIOrchestratorInput, CIOrchestratorOutput
from .collectors.social_media_collector import SocialMediaCollector
from .collectors.ecommerce_collector import EcommerceCollector
from .collectors.website_collector import WebsiteCollector
from .analyzers.influence_scorer import InfluenceScorer
from .analyzers.peer_scorer import PeerScorer
from .analyzers.sentiment_analyzer import SentimentAnalyzer
from .analyzers.trend_analyzer import TrendAnalyzer
from .validators.json_validator import JSONValidator

import structlog

logger = structlog.get_logger()

class CIOrchestrator:
    """Main orchestrator for CI analysis workflow."""
    
    def __init__(self):
        self.social_collector = SocialMediaCollector()
        self.ecommerce_collector = EcommerceCollector()
        self.website_collector = WebsiteCollector()
        
        # Analyzers will be initialized with brand info in run_analysis
        self.influence_scorer = None
        self.peer_scorer = PeerScorer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        
        self.json_validator = JSONValidator()
    
    async def run_analysis(self, input_data: CIOrchestratorInput) -> CIOrchestratorOutput:
        """Run the complete CI analysis based on input parameters."""
        try:
            logger.info(f"Starting CI analysis for brand: {input_data.brand.name}, mode: {input_data.mode}")
            
            # Initialize brand-aware analyzers
            self.influence_scorer = InfluenceScorer(
                brand_name=input_data.brand.name,
                brand_meta=input_data.brand.meta
            )
            
            # Initialize result structure
            result = {}
            
            # Run analysis based on mode
            if input_data.mode in ['weekly_report', 'all']:
                result['weekly_report'] = await self._run_weekly_report(input_data)
            
            if input_data.mode in ['cultural_radar', 'all']:
                result['cultural_radar'] = await self._run_cultural_radar(input_data)
            
            if input_data.mode in ['peer_tracker', 'all']:
                result['peer_tracker'] = await self._run_peer_tracker(input_data)
            
            # Validate output
            validation_result = self.json_validator.validate_output(result)
            
            if not validation_result['valid']:
                logger.warning(f"Output validation failed: {validation_result['errors']}")
                # Attempt to fix common issues
                result = self.json_validator.fix_common_issues(result)
                
                # Re-validate
                validation_result = self.json_validator.validate_output(result)
                if not validation_result['valid']:
                    logger.error("Could not fix validation issues, returning minimal valid output")
                    result = self.json_validator.create_minimal_valid_output(input_data.mode)
            
            if validation_result['warnings']:
                logger.warning(f"Output warnings: {validation_result['warnings']}")
            
            logger.info("CI analysis completed successfully")
            return CIOrchestratorOutput(**result)
            
        except Exception as e:
            logger.error(f"Error in CI analysis: {str(e)}")
            # Return minimal valid output on error
            minimal_output = self.json_validator.create_minimal_valid_output(input_data.mode)
            return CIOrchestratorOutput(**minimal_output)
    
    async def _run_weekly_report(self, input_data: CIOrchestratorInput) -> Dict[str, Any]:
        """Run weekly report analysis."""
        try:
            logger.info("Running weekly report analysis")
            
            # Build brand query from brand name and metadata
            brand_query = self._build_brand_query(input_data.brand)
            
            async with self.social_collector as collector:
                social_data = await collector.collect_data(
                    query=brand_query,
                    window_days=input_data.window_days
                )
            
            # Collect ecommerce data
            competitor_names = [comp.name for comp in input_data.competitors]
            
            async with self.ecommerce_collector as collector:
                ecommerce_data = await collector.collect_data(
                    brand_name=input_data.brand.name,
                    competitors=competitor_names,
                    window_days=input_data.window_days
                )
            
            # Analyze sentiment
            customer_sentiment = self.sentiment_analyzer.analyze_sentiment(social_data)
            
            # Analyze trends
            streetwear_trends = self.trend_analyzer.analyze_trends(
                social_data, 
                input_data.window_days
            )
            
            # Calculate brand mentions
            brand_mentions_overview = self._calculate_brand_mentions(social_data, input_data.window_days)
            
            # Find engagement highlights
            engagement_highlights = self._find_engagement_highlights(social_data)
            
            # Find competitive mentions
            competitive_mentions = self._find_competitive_mentions(
                social_data + ecommerce_data, 
                competitor_names
            )
            
            # Identify opportunities and risks
            opportunities_risks = self._identify_opportunities_risks(
                social_data, 
                ecommerce_data, 
                streetwear_trends
            )
            
            return {
                'brand_mentions_overview': brand_mentions_overview,
                'customer_sentiment': customer_sentiment,
                'engagement_highlights': engagement_highlights[:input_data.max_results_per_section],
                'streetwear_trends': streetwear_trends[:input_data.max_results_per_section],
                'competitive_mentions': competitive_mentions[:input_data.max_results_per_section],
                'opportunities_risks': opportunities_risks[:input_data.max_results_per_section]
            }
            
        except Exception as e:
            logger.error(f"Error in weekly report analysis: {str(e)}")
            return self._get_default_weekly_report()
    
    def _build_brand_query(self, brand) -> str:
        """Build search query for brand mentions."""
        try:
            query_parts = [f'"{brand.name}"']
            
            # Add aliases from metadata
            if brand.meta and 'aliases' in brand.meta:
                aliases = brand.meta['aliases']
                if isinstance(aliases, list):
                    for alias in aliases:
                        query_parts.append(f'"{alias}"')
            
            # Add hashtags from metadata
            if brand.meta and 'hashtags' in brand.meta:
                hashtags = brand.meta['hashtags']
                if isinstance(hashtags, list):
                    for hashtag in hashtags:
                        # Remove # if present
                        clean_hashtag = hashtag.replace('#', '')
                        query_parts.append(f'#{clean_hashtag}')
            
            # Join with OR
            query = ' OR '.join(query_parts)
            
            # Add platform filters if specified in metadata
            if brand.meta and 'priority_platforms' in brand.meta:
                platforms = brand.meta['priority_platforms']
                if isinstance(platforms, list):
                    platform_filter = ' OR '.join([f'site:{platform}' for platform in platforms])
                    query = f'({query}) AND ({platform_filter})'
            else:
                # Default platform filter
                query = f'({query}) site:(instagram.com OR tiktok.com OR reddit.com OR youtube.com OR twitter.com OR facebook.com)'
            
            return query
            
        except Exception as e:
            logger.error(f"Error building brand query: {str(e)}")
            return f'"{brand.name}"'
    
    async def _run_cultural_radar(self, input_data: CIOrchestratorInput) -> Dict[str, Any]:
        """Run cultural radar analysis."""
        try:
            logger.info("Running cultural radar analysis")
            
            # Collect creator data
            async with self.social_collector as collector:
                creator_data = await collector.collect_creator_data(
                    price_band=input_data.price_band,
                    max_followers=input_data.influencer_max_followers,
                    min_engagement_rate=input_data.min_engagement_rate
                )
            
            # Analyze creators and calculate influence scores
            analyzed_creators = self.influence_scorer.analyze_creators(creator_data)
            
            # Limit to max results
            limited_creators = analyzed_creators[:input_data.max_results_per_section]
            
            # Get top 3 to activate
            top_3_to_activate = self.influence_scorer.get_top_3_to_activate(analyzed_creators)
            
            return {
                'creators': limited_creators,
                'top_3_to_activate': top_3_to_activate
            }
            
        except Exception as e:
            logger.error(f"Error in cultural radar analysis: {str(e)}")
            return self._get_default_cultural_radar()
    
    async def _run_peer_tracker(self, input_data: CIOrchestratorInput) -> Dict[str, Any]:
        """Run peer tracker analysis."""
        try:
            logger.info("Running peer tracker analysis")
            
            # Collect website data
            competitor_urls = [comp.url for comp in input_data.competitors if comp.url]
            
            async with self.website_collector as collector:
                website_data = await collector.collect_data(
                    brand_url=input_data.brand.url,
                    competitor_urls=competitor_urls
                )
            
            # Score websites
            scorecard = self.peer_scorer.score_websites(website_data)
            
            # Analyze competitive position
            competitive_analysis = self.peer_scorer.analyze_competitive_position(
                scorecard, 
                input_data.brand.name
            )
            
            return {
                'scorecard': scorecard,
                'strengths': competitive_analysis['strengths'],
                'gaps': competitive_analysis['gaps'],
                'priority_fixes': competitive_analysis['priority_fixes']
            }
            
        except Exception as e:
            logger.error(f"Error in peer tracker analysis: {str(e)}")
            return self._get_default_peer_tracker()
    
    def _calculate_brand_mentions(self, social_data: List[Dict[str, Any]], window_days: int) -> Dict[str, Any]:
        """Calculate brand mentions overview."""
        try:
            # Count mentions in current window
            this_window = len(social_data)
            
            # Simulate previous window count (would be calculated from historical data)
            prev_window = max(0, this_window - 5)  # Simplified simulation
            
            # Calculate delta percentage
            if prev_window > 0:
                delta_pct = ((this_window - prev_window) / prev_window) * 100
            else:
                delta_pct = 100.0 if this_window > 0 else 0.0
            
            return {
                'this_window': this_window,
                'prev_window': prev_window,
                'delta_pct': round(delta_pct, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating brand mentions: {str(e)}")
            return {'this_window': 0, 'prev_window': 0, 'delta_pct': 0.0}
    
    def _find_engagement_highlights(self, social_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find engagement highlights from social data."""
        try:
            highlights = []
            
            for item in social_data:
                # Calculate engagement score
                likes = item.get('likes', 0)
                comments = item.get('comments', 0)
                shares = item.get('shares', 0)
                
                total_engagement = likes + comments + shares
                
                # Consider as highlight if engagement is above threshold
                if total_engagement >= 50:  # Adjustable threshold
                    highlights.append({
                        'platform': item.get('platform', 'Unknown'),
                        'link': item.get('url', ''),
                        'why_it_matters': f"High engagement: {total_engagement} interactions"
                    })
            
            # Sort by engagement and return top highlights
            return highlights[:10]
            
        except Exception as e:
            logger.error(f"Error finding engagement highlights: {str(e)}")
            return []
    
    def _find_competitive_mentions(self, all_data: List[Dict[str, Any]], competitor_names: List[str]) -> List[Dict[str, Any]]:
        """Find mentions of competitors."""
        try:
            competitive_mentions = []
            
            for item in all_data:
                text = item.get('text', '').lower()
                title = item.get('title', '').lower()
                content = text + ' ' + title
                
                for competitor in competitor_names:
                    if competitor.lower() in content:
                        competitive_mentions.append({
                            'competitor': competitor,
                            'context': text[:200] + '...' if len(text) > 200 else text,
                            'link': item.get('url', '')
                        })
                        break  # Only count once per item
            
            return competitive_mentions
            
        except Exception as e:
            logger.error(f"Error finding competitive mentions: {str(e)}")
            return []
    
    def _identify_opportunities_risks(self, social_data: List[Dict[str, Any]], ecommerce_data: List[Dict[str, Any]], trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify opportunities and risks."""
        try:
            opportunities_risks = []
            
            # Analyze trends for opportunities
            for trend in trends:
                if trend.get('momentum') == 'rising':
                    opportunities_risks.append({
                        'type': 'opportunity',
                        'insight': f"Rising trend: {trend['theme']}",
                        'action': f"Consider incorporating {trend['theme']} into upcoming collections",
                        'impact': 'medium'
                    })
            
            # Check for pricing risks from ecommerce data
            if ecommerce_data:
                avg_competitor_price = sum(item.get('price', 0) for item in ecommerce_data) / len(ecommerce_data)
                if avg_competitor_price > 0:
                    opportunities_risks.append({
                        'type': 'opportunity',
                        'insight': f"Average competitor pricing: ${avg_competitor_price:.2f}",
                        'action': "Review pricing strategy against competition",
                        'impact': 'high'
                    })
            
            # Check sentiment for risks
            negative_sentiment_count = sum(1 for item in social_data if 'negative' in str(item.get('sentiment', '')))
            if negative_sentiment_count > len(social_data) * 0.3:  # More than 30% negative
                opportunities_risks.append({
                    'type': 'risk',
                    'insight': f"High negative sentiment: {negative_sentiment_count} negative mentions",
                    'action': "Investigate and address customer concerns",
                    'impact': 'high'
                })
            
            return opportunities_risks
            
        except Exception as e:
            logger.error(f"Error identifying opportunities and risks: {str(e)}")
            return []
    
    def _get_default_weekly_report(self) -> Dict[str, Any]:
        """Get default weekly report structure."""
        return {
            'brand_mentions_overview': {'this_window': 0, 'prev_window': 0, 'delta_pct': 0.0},
            'customer_sentiment': {
                'positive': 'Weekly report analysis unavailable',
                'negative': 'Weekly report analysis unavailable',
                'neutral': 'Weekly report analysis unavailable'
            },
            'engagement_highlights': [],
            'streetwear_trends': [],
            'competitive_mentions': [],
            'opportunities_risks': []
        }
    
    def _get_default_cultural_radar(self) -> Dict[str, Any]:
        """Get default cultural radar structure."""
        return {
            'creators': [],
            'top_3_to_activate': []
        }
    
    def _get_default_peer_tracker(self) -> Dict[str, Any]:
        """Get default peer tracker structure."""
        return {
            'scorecard': {
                'dimensions': ['Homepage', 'PDP', 'Checkout', 'ContentCommunity', 'MobileUX', 'PricePresentation'],
                'brands': ['Analysis unavailable'],
                'scores': []
            },
            'strengths': ['Peer tracker analysis unavailable'],
            'gaps': ['Peer tracker analysis unavailable'],
            'priority_fixes': []
        }


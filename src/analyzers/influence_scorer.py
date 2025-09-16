"""
Influence scoring algorithm for cultural radar analysis.
"""
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()

class InfluenceScorer:
    """Calculates influence scores for creators in the cultural radar."""
    
    def __init__(self, brand_name: str = None, brand_meta: Dict[str, Any] = None):
        self.brand_name = brand_name
        self.brand_meta = brand_meta or {}
        
        # Generic streetwear keywords (brand-neutral)
        self.streetwear_keywords = [
            'streetwear', 'urban', 'street style', 'hypebeast', 'sneakers',
            'grails', 'fit check', 'ootd', 'drip', 'fresh', 'clean',
            'vintage', 'thrift', 'archive', 'rare', 'limited edition'
        ]
        
        self.trend_keywords = [
            'trending', 'viral', 'hot', 'fire', 'heat', 'must have',
            'cop', 'drop', 'release', 'collab', 'collaboration',
            'capsule', 'collection', 'exclusive'
        ]
        
        # Brand-specific keywords from metadata
        self.brand_keywords = self._get_brand_keywords()
    
    def _get_brand_keywords(self) -> List[str]:
        """Get brand-specific keywords from metadata or derive from brand name."""
        keywords = []
        
        if self.brand_name:
            # Add the brand name itself
            keywords.append(self.brand_name.lower())
            
            # Add brand name variations
            brand_words = self.brand_name.lower().split()
            keywords.extend(brand_words)
            
            # Add aliases from metadata
            if self.brand_meta and 'aliases' in self.brand_meta:
                aliases = self.brand_meta['aliases']
                if isinstance(aliases, list):
                    keywords.extend([alias.lower() for alias in aliases])
            
            # Add hashtags from metadata
            if self.brand_meta and 'hashtags' in self.brand_meta:
                hashtags = self.brand_meta['hashtags']
                if isinstance(hashtags, list):
                    keywords.extend([tag.lower().replace('#', '') for tag in hashtags])
        
        return keywords
    
    def calculate_influence_score(self, creator_data: Dict[str, Any]) -> int:
        """
        Calculate influence score (0-100) based on engagement rate, content relevancy, and trend alignment.
        
        Formula: influence_score = round((ER * 0.5) + (relevancy * 0.3) + (trend_alignment * 0.2))
        """
        try:
            # Get engagement rate (already calculated, scale to 0-100)
            engagement_rate = min(creator_data.get('engagement_rate', 0) * 100, 100)
            
            # Calculate content relevancy (0-100)
            content_relevancy = self._calculate_content_relevancy(creator_data)
            
            # Calculate trend alignment (0-100)
            trend_alignment = self._calculate_trend_alignment(creator_data)
            
            # Apply weighted formula
            influence_score = round(
                (engagement_rate * 0.5) + 
                (content_relevancy * 0.3) + 
                (trend_alignment * 0.2)
            )
            
            # Ensure score is within bounds
            influence_score = max(0, min(100, influence_score))
            
            logger.info(f"Calculated influence score for {creator_data.get('creator', 'unknown')}: {influence_score}")
            
            return influence_score
            
        except Exception as e:
            logger.error(f"Error calculating influence score: {str(e)}")
            return 0
    
    def _calculate_content_relevancy(self, creator_data: Dict[str, Any]) -> float:
        """Calculate content relevancy score (0-100) based on content analysis."""
        try:
            relevancy_score = 0.0
            
            # Analyze recent posts/content
            content_text = creator_data.get('recent_content', '')
            if not content_text:
                content_text = creator_data.get('bio', '') + ' ' + creator_data.get('content_focus', '')
            
            content_text = content_text.lower()
            
            # Check for streetwear relevance (40 points max)
            streetwear_matches = sum(1 for keyword in self.streetwear_keywords if keyword in content_text)
            streetwear_score = min(streetwear_matches * 8, 40)  # 8 points per match, max 40
            relevancy_score += streetwear_score
            
            # Check for brand mentions (30 points max)
            brand_matches = sum(1 for keyword in self.brand_keywords if keyword in content_text)
            brand_score = min(brand_matches * 15, 30)  # 15 points per match, max 30
            relevancy_score += brand_score
            
            # Check content focus alignment (30 points max)
            content_focus = creator_data.get('content_focus', '').lower()
            if content_focus in ['streetwear', 'fashion']:
                relevancy_score += 30
            elif content_focus in ['lifestyle', 'music']:
                relevancy_score += 20
            else:
                relevancy_score += 10
            
            return min(relevancy_score, 100)
            
        except Exception as e:
            logger.error(f"Error calculating content relevancy: {str(e)}")
            return 0.0
    
    def _calculate_trend_alignment(self, creator_data: Dict[str, Any]) -> float:
        """Calculate trend alignment score (0-100) based on trending content participation."""
        try:
            alignment_score = 0.0
            
            # Analyze hashtags and content for trend participation
            hashtags = creator_data.get('hashtags', [])
            content_text = creator_data.get('recent_content', '').lower()
            
            # Check for trending hashtags (40 points max)
            trending_hashtag_score = self._score_trending_hashtags(hashtags)
            alignment_score += trending_hashtag_score
            
            # Check for trend keywords in content (30 points max)
            trend_matches = sum(1 for keyword in self.trend_keywords if keyword in content_text)
            trend_keyword_score = min(trend_matches * 6, 30)  # 6 points per match, max 30
            alignment_score += trend_keyword_score
            
            # Check posting frequency and recency (30 points max)
            posting_score = self._score_posting_activity(creator_data)
            alignment_score += posting_score
            
            return min(alignment_score, 100)
            
        except Exception as e:
            logger.error(f"Error calculating trend alignment: {str(e)}")
            return 0.0
    
    def _score_trending_hashtags(self, hashtags: List[str]) -> float:
        """Score based on use of trending hashtags."""
        try:
            trending_hashtags = [
                '#streetwear', '#ootd', '#fitcheck', '#hypebeast', '#sneakers',
                '#grails', '#vintage', '#thrift', '#drip', '#fresh',
                '#trending', '#viral', '#fyp', '#foryou'
            ]
            
            hashtag_matches = 0
            for hashtag in hashtags:
                if hashtag.lower() in trending_hashtags:
                    hashtag_matches += 1
            
            return min(hashtag_matches * 8, 40)  # 8 points per trending hashtag, max 40
            
        except Exception as e:
            logger.error(f"Error scoring trending hashtags: {str(e)}")
            return 0.0
    
    def _score_posting_activity(self, creator_data: Dict[str, Any]) -> float:
        """Score based on posting frequency and recency."""
        try:
            # Check last post timestamp
            last_post = creator_data.get('last_post_timestamp')
            if not last_post:
                return 10  # Default score if no timestamp
            
            # Calculate days since last post
            if isinstance(last_post, str):
                last_post_date = datetime.fromisoformat(last_post.replace('Z', '+00:00'))
            else:
                last_post_date = last_post
            
            days_since_last_post = (datetime.now() - last_post_date.replace(tzinfo=None)).days
            
            # Score based on recency
            if days_since_last_post <= 1:
                recency_score = 20
            elif days_since_last_post <= 3:
                recency_score = 15
            elif days_since_last_post <= 7:
                recency_score = 10
            else:
                recency_score = 5
            
            # Add posting frequency score (simplified)
            posts_per_week = creator_data.get('posts_per_week', 3)
            frequency_score = min(posts_per_week * 2, 10)  # 2 points per post/week, max 10
            
            return recency_score + frequency_score
            
        except Exception as e:
            logger.error(f"Error scoring posting activity: {str(e)}")
            return 10  # Default score
    
    def determine_recommendation(self, creator_data: Dict[str, Any], influence_score: int) -> str:
        """Determine recommendation tier based on influence score and other factors."""
        try:
            crooks_mentioned = creator_data.get('crooks_mentioned', False)
            
            # Tier 1: Already posting about brand
            if crooks_mentioned:
                if influence_score >= 70:
                    return 'collab'
                else:
                    return 'seed'
            
            # Tier 2: Relevant but not yet posting
            else:
                if influence_score >= 80:
                    return 'collab'
                elif influence_score >= 60:
                    return 'seed'
                else:
                    return 'monitor'
                    
        except Exception as e:
            logger.error(f"Error determining recommendation: {str(e)}")
            return 'monitor'
    
    def check_brand_mentions(self, creator_data: Dict[str, Any]) -> bool:
        """Check if creator has mentioned the target brand."""
        try:
            content_text = creator_data.get('recent_content', '').lower()
            bio_text = creator_data.get('bio', '').lower()
            
            all_text = content_text + ' ' + bio_text
            
            # Check for brand mentions using dynamic keywords
            for keyword in self.brand_keywords:
                if keyword in all_text:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking brand mentions: {str(e)}")
            return False
    
    def analyze_creators(self, creators_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze a list of creators and add influence scores and recommendations."""
        analyzed_creators = []
        
        for creator_data in creators_data:
            try:
                # Calculate influence score
                influence_score = self.calculate_influence_score(creator_data)
                
                # Check for brand mentions
                crooks_mentioned = self.check_crooks_mentions(creator_data)
                
                # Determine recommendation
                recommendation = self.determine_recommendation(creator_data, influence_score)
                
                # Create analyzed creator data
                analyzed_creator = {
                    'creator': creator_data.get('creator', 'Unknown'),
                    'platform': creator_data.get('platform', 'Unknown'),
                    'profile': creator_data.get('profile', ''),
                    'followers': creator_data.get('followers', 0),
                    'engagement_rate': creator_data.get('engagement_rate', 0.0),
                    'brand_mentioned': self.check_brand_mentions(creator_data),
                    'content_focus': self._determine_content_focus(creator_data),
                    'recommendation': self._determine_recommendation(influence_score, creator_data),
                    'influence_score': influence_score
                }
                
                analyzed_creators.append(analyzed_creator)
                
            except Exception as e:
                logger.error(f"Error analyzing creator {creator_data.get('creator', 'unknown')}: {str(e)}")
                continue
        
        # Sort by influence score (highest first)
        analyzed_creators.sort(key=lambda x: x['influence_score'], reverse=True)
        
        return analyzed_creators
    
    def get_top_3_to_activate(self, analyzed_creators: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get top 3 creators to activate based on influence score and recommendation."""
        try:
            # Filter creators with 'seed' or 'collab' recommendations
            actionable_creators = [
                creator for creator in analyzed_creators 
                if creator['recommendation'] in ['seed', 'collab']
            ]
            
            # Sort by influence score and take top 3
            top_creators = sorted(
                actionable_creators, 
                key=lambda x: x['influence_score'], 
                reverse=True
            )[:3]
            
            # Format for output
            top_3_to_activate = []
            for creator in top_creators:
                activation_reason = self._generate_activation_reason(creator)
                
                top_3_to_activate.append({
                    'creator': creator['creator'],
                    'why': activation_reason,
                    'action': creator['recommendation']
                })
            
            return top_3_to_activate
            
        except Exception as e:
            logger.error(f"Error getting top 3 to activate: {str(e)}")
            return []
    
    def _generate_activation_reason(self, creator: Dict[str, Any]) -> str:
        """Generate a reason for why this creator should be activated."""
        try:
            influence_score = creator['influence_score']
            engagement_rate = creator['engagement_rate']
            followers = creator['followers']
            content_focus = creator['content_focus']
            crooks_mentioned = creator['crooks_mentioned']
            
            if crooks_mentioned:
                return f"Already engaged with brand, high influence score ({influence_score}), {engagement_rate:.1%} ER"
            elif influence_score >= 80:
                return f"High influence potential ({influence_score}), {content_focus} focus, {followers:,} followers"
            elif engagement_rate >= 0.05:
                return f"Strong engagement ({engagement_rate:.1%} ER), relevant {content_focus} content"
            else:
                return f"Emerging creator with {influence_score} influence score, {content_focus} alignment"
                
        except Exception as e:
            logger.error(f"Error generating activation reason: {str(e)}")
            return "High potential creator for brand collaboration"


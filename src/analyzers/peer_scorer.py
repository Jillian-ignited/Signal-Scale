"""
Peer scoring algorithm for website analysis and competitive benchmarking.
"""
from typing import Dict, List, Any, Optional
import structlog

logger = structlog.get_logger()

class PeerScorer:
    """Scores websites across multiple dimensions for competitive analysis."""
    
    def __init__(self):
        self.dimensions = [
            'Homepage',
            'PDP',
            'Checkout',
            'ContentCommunity',
            'MobileUX',
            'PricePresentation'
        ]
    
    def score_websites(self, website_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Score multiple websites and create comparative scorecard."""
        try:
            scorecard = {
                'dimensions': self.dimensions.copy(),
                'brands': [],
                'scores': []
            }
            
            # Extract brand names and create scores
            for site_data in website_data:
                brand_name = site_data.get('brand_name', 'Unknown Brand')
                scorecard['brands'].append(brand_name)
                
                # Score each dimension for this brand
                dimensions_data = site_data.get('dimensions', {})
                
                for dimension in self.dimensions:
                    dimension_data = dimensions_data.get(dimension, {})
                    score, notes = self._score_dimension(dimension, dimension_data)
                    
                    scorecard['scores'].append({
                        'dimension': dimension,
                        'brand': brand_name,
                        'score': score,
                        'notes': notes
                    })
            
            return scorecard
            
        except Exception as e:
            logger.error(f"Error scoring websites: {str(e)}")
            return self._get_default_scorecard()
    
    def _score_dimension(self, dimension: str, dimension_data: Dict[str, Any]) -> tuple[int, List[str]]:
        """Score a specific dimension and return score with notes."""
        try:
            if dimension == 'Homepage':
                return self._score_homepage(dimension_data)
            elif dimension == 'PDP':
                return self._score_pdp(dimension_data)
            elif dimension == 'Checkout':
                return self._score_checkout(dimension_data)
            elif dimension == 'ContentCommunity':
                return self._score_content_community(dimension_data)
            elif dimension == 'MobileUX':
                return self._score_mobile_ux(dimension_data)
            elif dimension == 'PricePresentation':
                return self._score_price_presentation(dimension_data)
            else:
                return 0, [f"Unknown dimension: {dimension}"]
                
        except Exception as e:
            logger.error(f"Error scoring {dimension}: {str(e)}")
            return 0, [f"Error scoring {dimension}"]
    
    def _score_homepage(self, data: Dict[str, Any]) -> tuple[int, List[str]]:
        """Score homepage (max 10 points)."""
        try:
            score = 0
            notes = []
            
            # Hero clarity (2 points)
            hero_score = data.get('hero_clarity', 0)
            score += min(hero_score, 2)
            if hero_score < 2:
                notes.append("Hero section needs clearer messaging")
            
            # New/drop surfacing (2 points)
            drops_score = data.get('new_drop_surfacing', 0)
            score += min(drops_score, 2)
            if drops_score < 2:
                notes.append("New drops not prominently featured")
            
            # Load performance (2 points)
            perf_score = data.get('load_performance', 0)
            score += min(perf_score, 2)
            if perf_score < 2:
                notes.append("Page load performance below optimal")
            
            # Navigation clarity (2 points)
            nav_score = data.get('nav_clarity', 0)
            score += min(nav_score, 2)
            if nav_score < 2:
                notes.append("Navigation could be more intuitive")
            
            # Merchandising (2 points)
            merch_score = data.get('merchandising', 0)
            score += min(merch_score, 2)
            if merch_score < 2:
                notes.append("Product merchandising needs improvement")
            
            if not notes:
                notes.append("Strong homepage performance across all areas")
            
            return min(score, 10), notes
            
        except Exception as e:
            logger.error(f"Error scoring homepage: {str(e)}")
            return 0, ["Error analyzing homepage"]
    
    def _score_pdp(self, data: Dict[str, Any]) -> tuple[int, List[str]]:
        """Score Product Detail Page (max 10 points)."""
        try:
            score = 0
            notes = []
            
            # Media richness (2 points)
            media_score = data.get('media_richness', 0)
            score += min(media_score, 2)
            if media_score < 2:
                notes.append("Product images/videos need enhancement")
            
            # Details depth (2 points)
            details_score = data.get('details_depth', 0)
            score += min(details_score, 2)
            if details_score < 2:
                notes.append("Product details lack depth")
            
            # Reviews/UGC (2 points)
            reviews_score = data.get('reviews_ugc', 0)
            score += min(reviews_score, 2)
            if reviews_score < 2:
                notes.append("Missing reviews or user-generated content")
            
            # Size/fit information (2 points)
            size_score = data.get('size_fit', 0)
            score += min(size_score, 2)
            if size_score < 2:
                notes.append("Size guide and fit info insufficient")
            
            # Cross-sell/up-sell (2 points)
            cross_sell_score = data.get('cross_sell', 0)
            score += min(cross_sell_score, 2)
            if cross_sell_score < 2:
                notes.append("Cross-sell opportunities underutilized")
            
            if not notes:
                notes.append("Excellent PDP with comprehensive product info")
            
            return min(score, 10), notes
            
        except Exception as e:
            logger.error(f"Error scoring PDP: {str(e)}")
            return 0, ["Error analyzing PDP"]
    
    def _score_checkout(self, data: Dict[str, Any]) -> tuple[int, List[str]]:
        """Score checkout process (max 10 points)."""
        try:
            score = 0
            notes = []
            
            # Express pay options (3 points)
            express_pay = data.get('express_pay_options', 0)
            score += min(express_pay, 3)
            if express_pay < 2:
                notes.append("Limited express payment options")
            
            # Guest checkout (3 points)
            guest_checkout = data.get('guest_checkout', 0)
            score += min(guest_checkout, 3)
            if guest_checkout < 2:
                notes.append("Guest checkout not available or unclear")
            
            # Checkout steps (2 points)
            steps_score = data.get('checkout_steps', 0)
            score += min(steps_score, 2)
            if steps_score < 2:
                notes.append("Too many checkout steps")
            
            # Pricing clarity (2 points)
            pricing_clarity = data.get('pricing_clarity', 0)
            score += min(pricing_clarity, 2)
            if pricing_clarity < 2:
                notes.append("Pricing and fees not transparent")
            
            if not notes:
                notes.append("Streamlined checkout with clear pricing")
            
            return min(score, 10), notes
            
        except Exception as e:
            logger.error(f"Error scoring checkout: {str(e)}")
            return 0, ["Error analyzing checkout"]
    
    def _score_content_community(self, data: Dict[str, Any]) -> tuple[int, List[str]]:
        """Score content and community features (max 10 points)."""
        try:
            score = 0
            notes = []
            
            # UGC integration (3 points)
            ugc_score = data.get('ugc_integration', 0)
            score += min(ugc_score, 3)
            if ugc_score < 2:
                notes.append("Limited user-generated content integration")
            
            # Collaborations (3 points)
            collab_score = data.get('collaborations', 0)
            score += min(collab_score, 3)
            if collab_score < 2:
                notes.append("Collaborations not well showcased")
            
            # Editorial content (2 points)
            editorial_score = data.get('editorial_content', 0)
            score += min(editorial_score, 2)
            if editorial_score < 2:
                notes.append("Lacks editorial content or blog")
            
            # Community features (2 points)
            community_score = data.get('community_features', 0)
            score += min(community_score, 2)
            if community_score < 2:
                notes.append("Community engagement features missing")
            
            if not notes:
                notes.append("Strong content strategy with community focus")
            
            return min(score, 10), notes
            
        except Exception as e:
            logger.error(f"Error scoring content/community: {str(e)}")
            return 0, ["Error analyzing content/community"]
    
    def _score_mobile_ux(self, data: Dict[str, Any]) -> tuple[int, List[str]]:
        """Score mobile user experience (max 10 points)."""
        try:
            score = 0
            notes = []
            
            # Responsive design (3 points)
            responsive_score = data.get('responsive_design', 0)
            score += min(responsive_score, 3)
            if responsive_score < 2:
                notes.append("Mobile responsiveness needs improvement")
            
            # Tap targets (3 points)
            tap_score = data.get('tap_targets', 0)
            score += min(tap_score, 3)
            if tap_score < 2:
                notes.append("Tap targets too small or poorly spaced")
            
            # Navigation ease (2 points)
            nav_score = data.get('navigation_ease', 0)
            score += min(nav_score, 2)
            if nav_score < 2:
                notes.append("Mobile navigation difficult to use")
            
            # Mobile performance (2 points)
            perf_score = data.get('mobile_performance', 0)
            score += min(perf_score, 2)
            if perf_score < 2:
                notes.append("Mobile page load speed suboptimal")
            
            if not notes:
                notes.append("Excellent mobile experience")
            
            return min(score, 10), notes
            
        except Exception as e:
            logger.error(f"Error scoring mobile UX: {str(e)}")
            return 0, ["Error analyzing mobile UX"]
    
    def _score_price_presentation(self, data: Dict[str, Any]) -> tuple[int, List[str]]:
        """Score price presentation (max 10 points)."""
        try:
            score = 0
            notes = []
            
            # Entry price clarity (3 points)
            entry_price = data.get('entry_price_clarity', 0)
            score += min(entry_price, 3)
            if entry_price < 2:
                notes.append("Entry-level pricing not clear")
            
            # Hero price anchoring (3 points)
            hero_price = data.get('hero_price_anchoring', 0)
            score += min(hero_price, 3)
            if hero_price < 2:
                notes.append("Price anchoring strategy unclear")
            
            # Promotion visibility (2 points)
            promo_score = data.get('promo_visibility', 0)
            score += min(promo_score, 2)
            if promo_score < 2:
                notes.append("Promotions not prominently displayed")
            
            # Shipping transparency (2 points)
            shipping_score = data.get('shipping_transparency', 0)
            score += min(shipping_score, 2)
            if shipping_score < 2:
                notes.append("Shipping costs not transparent")
            
            if not notes:
                notes.append("Clear and effective price presentation")
            
            return min(score, 10), notes
            
        except Exception as e:
            logger.error(f"Error scoring price presentation: {str(e)}")
            return 0, ["Error analyzing price presentation"]
    
    def analyze_competitive_position(self, scorecard: Dict[str, Any], main_brand: str) -> Dict[str, Any]:
        """Analyze competitive position and identify strengths, gaps, and priority fixes."""
        try:
            analysis = {
                'strengths': [],
                'gaps': [],
                'priority_fixes': []
            }
            
            # Find main brand scores
            main_brand_scores = {}
            competitor_scores = {}
            
            for score_item in scorecard['scores']:
                brand = score_item['brand']
                dimension = score_item['dimension']
                score = score_item['score']
                
                if brand == main_brand:
                    main_brand_scores[dimension] = score
                else:
                    if dimension not in competitor_scores:
                        competitor_scores[dimension] = []
                    competitor_scores[dimension].append(score)
            
            # Analyze each dimension
            for dimension in self.dimensions:
                main_score = main_brand_scores.get(dimension, 0)
                competitor_avg = sum(competitor_scores.get(dimension, [0])) / max(len(competitor_scores.get(dimension, [1])), 1)
                
                # Identify strengths (above average)
                if main_score > competitor_avg + 1:
                    analysis['strengths'].append(f"{dimension}: {main_score}/10 (vs {competitor_avg:.1f} avg)")
                
                # Identify gaps (below average)
                elif main_score < competitor_avg - 1:
                    gap_size = competitor_avg - main_score
                    impact = 'high' if gap_size >= 3 else 'medium' if gap_size >= 2 else 'low'
                    analysis['gaps'].append(f"{dimension}: {main_score}/10 (vs {competitor_avg:.1f} avg)")
                    
                    # Add to priority fixes
                    fix_recommendation = self._get_fix_recommendation(dimension, main_score)
                    analysis['priority_fixes'].append({
                        'fix': fix_recommendation,
                        'impact': impact,
                        'why': f"{dimension} scores {gap_size:.1f} points below competition"
                    })
            
            # Sort priority fixes by impact
            impact_order = {'high': 3, 'medium': 2, 'low': 1}
            analysis['priority_fixes'].sort(key=lambda x: impact_order.get(x['impact'], 0), reverse=True)
            
            # Limit to top 5 priority fixes
            analysis['priority_fixes'] = analysis['priority_fixes'][:5]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing competitive position: {str(e)}")
            return {
                'strengths': ["Analysis unavailable"],
                'gaps': ["Analysis unavailable"],
                'priority_fixes': []
            }
    
    def _get_fix_recommendation(self, dimension: str, current_score: int) -> str:
        """Get specific fix recommendation for a dimension."""
        fix_recommendations = {
            'Homepage': 'Redesign hero section and improve new product surfacing',
            'PDP': 'Add more product images, reviews, and detailed specifications',
            'Checkout': 'Implement express payment options and simplify checkout flow',
            'ContentCommunity': 'Integrate user-generated content and showcase collaborations',
            'MobileUX': 'Optimize mobile responsiveness and touch interactions',
            'PricePresentation': 'Clarify pricing strategy and improve promotion visibility'
        }
        
        return fix_recommendations.get(dimension, f"Improve {dimension} performance")
    
    def _get_default_scorecard(self) -> Dict[str, Any]:
        """Get default scorecard when analysis fails."""
        return {
            'dimensions': self.dimensions.copy(),
            'brands': ['Analysis unavailable'],
            'scores': [
                {
                    'dimension': dim,
                    'brand': 'Analysis unavailable',
                    'score': 0,
                    'notes': ['Data unavailable']
                }
                for dim in self.dimensions
            ]
        }


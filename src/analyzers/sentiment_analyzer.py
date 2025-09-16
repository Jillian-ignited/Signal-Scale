"""
Sentiment analysis module for analyzing customer sentiment from social media and text data.
"""
from typing import Dict, List, Any, Optional
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import structlog

logger = structlog.get_logger()

class SentimentAnalyzer:
    """Analyzes sentiment from text data using multiple approaches."""
    
    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Brand-specific positive and negative indicators
        self.positive_indicators = [
            'love', 'amazing', 'fire', 'heat', 'fresh', 'clean', 'dope',
            'sick', 'hard', 'goes hard', 'slaps', 'hits different',
            'quality', 'worth it', 'recommend', 'cop', 'must have',
            'grail', 'iconic', 'classic', 'timeless', 'perfect'
        ]
        
        self.negative_indicators = [
            'trash', 'wack', 'mid', 'overpriced', 'cheap', 'poor quality',
            'disappointed', 'waste', 'regret', 'fake', 'knockoff',
            'overrated', 'not worth', 'skip', 'pass', 'terrible'
        ]
        
        # Streetwear-specific context modifiers
        self.context_modifiers = {
            'fit': 0.1,      # "fit is fire" vs "fit is trash"
            'drop': 0.15,    # "drop was amazing" vs "drop was mid"
            'collab': 0.2,   # "collab is heat" vs "collab is wack"
            'quality': 0.25, # "quality is good" vs "quality is poor"
            'price': 0.2,    # "price is fair" vs "price is crazy"
            'style': 0.15    # "style is fresh" vs "style is outdated"
        }
    
    def analyze_sentiment(self, text_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Analyze sentiment from a collection of text data."""
        try:
            if not text_data:
                return {
                    'positive': 'No data available for sentiment analysis',
                    'negative': 'No data available for sentiment analysis',
                    'neutral': 'No data available for sentiment analysis'
                }
            
            # Analyze each text item
            sentiment_results = []
            for item in text_data:
                text = item.get('text', '') or item.get('content', '')
                if text:
                    sentiment = self._analyze_text_sentiment(text)
                    sentiment_results.append({
                        'text': text,
                        'sentiment': sentiment,
                        'platform': item.get('platform', 'unknown'),
                        'timestamp': item.get('timestamp', ''),
                        'author': item.get('author', 'unknown')
                    })
            
            # Aggregate sentiment insights
            return self._aggregate_sentiment_insights(sentiment_results)
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                'positive': 'Sentiment analysis unavailable',
                'negative': 'Sentiment analysis unavailable',
                'neutral': 'Sentiment analysis unavailable'
            }
    
    def _analyze_text_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of a single text using multiple methods."""
        try:
            text_lower = text.lower()
            
            # VADER sentiment analysis
            vader_scores = self.vader_analyzer.polarity_scores(text)
            
            # TextBlob sentiment analysis
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity
            textblob_subjectivity = blob.sentiment.subjectivity
            
            # Custom streetwear-specific analysis
            custom_sentiment = self._analyze_streetwear_sentiment(text_lower)
            
            # Combine scores with weights
            combined_score = (
                vader_scores['compound'] * 0.4 +
                textblob_polarity * 0.3 +
                custom_sentiment * 0.3
            )
            
            # Determine overall sentiment
            if combined_score >= 0.1:
                overall_sentiment = 'positive'
            elif combined_score <= -0.1:
                overall_sentiment = 'negative'
            else:
                overall_sentiment = 'neutral'
            
            return {
                'overall_sentiment': overall_sentiment,
                'combined_score': combined_score,
                'vader_compound': vader_scores['compound'],
                'textblob_polarity': textblob_polarity,
                'custom_score': custom_sentiment,
                'confidence': abs(combined_score),
                'subjectivity': textblob_subjectivity
            }
            
        except Exception as e:
            logger.error(f"Error analyzing text sentiment: {str(e)}")
            return {
                'overall_sentiment': 'neutral',
                'combined_score': 0.0,
                'confidence': 0.0
            }
    
    def _analyze_streetwear_sentiment(self, text: str) -> float:
        """Analyze sentiment using streetwear-specific indicators."""
        try:
            sentiment_score = 0.0
            
            # Check for positive indicators
            for indicator in self.positive_indicators:
                if indicator in text:
                    # Apply context modifier if relevant
                    modifier = 1.0
                    for context, mod_value in self.context_modifiers.items():
                        if context in text:
                            modifier += mod_value
                    
                    sentiment_score += 0.3 * modifier
            
            # Check for negative indicators
            for indicator in self.negative_indicators:
                if indicator in text:
                    # Apply context modifier if relevant
                    modifier = 1.0
                    for context, mod_value in self.context_modifiers.items():
                        if context in text:
                            modifier += mod_value
                    
                    sentiment_score -= 0.3 * modifier
            
            # Normalize score to [-1, 1] range
            return max(-1.0, min(1.0, sentiment_score))
            
        except Exception as e:
            logger.error(f"Error in streetwear sentiment analysis: {str(e)}")
            return 0.0
    
    def _aggregate_sentiment_insights(self, sentiment_results: List[Dict[str, Any]]) -> Dict[str, str]:
        """Aggregate sentiment results into insights."""
        try:
            if not sentiment_results:
                return {
                    'positive': 'No sentiment data available',
                    'negative': 'No sentiment data available',
                    'neutral': 'No sentiment data available'
                }
            
            # Categorize sentiments
            positive_items = [item for item in sentiment_results if item['sentiment']['overall_sentiment'] == 'positive']
            negative_items = [item for item in sentiment_results if item['sentiment']['overall_sentiment'] == 'negative']
            neutral_items = [item for item in sentiment_results if item['sentiment']['overall_sentiment'] == 'neutral']
            
            # Generate insights
            positive_insight = self._generate_positive_insight(positive_items)
            negative_insight = self._generate_negative_insight(negative_items)
            neutral_insight = self._generate_neutral_insight(neutral_items, len(sentiment_results))
            
            return {
                'positive': positive_insight,
                'negative': negative_insight,
                'neutral': neutral_insight
            }
            
        except Exception as e:
            logger.error(f"Error aggregating sentiment insights: {str(e)}")
            return {
                'positive': 'Error generating positive sentiment insight',
                'negative': 'Error generating negative sentiment insight',
                'neutral': 'Error generating neutral sentiment insight'
            }
    
    def _generate_positive_insight(self, positive_items: List[Dict[str, Any]]) -> str:
        """Generate insight from positive sentiment items."""
        try:
            if not positive_items:
                return "Limited positive sentiment detected in recent mentions"
            
            count = len(positive_items)
            
            # Find common positive themes
            positive_themes = []
            all_positive_text = ' '.join([item['text'].lower() for item in positive_items])
            
            for indicator in self.positive_indicators:
                if indicator in all_positive_text:
                    positive_themes.append(indicator)
            
            # Find most active platforms for positive sentiment
            platform_counts = {}
            for item in positive_items:
                platform = item.get('platform', 'unknown')
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
            
            top_platform = max(platform_counts.items(), key=lambda x: x[1])[0] if platform_counts else 'social media'
            
            # Generate insight
            if positive_themes:
                themes_str = ', '.join(positive_themes[:3])
                return f"{count} positive mentions highlighting {themes_str}, primarily on {top_platform}"
            else:
                return f"{count} positive mentions detected across platforms, with strongest sentiment on {top_platform}"
                
        except Exception as e:
            logger.error(f"Error generating positive insight: {str(e)}")
            return "Positive sentiment analysis unavailable"
    
    def _generate_negative_insight(self, negative_items: List[Dict[str, Any]]) -> str:
        """Generate insight from negative sentiment items."""
        try:
            if not negative_items:
                return "Minimal negative sentiment in recent brand mentions"
            
            count = len(negative_items)
            
            # Find common negative themes
            negative_themes = []
            all_negative_text = ' '.join([item['text'].lower() for item in negative_items])
            
            for indicator in self.negative_indicators:
                if indicator in all_negative_text:
                    negative_themes.append(indicator)
            
            # Check for specific concern areas
            concern_areas = []
            if 'price' in all_negative_text or 'expensive' in all_negative_text:
                concern_areas.append('pricing')
            if 'quality' in all_negative_text:
                concern_areas.append('quality')
            if 'shipping' in all_negative_text or 'delivery' in all_negative_text:
                concern_areas.append('shipping')
            if 'size' in all_negative_text or 'fit' in all_negative_text:
                concern_areas.append('sizing')
            
            # Generate insight
            if concern_areas:
                concerns_str = ', '.join(concern_areas[:2])
                return f"{count} negative mentions focusing on {concerns_str} concerns"
            elif negative_themes:
                themes_str = ', '.join(negative_themes[:2])
                return f"{count} negative mentions with themes around {themes_str}"
            else:
                return f"{count} negative mentions detected, requiring further analysis"
                
        except Exception as e:
            logger.error(f"Error generating negative insight: {str(e)}")
            return "Negative sentiment analysis unavailable"
    
    def _generate_neutral_insight(self, neutral_items: List[Dict[str, Any]], total_items: int) -> str:
        """Generate insight from neutral sentiment items."""
        try:
            neutral_count = len(neutral_items)
            neutral_percentage = (neutral_count / total_items * 100) if total_items > 0 else 0
            
            if neutral_percentage > 60:
                return f"{neutral_count} neutral mentions ({neutral_percentage:.0f}%) suggest informational or factual discussions"
            elif neutral_percentage > 30:
                return f"{neutral_count} neutral mentions ({neutral_percentage:.0f}%) indicate balanced brand perception"
            else:
                return f"{neutral_count} neutral mentions with most sentiment being either positive or negative"
                
        except Exception as e:
            logger.error(f"Error generating neutral insight: {str(e)}")
            return "Neutral sentiment analysis unavailable"
    
    def analyze_sentiment_trends(self, sentiment_results: List[Dict[str, Any]], window_days: int = 7) -> Dict[str, Any]:
        """Analyze sentiment trends over time."""
        try:
            # This would typically analyze sentiment changes over time
            # For now, provide a simplified trend analysis
            
            total_items = len(sentiment_results)
            if total_items == 0:
                return {'trend': 'insufficient_data', 'direction': 'stable'}
            
            positive_count = sum(1 for item in sentiment_results if item['sentiment']['overall_sentiment'] == 'positive')
            negative_count = sum(1 for item in sentiment_results if item['sentiment']['overall_sentiment'] == 'negative')
            
            positive_ratio = positive_count / total_items
            negative_ratio = negative_count / total_items
            
            if positive_ratio > 0.6:
                trend = 'positive'
                direction = 'improving'
            elif negative_ratio > 0.4:
                trend = 'negative'
                direction = 'declining'
            else:
                trend = 'mixed'
                direction = 'stable'
            
            return {
                'trend': trend,
                'direction': direction,
                'positive_ratio': positive_ratio,
                'negative_ratio': negative_ratio,
                'sample_size': total_items
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment trends: {str(e)}")
            return {'trend': 'unknown', 'direction': 'stable'}


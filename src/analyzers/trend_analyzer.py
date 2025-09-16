"""
Trend analysis module for detecting streetwear trends and cultural movements.
"""
import re
from collections import Counter
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()

class TrendAnalyzer:
    """Analyzes trends in streetwear and fashion from social media and cultural data."""
    
    def __init__(self):
        # Core streetwear trend categories
        self.trend_categories = {
            'aesthetics': [
                'y2k', 'grunge', 'minimalist', 'maximalist', 'vintage',
                'retro', 'futuristic', 'cyberpunk', 'cottagecore', 'dark academia'
            ],
            'styles': [
                'oversized', 'cropped', 'baggy', 'fitted', 'layered',
                'deconstructed', 'reconstructed', 'patchwork', 'distressed'
            ],
            'items': [
                'cargo pants', 'wide leg', 'mom jeans', 'platform shoes',
                'chunky sneakers', 'bucket hat', 'beanie', 'tote bag',
                'crossbody', 'fanny pack', 'hoodie', 'crewneck'
            ],
            'colors': [
                'neon', 'pastel', 'earth tones', 'monochrome', 'tie dye',
                'gradient', 'holographic', 'metallic', 'matte black'
            ],
            'collaborations': [
                'collab', 'collaboration', 'x ', ' x ', 'limited edition',
                'exclusive', 'capsule', 'collection', 'drop'
            ]
        }
        
        # Trend momentum indicators
        self.momentum_keywords = {
            'rising': [
                'trending', 'viral', 'blowing up', 'taking off', 'hot right now',
                'everyone wearing', 'new wave', 'emerging', 'up and coming'
            ],
            'stable': [
                'classic', 'timeless', 'staple', 'essential', 'always',
                'consistent', 'reliable', 'go-to', 'standard'
            ],
            'declining': [
                'over', 'done', 'played out', 'outdated', 'last season',
                'not cool anymore', 'dead trend', 'moving on from'
            ]
        }
        
        # Platform-specific trend indicators
        self.platform_indicators = {
            'tiktok': ['fyp', 'foryou', 'viral', 'trend', 'challenge'],
            'instagram': ['ootd', 'outfit', 'style', 'look', 'fit'],
            'youtube': ['haul', 'review', 'styling', 'lookbook', 'try on'],
            'reddit': ['discussion', 'thoughts', 'opinion', 'review', 'cop or drop']
        }
    
    def analyze_trends(self, social_data: List[Dict[str, Any]], window_days: int = 7) -> List[Dict[str, Any]]:
        """Analyze trends from social media data."""
        try:
            if not social_data:
                return []
            
            # Extract and analyze hashtags
            hashtag_trends = self._analyze_hashtag_trends(social_data)
            
            # Analyze content themes
            content_trends = self._analyze_content_trends(social_data)
            
            # Detect emerging trends
            emerging_trends = self._detect_emerging_trends(social_data, window_days)
            
            # Combine and rank trends
            all_trends = hashtag_trends + content_trends + emerging_trends
            
            # Remove duplicates and rank by evidence strength
            unique_trends = self._deduplicate_and_rank_trends(all_trends)
            
            return unique_trends[:10]  # Return top 10 trends
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return []
    
    def _analyze_hashtag_trends(self, social_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze trending hashtags."""
        try:
            all_hashtags = []
            
            # Extract hashtags from all posts
            for item in social_data:
                hashtags = item.get('hashtags', [])
                if isinstance(hashtags, list):
                    all_hashtags.extend([tag.lower() for tag in hashtags])
                elif isinstance(hashtags, str):
                    # Extract hashtags from text
                    extracted_tags = re.findall(r'#\w+', hashtags.lower())
                    all_hashtags.extend(extracted_tags)
            
            # Count hashtag frequency
            hashtag_counts = Counter(all_hashtags)
            
            # Convert to trend format
            hashtag_trends = []
            for hashtag, count in hashtag_counts.most_common(20):
                if count >= 2:  # Minimum threshold
                    trend = {
                        'theme': f"Hashtag trend: {hashtag}",
                        'evidence': f"Used in {count} posts across platforms",
                        'hashtags': [hashtag],
                        'momentum': self._determine_hashtag_momentum(hashtag, social_data),
                        'category': 'hashtag',
                        'strength': count
                    }
                    hashtag_trends.append(trend)
            
            return hashtag_trends
            
        except Exception as e:
            logger.error(f"Error analyzing hashtag trends: {str(e)}")
            return []
    
    def _analyze_content_trends(self, social_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze content-based trends."""
        try:
            content_trends = []
            
            # Combine all text content
            all_text = ' '.join([
                item.get('text', '') + ' ' + item.get('content', '')
                for item in social_data
            ]).lower()
            
            # Analyze each trend category
            for category, keywords in self.trend_categories.items():
                category_trends = self._find_category_trends(all_text, category, keywords, social_data)
                content_trends.extend(category_trends)
            
            return content_trends
            
        except Exception as e:
            logger.error(f"Error analyzing content trends: {str(e)}")
            return []
    
    def _find_category_trends(self, all_text: str, category: str, keywords: List[str], social_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find trends within a specific category."""
        try:
            category_trends = []
            
            for keyword in keywords:
                # Count occurrences
                count = all_text.count(keyword.lower())
                
                if count >= 2:  # Minimum threshold
                    # Find related hashtags
                    related_hashtags = self._find_related_hashtags(keyword, social_data)
                    
                    # Determine momentum
                    momentum = self._determine_content_momentum(keyword, all_text)
                    
                    trend = {
                        'theme': f"{category.title()}: {keyword}",
                        'evidence': f"Mentioned {count} times in recent posts",
                        'hashtags': related_hashtags,
                        'momentum': momentum,
                        'category': category,
                        'strength': count
                    }
                    category_trends.append(trend)
            
            return category_trends
            
        except Exception as e:
            logger.error(f"Error finding category trends: {str(e)}")
            return []
    
    def _detect_emerging_trends(self, social_data: List[Dict[str, Any]], window_days: int) -> List[Dict[str, Any]]:
        """Detect emerging trends using pattern analysis."""
        try:
            emerging_trends = []
            
            # Look for sudden spikes in specific terms
            recent_text = []
            older_text = []
            
            cutoff_date = datetime.now() - timedelta(days=window_days // 2)
            
            for item in social_data:
                timestamp_str = item.get('timestamp', '')
                try:
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        text = item.get('text', '') + ' ' + item.get('content', '')
                        
                        if timestamp > cutoff_date:
                            recent_text.append(text.lower())
                        else:
                            older_text.append(text.lower())
                except:
                    # If timestamp parsing fails, add to recent
                    recent_text.append((item.get('text', '') + ' ' + item.get('content', '')).lower())
            
            # Find terms that appear more frequently in recent vs older content
            recent_combined = ' '.join(recent_text)
            older_combined = ' '.join(older_text)
            
            # Extract potential trend terms (2-3 word phrases)
            recent_phrases = self._extract_phrases(recent_combined)
            older_phrases = self._extract_phrases(older_combined)
            
            # Compare frequencies
            for phrase, recent_count in recent_phrases.items():
                older_count = older_phrases.get(phrase, 0)
                
                # Look for significant increases
                if recent_count >= 2 and (older_count == 0 or recent_count > older_count * 2):
                    emerging_trends.append({
                        'theme': f"Emerging: {phrase}",
                        'evidence': f"Increased from {older_count} to {recent_count} mentions",
                        'hashtags': [f"#{phrase.replace(' ', '')}"],
                        'momentum': 'rising',
                        'category': 'emerging',
                        'strength': recent_count - older_count
                    })
            
            return emerging_trends[:5]  # Limit to top 5 emerging trends
            
        except Exception as e:
            logger.error(f"Error detecting emerging trends: {str(e)}")
            return []
    
    def _extract_phrases(self, text: str) -> Dict[str, int]:
        """Extract 2-3 word phrases from text."""
        try:
            # Clean text and split into words
            words = re.findall(r'\b\w+\b', text.lower())
            
            phrases = {}
            
            # Extract 2-word phrases
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                if len(phrase) > 6:  # Minimum phrase length
                    phrases[phrase] = phrases.get(phrase, 0) + 1
            
            # Extract 3-word phrases
            for i in range(len(words) - 2):
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                if len(phrase) > 10:  # Minimum phrase length
                    phrases[phrase] = phrases.get(phrase, 0) + 1
            
            # Filter out common phrases
            filtered_phrases = {
                phrase: count for phrase, count in phrases.items()
                if count >= 2 and not self._is_common_phrase(phrase)
            }
            
            return filtered_phrases
            
        except Exception as e:
            logger.error(f"Error extracting phrases: {str(e)}")
            return {}
    
    def _is_common_phrase(self, phrase: str) -> bool:
        """Check if phrase is too common to be a trend."""
        common_phrases = [
            'in the', 'on the', 'for the', 'with the', 'to the',
            'and the', 'of the', 'at the', 'from the', 'by the',
            'this is', 'that is', 'it is', 'i am', 'you are',
            'we are', 'they are', 'i have', 'you have', 'we have'
        ]
        return phrase in common_phrases
    
    def _determine_hashtag_momentum(self, hashtag: str, social_data: List[Dict[str, Any]]) -> str:
        """Determine momentum for a hashtag trend."""
        try:
            # Simple momentum detection based on context
            contexts = []
            for item in social_data:
                text = item.get('text', '').lower()
                if hashtag in text:
                    contexts.append(text)
            
            combined_context = ' '.join(contexts)
            
            # Check for momentum indicators
            rising_score = sum(1 for keyword in self.momentum_keywords['rising'] if keyword in combined_context)
            declining_score = sum(1 for keyword in self.momentum_keywords['declining'] if keyword in combined_context)
            
            if rising_score > declining_score:
                return 'rising'
            elif declining_score > rising_score:
                return 'declining'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Error determining hashtag momentum: {str(e)}")
            return 'stable'
    
    def _determine_content_momentum(self, keyword: str, all_text: str) -> str:
        """Determine momentum for content-based trends."""
        try:
            # Find sentences containing the keyword
            sentences = re.split(r'[.!?]', all_text)
            keyword_sentences = [s for s in sentences if keyword in s]
            
            if not keyword_sentences:
                return 'stable'
            
            combined_context = ' '.join(keyword_sentences)
            
            # Check for momentum indicators
            rising_score = sum(1 for keyword in self.momentum_keywords['rising'] if keyword in combined_context)
            declining_score = sum(1 for keyword in self.momentum_keywords['declining'] if keyword in combined_context)
            
            if rising_score > declining_score:
                return 'rising'
            elif declining_score > rising_score:
                return 'declining'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Error determining content momentum: {str(e)}")
            return 'stable'
    
    def _find_related_hashtags(self, keyword: str, social_data: List[Dict[str, Any]]) -> List[str]:
        """Find hashtags related to a keyword."""
        try:
            related_hashtags = []
            
            for item in social_data:
                text = item.get('text', '').lower()
                if keyword in text:
                    hashtags = item.get('hashtags', [])
                    if isinstance(hashtags, list):
                        related_hashtags.extend(hashtags)
                    elif isinstance(hashtags, str):
                        extracted_tags = re.findall(r'#\w+', hashtags)
                        related_hashtags.extend(extracted_tags)
            
            # Return most common related hashtags
            hashtag_counts = Counter(related_hashtags)
            return [tag for tag, count in hashtag_counts.most_common(5)]
            
        except Exception as e:
            logger.error(f"Error finding related hashtags: {str(e)}")
            return []
    
    def _deduplicate_and_rank_trends(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate trends and rank by strength."""
        try:
            # Group similar trends
            unique_trends = {}
            
            for trend in trends:
                theme = trend['theme'].lower()
                
                # Check if this is similar to an existing trend
                found_similar = False
                for existing_theme in unique_trends.keys():
                    if self._are_similar_trends(theme, existing_theme):
                        # Merge with existing trend if this one is stronger
                        if trend['strength'] > unique_trends[existing_theme]['strength']:
                            unique_trends[existing_theme] = trend
                        found_similar = True
                        break
                
                if not found_similar:
                    unique_trends[theme] = trend
            
            # Sort by strength and return
            sorted_trends = sorted(
                unique_trends.values(),
                key=lambda x: x['strength'],
                reverse=True
            )
            
            return sorted_trends
            
        except Exception as e:
            logger.error(f"Error deduplicating trends: {str(e)}")
            return trends
    
    def _are_similar_trends(self, theme1: str, theme2: str) -> bool:
        """Check if two trend themes are similar."""
        try:
            # Simple similarity check based on common words
            words1 = set(theme1.split())
            words2 = set(theme2.split())
            
            # Calculate Jaccard similarity
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            similarity = intersection / union if union > 0 else 0
            
            return similarity > 0.5
            
        except Exception as e:
            logger.error(f"Error checking trend similarity: {str(e)}")
            return False


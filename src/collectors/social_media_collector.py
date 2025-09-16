"""
Social media data collector for Instagram, TikTok, Twitter, Reddit, and YouTube.
"""
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .base_collector import BaseCollector
import structlog

logger = structlog.get_logger()

class SocialMediaCollector(BaseCollector):
    """Collector for social media platforms."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.platforms = {
            'instagram': 'instagram.com',
            'tiktok': 'tiktok.com',
            'twitter': 'twitter.com',
            'reddit': 'reddit.com',
            'youtube': 'youtube.com',
            'facebook': 'facebook.com'
        }
    
    async def collect_data(self, query: str, window_days: int = 7, platforms: Optional[List[str]] = None, **kwargs) -> List[Dict[str, Any]]:
        """Collect social media data for a given query."""
        if platforms is None:
            platforms = list(self.platforms.keys())
        
        all_data = []
        
        # Create search queries for each platform
        search_tasks = []
        for platform in platforms:
            if platform in self.platforms:
                search_tasks.append(
                    self._search_platform(platform, query, window_days)
                )
        
        # Execute searches in parallel
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Combine results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error collecting from {platforms[i]}: {str(result)}")
                all_data.append(self.handle_unavailable_source(platforms[i]))
            else:
                all_data.extend(result)
        
        return self.normalize_data(all_data)
    
    async def _search_platform(self, platform: str, query: str, window_days: int) -> List[Dict]:
        """Search a specific platform for mentions."""
        try:
            # Construct platform-specific search query
            site_query = f'site:{self.platforms[platform]} "{query}"'
            
            # Add date filter for recent content
            end_date = datetime.now()
            start_date = end_date - timedelta(days=window_days)
            
            # Use web search API (placeholder - would integrate with actual search APIs)
            search_url = "https://api.example-search.com/search"
            params = {
                'q': site_query,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'limit': 50
            }
            
            response = await self.make_request(search_url, params=params)
            
            if response and 'results' in response:
                return response['results']
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error searching {platform}: {str(e)}")
            return []
    
    async def collect_creator_data(self, price_band: str, max_followers: int, min_engagement_rate: float, **kwargs) -> List[Dict[str, Any]]:
        """Collect data about emerging creators for cultural radar."""
        creators = []
        
        # Search for creators in the specified price band
        search_queries = [
            f'streetwear {price_band} outfit',
            f'fashion {price_band} style',
            f'street style {price_band}',
            f'urban fashion {price_band}'
        ]
        
        for query in search_queries:
            platform_data = await self.collect_data(query, platforms=['instagram', 'tiktok', 'youtube'])
            
            # Extract creator information from posts
            for item in platform_data:
                creator_info = self._extract_creator_info(item, max_followers, min_engagement_rate)
                if creator_info:
                    creators.append(creator_info)
        
        return self._deduplicate_creators(creators)
    
    def _extract_creator_info(self, post_data: Dict, max_followers: int, min_engagement_rate: float) -> Optional[Dict]:
        """Extract creator information from a social media post."""
        try:
            # Extract basic creator info (placeholder logic)
            creator_name = post_data.get('author', 'Unknown')
            platform = self._detect_platform(post_data.get('url', ''))
            followers = post_data.get('author_followers', 0)
            
            # Skip if too many followers
            if followers > max_followers:
                return None
            
            # Calculate engagement rate
            likes = post_data.get('likes', 0)
            comments = post_data.get('comments', 0)
            shares = post_data.get('shares', 0)
            
            total_engagement = likes + comments + shares
            engagement_rate = total_engagement / max(followers, 1) if followers > 0 else 0
            
            # Skip if engagement rate too low
            if engagement_rate < min_engagement_rate:
                return None
            
            return {
                'creator': creator_name,
                'platform': platform,
                'profile': post_data.get('author_profile', ''),
                'followers': followers,
                'engagement_rate': round(engagement_rate, 4),
                'content_focus': self._analyze_content_focus(post_data.get('text', '')),
                'post_url': post_data.get('url', ''),
                'timestamp': post_data.get('timestamp', datetime.now().isoformat())
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract creator info: {str(e)}")
            return None
    
    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL."""
        for platform, domain in self.platforms.items():
            if domain in url:
                return platform
        return 'unknown'
    
    def _analyze_content_focus(self, text: str) -> str:
        """Analyze the content focus based on text."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['streetwear', 'urban', 'street style']):
            return 'streetwear'
        elif any(word in text_lower for word in ['fashion', 'style', 'outfit']):
            return 'fashion'
        elif any(word in text_lower for word in ['music', 'hip hop', 'rap']):
            return 'music'
        else:
            return 'lifestyle'
    
    def _deduplicate_creators(self, creators: List[Dict]) -> List[Dict]:
        """Remove duplicate creators based on name and platform."""
        seen = set()
        unique_creators = []
        
        for creator in creators:
            key = (creator['creator'], creator['platform'])
            if key not in seen:
                seen.add(key)
                unique_creators.append(creator)
        
        return unique_creators
    
    def _normalize_item(self, item: Dict) -> Optional[Dict[str, Any]]:
        """Normalize a social media item to standard format."""
        try:
            return {
                'id': item.get('id', ''),
                'platform': self._detect_platform(item.get('url', '')),
                'author': item.get('author', ''),
                'text': item.get('text', ''),
                'url': item.get('url', ''),
                'timestamp': item.get('timestamp', ''),
                'likes': item.get('likes', 0),
                'comments': item.get('comments', 0),
                'shares': item.get('shares', 0),
                'hashtags': self._extract_hashtags(item.get('text', '')),
                'mentions': self._extract_mentions(item.get('text', ''))
            }
        except Exception as e:
            logger.warning(f"Failed to normalize social media item: {str(e)}")
            return None
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        return re.findall(r'#\w+', text)
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text."""
        return re.findall(r'@\w+', text)


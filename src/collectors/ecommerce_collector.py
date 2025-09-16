"""
Ecommerce data collector for Amazon, eBay, StockX, Grailed, Depop, Farfetch, SSENSE.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .base_collector import BaseCollector
import structlog

logger = structlog.get_logger()

class EcommerceCollector(BaseCollector):
    """Collector for ecommerce platforms."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.platforms = {
            'amazon': 'amazon.com',
            'ebay': 'ebay.com',
            'stockx': 'stockx.com',
            'grailed': 'grailed.com',
            'depop': 'depop.com',
            'farfetch': 'farfetch.com',
            'ssense': 'ssense.com'
        }
    
    async def collect_data(self, brand_name: str, competitors: List[str], window_days: int = 7, **kwargs) -> List[Dict[str, Any]]:
        """Collect ecommerce data for brand and competitors."""
        all_data = []
        
        # Collect data for the main brand
        brand_data = await self._collect_brand_data(brand_name, window_days)
        all_data.extend(brand_data)
        
        # Collect data for competitors
        competitor_tasks = []
        for competitor in competitors:
            competitor_tasks.append(
                self._collect_brand_data(competitor, window_days)
            )
        
        competitor_results = await asyncio.gather(*competitor_tasks, return_exceptions=True)
        
        for i, result in enumerate(competitor_results):
            if isinstance(result, Exception):
                logger.error(f"Error collecting competitor data for {competitors[i]}: {str(result)}")
                all_data.append(self.handle_unavailable_source(f"competitor_{competitors[i]}"))
            else:
                all_data.extend(result)
        
        return self.normalize_data(all_data)
    
    async def _collect_brand_data(self, brand_name: str, window_days: int) -> List[Dict]:
        """Collect data for a specific brand across all ecommerce platforms."""
        brand_data = []
        
        # Search each platform for the brand
        platform_tasks = []
        for platform, domain in self.platforms.items():
            platform_tasks.append(
                self._search_platform(platform, brand_name, window_days)
            )
        
        platform_results = await asyncio.gather(*platform_tasks, return_exceptions=True)
        
        for i, result in enumerate(list(self.platforms.keys())):
            platform_result = platform_results[i]
            if isinstance(platform_result, Exception):
                logger.error(f"Error collecting from {result}: {str(platform_result)}")
                brand_data.append(self.handle_unavailable_source(result))
            else:
                brand_data.extend(platform_result)
        
        return brand_data
    
    async def _search_platform(self, platform: str, brand_name: str, window_days: int) -> List[Dict]:
        """Search a specific ecommerce platform for brand mentions."""
        try:
            # Construct platform-specific search query
            site_query = f'site:{self.platforms[platform]} "{brand_name}"'
            
            # Use web search API (placeholder - would integrate with actual APIs)
            search_url = "https://api.example-search.com/search"
            params = {
                'q': site_query,
                'limit': 20,
                'type': 'product'
            }
            
            response = await self.make_request(search_url, params=params)
            
            if response and 'results' in response:
                # Add platform context to each result
                for result in response['results']:
                    result['platform'] = platform
                    result['brand_searched'] = brand_name
                return response['results']
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error searching {platform} for {brand_name}: {str(e)}")
            return []
    
    async def collect_pricing_data(self, brand_name: str, price_band: str) -> List[Dict[str, Any]]:
        """Collect pricing data for products in the specified price band."""
        pricing_data = []
        
        # Extract price range from price_band string (e.g., "$40–$150")
        price_range = self._parse_price_band(price_band)
        
        # Search for products in the price range
        for platform, domain in self.platforms.items():
            try:
                platform_pricing = await self._collect_platform_pricing(platform, brand_name, price_range)
                pricing_data.extend(platform_pricing)
            except Exception as e:
                logger.error(f"Error collecting pricing from {platform}: {str(e)}")
                continue
        
        return self.normalize_data(pricing_data)
    
    def _parse_price_band(self, price_band: str) -> Dict[str, float]:
        """Parse price band string to extract min and max prices."""
        try:
            # Remove currency symbols and split on dash/hyphen
            clean_band = price_band.replace('$', '').replace(',', '')
            if '–' in clean_band:
                parts = clean_band.split('–')
            elif '-' in clean_band:
                parts = clean_band.split('-')
            else:
                # Single price or invalid format
                return {'min': 0, 'max': 1000}
            
            min_price = float(parts[0].strip())
            max_price = float(parts[1].strip())
            
            return {'min': min_price, 'max': max_price}
        except Exception as e:
            logger.warning(f"Failed to parse price band '{price_band}': {str(e)}")
            return {'min': 0, 'max': 1000}
    
    async def _collect_platform_pricing(self, platform: str, brand_name: str, price_range: Dict[str, float]) -> List[Dict]:
        """Collect pricing data from a specific platform."""
        try:
            # Construct search query with price filters
            query = f'site:{self.platforms[platform]} "{brand_name}" price:{price_range["min"]}..{price_range["max"]}'
            
            search_url = "https://api.example-search.com/search"
            params = {
                'q': query,
                'limit': 15,
                'type': 'product'
            }
            
            response = await self.make_request(search_url, params=params)
            
            if response and 'results' in response:
                # Add platform and pricing context
                for result in response['results']:
                    result['platform'] = platform
                    result['brand_searched'] = brand_name
                    result['price_range'] = price_range
                return response['results']
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error collecting pricing from {platform}: {str(e)}")
            return []
    
    def _normalize_item(self, item: Dict) -> Optional[Dict[str, Any]]:
        """Normalize an ecommerce item to standard format."""
        try:
            return {
                'id': item.get('id', ''),
                'platform': item.get('platform', ''),
                'title': item.get('title', ''),
                'brand': item.get('brand', ''),
                'price': self._extract_price(item.get('price', '')),
                'currency': item.get('currency', 'USD'),
                'url': item.get('url', ''),
                'image_url': item.get('image_url', ''),
                'description': item.get('description', ''),
                'availability': item.get('availability', 'unknown'),
                'rating': item.get('rating', 0),
                'review_count': item.get('review_count', 0),
                'seller': item.get('seller', ''),
                'timestamp': item.get('timestamp', datetime.now().isoformat()),
                'category': item.get('category', ''),
                'tags': item.get('tags', [])
            }
        except Exception as e:
            logger.warning(f"Failed to normalize ecommerce item: {str(e)}")
            return None
    
    def _extract_price(self, price_str: str) -> float:
        """Extract numeric price from price string."""
        try:
            # Remove currency symbols and commas
            clean_price = price_str.replace('$', '').replace(',', '').replace('€', '').replace('£', '')
            
            # Extract first number found
            import re
            numbers = re.findall(r'\d+\.?\d*', clean_price)
            if numbers:
                return float(numbers[0])
            else:
                return 0.0
        except Exception:
            return 0.0
    
    async def analyze_competitive_pricing(self, brand_name: str, competitors: List[str], price_band: str) -> Dict[str, Any]:
        """Analyze competitive pricing across platforms."""
        try:
            # Collect pricing data for brand and competitors
            all_brands = [brand_name] + competitors
            pricing_tasks = []
            
            for brand in all_brands:
                pricing_tasks.append(
                    self.collect_pricing_data(brand, price_band)
                )
            
            pricing_results = await asyncio.gather(*pricing_tasks, return_exceptions=True)
            
            # Analyze pricing patterns
            analysis = {
                'brand_pricing': {},
                'competitor_pricing': {},
                'price_insights': [],
                'opportunities': []
            }
            
            for i, result in enumerate(pricing_results):
                brand = all_brands[i]
                if not isinstance(result, Exception) and result:
                    avg_price = sum(item['price'] for item in result if item['price'] > 0) / len(result)
                    price_range = {
                        'min': min(item['price'] for item in result if item['price'] > 0),
                        'max': max(item['price'] for item in result if item['price'] > 0)
                    }
                    
                    pricing_info = {
                        'average_price': round(avg_price, 2),
                        'price_range': price_range,
                        'product_count': len(result),
                        'platforms': list(set(item['platform'] for item in result))
                    }
                    
                    if brand == brand_name:
                        analysis['brand_pricing'] = pricing_info
                    else:
                        analysis['competitor_pricing'][brand] = pricing_info
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing competitive pricing: {str(e)}")
            return self.handle_unavailable_source("competitive_pricing")


import httpx
from selectolax.parser import HTMLParser

async def scrape_site(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Signal & Scale Bot/1.0"
            })
            response.raise_for_status()
            
            html = HTMLParser(response.text)
            return {
                "url": url,
                "title": html.css_first("title").text(strip=True) if html.css_first("title") else "",
                "h1": html.css_first("h1").text(strip=True) if html.css_first("h1") else "",
                "status_code": response.status_code,
                "scraped_successfully": True
            }
    except Exception as e:
        return {"url": url, "error": str(e), "scraped_successfully": False}

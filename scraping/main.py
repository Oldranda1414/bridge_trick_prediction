import requests
from bs4 import BeautifulSoup
import re

def get_vugraph_download_links(search_string="2023-03"):
    """
    Scrape download links from BridgeBase vugraph archives
    
    Args:
        search_string (str): Search term in format YYYY-MM (e.g., "2023-03")
    
    Returns:
        list: List of download URLs
    """
    
    # Base URL
    base_url = "https://www.bridgebase.com/vugraph_archives/vugraph_archives.php"
    
    # Session to maintain cookies
    session = requests.Session()
    
    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.bridgebase.com',
        'Referer': 'https://www.bridgebase.com/vugraph_archives/vugraph_archives.php?v3b=',
    }
    
    # Form data for the POST request
    data = {
        'searchstring': search_string,
        'command': 'search'
    }
    
    try:
        # Send POST request to perform search
        response = session.post(
            base_url,
            params={'v3b': ''},  # query string parameter
            data=data,
            headers=headers,
            timeout=30
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all download buttons/links
        # Look for various patterns that might indicate download links
        download_links = []
        
        # Pattern 1: Look for buttons with "Download" text
        download_buttons = soup.find_all('button', string=re.compile(r'download', re.I))
        for button in download_buttons:
            # Check if button has onclick event with URL
            if button.get('onclick'):
                url_match = re.search(r"window\.open\('([^']+)'", button.get('onclick'))
                if url_match:
                    download_links.append(url_match.group(1))
        
        # Pattern 2: Look for links with "download" in href or text
        download_anchors = soup.find_all('a', href=True, string=re.compile(r'download', re.I))
        for anchor in download_anchors:
            href = anchor['href']
            if href.startswith(('http', '//', '/')):
                # Convert relative URLs to absolute
                if href.startswith('//'):
                    download_links.append('https:' + href)
                elif href.startswith('/'):
                    download_links.append('https://www.bridgebase.com' + href)
                else:
                    download_links.append(href)
        
        # Pattern 3: Look for any elements with download-related attributes
        potential_downloads = soup.find_all(['a', 'button'], attrs={
            'onclick': re.compile(r'download|window\.open', re.I)
        })
        for element in potential_downloads:
            onclick = element.get('onclick', '')
            url_match = re.search(r"window\.open\('([^']+)'", onclick)
            if url_match:
                download_links.append(url_match.group(1))
        
        # Remove duplicates and filter out non-download links
        unique_links = list(set(download_links))
        
        # Filter to only include likely download links (LIN, PBN files, etc.)
        filtered_links = [
            link for link in unique_links 
            if any(ext in link.lower() for ext in ['.lin', '.pbn', '.zip', '.rar', '.7z', 'download'])
        ]
        
        return filtered_links
        
    except requests.RequestException as e:
        print(f"Error making request: {e}")
        return []
    except Exception as e:
        print(f"Error parsing response: {e}")
        return []

def main():
    # Example usage
    search_term = "2023-03"  # Change this to your desired search term
    
    print(f"Searching for downloads with term: {search_term}")
    download_links = get_vugraph_download_links(search_term)
    
    if download_links:
        print(f"Found {len(download_links)} download links:")
        for i, link in enumerate(download_links, 1):
            print(f"{i}. {link}")
    else:
        print("No download links found.")
        
        # Let's try to debug by looking at the page structure
        print("\nTrying to debug by examining page structure...")
        try:
            session = requests.Session()
            response = session.post(
                "https://www.bridgebase.com/vugraph_archives/vugraph_archives.php",
                params={'v3b': ''},
                data={'searchstring': search_term, 'command': 'search'},
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            # Save the response to a file for inspection
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("Saved page content to 'debug_page.html' for inspection")
            
        except Exception as e:
            print(f"Debug failed: {e}")

if __name__ == "__main__":
    main()

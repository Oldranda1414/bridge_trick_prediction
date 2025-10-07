import requests
from bs4 import BeautifulSoup

def get_vugraph_download_links(search_string="2023-03"):
    """
    Scrape download links from BridgeBase vugraph archives
    
    Args:
        search_string (str): Search term in format YYYY-MM (e.g., "2023-03")
    
    Returns:
        list: List of download URLs and their IDs
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
        # Send POST request to perform search with longer timeout
        print("Sending search request...")
        response = session.post(
            base_url,
            params={'v3b': ''},  # query string parameter
            data=data,
            headers=headers,
            timeout=60  # Increased timeout
        )
        
        # Check if request was successful
        response.raise_for_status()
        print("Search successful! Parsing results...")
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all download links with the specific pattern
        download_links = []
        
        # Look for <a> tags with href containing "vugraph_linfetch.php?id="
        download_anchors = soup.find_all('a', href=lambda x: x and 'vugraph_linfetch.php?id=' in x)
        
        for anchor in download_anchors:
            href = anchor['href']
            # Extract the ID from the URL
            id_start = href.find('id=') + 3
            file_id = href[id_start:]
            
            # Create the full download URL
            full_url = f"https://www.bridgebase.com/tools/vugraph_linfetch.php?id={file_id}"
            
            # Get the link text for context (usually "Download" or similar)
            link_text = anchor.get_text(strip=True)
            
            download_links.append({
                'id': file_id,
                'url': full_url,
                'text': link_text,
                'href': href
            })
        
        return download_links
        
    except requests.RequestException as e:
        print(f"Error making request: {e}")
        return []
    except Exception as e:
        print(f"Error parsing response: {e}")
        return []

def save_links_to_file(links, filename="download_links.txt"):
    """Save the found links to a text file"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Found {len(links)} download links:\n\n")
        for i, link in enumerate(links, 1):
            f.write(f"{i}. ID: {link['id']}\n")
            f.write(f"   URL: {link['url']}\n")
            f.write(f"   Text: {link['text']}\n")
            f.write(f"   Href: {link['href']}\n\n")

def main():
    # Example usage
    search_term = "2023-03"  # Change this to your desired search term
    
    print(f"Searching for downloads with term: {search_term}")
    download_links = get_vugraph_download_links(search_term)
    
    if download_links:
        print(f"Found {len(download_links)} download links:")
        for i, link in enumerate(download_links, 1):
            print(f"{i}. ID: {link['id']} - {link['text']}")
            print(f"   URL: {link['url']}")
        
        # Save to file
        save_links_to_file(download_links)
        print(f"\nLinks saved to 'download_links.txt'")
        
        # Also save just the URLs for easy downloading
        with open("urls_only.txt", 'w', encoding='utf-8') as f:
            for link in download_links:
                f.write(link['url'] + '\n')
        print("URLs-only list saved to 'urls_only.txt'")
        
    else:
        print("No download links found.")
        
        # Debug: check what's on the page
        print("\nChecking page content...")
        try:
            session = requests.Session()
            response = session.post(
                "https://www.bridgebase.com/vugraph_archives/vugraph_archives.php",
                params={'v3b': ''},
                data={'searchstring': search_term, 'command': 'search'},
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                timeout=60
            )
            
            # Check if we have any links at all
            soup = BeautifulSoup(response.content, 'html.parser')
            all_links = soup.find_all('a', href=True)
            print(f"Total links on page: {len(all_links)}")
            
            # Show links that contain 'vugraph'
            vugraph_links = [a for a in all_links if 'vugraph' in a['href']]
            print(f"Links containing 'vugraph': {len(vugraph_links)}")
            for link in vugraph_links[:5]:  # Show first 5
                print(f"  - {link['href']}")
                
        except Exception as e:
            print(f"Debug failed: {e}")

if __name__ == "__main__":
    main()

import requests
from bs4 import BeautifulSoup
import time

SLEEP_TIME = 5

def get_vugraph_ids(search_string="2023-03") -> set[int]:
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
        download_links: set = set()
        
        # Look for <a> tags with href containing "vugraph_linfetch.php?id="
        download_anchors = soup.find_all('a', href=lambda x: x and 'vugraph_linfetch.php?id=' in x)
        
        for anchor in download_anchors:
            href = anchor['href']
            # Extract the ID from the URL
            id_start = href.find('id=') + 3
            file_id = href[id_start:]
            
            download_links.add(int(file_id))
        
        return download_links
        
    except requests.RequestException as e:
        print(f"Error making request: {e}")
        return set()
    except Exception as e:
        print(f"Error parsing response: {e}")
        return set()

def download_file(session, url, file_id, max_retries=3):
    """
    Download a single file with retry logic
    """
    for attempt in range(max_retries):
        try:
            # print(f"  Downloading file ID {file_id}... (attempt {attempt + 1})")
            
            response = session.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            
            # Get the content as text
            content = response.text
            
            # Check if we got actual content (not an error page)
            if len(content.strip()) > 0 and "error" not in content.lower():
                return content
            else:
                print(f"    Warning: File {file_id} appears to be empty or error")
                return None
                
        except requests.RequestException as e:
            print(f"    Error downloading {file_id}: {e}")
            if attempt < max_retries - 1:
                print(f"    Retrying in 5 seconds...")
                time.sleep(SLEEP_TIME)
            else:
                print(f"    Failed to download {file_id} after {max_retries} attempts")
                return None

def download_and_concatenate_files(search_term="2023-03", output_filename="combined_vugraph_files.txt") -> int:
    """
    Main function to get IDs, download files, and concatenate contents
    """
    print(f"Searching for downloads with term: {search_term}")
    
    # Get the file IDs
    download_ids = get_vugraph_ids(search_term)
    
    if not download_ids:
        print("No download links found.")
        return 0
    
    print(f"Found {len(download_ids)} files to download")
    
    # Create session for persistent connections
    session = requests.Session()
    
    # List to store all file contents
    all_contents = []
    successful_downloads = 0
    
    # Download each file
    for i, file_id in enumerate(download_ids, 1):
        full_url = f"https://www.bridgebase.com/tools/vugraph_linfetch.php?id={file_id}"
        
        # print(f"File {i}/{len(download_ids)}:")
        content = download_file(session, full_url, file_id)
        
        if content:
            # Add a separator with file info
            file_header = f"\n{'='*60}\n"
            file_header += f"File ID: {file_id}\n"
            file_header += f"URL: {full_url}\n"
            file_header += f"Downloaded at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            file_header += f"{'='*60}\n\n"
            
            all_contents.append(file_header + content)
            successful_downloads += 1
            # print(f"  ✓ Successfully downloaded file {file_id}")
        else:
            print(f"  ✗ Failed to download file {file_id}")
        
        # Small delay to be respectful to the server
        time.sleep(SLEEP_TIME)
    
    # Concatenate all contents
    if all_contents:
        print(f"\nConcatenating {successful_downloads} files...")
        combined_content = "\n".join(all_contents)
        
        # Save to file
        try:
            with open(output_filename, 'a', encoding='utf-8') as f:
                f.write(combined_content)
            
            print(f"✓ Successfully saved {successful_downloads} files to '{output_filename}'")
            print(f"Total file size: {len(combined_content)} characters")
            
        except Exception as e:
            print(f"Error saving file: {e}")
        return successful_downloads
    else:
        print("No files were successfully downloaded.")
        return 0

def count_lines(filename) -> int:
    with open(filename, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)

def main():
    months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    downloaded_count = 0
    output_file = "scraped_data.txt"
    for month in months:
        search_term = f"2024-{month}"
        downloaded_count += download_and_concatenate_files(search_term, output_file)
        games_count = (count_lines(output_file) - downloaded_count * 7) / 13
        print(f"circa {games_count} games found till now")
        if games_count > 50000:
            print(f"circa {games_count} games found in total")
            break
    
if __name__ == "__main__":
    main()

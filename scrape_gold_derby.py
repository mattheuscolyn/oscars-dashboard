from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import csv
import re
import time

people_categories = [
    "Best Actor",
    "Best Actress",
    "Best Supporting Actor",
    "Best Supporting Actress",
    "Best Director"
]

def scrape_gold_derby_oscars():
    """
    Scrape Oscar nomination predictions from Gold Derby using Selenium.
    """
    url = 'https://www.goldderby.com/odds/combined-odds/oscars-nominations-2026/'
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    print("Starting web driver...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    data = []
    
    try:
        print(f"Loading page: {url}")
        driver.set_page_load_timeout(30)
        driver.get(url)
        
        # Wait for page to fully load
        print("Waiting for JavaScript to load content...")
        time.sleep(5)
        
        # Check if content loaded
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if not body_text or len(body_text) < 500:
            print("Page seems empty, waiting more...")
            time.sleep(5)
        
        # Find all contestant items
        print("Extracting data...")
        contestant_items = driver.find_elements(By.CSS_SELECTOR, '[data-component="predictions-contestant-item"]')
        print(f"Found {len(contestant_items)} contestant items")
        
        # Extract category headings
        categories = {}
        headings = driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, h4')
        for heading in headings:
            text = heading.text.strip()
            if 'Best' in text and len(text) < 80:
                categories[heading] = text
        
        print(f"Found {len(categories)} category headings")
        
        # Process each contestant item
        category_stats = {}
        filtered_count = 0
        last_known_category = None
        
        for item in contestant_items:
            try:
                # Get ranking
                index_elem = item.find_element(By.CSS_SELECTOR, 'span._contestantIndex_u2o28_1')

                # Try visible text first, then fall back to DOM textContent
                ranking_text = index_elem.text.strip()
                if not ranking_text:
                    ranking_text = index_elem.get_attribute('textContent').strip()

                # Extract digits
                match = re.search(r'(\d+)', ranking_text)
                ranking = int(match.group(1)) if match else 0

                # Get name from title
                name_elem = item.find_element(By.CSS_SELECTOR, '[data-alias="predictions-contestant-item__title"]')

                # Try visible text first
                name = name_elem.text.strip()

                # Fallback if it's empty
                if not name:
                    # textContent will usually include what you see in outerHTML
                    name = name_elem.get_attribute('textContent').strip()
                
                def safe_text(elem):
                    """Return visible text or fallback to textContent if .text is empty."""
                    text = elem.text.strip()
                    if not text:
                        text = (elem.get_attribute('textContent') or '').strip()
                    return text

                # --- Subtitle (optional) ---
                subtitle = ""
                try:
                    subtitle_elem = item.find_element(By.CSS_SELECTOR, '[data-alias="predictions-contestant-item__sub-title"]')
                    subtitle = safe_text(subtitle_elem)
                except:
                    pass

                # --- Percentage ---
                percentage = "0%"
                try:
                    progress_elem = item.find_element(By.CSS_SELECTOR, '[data-alias="predictions-contestant-item__progress-text"]')
                    percentage = safe_text(progress_elem)
                except:
                    pass

                
                # Find category by looking at the parent predictions-award-item
                category = None
                try:
                    # Find the parent predictions-award-item component
                    award_item = item.find_element(By.XPATH, './ancestor::*[@data-component="predictions-award-item"]')
                    category_heading = award_item.find_element(By.CSS_SELECTOR, 'h1, h2, h3, h4, h5, h6')
                    category = category_heading.text.strip()
                except:
                    # If no category found, use last known one if available
                    if last_known_category:
                        category = last_known_category
                    else:
                        category = "Unknown"

                # Update the last known category if this one is valid
                if category != "Unknown":
                    last_known_category = category
                
                # --- Candidate Name ---
                # For categories like Best Actor/Actress/Director: "Name (Film)"
                # For categories like Best Picture: just "Film Name"
                # For Best Song: use title (film name), not subtitle (song name)
                candidate_name = name
                if subtitle and category != "Best Song":
                    candidate_name = subtitle
                
                # Track category stats
                if category not in category_stats:
                    category_stats[category] = 0
                category_stats[category] += 1
                
                if candidate_name and category != "Unknown" and ranking > 0:
                    data.append({
                        'Film': candidate_name,
                        'Category': category,
                        'Ranking': ranking,
                        'Percentage': percentage
                    })
                else:
                    filtered_count += 1
                    
            except Exception as e:
                print(f"Error processing item: {e}")
                continue
        
        print(f"\nCategory breakdown:")
        for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {cat}: {count} items")
        print(f"\nFiltered out {filtered_count} items (category='Unknown' or ranking=0)")
        
        print(f"Extracted {len(data)} entries")
        return data
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        driver.quit()
        print("Driver closed")

def save_to_csv(data, filename='oscar_predictions_goldderby_011926.csv'):
    """Save scraped data to CSV file"""
    if not data:
        print("No data to save!")
        return
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Film', 'Category', 'Ranking', 'Percentage']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    
    print(f"✅ Saved {len(data)} entries to {filename}")

if __name__ == "__main__":
    print("=" * 60)
    print("Gold Derby Oscar Predictions Scraper")
    print("=" * 60)
    
    try:
        data = scrape_gold_derby_oscars()
        
        if data:
            save_to_csv(data)
            
            # Print summary
            print("\nSummary:")
            print(f"Total entries: {len(data)}")
            
            # Count by category
            categories = {}
            for entry in data:
                cat = entry['Category']
                categories[cat] = categories.get(cat, 0) + 1
            
            print("\nEntries by category:")
            for cat, count in sorted(categories.items()):
                print(f"  {cat}: {count} entries")
            
            # Print sample entries
            if data:
                print("\nSample entries (first 10):")
                for i, entry in enumerate(data[:10]):
                    print(f"  {i+1}. {entry['Film']} - {entry['Category']} (Rank {entry['Ranking']}, {entry['Percentage']})")
            
        else:
            print("❌ No data was extracted.")
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

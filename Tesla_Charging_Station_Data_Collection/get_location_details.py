import json
import time
import os
import random
import urllib.parse
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def listtostr(lst):
    return ','.join(lst)

def fetch_and_save_locations(valid_slugs, function_types):
    print("Launching browser (Stealth Mode)...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    
    try:
        print("Accessing Tesla Find Us page to obtain cookie authorization...")
        driver.get("https://www.tesla.com/findus")
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(5)
        
        os.makedirs('locations', exist_ok=True)
        
        existing_files = set(os.listdir('locations'))
        final_slugs = []
        final_types = []
        skipped_count = 0
        
        for s, t in zip(valid_slugs, function_types):
            filename = f"location_{s}.json"
            if filename in existing_files:
                skipped_count += 1
            else:
                final_slugs.append(s)
                final_types.append(t)
        
        valid_slugs = final_slugs
        function_types = final_types
        
        total = len(valid_slugs)
        print(f"Total: {skipped_count + total}, Skipped: {skipped_count}, Remaining: {total}")
        print(f"Starting to scrape and save details for {total} locations...")
        
        fetch_script = """
        var url = arguments[0];
        var callback = arguments[1];
        
        fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json, text/plain, */*'
            }
        })
        .then(response => {
            if (!response.ok) {
                callback({'error': 'HTTP_ERROR', 'status': response.status});
            } else {
                return response.json();
            }
        })
        .then(data => callback(data))
        .catch(err => callback({'error': 'FETCH_ERROR', 'msg': err.toString()}));
        """

        for i, (slug, f_type) in enumerate(zip(valid_slugs, function_types), 1):
            safe_slug = urllib.parse.quote(slug)
            safe_type = urllib.parse.quote(f_type)
            
            url = f"https://www.tesla.com/api/findus/get-location-details?locationSlug={safe_slug}&functionTypes={safe_type}&locale=en-US&isInHkMoTw=false"
            # Retry logic
            success = False
            for attempt in range(2): 
                try:
                    delay = random.uniform(0.5, 1.5)
                    print(f"[{i}/{total}] Scraping {slug} (attempt {attempt+1})... Waiting {delay:.1f}s", end='\r')
                    time.sleep(delay)

                    result = driver.execute_async_script(fetch_script, url)
                    
                    if isinstance(result, dict) and 'error' in result:
                        print(f"\n {slug} failed: {result}")
                        if result.get('status') == 403:
                            print("Rate-limited (403). Pausing for 20s...")
                            time.sleep(20)
                    else:
                        filepath = os.path.join('locations', f"location_{slug}.json")
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=4, ensure_ascii=False)
                        success = True
                        break
                        
                except Exception as e:
                    print(f"\nScript execution error for {slug}: {e}")
            
            # If all retries failed, refresh the page to renew session
            if not success:
                print("\nWarning: Continuous failures detected. Refreshing page to renew session...")
                driver.get("https://www.tesla.com/findus")
                time.sleep(10)

    finally:
        driver.quit()
    
    print("\nAll tasks completed.")

if __name__ == '__main__':
    json_path = "Tesla_charger_stations.json"
    
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        dataused = data.get("data", {}).get("data", [])
        charger_types = {'party', 'destination_charger', 'nacs', 'supercharger', 'destination_charger_nontesla'}
        
        valid_slugs = []
        function_types = []
        
        for slug in dataused:
            # Skip China locations
            if slug.get('inCN') is True:
                continue
                
            if 'location_type' in slug and any(t in charger_types for t in slug['location_type']):
                valid_slugs.append(slug['location_url_slug'])
                function_types.append(listtostr(slug['location_type']))
                
        fetch_and_save_locations(valid_slugs, function_types)
    else:
        print(f"Error: File not found - {json_path}")
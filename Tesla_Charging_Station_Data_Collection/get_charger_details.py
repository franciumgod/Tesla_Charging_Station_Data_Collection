import json
import time
import os
import random
import urllib.parse
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def fetch_and_save_chargers(valid_data):
    """
    valid_data: list of tuples -> [(slug, location_types_list), ...]
    """
    print("Launching browser (Stealth Mode)...")
    options = uc.ChromeOptions()
    # options.add_argument('--proxy-server=http://127.0.0.1:7890') 
    driver = uc.Chrome(options=options)
    
    try:
        print("Accessing the Tesla Find Us page to obtain cookie authorization...")
        driver.get("https://www.tesla.com/findus")
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(5)
        
        os.makedirs('charger', exist_ok=True)
        existing_files = set(os.listdir('charger'))
        to_fetch_data = []
        skipped_count = 0
        
        for item in valid_data:
            slug = item[0]
            filename = f"charger_{slug}.json"
            if filename in existing_files:
                skipped_count += 1
            else:
                to_fetch_data.append(item)
        
        total = len(to_fetch_data)
        print(f"Total: {len(valid_data)}, Skipped: {skipped_count}, Remaining: {total}")
        print(f"Starting to scrape and save details for {total} charging stations....")
        
        # Fetch script
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

        for i, (slug, l_types) in enumerate(to_fetch_data, 1):

            program_type = None
            type_set = set(l_types)
            
            # First: Supercharger station
            if any(t in type_set for t in {'supercharger', 'nacs', 'party'}):
                program_type = 'supercharger'
            
            # Second: Charger station
            elif any(t in type_set for t in {'destination_charger_nontesla', 'destination_charger'}):
                program_type = 'charger'
            # Skip non-charging-station
            if not program_type:
                print(f"[{i}/{total}] Skipping {slug}: type mismatch {l_types}")
                continue
            
            # -----------------------------------------------

            safe_slug = urllib.parse.quote(slug)
            
            # Create URL
            url = f"https://www.tesla.com/api/findus/get-charger-details?locationSlug={safe_slug}&programType={program_type}&locale=en-US&isInHkMoTw=false"
            
            # Retry logic
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    delay = random.uniform(0.3, 1.0)
                    '''
                    You can adjust this range appropriately to avoid triggering the website's anti-bot measures,
                    or to speed up data collection.
                    '''
                    print(f"[{i}/{total}] Scraping {slug} ({program_type})... Waiting {delay:.1f}s", end='\r')
                    time.sleep(delay)

                    result = driver.execute_async_script(fetch_script, url)
                    
                    if isinstance(result, dict) and 'error' in result:
                        status = result.get('status')
                        # A 404 error means the Tesla database does not have corresponding data for this entry.
                        if status == 404:
                            print(f"\n {slug} has no detail data (404) -- skipping")
                            break
                        elif status == 403:
                            print(f"\n {slug} blocked by anti-bot protection (403) -- pausing for 10s...")
                            time.sleep(10)
                        else:
                            print(f"\n {slug} Error: {result}")
                    else:

                        filepath = os.path.join('charger', f"charger_{slug}.json")
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=4, ensure_ascii=False)
                        break 
                        
                except Exception as e:
                    print(f"\nScript execution failed due to an unexpected error. {slug}: {e}")
                    time.sleep(3)
            
    finally:
        driver.quit()
    
    print("\n ALL tasks are completed!")

if __name__ == '__main__':
    json_path = "Tesla_charger_stations.json"
    
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        dataused = data.get("data", {}).get("data", [])
        
        target_types = {'party', 'destination_charger', 'nacs', 'supercharger', 'destination_charger_nontesla'}
        
        valid_data = []
        for item in dataused:
            slug = item.get('location_url_slug')
            l_types = item.get('location_type', [])
            
            # Skip China stations
            if slug and any(t in target_types for t in l_types):
                if item.get('inCN') is True:
                    continue
                    
                valid_data.append((slug, l_types))
                
        fetch_and_save_chargers(valid_data)
    else:
        print(f"Error: cannot find the file {json_path}")
import undetected_chromedriver as uc
import json
import time

driver = uc.Chrome()
try:

    print("Accumulating cookies while accessing the homepage...")
    driver.get("https://www.tesla.com/findus")
    time.sleep(10)

    # Request API
    api_url = "https://www.tesla.com/api/findus/get-locations?country=US&view=map"
    # api_url="https://www.tesla.com/findus/list/chargers/United+States"
    print(f"Requesting API: {api_url}")
    driver.get(api_url)
    time.sleep(3)
    json_text = driver.execute_script("return document.body.innerText")

    try:
        data = json.loads(json_text)
        all_locations = data.get('data',{}).get('data',[])

        with open("Tesla_charger_stations.json", "w", encoding="utf-8") as f:
            json.dump(all_locations, f, indent=4, ensure_ascii=False)
            
        print(f"Success! Data for {len(all_locations)} locations has been successfully scraped and saved to Tesla_charger_stations.json.")
        
    except json.JSONDecodeError:
        print("Error: The retrieved content is not in valid JSON format.")
        print("Page content preview:", json_text[:500])

finally:
    driver.quit()
    pass
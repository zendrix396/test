import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import config
from utils import build_search_url, extract_profile_data

class LinkedInScraper:
    def __init__(self):
        self.driver = None
        self.profile_urls = []

    def _save_debug_info(self, driver, filename_prefix):
        try:
            screenshot_path = f"{filename_prefix}_screenshot.png"
            source_path = f"{filename_prefix}_page_source.html"
            
            driver.save_screenshot(screenshot_path)
            print(f"[DEBUG] Screenshot saved to '{screenshot_path}'")
            
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"[DEBUG] Page source saved to '{source_path}'")
        except Exception as e:
            print(f"[ERROR] Could not save debug info: {e}")

    def _setup_driver(self):
        options = Options()
        if config.HEADLESS:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        self.driver = webdriver.Firefox(options=options)
        self.driver.set_window_size(1920, 1080)

    def _load_cookies(self):
        try:
            with open(config.COOKIES_FILENAME, "r") as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                if 'sameSite' in cookie and cookie['sameSite'] == 'None':
                    cookie['sameSite'] = 'Lax'
                if 'expiry' in cookie:
                    del cookie['expiry']
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"[WARNING] Could not add cookie: {cookie.get('name')}. Error: {e}")

            print("[SUCCESS] Cookies loaded successfully.")
            return True
        except FileNotFoundError:
            print(f"[ERROR] '{config.COOKIES_FILENAME}' not found. Please run the login process first.")
            return False

    def _get_profile_urls(self, search_url):
        self.driver.get(search_url)
        print(f"Navigated to search results page: {self.driver.current_url}")
        
        urls = set()
        page_number = 1

        while len(urls) < config.PROFILES_TO_SCRAPE:
            print(f"\nScraping page {page_number}...")
            
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "search-results-container"))
                )
                time.sleep(3)
            except TimeoutException:
                print("[ERROR] Timed out waiting for search results container.")
                self._save_debug_info(self.driver, "debug_timeout_page")
                break

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            links = self.driver.find_elements(
                By.CSS_SELECTOR,
                "a[data-test-app-aware-link][href*='/in/']",
            )

            if not links:
                print("Selector 1 failed. Trying Selector 2 (for any /in/ links)...")
                links = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, '/in/')]",
                )

            if not links:
                print("[ERROR] Both selectors failed. Could not find any profile links.")
                self._save_debug_info(self.driver, "debug_link_finding_failed")
                break
                
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/in/' in href and '/search/' not in href:
                        clean_url = href.split('?')[0]
                        if clean_url not in urls and clean_url.count('/in/') == 1:
                            urls.add(clean_url)
                            if len(urls) >= config.PROFILES_TO_SCRAPE:
                                break
                except Exception as e:
                    print(f"Error processing a link element: {e}")
            
            print(f"Collected {len(urls)} unique URLs so far.")

            if len(urls) >= config.PROFILES_TO_SCRAPE:
                break
            
            try:
                next_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next']")
                if not next_button.is_enabled():
                    print("Reached the last page of results.")
                    break
                
                self.driver.execute_script("arguments[0].click();", next_button)
                page_number += 1
                time.sleep(3)
            except NoSuchElementException:
                print("Could not find the 'Next' button. Reached the end of results.")
                break

        self.profile_urls = list(urls)[:config.PROFILES_TO_SCRAPE]
        print(f"\nFinished URL collection. Total unique profiles found: {len(self.profile_urls)}")


    def scrape_profiles(self):
        search_url = build_search_url(config.SEARCH_KEYWORDS, config.LOCATION)
        self._setup_driver()
        
        try:
            self.driver.get("https://www.linkedin.com/")
            if not self._load_cookies():
                return
            
            self._get_profile_urls(search_url)
            
            if not self.profile_urls:
                print("No profile URLs were collected. Exiting.")
                return

            profiles_data = []
            for i, url in enumerate(self.profile_urls):
                print("\n" + "="*80)
                print(f"[INFO] Scraping profile {i+1}/{len(self.profile_urls)}")
                print("="*80)
                print(f"URL: {url}")
                
                self.driver.get(url)
                time.sleep(5)
                
                profile_data = extract_profile_data(self.driver, url)
                
                print("\n" + "-"*80)
                print("SCRAPED DATA:")
                print("-"*80)
                print(f"Name:       {profile_data.get('name', 'N/A')}")
                print(f"Headline:   {profile_data.get('headline', 'N/A')}")
                print(f"Location:   {profile_data.get('location', 'N/A')}")
                
                if profile_data.get('experience'):
                    print(f"\nExperience:")
                    exp_items = profile_data.get('experience').split(' | ')
                    for idx, exp in enumerate(exp_items, 1):
                        print(f"  {idx}. {exp}")
                else:
                    print(f"\nExperience: No data extracted")
                
                if profile_data.get('education'):
                    print(f"\nEducation:")
                    edu_items = profile_data.get('education').split(' | ')
                    for idx, edu in enumerate(edu_items, 1):
                        print(f"  {idx}. {edu}")
                else:
                    print(f"\nEducation:  No data extracted")

                if profile_data.get('skills'):
                    print(f"\nSkills:")
                    skill_items = profile_data.get('skills').split(' | ')
                    skills_in_columns = [skill_items[i:i + 2] for i in range(0, len(skill_items), 2)]
                    for row in skills_in_columns:
                        print(f"  - {row[0]:<40} {('- ' + row[1]) if len(row) > 1 else ''}")
                else:
                    print(f"\nSkills:     No data extracted")
                
                print("-"*80)
                print(f"[SUCCESS] Profile {i+1}/{len(self.profile_urls)} completed")
                print("="*80)
                
                profiles_data.append(profile_data)
                time.sleep(2)
            
            df = pd.DataFrame(profiles_data)
            df.to_csv(config.OUTPUT_FILENAME, index=False)
            print(f"\n[SUCCESS] Successfully saved {len(profiles_data)} profiles to '{config.OUTPUT_FILENAME}'")

        except Exception as e:
            print(f"[ERROR] An error occurred: {e}")
            self._save_debug_info(self.driver, "debug_fatal_error")
        finally:
            if self.driver:
                print("[INFO] Closing browser.")
                self.driver.quit()

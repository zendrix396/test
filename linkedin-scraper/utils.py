import config
from urllib.parse import quote
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

COUNTRY_TO_GEO_URN = {
    "france": "105015875",
    "belgium": "100565514",
    "spain": "105646813",
    "england": "102299470",
    "germany": "101282230",
    "italy": "103350119",
    "united states": "103644278",
    "canada": "101174742",
    "australia": "101452733",
    "india": "102713980",
    "china": "102890883",
    "japan": "101355337",
    "brazil": "106057199",
    "mexico": "103323778",
    "netherlands": "102890719",
    "singapore": "102454443",
    "switzerland": "106693272",
    "sweden": "105117694",
    "south korea": "105149562",
    "russia": "101728296",
    "united arab emirates": "104305776",
    # Helpful aliases
    "uae": "104305776",
    "uk": "102299470",
    "united kingdom": "102299470",
    "usa": "103644278",
    "us": "103644278",
}

def _get_geo_urn(location: str):
    if not location:
        return None
    key = location.strip().lower()
    return COUNTRY_TO_GEO_URN.get(key)

def build_search_url(keywords, location):
    encoded_keywords = quote(keywords)
    base = f"https://www.linkedin.com/search/results/people/?keywords={encoded_keywords}&origin=GLOBAL_SEARCH_HEADER"
    geo_urn = _get_geo_urn(location)
    if geo_urn:
        return f"{base}&geoUrn=%5B%22{geo_urn}%22%5D"
    return base

def extract_experience_details(driver, experience_url):
    driver.get(experience_url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.pvs-list__paged-list-item"))
        )
    except TimeoutException:
        print(f"[INFO] No experience found or page did not load: {experience_url}")
        return []

    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    experience_list = []
    try:
        exp_items = driver.find_elements(By.CSS_SELECTOR, "li.pvs-list__paged-list-item")
        for item in exp_items:
            try:
                spans = item.find_elements(By.CSS_SELECTOR, "span[aria-hidden='true']")
                if not spans:
                    continue

                job_title = spans[0].text.strip()
                company = spans[1].text.strip() if len(spans) > 1 else ""
                
                full_text = f"{job_title} at {company}" if company else job_title
                experience_list.append(full_text)
            except Exception:
                continue
    except Exception as e:
        print(f"[WARNING] Error while parsing experience section: {e}")
        
    return experience_list[:5]

def extract_education_details(driver, education_url):
    driver.get(education_url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.pvs-list__paged-list-item"))
        )
    except TimeoutException:
        print(f"[INFO] No education found or page did not load: {education_url}")
        return []

    education_list = []
    try:
        edu_items = driver.find_elements(By.CSS_SELECTOR, "li.pvs-list__paged-list-item")
        for item in edu_items:
            try:
                institution = item.find_element(By.CSS_SELECTOR, "div.hoverable-link-text span[aria-hidden='true']").text.strip()
                
                degree = ""
                try:
                    degree = item.find_element(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']").text.strip()
                except NoSuchElementException:
                    pass

                full_text = f"{institution} - {degree}" if degree else institution
                education_list.append(full_text)
            except Exception:
                continue
    except Exception as e:
        print(f"[WARNING] Error while parsing education section: {e}")

    return education_list[:5]

def extract_skills_details(driver, skills_url):
    driver.get(skills_url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.pvs-list__paged-list-item"))
        )
    except TimeoutException:
        print(f"[INFO] No skills found or page did not load: {skills_url}")
        return []

    skills_list = []
    try:
        skill_items = driver.find_elements(By.CSS_SELECTOR, "li.pvs-list__paged-list-item")
        for item in skill_items:
            try:
                skill_name = item.find_element(By.CSS_SELECTOR, "div.hoverable-link-text span[aria-hidden='true']").text.strip()
                if skill_name:
                    skills_list.append(skill_name)
            except Exception:
                continue
    except Exception as e:
        print(f"[WARNING] Error while parsing skills section: {e}")

    return skills_list[:10]

def extract_summary_experience(driver):
    experience_list = []
    try:
        experience_heading = driver.find_element(By.XPATH, "//h2[contains(., 'Experience')]")
        experience_section = experience_heading.find_element(By.XPATH, "./ancestor::section")
        experience_items = experience_section.find_elements(By.CSS_SELECTOR, 'li.artdeco-list__item')
        
        for item in experience_items:
            try:
                title_element = item.find_element(By.CSS_SELECTOR, "div.hoverable-link-text span[aria-hidden='true']")
                title = title_element.text.strip()

                company_element = item.find_element(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']")
                company = company_element.text.strip()
                
                full_text = f"{title} at {company}" if company else title
                experience_list.append(full_text)
            except NoSuchElementException:
                try:
                    spans = item.find_elements(By.CSS_SELECTOR, "span[aria-hidden='true']")
                    if spans:
                        title = spans[0].text.strip()
                        company = spans[1].text.strip() if len(spans) > 1 else ""
                        full_text = f"{title} at {company}" if company else title
                        if full_text not in experience_list:
                           experience_list.append(full_text)
                except Exception:
                    continue
    except NoSuchElementException:
        print("[INFO] Summary experience section not found on main page.")
    return experience_list[:5]

def extract_summary_education(driver):
    education_list = []
    try:
        education_heading = driver.find_element(By.XPATH, "//h2[contains(., 'Education')]")
        education_section = education_heading.find_element(By.XPATH, "./ancestor::section")
        education_items = education_section.find_elements(By.CSS_SELECTOR, 'li.artdeco-list__item')

        for item in education_items:
            try:
                institution_element = item.find_element(By.CSS_SELECTOR, "div.hoverable-link-text span[aria-hidden='true']")
                institution = institution_element.text.strip()

                degree_element = item.find_element(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']")
                degree = degree_element.text.strip()

                full_text = f"{institution} - {degree}" if degree else institution
                education_list.append(full_text)
            except NoSuchElementException:
                try:
                    spans = item.find_elements(By.CSS_SELECTOR, "span[aria-hidden='true']")
                    if spans:
                        institution = spans[0].text.strip()
                        degree = spans[1].text.strip() if len(spans) > 1 else ""
                        full_text = f"{institution} - {degree}" if degree else institution
                        if full_text not in education_list:
                            education_list.append(full_text)
                except Exception:
                    continue
    except NoSuchElementException:
        print("[INFO] Summary education section not found on main page.")
    return education_list[:5]

def extract_summary_skills(driver):
    skills_list = []
    try:
        skills_heading = driver.find_element(By.XPATH, "//h2[contains(., 'Skills')]")
        skills_section = skills_heading.find_element(By.XPATH, "./ancestor::section")
        skill_items = skills_section.find_elements(By.CSS_SELECTOR, "div.hoverable-link-text span[aria-hidden='true']")
        
        for item in skill_items:
            skills_list.append(item.text.strip())
    except NoSuchElementException:
         print("[INFO] Summary skills section not found on main page.")
    return skills_list[:10]

def extract_profile_data(driver, url):
    data = {"url": url, "name": "", "headline": "", "location": "", "experience": "", "education": "", "skills": ""}
    
    print(f"[INFO] Scraping main profile page for top card...")
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
        time.sleep(3)
    except TimeoutException:
        print(f"[WARNING] Main profile page did not load correctly: {url}")
        return data

    try:
        data["name"] = driver.find_element(By.CSS_SELECTOR, "h1.text-heading-xlarge").text.strip()
    except NoSuchElementException:
        try:
             data["name"] = driver.find_element(By.XPATH, "//main//h1").text.strip()
        except NoSuchElementException:
            print(f"[WARNING] Could not extract name for {url}")

    try:
        data["headline"] = driver.find_element(By.CSS_SELECTOR, "div.text-body-medium.break-words").text.strip()
    except NoSuchElementException:
        print(f"[WARNING] Could not extract headline for {url}")

    try:
        data["location"] = driver.find_element(By.CSS_SELECTOR, "span.text-body-small.inline").text.strip()
    except NoSuchElementException:
        print(f"[WARNING] Could not extract location for {url}")

    if config.SCRAPE_MODE == "DETAILED":
        print("[INFO] Running in DETAILED mode.")
        experience_url = url.rstrip('/') + '/details/experience/'
        print(f"[INFO] Navigating to experience page...")
        experience_list = extract_experience_details(driver, experience_url)
        if experience_list:
            data["experience"] = " | ".join(experience_list)

        education_url = url.rstrip('/') + '/details/education/'
        print(f"[INFO] Navigating to education page...")
        education_list = extract_education_details(driver, education_url)
        if education_list:
            data["education"] = " | ".join(education_list)

        skills_url = url.rstrip('/') + '/details/skills/'
        print(f"[INFO] Navigating to skills page...")
        skills_list = extract_skills_details(driver, skills_url)
        if skills_list:
            data["skills"] = " | ".join(skills_list)
    
    else:
        print("[INFO] Running in SUMMARY mode.")
        print("[INFO] Scrolling to load all page content...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        experience_list = extract_summary_experience(driver)
        if experience_list:
            data["experience"] = " | ".join(experience_list)

        education_list = extract_summary_education(driver)
        if education_list:
            data["education"] = " | ".join(education_list)

        skills_list = extract_summary_skills(driver)
        if skills_list:
            data["skills"] = " | ".join(skills_list)


    return data

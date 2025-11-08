# Search settings
SEARCH_KEYWORDS = "Data Science"
LOCATION = "India"
PROFILES_TO_SCRAPE = 5

# New setting for scrape mode: "SUMMARY" or "DETAILED"
# "SUMMARY": Scrapes only the main profile page (more reliable).
# "DETAILED": Navigates to the details pages for Experience, Education, etc. (more comprehensive but can fail).
SCRAPE_MODE = "SUMMARY"

# Browser settings
HEADLESS = True

# Output settings
OUTPUT_FILENAME = "linkedin_profiles.csv"
COOKIES_FILENAME = "cookies.json"
LOGIN_URL = "https://www.linkedin.com/login"

# LinkedIn Profile Scraper

A Python script to scrape LinkedIn profiles based on search queries. It supports two modes for data extraction: a reliable "summary" mode that scrapes from the main profile page and a "detailed" mode that navigates to specific sub-pages for more comprehensive data.

---

## Setup

Choose either the `uv` (recommended) or `pip` setup method.

### 1. Using `uv` (Recommended)

**Prerequisites**: `uv` must be installed.

1.  **Create and activate a virtual environment:**
    ```bash
    uv venv
    source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    uv pip install -r requirements.txt
    ```

### 2. Using `pip`

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use: venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## Usage

The scraper requires you to be authenticated with a LinkedIn account.

### 1. Authenticate and Save Cookies

Run the `login` command to authenticate. This will open a browser window where you can enter your LinkedIn credentials. Upon successful login, your session cookies will be saved to `cookies.json`, allowing the scraper to run without needing to log in again.

```bash
python main.py login
```

### 2. Configure the Scraper

Edit the `config.py` file to customize the scraper's behavior:

-   `SEARCH_KEYWORDS`: The job title or keyword to search for (e.g., "Data Scientist").
-   `LOCATION`: The geographical location to search within (e.g., "United States").
-   `PROFILES_TO_SCRAPE`: The total number of profiles to collect.
-   `SCRAPE_MODE`:
    -   `"SUMMARY"` (Default): Faster and more reliable. Scrapes data visible on the main profile page.
    -   `"DETAILED"`: Slower but more comprehensive. Navigates to the `details/experience`, `details/education`, and `details/skills` sub-pages.
-   `HEADLESS`:
    -   `True` (Default): Runs the browser in the background without a visible UI.
    -   `False`: Opens a visible browser window, which can be useful for debugging.

### 3. Run the Scraper

Once authenticated and configured, run the `scrape` command:

```bash
python main.py scrape
```

The scraper will begin its process, and you will see the extracted data printed to the terminal in real-time. The final results will be saved to `linkedin_profiles.csv`.

### A Note on Delays

The script includes intentional delays (`time.sleep()`) between requests and actions to mimic human behavior and reduce the risk of being blocked by LinkedIn. If you are on a very fast and reliable network, you may be able to slightly reduce these delays in `scraper.py` and `utils.py`, but this is not recommended.

import json
import getpass
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import config

class LinkedInAuth:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = None

    def login(self):
        options = Options()
        if config.HEADLESS:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        
        self.driver = webdriver.Firefox(options=options)
        print("[INFO] Starting browser...")

        try:
            self.driver.get(config.LOGIN_URL)
            print(f"Navigated to {config.LOGIN_URL}")

            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            print("[INFO] Found username field. Entering username...")
            username_field.send_keys(self.username)

            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            print("[INFO] Found password field. Entering password...")
            password_field.send_keys(self.password)

            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            login_button.click()
            print("[SUCCESS] Clicked 'Log in' button.")

            print("[INFO] Verifying login success...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "global-nav-search"))
            )
            
            print("\n[SUCCESS] Login successful!")
            self._save_cookies()

        except TimeoutException:
            print(f"\n[ERROR] Login Failed: A timeout occurred. This could be due to:")
            print("- Incorrect username or password.")
            print("- A CAPTCHA challenge.")
            print("- Slow network connection or a change in LinkedIn's login page structure.")
        
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        finally:
            if self.driver:
                print("[INFO] Closing browser.")
                self.driver.quit()

    def _save_cookies(self):
        cookies = self.driver.get_cookies()
        with open(config.COOKIES_FILENAME, "w") as f:
            json.dump(cookies, f, indent=2)
        print(f"[SUCCESS] Cookies have been saved to '{config.COOKIES_FILENAME}'")

def main():
    username = input("Enter your LinkedIn username or email: ")
    password = getpass.getpass("Enter your LinkedIn password: ")
    if username and password:
        auth = LinkedInAuth(username, password)
        auth.login()
    else:
        print("[ERROR] Username and password cannot be empty. Aborting.")

if __name__ == "__main__":
    main()

import argparse
from auth import LinkedInAuth
from scraper import LinkedInScraper
import getpass

def main():
    parser = argparse.ArgumentParser(description="LinkedIn Scraper Tool")
    parser.add_argument('action', choices=['login', 'scrape'], help="Action to perform: 'login' to save cookies, 'scrape' to start scraping.")
    
    args = parser.parse_args()

    if args.action == 'login':
        username = input("Enter your LinkedIn username or email: ")
        password = getpass.getpass("Enter your LinkedIn password: ")
        if username and password:
            auth = LinkedInAuth(username, password)
            auth.login()
        else:
            print("[ERROR] Username and password cannot be empty. Aborting.")
    
    elif args.action == 'scrape':
        scraper = LinkedInScraper()
        scraper.scrape_profiles()

if __name__ == "__main__":
    main()

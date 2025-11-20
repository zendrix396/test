from django.core.management.base import BaseCommand
from products.models import ScrapedProduct
from products.scrapers import kiaya, comicsense, offostore, theyouthspace

class Command(BaseCommand):
    help = 'Scrapes product data from competitor websites.'

    # define all available scrapers
    SCRAPERS = {
        'kiaya': kiaya.scrape,
        'comicsense': comicsense.scrape,
        'offo': offostore.scrape,
        'youthspace': theyouthspace.scrape,
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--scraper',
            nargs='+',
            type=str,
            help='Specify which scraper(s) to run (e.g., kiaya comicsense). Runs all if not specified.'
        )

    def handle(self, *args, **options):
        scrapers_to_run = options['scraper'] or self.SCRAPERS.keys()
        total_saved = 0

        for scraper_name in scrapers_to_run:
            if scraper_name not in self.SCRAPERS:
                self.stdout.write(self.style.ERROR(f"Scraper '{scraper_name}' not found."))
                continue

            self.stdout.write(self.style.SUCCESS(f"--- Running scraper: {scraper_name} ---"))
            scraped_products = self.SCRAPERS[scraper_name]()

            for product_data in scraped_products:
                obj, created = ScrapedProduct.objects.update_or_create(
                    source_url=product_data['source_url'],
                    defaults={
                        'name': product_data['name'],
                        'description': product_data['description'],
                        'price': product_data['price'],
                        'image_urls': product_data['image_urls'],
                        'tags': product_data['tags'],
                        'source_site': product_data['source_site'],
                    }
                )
                if created:
                    total_saved += 1
        
        self.stdout.write(self.style.SUCCESS(f"\n--- Scraping complete. Saved {total_saved} new products. ---"))

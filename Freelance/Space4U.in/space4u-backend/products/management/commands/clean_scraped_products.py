from django.core.management.base import BaseCommand
from django.db.models import Count
from products.models import ScrapedProduct

class Command(BaseCommand):
    help = 'Removes duplicate ScrapedProduct entries based on name and price.'

    def handle(self, *args, **options):
        self.stdout.write("Finding duplicate scraped products...")

        duplicates = (
            ScrapedProduct.objects.values('name', 'price')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        if not duplicates:
            self.stdout.write(self.style.SUCCESS("No duplicates found."))
            return

        self.stdout.write(f"Found {len(duplicates)} groups of duplicate products.")
        total_deleted = 0

        for item in duplicates:
            # Get all products in the duplicate group, ordered by creation time
            products_in_group = ScrapedProduct.objects.filter(
                name=item['name'],
                price=item['price']
            ).order_by('pk')

            # The first one is the one we want to keep
            product_to_keep = products_in_group.first()
            
            # And the rest are the ones we want to delete
            products_to_delete = products_in_group.exclude(pk=product_to_keep.pk)
            
            count_to_delete = products_to_delete.count()
            if count_to_delete > 0:
                self.stdout.write(
                    f"  - Deleting {count_to_delete} duplicate(s) for '{item['name']}'"
                )
                # The delete() method returns the number of objects deleted
                deleted_count, _ = products_to_delete.delete()
                total_deleted += deleted_count

        self.stdout.write(
            self.style.SUCCESS(f"\nCleanup complete. Deleted {total_deleted} duplicate products.")
        )

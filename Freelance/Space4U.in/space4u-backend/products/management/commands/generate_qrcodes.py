import os
import io
import zipfile
import qrcode
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.conf import settings
from products.models import Batch

class Command(BaseCommand):
    help = 'Generates QR codes for product batches.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate QR codes for all batches, ignoring their current status.'
        )

    def handle(self, *args, **options):
        if options['all']:
            batches_to_process = Batch.objects.all()
            self.stdout.write(self.style.WARNING('Processing all batches...'))
        else:
            batches_to_process = Batch.objects.filter(qr_code_generated=False)
            self.stdout.write(self.style.SUCCESS('Processing only new batches (qr_code_generated=False)...'))

        if not batches_to_process.exists():
            self.stdout.write('No batches to process.')
            return

        zip_path = os.path.join(settings.MEDIA_ROOT or settings.BASE_DIR, 'qr_codes_bulk.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for batch in batches_to_process:
                # we need a dummy host for the URL since we're not in a request
                qr_url = f"https://space4u.in{reverse('core:qr_redirect', args=[batch.batch_code])}"
                img = qrcode.make(qr_url)
                
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                zf.writestr(f'{batch.batch_code}.png', img_buffer.read())
                self.stdout.write(f'Generated QR for {batch.batch_code}')

        # update status in bulk
        batches_to_process.update(qr_code_generated=True)

        self.stdout.write(self.style.SUCCESS(f'Successfully generated {batches_to_process.count()} QR codes.'))
        self.stdout.write(self.style.SUCCESS(f'Zip file saved to: {zip_path}'))


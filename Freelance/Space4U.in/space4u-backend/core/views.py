from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from products.models import Batch
from drf_spectacular.utils import extend_schema, OpenApiResponse

@extend_schema(
    summary="QR Code Redirect",
    description="This is the special endpoint designed to be embedded in QR codes for physical product batches. When a user scans a QR code, this view checks if the user is a staff member. If staff, it redirects to the product's edit page in the Django admin. If a regular user or not logged in, it redirects to the public-facing product page. This provides a direct link between physical inventory and the digital system.",
    responses={
        302: OpenApiResponse(description="Redirecting to the appropriate product page.")
    }
)
class QRRedirectView(View):
    def get(self, request, *args, **kwargs):
        batch_code = kwargs.get('batch_code')
        batch = get_object_or_404(Batch, batch_code=batch_code)
        product = batch.product

        # check if user is logged in and is staff
        if request.user.is_authenticated and request.user.is_staff:
            admin_url = reverse('admin:products_product_change', args=[product.id])
            return redirect(admin_url)
        else:
            # this domain should come from settings in production
            frontend_url = f"https://space4u.in/products/{product.sku}"
            return redirect(frontend_url)

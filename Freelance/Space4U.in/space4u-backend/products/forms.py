from django import forms
from .models import TrendingDeal, Category

class BatchImportForm(forms.Form):
    """Form for batch importing scraped products with initial batch details."""
    cost_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        initial=0.00,
        help_text="Cost price for the initial batch"
    )
    tags = forms.CharField(
        max_length=500,
        required=False,
        help_text="Comma-separated tags (e.g., 'tag1, tag2, tag3')"
    )
    quantity_initial = forms.IntegerField(
        min_value=0,
        required=True,
        help_text="Initial quantity for the batch"
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        help_text="Product category"
    )
    received_date = forms.DateField(
        required=True,
        help_text="Date when the batch was received"
    )


class TrendingDealForm(forms.ModelForm):
    class Meta:
        model = TrendingDeal
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        flat_discount_amount = cleaned_data.get('flat_discount_amount')
        discount_percent = cleaned_data.get('discount_percent')
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')

        if starts_at and ends_at and ends_at <= starts_at:
            raise forms.ValidationError("End time must be after the start time for a deal.")
        
        if product and (flat_discount_amount or discount_percent):
            # Get base price from product or its default variant
            base_price = None
            if not product.has_variants and product.price:
                base_price = float(product.price)
            elif product.has_variants:
                default_variant = product.variants.filter(is_default=True).first()
                if default_variant:
                    base_price = float(default_variant.price)
            
            if base_price and base_price > 0:
                # Check flat discount
                if flat_discount_amount:
                    discount_amount = float(flat_discount_amount)
                    if discount_amount > base_price:
                        raise forms.ValidationError(
                            f"Flat discount ({discount_amount}) cannot exceed product price ({base_price})"
                        )
                    discount_percent_calc = (discount_amount / base_price) * 100
                    if discount_percent_calc > 60:
                        raise forms.ValidationError(
                            f"Discount cannot exceed 60%. Calculated: {discount_percent_calc:.1f}%"
                        )
                    final_price = base_price - discount_amount
                    if final_price < 0:
                        raise forms.ValidationError("Discount cannot result in negative price")
                
                # Check percentage discount
                if discount_percent:
                    discount_percent_val = float(discount_percent)
                    if discount_percent_val > 60:
                        raise forms.ValidationError(
                            f"Percentage discount cannot exceed 60%. Provided: {discount_percent_val}%"
                        )
                    discount_amount = base_price * (discount_percent_val / 100)
                    final_price = base_price - discount_amount
                    if final_price < 0:
                        raise forms.ValidationError("Discount cannot result in negative price")
        
        return cleaned_data

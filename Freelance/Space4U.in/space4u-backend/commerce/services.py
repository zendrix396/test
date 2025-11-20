import logging
from decimal import Decimal
from django.conf import settings
from decouple import config
import razorpay
from .models import Order, UserCouponUsage
from products.models import Batch, StockMovement, StockAdjustmentReason, ProductVariant
from shipping.services import create_shipment as create_shipping_label
from users.models import CustomUser, UserBadge, Badge
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def process_order_success(order: Order):
    """
    Processes an order after successful payment or manual confirmation.
    - Updates order status to PROCESSING.
    - Manages inventory and stock movements.
    - Handles coupon usage.
    - Creates shipping labels.
    - Manages wallet and loyalty points.
    """
    logger.info(f"[PROCESS_ORDER] Starting process_order_success for order {order.id}, current status: {order.status}")
    print(f"[PROCESS_ORDER] Starting process_order_success for order {order.id}, current status: {order.status}")
    
    if order.status != Order.Status.PROCESSING:
        order.status = Order.Status.PROCESSING
        order.save(update_fields=["status"])
        logger.info(f"[PROCESS_ORDER] Updated order {order.id} status to PROCESSING")
        print(f"[PROCESS_ORDER] Updated order {order.id} status to PROCESSING")
        
        # Send status update email
        try:
            from users.services import send_shipping_update_email
            send_shipping_update_email(order)
        except Exception as e:
            logger.error(f"Failed to send status update email for order {order.id}: {e}")
            print(f"Failed to send status update email for order {order.id}: {e}")

    # Get the reason for web sales, creating it if it doesn't exist.
    web_sale_reason, _ = StockAdjustmentReason.objects.get_or_create(
        reason__iexact="Web Sales", defaults={'reason': 'Web Sales'}
    )

    # Increment coupon usage
    if order.applied_coupon:
        coupon = order.applied_coupon
        coupon.times_used += 1
        coupon.save(update_fields=["times_used"])

        if order.user:
            user_usage, _ = UserCouponUsage.objects.get_or_create(user=order.user, coupon=coupon)
            user_usage.times_used += 1
            user_usage.save(update_fields=["times_used"])

    # Reserve inventory on PROCESSING: increase reserved on the variant
    logger.info(f"[PROCESS_ORDER] Starting reservation for order {order.id} with {order.items.count()} items")
    print(f"[PROCESS_ORDER] Starting reservation for order {order.id} with {order.items.count()} items")
    
    for item in order.items.select_related("variant", "product").all():
        logger.info(f"[PROCESS_ORDER] Processing item {item.id}: variant={item.variant_id}, product={item.product_id}, qty={item.quantity}")
        print(f"[PROCESS_ORDER] Processing item {item.id}: variant={item.variant_id}, product={item.product_id}, qty={item.quantity}")
        
        variant = item.variant
        if variant is None and item.product:
            # choose default variant or first available
            variant = item.product.variants.filter(is_default=True).first() or item.product.variants.first()
            logger.info(f"[PROCESS_ORDER] No variant on item, found variant: {variant.id if variant else None}")
            print(f"[PROCESS_ORDER] No variant on item, found variant: {variant.id if variant else None}")
        
        if not variant:
            logger.warning(f"[PROCESS_ORDER] No variant found for item {item.id}, skipping reservation")
            print(f"[PROCESS_ORDER] No variant found for item {item.id}, skipping reservation")
            continue
            
        old_reserved = variant.reserved_quantity or 0
        variant.reserved_quantity = old_reserved + int(item.quantity)
        variant.save(update_fields=["reserved_quantity"])
        logger.info(f"[PROCESS_ORDER] Reserved stock for variant {variant.id}: {old_reserved} -> {variant.reserved_quantity}")
        print(f"[PROCESS_ORDER] Reserved stock for variant {variant.id}: {old_reserved} -> {variant.reserved_quantity}")

    # Create shipment
    if order.shipping_label_required:
        try:
            shipment_data, error = create_shipping_label(order)
            if error:
                logger.error(f"Failed to create shipment for order {order.id}: {error}")
            else:
                order.shipping_id = shipment_data.get("shipment_id")
                order.tracking_number = shipment_data.get("tracking_id")
                order.courier_name = "Shiprocket" 
                order.save(update_fields=["shipping_id", "tracking_number", "courier_name"])
        except Exception as e:
            logger.error(f"An unexpected error occurred during shipment creation for order {order.id}: {e}")
    else:
        logger.info(f"[PROCESS_ORDER] Skipping automatic shipment creation for order {order.id} (shipping_label_required=False)")

    # Apply wallet deduction on success
    if order.wallet_applied_amount and order.wallet_applied_amount > 0 and order.user:
        user = order.user
        user.wallet_balance -= order.wallet_applied_amount
        user.save(update_fields=["wallet_balance"])
        from users.models import WalletTransaction
        WalletTransaction.objects.create(
            user=user,
            amount=-order.wallet_applied_amount,
            kind=WalletTransaction.Kind.DEBIT,
            reference=f"order:{order.id}"
        )

    # Process cashback from deals
    from products.deal_utils import get_deal_for_product_or_variant
    from users.models import WalletTransaction
    
    total_cashback = Decimal("0.00")
    cashback_details = []
    
    if order.user:
        for item in order.items.select_related("variant", "variant__product").all():
            variant = item.variant
            if not variant:
                continue
            
            deal, _ = get_deal_for_product_or_variant(variant.product, variant)
            if deal and deal.cashback_amount and deal.cashback_amount > 0:
                item_cashback = deal.cashback_amount * item.quantity
                total_cashback += item_cashback
                cashback_details.append({
                    'product_name': variant.product.name if variant.product else 'Unknown',
                    'quantity': item.quantity,
                    'cashback_per_unit': str(deal.cashback_amount),
                    'total_cashback': str(item_cashback),
                })
        
        # Credit cashback to user's wallet
        if total_cashback > 0:
            user = order.user
            user.wallet_balance += total_cashback
            user.save(update_fields=["wallet_balance"])
            
            WalletTransaction.objects.create(
                user=user,
                amount=total_cashback,
                kind=WalletTransaction.Kind.CREDIT,
                reference=f"order:{order.id}:cashback"
            )
            
            logger.info(f"[PROCESS_ORDER] Applied {total_cashback} cashback to user {user.id} for order {order.id}")
            print(f"[PROCESS_ORDER] Applied {total_cashback} cashback to user {user.id} for order {order.id}")

    # Loyalty points and tier/badge updates are awarded on COMPLETED status, not here.


def ship_order(order: Order):
    """Ship an order: remove reservations and decrement physical stock (FIFO)."""
    logger.info(f"[SHIP_ORDER] Starting ship_order for order {order.id}")
    print(f"[SHIP_ORDER] Starting ship_order for order {order.id}")
    
    # Get the reason for web sales, creating it if it doesn't exist.
    web_sale_reason, _ = StockAdjustmentReason.objects.get_or_create(
        reason__iexact="Web Sales", defaults={'reason': 'Web Sales'}
    )

    # For each item, reduce reserved and decrement batches
    for item in order.items.select_related("variant", "product").all():
        logger.info(f"[SHIP_ORDER] Processing item {item.id}: variant={item.variant_id}, product={item.product_id}, qty={item.quantity}")
        print(f"[SHIP_ORDER] Processing item {item.id}: variant={item.variant_id}, product={item.product_id}, qty={item.quantity}")
        
        variant = item.variant
        if variant is None and item.product:
            variant = item.product.variants.filter(is_default=True).first() or item.product.variants.first()
            logger.info(f"[SHIP_ORDER] No variant on item, found variant: {variant.id if variant else None}")
            print(f"[SHIP_ORDER] No variant on item, found variant: {variant.id if variant else None}")
        
        if not variant:
            logger.warning(f"[SHIP_ORDER] No variant found for item {item.id}, skipping")
            print(f"[SHIP_ORDER] No variant found for item {item.id}, skipping")
            continue

        # Reduce reservation
        old_reserved = variant.reserved_quantity or 0
        new_reserved = max(old_reserved - int(item.quantity), 0)
        if new_reserved != variant.reserved_quantity:
            variant.reserved_quantity = new_reserved
            variant.save(update_fields=["reserved_quantity"])
            logger.info(f"[SHIP_ORDER] Reduced reservation for variant {variant.id}: {old_reserved} -> {new_reserved}")
            print(f"[SHIP_ORDER] Reduced reservation for variant {variant.id}: {old_reserved} -> {new_reserved}")

        # Decrement inventory from batches (FIFO)
        qty_needed = int(item.quantity)
        batches = list(Batch.objects.filter(variant=variant, quantity_current__gt=0).order_by("created_at"))
        logger.info(f"[SHIP_ORDER] Found {len(batches)} batches for variant {variant.id}, need to ship {qty_needed}")
        print(f"[SHIP_ORDER] Found {len(batches)} batches for variant {variant.id}, need to ship {qty_needed}")
        
        for batch in batches:
            if qty_needed <= 0:
                break
            take = min(batch.quantity_current, qty_needed)
            if take > 0:
                old_qty = batch.quantity_current
                batch.quantity_current -= take
                batch.save(update_fields=["quantity_current"])
                logger.info(f"[SHIP_ORDER] Batch {batch.id} stock: {old_qty} -> {batch.quantity_current} (took {take})")
                print(f"[SHIP_ORDER] Batch {batch.id} stock: {old_qty} -> {batch.quantity_current} (took {take})")
                
                movement = StockMovement.objects.create(
                    batch=batch,
                    user=order.user,
                    order=order,
                    change=-int(take),
                    notes=f"Sale (shipped) for order {order.id}",
                    reason=web_sale_reason
                )
                logger.info(f"[SHIP_ORDER] Created StockMovement {movement.id} for batch {batch.id}")
                print(f"[SHIP_ORDER] Created StockMovement {movement.id} for batch {batch.id}")
                qty_needed -= take
        
        if qty_needed > 0:
            logger.error(f"[SHIP_ORDER] Insufficient stock! Still need {qty_needed} units for variant {variant.id}")
            print(f"[SHIP_ORDER] Insufficient stock! Still need {qty_needed} units for variant {variant.id}")


def release_reservations(order: Order):
    for item in order.items.select_related("variant", "product").all():
        variant = item.variant
        if variant is None and item.product:
            variant = item.product.variants.filter(is_default=True).first() or item.product.variants.first()
        if not variant:
            continue
        new_reserved = max((variant.reserved_quantity or 0) - int(item.quantity), 0)
        if new_reserved != variant.reserved_quantity:
            variant.reserved_quantity = new_reserved
            variant.save(update_fields=["reserved_quantity"])


def compute_refund_amount(order: Order, *, kind: str = "cancellation"):
    from .models import RefundConfig
    percent = 0
    cfg = RefundConfig.objects.first()
    if not cfg or not cfg.enabled:
        return Decimal("0.00")
    if kind == "cancellation":
        percent = cfg.cancelled_before_shipment_percent
    else:
        percent = cfg.returned_after_shipment_percent
    paid_amount = order.total_cost - order.wallet_applied_amount
    if paid_amount < 0:
        paid_amount = Decimal("0.00")
    return (paid_amount * (Decimal(str(percent)) / Decimal("100"))).quantize(Decimal("0.01"))


def cancel_order(order: Order):
    """Cancel an order: release reservations and create refund if applicable."""
    # Release any reservations
    release_reservations(order)
    # Create refund record for prepaid methods before shipment
    if order.payment_method == order.PaymentMethod.RAZORPAY and order.status in (Order.Status.PROCESSING, Order.Status.PAID):
        refundable = compute_refund_amount(order, kind="cancellation")
        if refundable > 0 and order.razorpay_payment_id:
            from .models import OrderRefund
            # Create pending refund record
            rf = OrderRefund.objects.create(order=order, amount=refundable, reason="Order cancelled")
            # Initiate Razorpay refund
            try:
                client = razorpay.Client(auth=(config("RAZORPAY_KEY_ID"), config("RAZORPAY_KEY_SECRET")))
                refund_amount = int(refundable * 100)  # Convert to paise
                rp_refund = client.payment.refund(order.razorpay_payment_id, {"amount": refund_amount})
                rf.status = rf.Status.COMPLETED
                rf.transaction_id = rp_refund.get("id", "")
                rf.save(update_fields=["status", "transaction_id"])
                logger.info(f"Refund initiated for order {order.id}: Razorpay refund ID {rf.transaction_id}")
            except Exception as e:
                logger.error(f"Failed to initiate Razorpay refund for order {order.id}: {e}")
                rf.status = rf.Status.FAILED
                rf.save(update_fields=["status"])


def render_invoice_latex(order: Order) -> str:
    from jinja2 import Environment, FileSystemLoader
    
    # Using Environment to better handle templates
    # In a real app, this might point to a template directory
    env = Environment()

    # --- 1. Main LaTeX Template with Placeholders ---
    # This part has no complex Jinja logic, making it safe.
    template_str = r"""
\documentclass[12pt]{article}
\usepackage[a4paper, margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{array}
\usepackage{longtable}
\usepackage{fontspec}
\usepackage{lmodern} % A more complete font set
\usepackage{textcomp} % Required for text symbols

% Define rupee symbol command
\newcommand{\textrupee}{₹}
\newcommand{\currencysymbol}{ {{ currency_symbol_latex }} }

% --- Template Commands for Order Details ---
__COMMANDS__

\begin{document}

% Header
\begin{center}
    {\Large\bfseries \companyname}\\
    {\companyaddress}\\
    {\companycity, \companystate, \companyzip}\\
    Email: \companyemail \hspace{1cm} Phone: \companyphone
\end{center}

\vspace{0.5cm}
\hrule
\vspace{0.5cm}

% Invoice Header Section
\begin{minipage}[t]{0.5\textwidth}
    \textbf{Bill To:}\\
    \invoiceto\\
    \invoiceaddress
\end{minipage}
\begin{minipage}[t]{0.5\textwidth}
    \begin{flushright}
        \textbf{Invoice \#:} \invoiceid\\
        \textbf{Date:} \invoicedate\\
        \textbf{Status:} \invoicestatus\\
        \textbf{Payment:} \paymentmethod
    \end{flushright}
\end{minipage}

\vspace{0.5cm}

% --- Items Table Placeholder ---
__ITEMS_TABLE__

\vspace{0.5cm}

% --- Totals Section Placeholder ---
__TOTALS_SECTION__

\vspace{1cm}

% Footer
\begin{center}
    {\textit{\companyfooter}}
\end{center}

\end{document}
"""

    # --- 2. Sub-templates for Dynamic Parts ---

    commands_template_str = r"""
\newcommand{\companyname}{ {{ company.name }} }
\newcommand{\companyaddress}{ {{ company.address }} }
\newcommand{\companycity}{ {{ company.city }} }
\newcommand{\companystate}{ {{ company.state }} }
\newcommand{\companyzip}{ {{ company.zip }} }
\newcommand{\companyemail}{ {{ company.email }} }
\newcommand{\companyphone}{ {{ company.phone }} }
\newcommand{\companyfooter}{ {{ company.footer }} }
\newcommand{\invoiceto}{ {{ bill_to }} }
\newcommand{\invoiceaddress}{ {{ invoice_address }} }
\newcommand{\invoicedate}{ {{ invoice_date }} }
\newcommand{\invoiceid}{ {{ invoice_id }} }
\newcommand{\invoicestatus}{ {{ invoice_status }} }
\newcommand{\paymentmethod}{ {{ payment_method }} }
"""

    items_template_str = r"""
\begin{longtable}{|p{4cm}|p{1.5cm}|p{2cm}|p{2.5cm}|}
    \hline
    \textbf{Item Description} & \textbf{Qty} & \textbf{Unit Price} & \textbf{Total} \\
    \hline
    \endfirsthead
    \hline
    \textbf{Item Description} & \textbf{Qty} & \textbf{Unit Price} & \textbf{Total} \\
    \hline
    \endhead
{% for it in items %}
    {{ it.description }} & {{ it.quantity }} & \currencysymbol{{ it.unit_price_rounded }} & \currencysymbol{{ it.line_total_rounded }} \\
{% endfor %}
    \hline
\end{longtable}
"""

    totals_template_str = r"""
\begin{flushright}
    \begin{tabular}{r l}
        \textbf{Subtotal:} & \currencysymbol{{ subtotal }} \\
{% if gift_wrap_amount > 0 %}
        \textbf{Gift Wrap:} & \currencysymbol{{ gift_wrap_amount }} \\
{% endif %}
{% if discount_amount > 0 %}
        \textbf{Discount:} & -\currencysymbol{{ discount_amount }} \\
{% endif %}
{% if wallet_applied_amount > 0 %}
        \textbf{Wallet Applied:} & -\currencysymbol{{ wallet_applied_amount }} \\
{% endif %}
        \hline
        \textbf{Total:} & \currencysymbol{{ total_cost }} \\
    \end{tabular}
\end{flushright}
"""

    # --- 3. Prepare Data Context ---

    def escape_latex(text):
        if text is None:
            return ''
        return str(text).replace('&', r'\&').replace('%', r'\%').replace('$', r'\$') \
                        .replace('#', r'\#').replace('_', r'\_').replace('{', r'\{') \
                        .replace('}', r'\}').replace('~', r'\textasciitilde{}') \
                        .replace('^', r'\textasciicircum{}').replace('\\', r'\textbackslash{}')

    items = []
    for oi in order.items.select_related('variant__product', 'product'):
        if oi.variant and oi.variant.product:
            desc = f"{oi.variant.product.name}"
            if oi.variant.name and oi.variant.name != oi.variant.product.name:
                desc += f" - {oi.variant.name}"
            if oi.variant.sku:
                desc += f" (SKU: {oi.variant.sku})"
        elif oi.product:
            desc = oi.product.name
            if oi.product.sku:
                desc += f" (SKU: {oi.product.sku})"
        else:
            desc = f"Item #{oi.id}"
        
        items.append({
            "description": escape_latex(desc),
            "quantity": int(oi.quantity),
            "unit_price": float(oi.unit_price),
            "line_total": float(oi.line_total),
        })

    address_parts = [order.address_line1]
    if order.address_line2:
        address_parts.append(order.address_line2)
    address_parts.extend([order.city, order.state, order.postal_code, order.country])
    invoice_address = ", ".join(filter(None, address_parts))
    
    company = {
        "name": escape_latex(getattr(settings, 'COMPANY_NAME', 'SPACE4U')),
        "address": escape_latex(getattr(settings, 'COMPANY_ADDRESS', 'Your Otaku Haven')),
        "city": escape_latex(getattr(settings, 'COMPANY_CITY', '')),
        "state": escape_latex(getattr(settings, 'COMPANY_STATE', '')),
        "zip": escape_latex(getattr(settings, 'COMPANY_ZIP', '')),
        "email": escape_latex(getattr(settings, 'COMPANY_EMAIL', 'support@space4u.in')),
        "phone": escape_latex(getattr(settings, 'COMPANY_PHONE', '+91 73554 80402')),
        "footer": escape_latex(getattr(settings, 'COMPANY_FOOTER', 'Thank you for your purchase!')),
    }
    
    currency_symbol = "₹" if order.currency == "INR" else "$"
    currency_symbol_latex = r"\textrupee" if currency_symbol == "₹" else r"\$"

    def round_value(val):
        return round(float(val), 2)

    for item in items:
        item['unit_price_rounded'] = round_value(item['unit_price'])
        item['line_total_rounded'] = round_value(item['line_total'])

    context = {
        "company": company,
        "bill_to": escape_latex(order.full_name),
        "invoice_address": escape_latex(invoice_address),
        "invoice_date": str(order.created_at.date()),
        "invoice_id": order.order_number or str(order.id),
        "invoice_status": escape_latex(order.get_status_display()),
        "payment_method": escape_latex(order.get_payment_method_display()),
        "items": items,
        "subtotal": round_value(order.subtotal),
        "gift_wrap_amount": round_value(order.gift_wrap_amount) if order.gift_wrap else 0.0,
        "discount_amount": round_value(order.discount_amount),
        "wallet_applied_amount": round_value(order.wallet_applied_amount),
        "total_cost": round_value(order.total_cost),
        "currency_symbol_latex": currency_symbol_latex,
    }

    # --- 4. Render Sub-templates and Replace Placeholders ---

    # Set Jinja2 autoescape to False because we are manually escaping for LaTeX
    env.autoescape = False
    
    # Render parts
    rendered_commands = env.from_string(commands_template_str).render(context)
    rendered_items = env.from_string(items_template_str).render(context)
    rendered_totals = env.from_string(totals_template_str).render(context)

    # Inject into main template
    final_latex = template_str.replace('__COMMANDS__', rendered_commands)
    final_latex = final_latex.replace('__ITEMS_TABLE__', rendered_items)
    final_latex = final_latex.replace('__TOTALS_SECTION__', rendered_totals)

    # Finally, render the main template to insert the currency symbol
    final_latex = env.from_string(final_latex).render(context)
    
    return final_latex


def generate_invoice_pdf(order: Order) -> bytes:
    """
    Generates a PDF invoice for an order by compiling a LaTeX template.
    Returns the PDF content as bytes.
    Uses XeLaTeX for Unicode support (rupee symbol, etc.).
    Raises Exception if xelatex command fails or is not found.
    """
    latex_source = render_invoice_latex(order)

    with tempfile.TemporaryDirectory() as temp_dir:
        tex_filename = f"invoice_{order.id}.tex"
        tex_filepath = os.path.join(temp_dir, tex_filename)
        
        with open(tex_filepath, 'w', encoding='utf-8') as f:
            f.write(latex_source)

        try:
            # Run xelatex once. For simple documents like an invoice, a second pass is usually not needed.
            # This should significantly speed up the generation time.
            process = subprocess.run(
                ['xelatex', '-interaction=nonstopmode', '-output-directory', temp_dir, tex_filepath],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log_output = e.stdout + "\\n" + e.stderr if hasattr(e, 'stdout') else ""
            logger.error(f"xelatex failed for order {order.id}. Is xelatex installed and in PATH? Error: {e} Log: {log_output}")
            raise Exception("PDF generation failed: xelatex command error.") from e

        pdf_filename = f"invoice_{order.id}.pdf"
        pdf_filepath = os.path.join(temp_dir, pdf_filename)

        if not os.path.exists(pdf_filepath):
            logger.error(f"PDF file not found after compilation for order {order.id}.")
            raise Exception("PDF file not created.")
        
        with open(pdf_filepath, 'rb') as f:
            pdf_content = f.read()
        
        return pdf_content

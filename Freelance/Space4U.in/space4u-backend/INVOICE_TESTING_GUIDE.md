# Invoice Feature Testing Guide

This guide explains how to test the invoice feature in the Space4U backend.

## Overview

The invoice feature provides three endpoints:
1. **LaTeX Source** (`/api/commerce/invoices/tex/<order_id>/`) - Returns raw LaTeX source code (for debugging)
2. **PDF Invoice** (`/api/commerce/invoices/pdf/<order_id>/`) - Returns PDF invoice for authenticated users
3. **Internal PDF Invoice** (`/api/commerce/invoices/internal/<order_id>/`) - Admin-only endpoint for any order

## Prerequisites

### For PDF Generation
The invoice feature uses LaTeX to generate PDFs. You need `pdflatex` installed:

**Windows:**
- Install MiKTeX or TeX Live
- Ensure `pdflatex` is in your PATH

**Linux:**
```bash
sudo apt-get install texlive-latex-base texlive-latex-extra
```

**macOS:**
```bash
brew install --cask mactex
# or for smaller installation:
brew install --cask basictex
```

**Verify installation:**
```bash
pdflatex --version
```

## Running Automated Tests

### Run All Invoice Tests
```bash
cd space4u-backend
.venv/Scripts/activate  # Windows
# or
source .venv/bin/activate  # Linux/macOS

python manage.py test commerce.tests.CommerceFeatureTests.test_invoice_pdf_generation
python manage.py test commerce.test_security.OrderAuthorizationTests.test_user_can_access_own_invoice
python manage.py test commerce.test_security.OrderAuthorizationTests.test_user_cannot_access_other_user_invoice
python manage.py test commerce.test_security.PaymentAuthenticationTests.test_invoice_access_requires_auth
```

### Run All Commerce Tests (includes invoice tests)
```bash
python manage.py test commerce
```

### Run with Verbose Output
```bash
python manage.py test commerce -v 2
```

## Manual Testing via API

### Step 1: Set Up Test Environment

1. **Start the Django server:**
```bash
cd space4u-backend
.venv/Scripts/activate
python manage.py runserver
```

2. **Create a test user and get JWT token:**
```bash
# Using Django shell or API
python manage.py shell
```

Or use the API endpoint:
```bash
POST /api/auth/jwt/create/
{
  "username": "testuser",
  "password": "testpass123"
}
```

### Step 2: Create an Order

Before testing invoices, you need a completed order:

1. **Add items to cart:**
```bash
POST /api/commerce/cart/
Authorization: Bearer <your_jwt_token>
{
  "variant_id": <variant_id>,
  "quantity": 2
}
```

2. **Create preliminary order:**
```bash
POST /api/commerce/orders/create/
Authorization: Bearer <your_jwt_token>
{
  "full_name": "Test User",
  "address_line1": "123 Test Street",
  "city": "Test City",
  "postal_code": "12345",
  "email": "test@example.com"
}
```

3. **Complete payment (COD or Razorpay):**
```bash
POST /api/commerce/orders/create-payment/
Authorization: Bearer <your_jwt_token>
{
  "order_id": <order_id>,
  "payment_method": "COD"
}
```

### Step 3: Test Invoice Endpoints

#### Test 1: Get LaTeX Source (Debug Endpoint)
```bash
GET /api/commerce/invoices/tex/<order_id>/
Authorization: Bearer <your_jwt_token>
```

**Expected Response:**
- Status: 200 OK
- Body: `{"latex": "\\documentclass[12pt]{article}..."}`

**Use Cases:**
- Debug LaTeX template issues
- Verify invoice data structure
- Test without PDF generation

#### Test 2: Get PDF Invoice (User Endpoint)
```bash
GET /api/commerce/invoices/pdf/<order_id>/
Authorization: Bearer <your_jwt_token>
```

**Expected Response:**
- Status: 200 OK
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="invoice_<order_id>.pdf"`
- Body: PDF binary content

**Test Scenarios:**

1. **Valid Order (Own Order):**
   - Should return PDF successfully
   - PDF should contain order details, items, totals

2. **Invalid Order ID:**
   - Should return 404 Not Found

3. **Other User's Order:**
   - Should return 403 Forbidden or 404 Not Found

4. **Unauthenticated Request:**
   - Should return 401 Unauthorized

#### Test 3: Get Internal PDF Invoice (Admin Only)
```bash
GET /api/commerce/invoices/internal/<order_id>/
Authorization: Bearer <admin_jwt_token>
```

**Expected Response:**
- Status: 200 OK (if admin)
- Status: 403 Forbidden (if regular user)
- PDF content

**Use Cases:**
- Staff can generate invoices for any order
- Useful for offline orders or customer support

## Testing with cURL

### Example: Get PDF Invoice
```bash
# Get JWT token first
TOKEN=$(curl -X POST http://localhost:8000/api/auth/jwt/create/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}' \
  | jq -r '.access')

# Get invoice PDF
curl -X GET "http://localhost:8000/api/commerce/invoices/pdf/1/" \
  -H "Authorization: Bearer $TOKEN" \
  -o invoice_1.pdf
```

### Example: Get LaTeX Source
```bash
curl -X GET "http://localhost:8000/api/commerce/invoices/tex/1/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  | jq '.latex' > invoice.tex
```

## Testing with Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Login and get token
login_response = requests.post(
    f"{BASE_URL}/api/auth/jwt/create/",
    json={"username": "testuser", "password": "testpass123"}
)
token = login_response.json()["access"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Create order (simplified - you'd need cart items first)
# ... create order steps ...

# 3. Get PDF invoice
order_id = 1  # Replace with actual order ID
pdf_response = requests.get(
    f"{BASE_URL}/api/commerce/invoices/pdf/{order_id}/",
    headers=headers
)

if pdf_response.status_code == 200:
    with open(f"invoice_{order_id}.pdf", "wb") as f:
        f.write(pdf_response.content)
    print(f"Invoice saved as invoice_{order_id}.pdf")
else:
    print(f"Error: {pdf_response.status_code} - {pdf_response.text}")

# 4. Get LaTeX source
tex_response = requests.get(
    f"{BASE_URL}/api/commerce/invoices/tex/{order_id}/",
    headers=headers
)
if tex_response.status_code == 200:
    print(tex_response.json()["latex"])
```

## Testing Scenarios Checklist

### Authentication & Authorization
- [ ] Unauthenticated request returns 401
- [ ] User can access their own invoice
- [ ] User cannot access another user's invoice
- [ ] Admin can access any invoice via internal endpoint
- [ ] Regular user cannot access internal endpoint

### Invoice Content
- [ ] PDF contains company information
- [ ] PDF contains customer billing address
- [ ] PDF contains order items with correct quantities
- [ ] PDF contains correct pricing (subtotal, discounts, total)
- [ ] PDF contains order status and payment method
- [ ] PDF contains invoice date and ID
- [ ] Currency symbol is correct (₹ for INR, $ for USD)

### Edge Cases
- [ ] Order with gift wrap shows gift wrap amount
- [ ] Order with discount shows discount amount
- [ ] Order with wallet payment shows wallet applied amount
- [ ] Order with multiple items displays all items
- [ ] Order with variant SKU displays SKU in description
- [ ] Order without variant SKU still displays item

### Error Handling
- [ ] Non-existent order ID returns 404
- [ ] PDF generation failure returns 500 with error message
- [ ] Missing pdflatex returns appropriate error

## Common Issues & Solutions

### Issue: "pdflatex command not found"
**Solution:** Install LaTeX distribution (MiKTeX, TeX Live, or MacTeX)

### Issue: "PDF generation failed"
**Solution:** 
- Check pdflatex is in PATH
- Check LaTeX template syntax
- Review Django logs for detailed error

### Issue: "403 Forbidden" when accessing own invoice
**Solution:** 
- Verify JWT token is valid
- Check order belongs to authenticated user
- Verify order exists

### Issue: PDF is empty or corrupted
**Solution:**
- Test LaTeX source endpoint first to verify template
- Check order has items
- Verify all order fields are populated

## Integration with Frontend

If testing from frontend:

1. **Get invoice download link:**
```javascript
const orderId = 123;
const token = localStorage.getItem('access_token');
const invoiceUrl = `/api/commerce/invoices/pdf/${orderId}/`;

fetch(invoiceUrl, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(response => response.blob())
.then(blob => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `invoice_${orderId}.pdf`;
  a.click();
});
```

## Running Tests in CI/CD

The invoice tests use mocking to avoid requiring pdflatex in CI:

```python
@patch('commerce.views.generate_invoice_pdf')
def test_invoice_pdf_generation(self, mock_generate_pdf):
    mock_generate_pdf.return_value = b'%PDF-1.5\n%%EOF'
    # ... test code ...
```

This allows tests to run without LaTeX installed, but manual testing requires pdflatex.

## Next Steps

1. Run automated tests: `python manage.py test commerce`
2. Create a test order via API
3. Test PDF generation endpoint
4. Verify PDF content manually
5. Test authorization scenarios
6. Test edge cases (discounts, gift wrap, etc.)


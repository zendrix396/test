#!/usr/bin/env python
import re

# Fix products/test_comprehensive.py
with open('products/test_comprehensive.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove all stock= parameters
content = re.sub(r',?\s*stock=\d+', '', content)

# Fix is_primary to remove it
content = re.sub(r',?\s*is_primary=(True|False)', '', content)

# Fix TrendingDeal.DealType
content = content.replace('TrendingDeal.DealType.PRODUCT', 'TrendingDeal.DealType.PERCENT_OFF')
content = content.replace('TrendingDeal.DealType.CATEGORY', 'TrendingDeal.DealType.PERCENT_OFF')

# Fix search results - change response.data['results'] to response.data
content = content.replace("response.data['results']", 'response.data')

with open('products/test_comprehensive.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed test_comprehensive.py!')


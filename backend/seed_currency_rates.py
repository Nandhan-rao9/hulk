"""
Seed currency conversion rates for travel expense data.
Run with: python manage.py shell < seed_currency_rates.py
"""
from apps.core.models import CurrencyConversionRate
from datetime import date

rates = [
    {'currency_code': 'USD', 'rate_to_inr': 83.25, 'effective_date': date(2024, 1, 1), 'source': 'RBI'},
    {'currency_code': 'EUR', 'rate_to_inr': 91.50, 'effective_date': date(2024, 1, 1), 'source': 'RBI'},
    {'currency_code': 'GBP', 'rate_to_inr': 105.75, 'effective_date': date(2024, 1, 1), 'source': 'RBI'},
    {'currency_code': 'SGD', 'rate_to_inr': 62.40, 'effective_date': date(2024, 1, 1), 'source': 'RBI'},
    {'currency_code': 'AED', 'rate_to_inr': 22.65, 'effective_date': date(2024, 1, 1), 'source': 'RBI'},
    {'currency_code': 'JPY', 'rate_to_inr': 0.57, 'effective_date': date(2024, 1, 1), 'source': 'RBI'},
    {'currency_code': 'AUD', 'rate_to_inr': 55.20, 'effective_date': date(2024, 1, 1), 'source': 'RBI'},
    {'currency_code': 'CAD', 'rate_to_inr': 61.85, 'effective_date': date(2024, 1, 1), 'source': 'RBI'},
]

for rate_data in rates:
    CurrencyConversionRate.objects.update_or_create(
        currency_code=rate_data['currency_code'],
        defaults=rate_data
    )

print(f"✅ Seeded {len(rates)} currency conversion rates")

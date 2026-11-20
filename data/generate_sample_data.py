#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate sample sales data and company compliance policy document.

This script creates:
1. A CSV file with 1500 rows of synthetic sales transactions
2. A PDF document containing the company compliance policy
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Try to import fpdf2, provide alternative if not available
try:
    from fpdf import FPDF
except ImportError:
    print("Installing fpdf2...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'fpdf2'])
    from fpdf import FPDF


# Configuration
NUM_ROWS = 1500
START_DATE = datetime(2024, 1, 1)

# Regions and categories
REGIONS = ['North America', 'Europe', 'Asia Pacific', 'Latin America']
CATEGORIES = {'Electronics': ['Smartphone', 'Laptop', 'Tablet', 'Wearable', 'Gaming Console']}
PRODUCT_NAMES = [
    'Smartphone Pro', 'Phone X', 'Ultra Phone', 'Budget Phone',
    'Laptop Ultra', 'Business Notebook', 'Student Laptop', 'Gaming PC',
    'Pro Tablet', 'Mini Pad', 'Tablet Air',
    'Smart Watch', 'Fitness Tracker', 'VR Headset',
    'Gaming Console X', 'Console Pro', 'Portable Console'
]
CUST_SEGMENTS = ['Consumer', 'Business', 'Enterprise', 'Government']

# Compliance policy settings
COMPANY_NAME = "Acme Corporation"
POLICY_TITLE = "Discount and Profit Margin Policy"
DISCOUNT_CAPS = {
    'North America': 20,
    'Europe': 15,
    'Asia Pacific': 25,
    'Latin America': 30
}
MIN_PROFIT_MARGIN = 18  # percentage


def generate_transactions():
    """Generate synthetic sales transactions."""
    transactions = []
    transaction_id = 1

    current_date = START_DATE

    for i in range(NUM_ROWS):
        # Randomly advance date by 0-365 days with some clustering
        if random.random() < 0.7:
            current_date += timedelta(days=random.randint(0, 30))

        region = random.choice(REGIONS)
        category = random.choice(list(CATEGORIES.keys()))
        product_name = random.choice(CATEGORIES[category])
        customer_segment = random.choice(CUST_SEGMENTS)

        # Generate base unit price based on category/product
        base_prices = {
            'Smartphone': (500, 1200),
            'Laptop': (400, 2500),
            'Tablet': (200, 800),
            'Wearable': (100, 400),
            'Gaming Console': (300, 600)
        }

        price_range = base_prices.get(product_name, (100, 500))
        unit_price = random.uniform(*price_range)

        # Generate cost with reasonable margins
        cost = unit_price * random.uniform(0.4, 0.7)

        # Apply discount with regional cap compliance
        raw_discount_pct = random.uniform(5, DISCOUNT_CAPS[region] + 5)

        # For some rows, intentionally exceed the cap to simulate non-compliant data
        if random.random() < 0.1:  # 10% chance of violation
            raw_discount_pct = random.uniform(DISCOUNT_CAPS[region], DISCOUNT_CAPS[region] + 15)

        discount_pct = round(min(raw_discount_pct, DISCOUNT_CAPS[region]), 2)

        # Calculate final values
        revenue = round(unit_price * (1 - discount_pct/100), 2)
        profit = revenue - cost

        # Ensure some transactions have low margins (below minimum) for testing
        if random.random() < 0.08:  # 8% chance of margin violation
            profit = round(profit * random.uniform(0, MIN_PROFIT_MARGIN/100), 2)

        transactions.append({
            'transaction_id': f'TXN-{transaction_id:06d}',
            'date': current_date.strftime('%Y-%m-%d'),
            'quarter': f"Q{int(current_date.month / 3)}",
            'region': region,
            'category': category,
            'product_name': product_name,
            'customer_segment': customer_segment,
            'units_sold': random.randint(1, 50),
            'unit_price': round(unit_price, 2),
            'discount_pct': discount_pct,
            'revenue': revenue,
            'cost': round(cost, 2),
            'profit': profit
        })

        transaction_id += 1

    return transactions


def create_pdf_report(transactions):
    """Create PDF compliance policy document."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 5, COMPANY_NAME, ln=1, align='C')
    pdf.ln(5)

    # Add policy title
    pdf.set_font("Arial", 'B', 14)
    pdf.multi_cell(0, 8, POLICY_TITLE, align='C')
    pdf.ln(5)

    # Add compliance rules
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Compliance Rules:", ln=1)

    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 6,
        f"""
DISCOUNT CAPS BY REGION:
- North America: {DISCOUNT_CAPS['North America']}% maximum discount
- Europe: {DISCOUNT_CAPS['Europe']}% maximum discount
- Asia Pacific: {DISCOUNT_CAPS['Asia Pacific']}% maximum discount
- Latin America: {DISCOUNT_CAPS['Latin America']}% maximum discount

MINIMUM PROFIT MARGIN REQUIREMENT:
- All transactions must maintain at least {MIN_PROFIT_MARGIN}% profit margin

This policy ensures fair pricing across all regions and maintains profitability.
Violations of these rules may result in disciplinary action.
        """)

    # Add summary statistics
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Data Summary ({len(transactions)} transactions):", ln=1)

    total_revenue = sum(t['revenue'] for t in transactions)
    total_profit = sum(t['profit'] for t in transactions)
    avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    pdf.set_font("Arial", '', 11)
    stats_text = f"""
- Total Transactions: {len(transactions)}
- Total Revenue: ${total_revenue:,.2f}
- Total Profit: ${total_profit:,.2f}
- Average Profit Margin: {avg_margin:.2f}%
- Date Range: {transactions[0]['date']} to {transactions[-1]['date']}
    """
    pdf.multi_cell(0, 6, stats_text)

    # Add footer
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, "Generated by autonomous-data-analyst - Compliance Monitoring System", align='C')

    return pdf.output('data/company_compliance_policy.pdf')


def main():
    """Main execution function."""
    data_dir = Path(__file__).parent

    print(f"Generating {NUM_ROWS} sales transactions...")
    transactions = generate_transactions()

    csv_path = data_dir / 'sales_transactions.csv'
    print(f"Writing to {csv_path}...")

    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = [
            'transaction_id', 'date', 'quarter', 'region', 'category',
            'product_name', 'customer_segment', 'units_sold', 'unit_price',
            'discount_pct', 'revenue', 'cost', 'profit'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)

    print(f"Created CSV with {NUM_ROWS} rows")

    # Generate PDF report
    pdf_path = data_dir / 'company_compliance_policy.pdf'
    print(f"Creating compliance policy PDF at {pdf_path}...")
    create_pdf_report(transactions)
    print("PDF created successfully!")

    print("\nGeneration complete!")
    print(f"  - CSV: {csv_path}")
    print(f"  - PDF: {pdf_path}")


if __name__ == "__main__":
    main()

import os
import pandas as pd
import quantstats as qs
from weasyprint import HTML
import json
import io

import matplotlib.pyplot as plt

# ✅ Fix 3: Force Arial fallback (removes warnings on Linux)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Liberation Sans', 'DejaVu Sans', 'Arial', 'sans-serif']

REPORT_DIR = "app/reports" # Aligning with existing paths in backtest_engine.py
os.makedirs(REPORT_DIR, exist_ok=True)

def generate_report(task_id: str, returns_json: str, symbol: str, timeframe: str, format: str = "pdf"):
    """
    Backtest returns থেকে HTML বা PDF রিপোর্ট তৈরি করে।
    """
    try:
        # ১. JSON থেকে Pandas Series এ কনভার্ট করা
        returns = pd.read_json(io.StringIO(returns_json), typ='series')
        
        # Ensure index is datetime
        returns.index = pd.to_datetime(returns.index)
        
        # We need to localize/delocalize if there are timezone issues
        if returns.index.tz is not None:
             returns.index = returns.index.tz_localize(None)

        # ২. সেইফ সিম্বল (File system friendly)
        # ✅ Fix 1: Replace slash with underscore
        safe_symbol = symbol.replace("/", "_")
        
        # রিপোর্ট ফাইলের নাম জেনারেট করা
        report_filename = f"report_{safe_symbol}_{timeframe}_{task_id}.html"
        html_path = os.path.join(REPORT_DIR, report_filename)
        
        # ✅ Fix 2: Ensure directory exists
        os.makedirs(os.path.dirname(html_path), exist_ok=True)

        # QuantStats এর ডিফল্ট টাইটেল সেট করা
        qs.reports.html(returns, output=html_path, title=f"Backtest Report - {symbol} ({timeframe})", download_filename=html_path)

        if format == "html":
            return html_path

        # ৩. PDF এ কনভার্ট করা (WeasyPrint ব্যবহার করে)
        # ৩. PDF এ কনভার্ট করা (WeasyPrint ব্যবহার করে)
        if format == "pdf":
            pdf_path = os.path.join(REPORT_DIR, f"report_{safe_symbol}_{timeframe}_{task_id}.pdf")
            HTML(filename=html_path).write_pdf(pdf_path)
            return pdf_path
            
    except Exception as e:
        print(f"❌ Report Generation Error: {e}")
        return None

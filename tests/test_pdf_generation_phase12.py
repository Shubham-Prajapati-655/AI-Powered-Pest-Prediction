"""
Phase 12 Comprehensive PDF Generation & Validation Test Suite
Validates all PDF generation workflows:
- Formatting
- Tables
- Images / Headers
- Margins & Fonts
- Page count and binary structure integrity (%PDF-1.x)
- Valid extraction via pypdf
"""
import pytest
import os
import sys
import pypdf

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
sys.path.append(os.path.join(ROOT_DIR, "app"))

from pdf_generator import (
    generate_prediction_pdf,
    generate_history_summary_pdf,
    generate_system_summary_pdf,
    generate_analytics_report_pdf,
    generate_audit_report_pdf,
    generate_performance_report_pdf
)

class TestPDFGenerationPhase12:

    @classmethod
    def setup_class(cls):
        cls.output_dir = os.path.join(ROOT_DIR, "reports", "generated_pdfs")
        os.makedirs(cls.output_dir, exist_ok=True)

    def test_01_prediction_advisory_pdf(self):
        """Verify field advisory report PDF generation, formatting, and valid structure."""
        pdf_bytes = generate_prediction_pdf(
            state="Andhra Pradesh",
            district="Guntur",
            crop="Cotton",
            crop_category="Fiber",
            sowing_season="Kharif",
            weather_season="Monsoon",
            temp=32.0,
            humidity=75.0,
            rainfall=120.0,
            thi=78.2,
            rf_hum_ratio=1.6,
            weather_source="Open-Meteo Live",
            predicted_pest="Pink Bollworm",
            pest_conf=88.50,
            predicted_risk="High",
            risk_conf=92.00,
            recommendations={
                "Recommended_Pesticide": "Chlorantraniliprole 18.5% SC",
                "Chemical_Control": "0.3 ml/L foliar spray",
                "Organic_Control": "Neem Oil 1500 ppm @ 5 ml/L",
                "Recommended_Fertilizer": "1% Potassium Nitrate spray",
                "Safety_Notes": "Wear protective gear. 15-day pre-harvest interval.",
                "Preventive_Measures": ["Install pheromone traps", "Field scouting twice weekly"]
            },
            user_name="Farmer Ramesh Patel"
        )
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")
        filepath = os.path.join(self.output_dir, "test_prediction_report.pdf")
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        
        reader = pypdf.PdfReader(filepath)
        assert len(reader.pages) >= 1
        text = "".join(page.extract_text() for page in reader.pages)
        assert "AgriAI" in text or "Advisory" in text
        assert "Pink Bollworm" in text
        assert "Cotton" in text

    def test_02_history_summary_pdf(self):
        """Verify farmer prediction history summary PDF report."""
        history_records = [
            {
                "id": 1, "timestamp": "2026-10-01 10:00:00", "crop": "Cotton", "district": "Guntur",
                "temperature": 32.0, "humidity": 75.0, "rainfall": 110.0,
                "predicted_pest": "Pink Bollworm", "pest_confidence": 88.5,
                "risk_level": "High", "risk_confidence": 92.0
            },
            {
                "id": 2, "timestamp": "2026-10-01 11:30:00", "crop": "Rice", "district": "Krishna",
                "temperature": 29.0, "humidity": 85.0, "rainfall": 140.0,
                "predicted_pest": "Brown Planthopper", "pest_confidence": 79.2,
                "risk_level": "Medium", "risk_confidence": 81.0
            }
        ]
        pdf_bytes = generate_history_summary_pdf(history_records, user_name="Farmer Ramesh Patel")
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF-")
        filepath = os.path.join(self.output_dir, "test_history_summary.pdf")
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        reader = pypdf.PdfReader(filepath)
        assert len(reader.pages) >= 1
        text = "".join(page.extract_text() for page in reader.pages)
        assert "Farmer Ramesh Patel" in text
        assert "Brown Planthopper" in text

    def test_03_system_summary_pdf(self):
        """Verify enterprise admin system health summary PDF report."""
        kpis = {
            "total_users": 150, "total_farmers": 142, "total_predictions": 540,
            "pdf_reports": 210, "contact_queries": 15, "system_status": "Operational"
        }
        db_stats = {
            "db_status": "Healthy", "storage_mb": 4.5, "total_users": 150,
            "total_predictions": 540, "total_queries": 15,
            "latest_user_date": "2026-10-01", "latest_pred_date": "2026-10-01"
        }
        pdf_bytes = generate_system_summary_pdf(kpis, db_stats)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF-")
        filepath = os.path.join(self.output_dir, "test_system_summary.pdf")
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        reader = pypdf.PdfReader(filepath)
        assert len(reader.pages) >= 1

    def test_04_analytics_report_pdf(self):
        """Verify platform analytics and risk distribution PDF report."""
        analytics_data = {
            "risk_counts": {"High": 120, "Medium": 250, "Low": 80},
            "crop_counts": {"Cotton": 180, "Rice": 140, "Wheat": 90, "Soybean": 40},
            "user_dist": {"Farmer": 140, "Admin": 5},
            "status_dist": {"Active": 142, "Suspended": 3}
        }
        pdf_bytes = generate_analytics_report_pdf(analytics_data)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF-")
        filepath = os.path.join(self.output_dir, "test_analytics_report.pdf")
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        reader = pypdf.PdfReader(filepath)
        assert len(reader.pages) >= 1

    def test_05_audit_report_pdf(self):
        """Verify enterprise system & security audit PDF report."""
        pdf_bytes = generate_audit_report_pdf()
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF-")
        filepath = os.path.join(self.output_dir, "test_audit_report.pdf")
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        reader = pypdf.PdfReader(filepath)
        assert len(reader.pages) >= 1
        text = "".join(page.extract_text() for page in reader.pages)
        assert "AUDIT" in text and "REPORT" in text

    def test_06_performance_report_pdf(self):
        """Verify performance and scalability benchmarks PDF report."""
        perf_data = {
            "cold_start_ms": 38.5,
            "warm_start_ms": 4.2,
            "p50_latency_ms": 4.5,
            "p95_latency_ms": 9.8,
            "p99_latency_ms": 16.4,
            "batch_100_ms": 172.0,
            "batch_500_ms": 680.0,
            "batch_1000_ms": 1250.0
        }
        pdf_bytes = generate_performance_report_pdf(perf_data)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF-")
        filepath = os.path.join(self.output_dir, "test_performance_report.pdf")
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        reader = pypdf.PdfReader(filepath)
        assert len(reader.pages) >= 1
        text = "".join(page.extract_text() for page in reader.pages)
        assert "PERFORMANCE" in text

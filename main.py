"""
Entry point for the Healthcare AI Billing Anomaly Detection System.
Run with: uvicorn main:app --reload
"""
from app.main import app

__all__ = ["app"]
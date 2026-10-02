# OCR Receipt Processing & Inventory System

This module provides an OCR-based receipt processing pipeline for the Zawolf AI E-commerce system.

It extracts product information from receipt images, converts OCR results into structured product data, and automatically updates inventory records in PostgreSQL.

## Pipeline

```text
Receipt Image
      ↓
Image Preprocessing
      ↓
EasyOCR
      ↓
OCR JSON Output
      ↓
Receipt Parser
      ↓
Structured Product Data
      ↓
Inventory Service
      ↓
PostgreSQL
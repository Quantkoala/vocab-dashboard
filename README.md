# Vocabulary Dashboard

## Overview
A Streamlit app to help you practice vocabulary clusters daily, track your study time, exercises completed, and weekly scores, backed by a Google Sheets word list.

## Setup
1. Install dependencies:
```
pip install -r requirements.txt
```
2. Run the app:
```
streamlit run vocab_dashboard.py
```

## Files
- **vocab_dashboard.py**: Main Streamlit application
- **words_local.csv**: Cached copy of your Google Sheet (auto-generated)
- **tracking.csv**: Your exercise logs (auto-generated)
- **requirements.txt**: Python dependencies

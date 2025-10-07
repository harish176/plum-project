# Medical Bill Analyzer - Clean Project Structure

## Project Directory Structure

```
backend/
├── config/                      # Configuration files
│   ├── __init__.py
│   └── settings.py              # Application settings and environment variables
│
├── models/                      # Data models and schemas
│   ├── __init__.py
│   ├── data_models.py           # Core data structures (AmountType, etc.)
│   └── request_models.py        # API request/response models
│
├── services/                    # Core business logic
│   ├── __init__.py
│   ├── classification_service.py # Amount classification and item name extraction
│   ├── normalization_service.py # Amount normalization and cleaning
│   ├── ocr_service.py           # OCR text extraction from images
│   └── pipeline_service.py     # Main processing pipeline orchestration
│
├── utils/                       # Utility functions
│   ├── __init__.py
│   ├── currency_utils.py        # Currency detection and handling
│   ├── text_utils.py           # Text processing utilities
│   └── validation_utils.py     # Input validation helpers
│
├── tests/                       # Unit tests
│   ├── test_classification.py   # Classification service tests
│   ├── test_normalization.py   # Normalization service tests
│   ├── test_ocr.py             # OCR service tests
│   └── test_pipeline.py        # Pipeline integration tests
│
├── main.py                      # FastAPI application entry point
├── requirements.txt            # Python dependencies
├── start_server.bat           # Windows server startup script
├── .env.example               # Environment variables template
├── .env                       # Environment variables (local)
├── README.md                  # Project documentation
├── API_DOCUMENTATION.md       # API endpoint documentation
├── PROJECT_STRUCTURE.md       # This file
├── test_api.py                # API endpoint testing
├── test_images.py             # Image processing testing
└── test_medical_bill.png      # Sample test image

```

## Quick Start Commands

### Start the Server
```bash
# Method 1: Using batch file
start_server.bat

# Method 2: Direct command
python -m uvicorn main:app --reload --host localhost --port 8000
```

### API Endpoints
- **Documentation:** http://localhost:8000/docs
- **Text Analysis:** POST http://localhost:8000/extract-amounts-text
- **Image Analysis:** POST http://localhost:8000/extract-amounts-image

### Testing
```bash
# Test API endpoints
python test_api.py

# Test image processing
python test_images.py

# Run unit tests
python -m pytest tests/
```

## Cleanup Complete

### Removed Files:
- All debug_*.py files (9 files)
- Temporary test_*.py files (13 files)
- sample_data/ directory
- sample_images/ directory
- __pycache__/ directories
- setup.py, setup.bat, start_service.bat
- demo.py, create_test_images.py

### Kept Essential Files:
- Core application files (main.py, services/, models/, etc.)
- Configuration and utilities
- Documentation files
- Essential test files (test_api.py, test_images.py)
- Unit test structure (tests/ directory)
- Dependencies and environment setup

## Project Status: Production Ready!
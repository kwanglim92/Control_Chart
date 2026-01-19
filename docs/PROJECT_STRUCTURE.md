# Project Structure Documentation

This document outlines the directory structure and organization of the Control Chart application.

## Directory Layout

```
Control_Chart/
├── app.py                   # Main Application Entry Point
├── requirements.txt         # Python Dependencies
├── README.md                # General Project Documentation
├── CHANGELOG.md             # Version History and Changes
├── .gitignore               # Git Ignore Rules
│
├── config/                  # Configuration Files
│   ├── __init__.py
│   └── equipment_config.py  # Equipment Options and Helper Functions
│
├── modules/                 # Core Business Logic & Utilities
│   ├── __init__.py
│   ├── auth.py              # Authentication Logic
│   ├── database.py          # Database Interactions (SQLite)
│   ├── utils.py             # General Utility Functions
│   ├── charts.py            # Plotly Chart Generation
│   ├── spec_analysis.py     # Cpk & Spec Analysis Logic
│   ├── equipment_comparison.py # Equipment Comparison Logic
│   ├── equipment_tab_renderer.py # Equipment Tab Rendering Logic
│   ├── configuration_analysis.py # Configuration Analysis Logic
│   ├── monthly_shipment.py  # Monthly Shipment Analysis Logic
│   └── approval_utils.py    # Approval Queue Utilities
│
├── tabs/                    # UI Components (Streamlit Tabs)
│   ├── __init__.py
│   ├── guide_tab.py         # User Guide Tab
│   ├── data_upload_tab.py   # Data Upload Tab
│   ├── equipment_explorer_tab.py # Equipment Explorer Tab
│   ├── quality_analysis_tab.py   # Quality Analysis Tab
│   ├── approval_queue_tab.py     # Approval Queue Tab
│   ├── monthly_dashboard_tab.py  # Monthly Dashboard Tab
│   └── data_explorer_tab.py      # Data Explorer Tab
│
├── data/                    # Data Storage
│   ├── control_chart.db     # SQLite Database File
│   ├── data.xlsx            # Source Data File
│   └── samples/             # Sample Data Files
│       └── Industrial Check List v3.21.1.xlsx
│
├── tests/                   # Test Suite
│   ├── __init__.py
│   ├── test_extraction.py
│   ├── test_monthly_chart.py
│   └── analyze_last.py
│
├── deployment/              # Deployment Configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .dockerignore
│   ├── run.bat
│   └── .devcontainer/
│
├── docs/                    # Documentation
│   ├── AUTO_LOAD_GUIDE.md
│   └── PROJECT_STRUCTURE.md # This File
│
└── archive/                 # Legacy & Backup Files
    ├── app_backup.py
    ├── app_new.py
    └── upload_tab.py
```

## Key Modules Description

### `app.py`
The main entry point of the Streamlit application. It handles:
- Page configuration
- Session state initialization
- Main navigation (Sidebar/Tabs)
- Integration of all tabs

### `modules/`
Contains reusable business logic, separated from UI code.
- **`database.py`**: Handles all SQLite database operations (CRUD).
- **`charts.py`**: Contains Plotly code for generating Control Charts.
- **`spec_analysis.py`**: Calculates Cpk, Cp, and other quality metrics.
- **`auth.py`**: Manages admin authentication.

### `tabs/`
Contains the rendering logic for each main tab in the application.
- Each file typically exports a `render_<tab_name>_tab()` function.
- These functions are called by `app.py`.

### `config/`
- **`equipment_config.py`**: Centralizes equipment options and configuration dictionaries.

### `data/`
- Stores the SQLite database and any Excel files used for data loading.
- **Note**: `control_chart.db` is the source of truth for the application.

### `deployment/`
- Contains files necessary for Dockerizing and deploying the application.

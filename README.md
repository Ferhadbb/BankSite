# MyBank - Simple Banking Application

This is a simple web-based banking application built with Flask (Python) for the backend and HTML/CSS/JavaScript for the frontend.

## Features

*   User Registration and Login
*   Account Dashboard
*   View Account Balance
*   Deposit and Withdraw Funds
*   View Transaction History
*   Issue New Debit/Credit Cards (Simulated)
*   Basic Interest Calculation (Simulated)

## Project Structure

```
New Project/
├── backend/
│   ├── app.py             # Main Flask application, routes, and logic
│   ├── requirements.txt   # Python dependencies
│   └── bank.db            # SQLite database file (created on first run)
├── frontend/
│   ├── static/
│   │   └── style.css      # CSS styles
│   └── templates/
│       ├── base.html      # Base HTML template
│       ├── login.html     # Login page
│       ├── register.html  # Registration page
│       └── dashboard.html # User dashboard
└── README.md
```

## Setup and Running the Application

1.  **Clone the repository (or create the files as listed above).**

2.  **Navigate to the `backend` directory:**
    ```bash
    cd backend
    ```

3.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    ```
    Activate the virtual environment:
    *   Windows (Git Bash or CMD/PowerShell - might vary slightly):
        ```bash
        venv\Scripts\activate
        ```
    *   macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the Flask application:**
    ```bash
    python app.py
    ```
    The application will start, and it usually creates the `bank.db` SQLite database file automatically in the `backend` directory if it doesn't exist.

6.  **Open your web browser and go to:**
    [http://127.0.0.1:5001/](http://127.0.0.1:5001/)

## Notes

*   The application uses a SQLite database (`bank.db`) which is created in the `backend` folder. You can inspect it using a SQLite browser.
*   User passwords are hashed.
*   Interest calculation and card issuance are simplified for this demo.
*   For production, you would need a more robust database, proper background task scheduling (e.g., Celery or APScheduler for interest), more security measures, error handling, and comprehensive testing. 
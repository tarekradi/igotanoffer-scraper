# iGotAnOffer Session Scraper & Financial Reporter

A high-performance Python utility for **iGotAnOffer** coaches to export, analyze, and visualize coaching session data. This tool automates the retrieval of both historical and upcoming sessions, handles timezone conversions to **PDT/PST**, and generates real-time business insights directly in the console.

## 🚀 Key Features

* **Asynchronous Scraping**: Utilizes `ThreadPoolExecutor` to fetch all pages of history and client emails in parallel.
* **Timezone Conversion**: Automatically converts server-side GMT/UTC timestamps to **America/Los_Angeles** (PDT/PST).
* **Smart Data Tracking**:
    * Calculates **Days Since Session** (or days until upcoming sessions).
    * Identifies **Most Recent Session Date** per unique client across your entire history.
    * Formats revenue with comma separators for thousands (e.g., $3,026.80).
* **Visual Analytics**: Generates ASCII bar charts in the console for **Monthly Revenue Trends** and **Client Session Frequency**.
* **Data Export**: Generates a structured `igotanoffer_sessions_detailed.csv` for use in Excel or Google Sheets.

---

## 🛠 Installation

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/yourusername/igotanoffer-scraper.git](https://github.com/yourusername/igotanoffer-scraper.git)
    cd igotanoffer-scraper
    ```

2.  **Install dependencies**:
    ```bash
    pip install curl_cffi tzdata
    ```

---

## 📖 Usage Guide

Run the script without arguments to see your full history and summary charts, or use filters to isolate specific periods.

### Command Options
| Parameter | Description | Example |
| :--- | :--- | :--- |
| `--month [1-12]` | Filter by month | `--month 3` |
| `--week [num]` | Filter by week number | `--week 13` |
| `--year [year]` | Filter by year | `--year 2025` |
| `--doneonly` | Skip 'Upcoming' sessions | `--doneonly` |
| `--usage` | Show detailed help | `--usage` |

### Examples
* **View March 2026 Earnings**: `python igotanoffer.py --month 3 --year 2026`
* **View All 2025 Completed Work**: `python igotanoffer.py --year 2025 --doneonly`

---

## 📊 Console Output Preview

### Session Table
```text
ID       | D/M/Y        | Time   | Client             | Recent      | Days | Status
-------------------------------------------------------------------------------------
63033    | 26 Mar 2026  | 20:00  | Yusuke K.          | 2026-03-26  | In 1 | Upcoming
62706    | 31 Mar 2026  | 20:00  | Na Y.              | 2026-03-31  | In 6 | Done
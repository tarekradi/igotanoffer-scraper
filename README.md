# iGotAnOffer Session Scraper & Financial Reporter

A high-performance Python utility for iGotAnOffer coaches to export, analyze, and visualize coaching session data. This tool automates the retrieval of both historical and upcoming sessions, handles dynamic timezone conversions, and generates real-time business insights directly in the console.

---

## 🚀 Key Features

- **Asynchronous Scraping:** Utilizes `ThreadPoolExecutor` to fetch all pages of history and client emails in parallel for fast execution.
- **Global Timezone Support:** Automatically converts server-side UTC timestamps to any IANA timezone (e.g., `America/Los_Angeles`, `Europe/London`, `Asia/Dubai`).
- **Smart Data Tracking:**
  - Calculates Days Since Session (or days until upcoming sessions).
  - Identifies the Most Recent Session Date per unique client across your entire history.
  - Formats revenue with comma separators for thousands (e.g., `$3,026.80`).
- **Visual Analytics:** Generates ASCII bar charts in the console for Monthly Revenue Trends and Client Session Frequency.
- **Data Export:** Generates a structured `igotanoffer_sessions_detailed.csv` for use in Excel or Google Sheets.

---

## 📊 Sample Outputs

### Terminal Summary Table

When run, the script provides a clean overview of your filtered sessions:

```
ID       | D/M/Y        | Time   | Client             | Recent      | Days | Status
-------------------------------------------------------------------------------------
63033    | 26 Mar 2026  | 20:00  | Tarek R.           | 2026-03-26  | In 1 | Upcoming
62706    | 24 Mar 2026  | 13:00  | Nadeen R.          | 2026-03-24  | 2    | Done
```

### Monthly Revenue Chart

Visualize your growth over time directly in your terminal:

```
===========================================================================
   MONTHLY REVENUE BAR CHART
===========================================================================
Jan 2026   | $ 1,250.00 | ████████████████
Feb 2026   | $ 2,800.50 | ██████████████████████████████████
Mar 2026   | $ 3,120.25 | ████████████████████████████████████████
```

### CSV Export Structure

The generated `igotanoffer_sessions_detailed.csv` includes the following fields:

| Field | Description |
|---|---|
| `SessionID` | Unique ID for the coaching session |
| `WeekNum` | The week of the year the session occurred |
| `Client` | The shortened name of the student |
| `Amount` | Your earned coach fee |
| `Email` | The student's contact email |
| `MostRecentSession` | The date of the last time you coached this specific student |

---

## 🛠 Installation

### 1. Clone the repository

```bash
git clone https://github.com/tarekradi/igotanoffer-scraper.git
cd igotanoffer-scraper
```

### 2. Install dependencies

```bash
pip install curl_cffi
```

---

## 🔑 Authentication & Setup

To pull data from your account, you must update the `config.py` file located in the root directory.

### 1. Update `config.py`

Open the existing `config.py` file and paste your tokens into the variables:

```python
# config.py
SESSION_TOKEN = "PASTE_YOUR_SESSION_TOKEN_HERE"
CF_CLEARANCE = "PASTE_YOUR_CF_CLEARANCE_HERE"
```

### 2. How to get your cookies

1. Log in to your iGotAnOffer coach dashboard.
2. Open Developer Tools (`F12` or Right-click > Inspect).
3. Go to the **Application** tab (**Storage** in Firefox).
4. Under **Cookies**, select `https://igotanoffer.com`.
5. Copy the values for `__Secure-authjs.session-token` and `cf_clearance`.

---

## 📖 Usage Guide

Run the script with arguments to filter by time or change the display timezone.

### Command Options

| Parameter | Description | Example |
|---|---|---|
| `--month [1-12]` | Filter by month number | `--month 3` |
| `--week [num]` | Filter by week number | `--week 13` |
| `--year [year]` | Filter by year | `--year 2025` |
| `--tz [name]` | Set display timezone (Default: `America/Los_Angeles`) | `--tz Europe/London` |
| `--doneonly` | Skip "Upcoming" sessions | `--doneonly` |
| `--usage` | Display the detailed help guide | `--usage` |

> To see a list of common supported timezones, run: `python igotanoffer.py --tz list`

### Examples

**View March 2026 Earnings (New York Time)**

```bash
python igotanoffer.py --month 3 --year 2026 --tz America/New_York
```

**View All 2025 Completed Work**

```bash
python igotanoffer.py --year 2025 --doneonly
```

---

## 🔐 Security Note

- **Never** share your `config.py` file or push it to a public repository. Your session tokens provide full access to your coach account.
- Ensure `config.py` is ignored by your version control if you push to a public site.
- Use a private repository for added security.

---

## ⭐ Final Note

Developed by **Tarek Radi** for 5-Star Super Coaches.

import csv
import time
import sys
import argparse
import math
from datetime import datetime, timezone
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests

# Standard timezone handling
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # On Windows, you may need: pip install tzdata
    pass

# --- AUTHENTICATION ---
SESSION_TOKEN = "insert your token here"
CF_CLEARANCE   = "insert your cloudflare clearance cookie here"

# --- ENDPOINTS ---
UPCOMING_URL  = "https://igotanoffer.com/api/coach-account/sessions-upcoming"
DONE_URL      = "https://igotanoffer.com/api/coach-account/sessions-done"
EMAIL_URL     = "https://igotanoffer.com/api/s/coach-account/client-email?session_id="
OUTPUT_FILE   = "igotanoffer_sessions_detailed.csv"

def print_usage_guide():
    usage = """
===========================================================================
                IGOTANOFFER SESSION SCRAPER - USAGE GUIDE
===========================================================================
Filters and displays sessions in PDT. Generates CSV and ASCII charts.

COMMAND OPTIONS:
  --week [num]      Filter by week number (e.g., --week 13)
  --month [num]     Filter by month number (1-12, e.g., --month 3)
  --year [year]     Filter by year (e.g., --year 2025)
  --doneonly        Skip 'Upcoming' sessions.
  --usage           Display this help guide.
===========================================================================
    """
    print(usage)

def parse_date_components(dt_str):
    if not dt_str: return None
    try:
        dt_utc = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        local_tz = ZoneInfo("America/Los_Angeles")
        dt_local = dt_utc.astimezone(local_tz)
        
        now = datetime.now(timezone.utc).astimezone(local_tz)
        days_ago = (now - dt_local).days
        
        return {
            'day': dt_local.strftime("%d"),
            'month': dt_local.strftime("%b"),
            'month_num': dt_local.month,
            'year': dt_local.year,
            'time': dt_local.strftime("%H:%M"),
            'week': int(dt_local.strftime("%U")) + 1,
            'dt_obj': dt_local,
            'days_ago': days_ago
        }
    except Exception: return None

def fetch_email(session, sid):
    try:
        resp = session.get(f"{EMAIL_URL}{sid}", timeout=5)
        if resp.status_code == 200:
            return resp.json().get('email', 'N/A')
    except: pass
    return "N/A"

def fetch_single_page(page_num, target_week, target_month, target_year):
    s = requests.Session(impersonate="chrome124")
    s.cookies.update({"__Secure-authjs.session-token": SESSION_TOKEN, "cf_clearance": CF_CLEARANCE})
    url = f"{DONE_URL}?page={page_num}"
    r = s.get(url)
    if r.status_code != 200: return []
    
    data = r.json()
    page_sessions = []
    for item in data.get('results', []):
        info = parse_date_components(item.get('start'))
        if not info: continue
        if target_year and info['year'] != target_year: continue
        if target_month and info['month_num'] != target_month: continue
        if target_week and info['week'] != target_week: continue

        email = fetch_email(s, item['id'])
        page_sessions.append({
            'SessionID': item['id'], 'WeekNum': info['week'], 'Client': item.get('user', {}).get('shortened_name', 'N/A'),
            'Day': info['day'], 'Month': info['month'], 'Year': info['year'], 'Time': info['time'],
            'Amount': float(item.get('coach_fee', 0)), 'DaysSince': info['days_ago'],
            'Email': email, 'dt_obj': info['dt_obj'], 'Status': 'Done'
        })
    return page_sessions

def print_ascii_charts(sessions, client_counts):
    # 1. Revenue Chart
    monthly_revenue = defaultdict(float)
    for s in sessions:
        monthly_revenue[f"{s['Month']} {s['Year']}"] += s['Amount']
    
    sorted_months = sorted(monthly_revenue.keys(), key=lambda x: datetime.strptime(x, "%b %Y"))
    if monthly_revenue:
        max_rev = max(monthly_revenue.values())
        print("\n" + "="*75)
        print("   MONTHLY REVENUE BAR CHART (PDT CONVERTED)")
        print("="*75)
        for month in sorted_months:
            amount = monthly_revenue[month]
            bar_len = int((amount / max_rev) * 40) if max_rev > 0 else 0
            print(f"{month:<10} | ${amount:>9,.2f} | {'█' * bar_len}")

    # 2. Client Frequency Chart
    freq_data = {"1 Session": 0, "2 Sessions": 0, "3 Sessions": 0, "> 3 Sessions": 0}
    for count in client_counts.values():
        if count == 1: freq_data["1 Session"] += 1
        elif count == 2: freq_data["2 Sessions"] += 1
        elif count == 3: freq_data["3 Sessions"] += 1
        else: freq_data["> 3 Sessions"] += 1

    max_freq = max(freq_data.values())
    print("\n" + "="*75)
    print("   CLIENT SESSION FREQUENCY CHART")
    print("="*75)
    for label, count in freq_data.items():
        bar_len = int((count / max_freq) * 40) if max_freq > 0 else 0
        print(f"{label:<12} | {count:>3} clients | {'█' * bar_len}")
    print("="*75)

def scrape_all(target_week=None, target_month=None, target_year=None, done_only=False):
    main_s = requests.Session(impersonate="chrome124")
    main_s.cookies.update({"__Secure-authjs.session-token": SESSION_TOKEN, "cf_clearance": CF_CLEARANCE})
    all_sessions = []
    latest_session_map = {}
    client_counts = Counter()

    # 1. Upcoming
    if not done_only:
        print("Step 1: Fetching upcoming sessions...", end="\r")
        up_resp = main_s.get(UPCOMING_URL)
        if up_resp.status_code == 200:
            for item in up_resp.json():
                info = parse_date_components(item.get('start'))
                if info:
                    if (not target_year or info['year'] == target_year) and \
                       (not target_month or info['month_num'] == target_month) and \
                       (not target_week or info['week'] == target_week):
                        email = fetch_email(main_s, item['id'])
                        all_sessions.append({
                            'SessionID': item['id'], 'WeekNum': info['week'], 'Client': item['user']['shortened_name'],
                            'Day': info['day'], 'Month': info['month'], 'Year': info['year'], 'Time': info['time'],
                            'Amount': float(item.get('coach_fee', 0)), 'DaysSince': info['days_ago'],
                            'Email': email, 'dt_obj': info['dt_obj'], 'Status': 'Upcoming'
                        })

    # 2. Done
    print("Step 2: Detecting historical pages...", end="\r")
    first_page_resp = main_s.get(f"{DONE_URL}?page=1")
    if first_page_resp.status_code == 200:
        total_pages = math.ceil(first_page_resp.json().get('count', 0) / 8)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_single_page, p, target_week, target_month, target_year) for p in range(1, total_pages + 1)]
            for future in as_completed(futures):
                all_sessions.extend(future.result())

    if all_sessions:
        all_sessions.sort(key=lambda x: x['SessionID'], reverse=True)
        for s in all_sessions:
            cid = s['Email'] if s['Email'] != "N/A" else s['Client']
            client_counts[cid] += 1
            if cid not in latest_session_map or s['dt_obj'] > latest_session_map[cid]:
                latest_session_map[cid] = s['dt_obj']

        # Save CSV
        fieldnames = ['SessionID', 'WeekNum', 'Client', 'Day', 'Month', 'Year', 'Time', 'Amount', 'MostRecentSession', 'DaysSince', 'Email', 'Status']
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for s in all_sessions:
                cid = s['Email'] if s['Email'] != "N/A" else s['Client']
                writer.writerow({
                    'SessionID': s['SessionID'], 'WeekNum': s['WeekNum'], 'Client': s['Client'],
                    'Day': s['Day'], 'Month': s['Month'], 'Year': s['Year'], 'Time': s['Time'],
                    'Amount': s['Amount'], 'MostRecentSession': latest_session_map[cid].strftime("%Y-%m-%d"),
                    'DaysSince': s['DaysSince'], 'Email': s['Email'], 'Status': s['Status']
                })

        # Table Output
        print(f"\nSUCCESS: Exported {len(all_sessions)} total sessions to {OUTPUT_FILE}")
        header = f"{'ID':<8} | {'D/M/Y':<12} | {'Time':<6} | {'Client':<18} | {'Recent':<11} | {'Days':<4} | {'Status'}"
        print(header)
        print("-" * len(header))
        for s in all_sessions:
            cid = s['Email'] if s['Email'] != "N/A" else s['Client']
            recent = latest_session_map[cid].strftime("%Y-%m-%d")
            date_display = f"{s['Day']} {s['Month']} {s['Year']}"
            days_val = s['DaysSince'] if s['DaysSince'] >= 0 else f"In {-s['DaysSince']}"
            print(f"{s['SessionID']:<8} | {date_display:<12} | {s['Time']:<6} | {s['Client']:<18} | {recent:<11} | {days_val:<4} | {s['Status']}")

        if not (target_week or target_month or target_year):
            print_ascii_charts(all_sessions, client_counts)
    else:
        print("No sessions found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--week', type=int); parser.add_argument('--month', type=int)
    parser.add_argument('--year', type=int); parser.add_argument('--doneonly', action='store_true')
    parser.add_argument('--usage', action='store_true')
    args = parser.parse_args()
    if args.usage: print_usage_guide(); sys.exit()
    scrape_all(args.week, args.month, args.year, args.doneonly)
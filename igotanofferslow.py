import csv
import time
import sys
import argparse
import math
import random
from datetime import datetime, timezone, datetime as dt
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests

# Import credentials from the config file
try:
    import config
except ImportError:
    print("Error: config.py not found. Please create config.py with SESSION_TOKEN and CF_CLEARANCE.")
    sys.exit(1)

# Standard timezone handling
try:
    from zoneinfo import ZoneInfo, available_timezones
except ImportError:
    available_timezones = None

# --- ENDPOINTS ---
UPCOMING_URL  = "https://igotanoffer.com/api/coach-account/sessions-upcoming"
DONE_URL      = "https://igotanoffer.com/api/coach-account/sessions-done"
EMAIL_URL     = "https://igotanoffer.com/api/s/coach-account/client-email?session_id="
OUTPUT_FILE   = "igotanoffer_sessions_detailed.csv"

def robust_request(session, method, url, max_retries=5):
    """
    Handles requests with jitter and exponential backoff.
    Mimics human-like pacing to avoid Cloudflare detection.
    """
    for attempt in range(max_retries):
        try:
            # Human-like delay (0.8 to 2.2 seconds)
            time.sleep(random.uniform(0.8, 2.2))
            
            resp = session.request(method, url, timeout=15)
            
            if resp.status_code == 200:
                return resp
            
            # If hit by rate limits (429) or forbidden (403), back off
            if resp.status_code in [429, 403]:
                wait_time = (2 ** (attempt + 1)) + random.random()
                print(f"       ! Rate limited ({resp.status_code}). Backing off for {wait_time:.2f}s...")
                time.sleep(wait_time)
                continue
                
        except Exception as e:
            print(f"       ! Connection error: {e}")
            time.sleep(2)
            
    return None

def print_usage_guide():
    usage = """
===========================================================================
                IGOTANOFFER SESSION SCRAPER - ROBUST VERSION
===========================================================================
Filters and displays sessions in chosen Timezone. Generates CSV and Charts.

COMMAND OPTIONS:
  --week [num]      Filter by week number (e.g., --week 13)
  --month [num]     Filter by month number (1-12, e.g., --month 3)
  --year [year]     Filter by year (e.g., --year 2025)
  --tz [name]       Set display timezone (Default: America/Los_Angeles)
  --doneonly        Skip 'Upcoming' sessions.
  --usage           Display this help guide.
===========================================================================
    """
    print(usage)

def list_common_timezones():
    common = ["UTC", "America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/London", "Asia/Dubai"]
    print("\n--- COMMON TIMEZONES ---")
    for tz in common: print(f"  {tz}")
    if available_timezones: print(f"\nSystem supports {len(available_timezones())} zones.")

def parse_date_components(dt_str, tz_name="America/Los_Angeles"):
    if not dt_str: return None
    try:
        # Standardize UTC handling
        clean_dt = dt_str.replace('Z', '+00:00')
        dt_utc = datetime.fromisoformat(clean_dt)
        
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            
        try:
            local_tz = ZoneInfo(tz_name)
        except Exception:
            # Fallback if tzdata is still missing or name is invalid
            print(f"DEBUG: Timezone {tz_name} not found, falling back to UTC")
            local_tz = timezone.utc
            
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
    except Exception as e:
        print(f"DEBUG: Error parsing {dt_str}: {e}")
        return None
    

def fetch_email(session, sid):
    resp = robust_request(session, "GET", f"{EMAIL_URL}{sid}")
    if resp:
        try: return resp.json().get('email', 'N/A')
        except: pass
    return "N/A"

def fetch_single_page(page_num, target_week, target_month, target_year, tz_name):
    s = requests.Session(impersonate="chrome124")
    s.cookies.update({"__Secure-authjs.session-token": config.SESSION_TOKEN, "cf_clearance": config.CF_CLEARANCE})
    # Set Referer to mimic UI-driven requests
    s.headers.update({"Referer": "https://igotanoffer.com/coach-account/sessions"})
    
    url = f"{DONE_URL}?page={page_num}"
    r = robust_request(s, "GET", url)
    if not r: return []
    
    data = r.json()
    page_sessions = []
    for item in data.get('results', []):
        info = parse_date_components(item.get('start'), tz_name)
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

def print_ascii_charts(sessions, client_counts, show_revenue=True):
    if show_revenue:
        monthly_revenue = defaultdict(float)
        for s in sessions: monthly_revenue[f"{s['Month']} {s['Year']}"] += s['Amount']
        sorted_months = sorted(monthly_revenue.keys(), key=lambda x: dt.strptime(x, "%b %Y"))
        if monthly_revenue:
            max_rev = max(monthly_revenue.values())
            print("\n" + "="*75 + "\n   MONTHLY REVENUE BAR CHART\n" + "="*75)
            for month in sorted_months:
                amount = monthly_revenue[month]
                bar_len = int((amount / max_rev) * 40) if max_rev > 0 else 0
                print(f"{month:<10} | ${amount:>9,.2f} | {'█' * bar_len}")

    freq_data = {"1 Session": 0, "2 Sessions": 0, "3 Sessions": 0, "> 3 Sessions": 0}
    for count in client_counts.values():
        if count == 1: freq_data["1 Session"] += 1
        elif count == 2: freq_data["2 Sessions"] += 1
        elif count == 3: freq_data["3 Sessions"] += 1
        else: freq_data["> 3 Sessions"] += 1

    if any(freq_data.values()):
        max_freq = max(freq_data.values())
        print("\n" + "="*75 + "\n   CLIENT SESSION FREQUENCY CHART\n" + "="*75)
        for label, count in freq_data.items():
            bar_len = int((count / max_freq) * 40) if max_freq > 0 else 0
            print(f"{label:<12} | {count:>3} clients | {'█' * bar_len}")
        print("="*75)

def scrape_all(target_week=None, target_month=None, target_year=None, done_only=False, tz_name="America/Los_Angeles"):
    main_s = requests.Session(impersonate="chrome124")
    main_s.cookies.update({"__Secure-authjs.session-token": config.SESSION_TOKEN, "cf_clearance": config.CF_CLEARANCE})
    all_sessions = []
    latest_session_map = {}
    client_counts = Counter()

    if not done_only:
        print(f"Step 1: Fetching upcoming sessions...")
        up_resp = robust_request(main_s, "GET", UPCOMING_URL)
        if up_resp:
            found_up = 0
            for item in up_resp.json():
                info = parse_date_components(item.get('start'), tz_name)
                if not info:
                    continue
                if info and (not target_year or info['year'] == target_year) and \
                   (not target_month or info['month_num'] == target_month) and \
                   (not target_week or info['week'] == target_week):
                    email = fetch_email(main_s, item['id'])
                    all_sessions.append({
                        'SessionID': item['id'], 'WeekNum': info['week'], 'Client': item['user']['shortened_name'],
                        'Day': info['day'], 'Month': info['month'], 'Year': info['year'], 'Time': info['time'],
                        'Amount': float(item.get('coach_fee', 0)), 'DaysSince': info['days_ago'],
                        'Email': email, 'dt_obj': info['dt_obj'], 'Status': 'Upcoming'
                    })
                    found_up += 1
            print(f"       -> Added {found_up} upcoming sessions.")

    print("Step 2: Detecting historical pages...")
    first_page_resp = robust_request(main_s, "GET", f"{DONE_URL}?page=1")
    if first_page_resp:
        total_items = first_page_resp.json().get('count', 0)
        total_pages = math.ceil(total_items / 8)
        print(f"       -> Found {total_items} historical sessions across {total_pages} pages.")
        
        print(f"Step 3: Processing pages (Max Workers: 2)...")
        completed = 0
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Map futures to page numbers
            future_to_page = {executor.submit(fetch_single_page, p, target_week, target_month, target_year, tz_name): p for p in range(1, total_pages + 1)}
            
            for future in as_completed(future_to_page):
                completed += 1
                page_num = future_to_page[future]
                percent = (completed / total_pages) * 100
                
                # ANSI escape code \r returns the cursor to the start of the line
                sys.stdout.write(f"\r       Progress: [{completed}/{total_pages}] {percent:.1f}% complete (Last finished: Page {page_num})")
                sys.stdout.flush()
                
                try:
                    all_sessions.extend(future.result())
                except Exception as e:
                    print(f"\n       ! Error on page {page_num}: {e}")

        print("\n       -> Step 3 complete.")

    if all_sessions:
        # Sorting and CSV logic remains the same...
        all_sessions.sort(key=lambda x: x['SessionID'], reverse=True)
        for s in all_sessions:
            cid = s['Email'] if s['Email'] != "N/A" else s['Client']
            client_counts[cid] += 1
            if cid not in latest_session_map or s['dt_obj'] > latest_session_map[cid]:
                latest_session_map[cid] = s['dt_obj']

        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['SessionID', 'WeekNum', 'Client', 'Day', 'Month', 'Year', 'Time', 'Amount', 'MostRecentSession', 'DaysSince', 'Email', 'Status']
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

        print("\n--- SESSION SUMMARY ---")
        for s in all_sessions:
            print(f"{s['SessionID']:<8} | {s['Day']} {s['Month']} {s['Year']:<5} | {s['Client']:<18} | {s['Status']}")

        print_ascii_charts(all_sessions, client_counts, show_revenue=not (target_week or target_month))
    else:
        print("\nNo sessions found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--week', type=int)
    parser.add_argument('--month', type=int)
    parser.add_argument('--year', type=int)
    parser.add_argument('--tz', type=str, default="America/Los_Angeles")
    parser.add_argument('--doneonly', action='store_true')
    parser.add_argument('--usage', action='store_true')
    args = parser.parse_args()
    
    if args.usage: print_usage_guide(); sys.exit()
    if args.tz.lower() == "list": list_common_timezones(); sys.exit()
        
    scrape_all(args.week, args.month, args.year, args.doneonly, args.tz)
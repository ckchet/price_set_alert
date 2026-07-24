"""
SET Stock Price Alert -> Telegram
----------------------------------
เช็คราคาหุ้นในลิสต์ที่กำหนด ถ้าราคาเปลี่ยนแปลง (ขึ้นหรือลง) เกิน THRESHOLD_PERCENT
เมื่อเทียบกับราคาปิดวันก่อนหน้า จะส่งข้อความแจ้งเตือนเข้า Telegram

รายชื่อหุ้นที่ติดตามมาจาก 3 ไฟล์ (แก้ไข/เพิ่มได้อิสระ ต่อท้ายด้วย .BK เสมอ):
- watchlist_custom.txt  -> หุ้นที่คุณสนใจเป็นการส่วนตัว
- watchlist_set100.txt  -> หุ้นกลุ่ม SET100 (ต้องคัดลอกมาใส่เอง ดู README.md)
- watchlist_sethd.txt   -> หุ้นกลุ่ม SETHD (ต้องคัดลอกมาใส่เอง ดู README.md)

วิธีตั้งค่า:
1. ใส่รายชื่อหุ้นในไฟล์ .txt ทั้ง 3 ไฟล์ (บรรทัดละ 1 ตัว)
2. ตั้งค่า TELEGRAM_BOT_TOKEN และ TELEGRAM_CHAT_ID
   - แนะนำให้ตั้งเป็น Environment Variable แทนการเขียนลงโค้ดตรงๆ (ดู README.md)
3. รันสคริปต์นี้ทุก 30 นาที ผ่าน cron / Task Scheduler / GitHub Actions
   (สคริปต์นี้เช็คครั้งเดียวแล้วจบ ไม่ใช่ loop ค้างตลอด
    เพราะการรันซ้ำด้วย scheduler ภายนอกจะแข็งแรงและดูแลง่ายกว่า)
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import pytz
import yfinance as yf
import requests
from dotenv import load_dotenv

# ========== ตั้งค่า ==========

BASE_DIR = Path(__file__).resolve().parent

# โหลดค่าจากไฟล์ .env ถ้ามี (สะดวกเวลารันผ่าน cron ซึ่งไม่โหลด shell profile ให้)
load_dotenv(BASE_DIR / ".env")

WATCHLIST_FILES = [
    BASE_DIR / "watchlist_custom.txt",
    BASE_DIR / "watchlist_set100.txt",
    BASE_DIR / "watchlist_sethd.txt",
]


def load_watchlist() -> list[str]:
    """อ่านรายชื่อหุ้นจากไฟล์ .txt ทั้งหมด รวมกันและตัดตัวซ้ำออก"""
    symbols: list[str] = []
    for file_path in WATCHLIST_FILES:
        if not file_path.exists():
            print(f"[warn] ไม่พบไฟล์ {file_path.name} ข้ามไป")
            continue
        for line in file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip().upper()
            if not line or line.startswith("#"):
                continue
            if not line.endswith(".BK"):
                line += ".BK"
            symbols.append(line)
    # ตัดตัวซ้ำ (เช่นหุ้นที่อยู่ทั้ง watchlist ส่วนตัว และ SET100) โดยคงลำดับเดิม
    return list(dict.fromkeys(symbols))


WATCHLIST = load_watchlist()

# เกณฑ์ % ที่จะแจ้งเตือน (ทั้งขึ้นและลง)
THRESHOLD_PERCENT = 2.0

# ดึงค่าจาก Environment Variable (ปลอดภัยกว่าเขียนลงโค้ดตรงๆ)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# เช็คเฉพาะช่วงเวลาทำการของตลาดหุ้นไทย (จันทร์-ศุกร์ 10:00-16:30) หรือไม่
ONLY_DURING_MARKET_HOURS = True


def is_market_hours() -> bool:
    tz = pytz.timezone("Asia/Bangkok")
    now = datetime.now(tz)
    if now.weekday() >= 5:  # 5=เสาร์, 6=อาทิตย์
        return False
    market_open = now.replace(hour=10, minute=20, second=0, microsecond=0)
    market_close = now.replace(hour=17, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def send_telegram_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[warn] ยังไม่ได้ตั้งค่า TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
        print(text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    if not resp.ok:
        print(f"[error] ส่ง Telegram ไม่สำเร็จ: {resp.status_code} {resp.text}")


def fetch_price_changes(symbols: list[str]) -> dict:
    """
    ดึงราคาปิดล่าสุด 2 วันทำการของหุ้นทุกตัวพร้อมกัน (batch) แล้วคำนวณ % เปลี่ยนแปลง
    ใช้ history() แทน fast_info เพราะ fast_info บางครั้งมีข้อมูลค้าง/ไม่อัปเดตสำหรับหุ้นไทยบางตัว
    คืนค่า dict: {symbol: (current_price, prev_close, pct_change)}
    """
    results = {}
    if not symbols:
        return results

    data = yf.download(
        tickers=symbols,
        period="5d",
        interval="1d",
        group_by="ticker",
        progress=False,
        threads=True,
        auto_adjust=False,
    )

    for symbol in symbols:
        try:
            # เมื่อมีหลายหุ้น yfinance จะคืนเป็น multi-index column (symbol, field)
            if len(symbols) == 1:
                closes = data["Close"].dropna()
            else:
                closes = data[symbol]["Close"].dropna()

            if len(closes) < 2:
                print(f"[skip] {symbol}: ข้อมูลราคาย้อนหลังไม่พอ")
                continue

            current_price = float(closes.iloc[-1])
            prev_close = float(closes.iloc[-2])

            if prev_close == 0:
                print(f"[skip] {symbol}: ราคาปิดก่อนหน้าเป็น 0")
                continue

            pct_change = (current_price - prev_close) / prev_close * 100
            results[symbol] = (current_price, prev_close, pct_change)

        except Exception as e:
            print(f"[error] {symbol}: ดึงข้อมูลไม่ได้ ({e})")

    return results


def check_watchlist() -> None:
    print(f"ติดตามหุ้นทั้งหมด {len(WATCHLIST)} ตัว")

    force_run = os.environ.get("FORCE_RUN", "false").strip().lower() == "true"

    if force_run:
        print("[force_run] ข้ามการเช็คเวลาตลาด เช็คราคาทันที")
    elif ONLY_DURING_MARKET_HOURS and not is_market_hours():
        print("นอกเวลาทำการตลาด ข้ามการเช็ครอบนี้")
        return

    alerts = []

    price_changes = fetch_price_changes(WATCHLIST)

    for symbol, (current_price, prev_close, pct_change) in price_changes.items():
        print(f"{symbol}: {current_price:.2f} ({pct_change:+.2f}%)")

        if abs(pct_change) >= THRESHOLD_PERCENT:
            direction = "📈 ขึ้น" if pct_change > 0 else "📉 ลง"
            alerts.append(
                f"{direction} <b>{symbol}</b>\n"
                f"ราคาล่าสุด: {current_price:.2f} บาท\n"
                f"เปลี่ยนแปลง: {pct_change:+.2f}%\n"
                f"(ปิดก่อนหน้า: {prev_close:.2f})"
            )

    tz = pytz.timezone("Asia/Bangkok")
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M")

    if alerts:
        header = f"🔔 <b>แจ้งเตือนราคาหุ้น SET</b> ({now_str})\n\n"
        message = header + "\n\n".join(alerts)
        send_telegram_message(message)
        print("ส่งแจ้งเตือนแล้ว")
    else:
        message = f"ℹ️ ({now_str}) ยังไม่มีหุ้นน่าสนใจ"
        send_telegram_message(message)
        print("ไม่มีหุ้นที่เปลี่ยนแปลงเกินเกณฑ์รอบนี้ — ส่งข้อความแจ้งแล้ว")


if __name__ == "__main__":
    check_watchlist()
"""
SET Stock Price Alert -> Telegram
----------------------------------
เช็คราคาหุ้นในลิสต์ที่กำหนด ถ้าราคาเปลี่ยนแปลง (ขึ้นหรือลง) เกิน THRESHOLD_PERCENT
เมื่อเทียบกับราคาปิดวันก่อนหน้า จะส่งข้อความแจ้งเตือนเข้า Telegram

รายชื่อหุ้นที่ติดตามอยู่ในไฟล์เดียว: watchlist_custom.txt
(1 บรรทัดต่อ 1 ตัว ไม่ต้องเติม .BK ระบบเติมให้เอง)

วิธีตั้งค่า:
1. แก้ไขรายชื่อหุ้นในไฟล์ watchlist_custom.txt (เพิ่ม/ลบได้อิสระ)
2. ตั้งค่า TELEGRAM_BOT_TOKEN และ TELEGRAM_CHAT_ID
   - แนะนำให้ตั้งเป็น Environment Variable แทนการเขียนลงโค้ดตรงๆ (ดู README.md)
3. รันสคริปต์นี้ทุก 30 นาที ผ่าน cron / Task Scheduler / GitHub Actions
   (สคริปต์นี้เช็คครั้งเดียวแล้วจบ ไม่ใช่ loop ค้างตลอด
    เพราะการรันซ้ำด้วย scheduler ภายนอกจะแข็งแรงและดูแลง่ายกว่า)
"""

import os
import sys
import time
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

WATCHLIST_FILE = BASE_DIR / "watchlist_custom.txt"


def load_watchlist() -> list[str]:
    """อ่านรายชื่อหุ้นจาก watchlist_custom.txt ตัดตัวซ้ำออก"""
    symbols: list[str] = []
    if not WATCHLIST_FILE.exists():
        print(f"[warn] ไม่พบไฟล์ {WATCHLIST_FILE.name}")
        return symbols
    for line in WATCHLIST_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().upper()
        if not line or line.startswith("#"):
            continue
        if not line.endswith(".BK"):
            line += ".BK"
        symbols.append(line)
    # ตัดตัวซ้ำ โดยคงลำดับเดิม
    return list(dict.fromkeys(symbols))


WATCHLIST = load_watchlist()

# เกณฑ์ % ที่จะแจ้งเตือน (ทั้งขึ้นและลง)
THRESHOLD_PERCENT = 1.5

# ดึงค่าจาก Environment Variable (ปลอดภัยกว่าเขียนลงโค้ดตรงๆ)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# เช็คเฉพาะช่วงเวลาทำการของตลาดหุ้นไทย (จันทร์-ศุกร์ 10:20-17:30) หรือไม่
ONLY_DURING_MARKET_HOURS = True

# ไฟล์รายชื่อวันหยุดพิเศษ (นอกเหนือจากเสาร์-อาทิตย์) แก้ไขแค่ไฟล์นี้พอ
# ไม่ต้องแก้โค้ดหลักเวลาเพิ่ม/ลบวันหยุด
HOLIDAYS_FILE = BASE_DIR / "holidays.txt"


def load_holidays() -> set[str]:
    """อ่านวันที่หยุดพิเศษจาก holidays.txt (รูปแบบ YYYY-MM-DD บรรทัดละ 1 วัน)"""
    if not HOLIDAYS_FILE.exists():
        return set()
    dates = set()
    for line in HOLIDAYS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        dates.add(line)
    return dates


def is_holiday_today() -> bool:
    tz = pytz.timezone("Asia/Bangkok")
    today_str = datetime.now(tz).strftime("%Y-%m-%d")
    return today_str in load_holidays()


def is_market_hours() -> bool:
    tz = pytz.timezone("Asia/Bangkok")
    now = datetime.now(tz)
    if now.weekday() >= 5:  # 5=เสาร์, 6=อาทิตย์
        return False
    market_open = now.replace(hour=10, minute=20, second=0, microsecond=0)
    market_close = now.replace(hour=17, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


# Telegram จำกัดความยาวข้อความที่ 4096 ตัวอักษร เผื่อขอบไว้หน่อยให้ปลอดภัย
TELEGRAM_MAX_CHARS = 3800
# เว้นจังหวะระหว่างส่งแต่ละข้อความ (วินาที) กันโดน Telegram rate limit ตอนส่งหลายข้อความติดกัน
TELEGRAM_SEND_DELAY = 1.0


def _send_single_telegram_message(text: str, retries: int = 3) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for attempt in range(1, retries + 1):
        resp = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        if resp.ok:
            return
        if resp.status_code == 429:
            # โดน rate limit — Telegram จะบอกเวลาที่ต้องรอใน retry_after (วินาที)
            try:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
            except Exception:
                retry_after = 5
            print(f"[warn] โดน Telegram rate limit รอ {retry_after} วินาทีแล้วลองใหม่ (ครั้งที่ {attempt}/{retries})")
            time.sleep(retry_after + 1)
            continue
        print(f"[error] ส่ง Telegram ไม่สำเร็จ: {resp.status_code} {resp.text}")
        return
    print("[error] ส่ง Telegram ไม่สำเร็จหลังลองซ้ำครบจำนวนแล้ว (โดน rate limit ต่อเนื่อง)")


def _split_message(text: str, max_chars: int) -> list[str]:
    """
    แบ่งข้อความยาวๆ เป็นชิ้นย่อยไม่เกิน max_chars ตัวอักษร
    พยายามตัดตรงรอยต่อระหว่างหุ้นแต่ละตัว (คั่นด้วยบรรทัดว่าง) ไม่ตัดกลางหุ้นตัวเดียว
    """
    if len(text) <= max_chars:
        return [text]

    blocks = text.split("\n\n")
    chunks = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # เผื่อบล็อกเดียวยาวเกิน max_chars ก็ตัดดื้อๆ ไปเลย (กรณีนี้แทบไม่เกิดกับข้อความหุ้น)
            if len(block) > max_chars:
                for i in range(0, len(block), max_chars):
                    chunks.append(block[i:i + max_chars])
                current = ""
            else:
                current = block
    if current:
        chunks.append(current)
    return chunks


def send_telegram_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[warn] ยังไม่ได้ตั้งค่า TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
        print(text)
        return

    chunks = _split_message(text, TELEGRAM_MAX_CHARS)
    if len(chunks) > 1:
        print(f"[info] ข้อความยาวเกิน แบ่งส่งเป็น {len(chunks)} ชิ้น")

    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            chunk = f"({i + 1}/{len(chunks)})\n{chunk}"
        _send_single_telegram_message(chunk)
        if i < len(chunks) - 1:
            time.sleep(TELEGRAM_SEND_DELAY)


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
        print("[force_run] ข้ามการเช็คเวลาตลาด/วันหยุด เช็คราคาทันที")
    elif is_holiday_today():
        print("วันนี้เป็นวันหยุดพิเศษตาม holidays.txt ข้ามการเช็ครอบนี้")
        return
    elif ONLY_DURING_MARKET_HOURS and not is_market_hours():
        print("นอกเวลาทำการตลาด ข้ามการเช็ครอบนี้")
        return

    gainers = []  # หุ้นที่ราคาขึ้น (pct_change เป็นบวก)
    losers = []   # หุ้นที่ราคาลง (pct_change เป็นลบ)

    price_changes = fetch_price_changes(WATCHLIST)

    for symbol, (current_price, prev_close, pct_change) in price_changes.items():
        print(f"{symbol}: {current_price:.2f} ({pct_change:+.2f}%)")

        if abs(pct_change) >= THRESHOLD_PERCENT:
            entry = (symbol, current_price, prev_close, pct_change)
            if pct_change > 0:
                gainers.append(entry)
            else:
                losers.append(entry)

    # เรียงฝั่งบวก: มากที่สุด -> น้อยที่สุด (มาก% ก่อน)
    gainers.sort(key=lambda x: x[3], reverse=True)
    # เรียงฝั่งลบ: ลบมากที่สุด -> ลบน้อยที่สุด (ติดลบเยอะสุดก่อน)
    losers.sort(key=lambda x: x[3])

    def format_entry(entry) -> str:
        symbol, current_price, prev_close, pct_change = entry
        direction = "📈 ขึ้น" if pct_change > 0 else "📉 ลง"
        return (
            f"{direction} <b>{symbol}</b>\n"
            f"ราคาล่าสุด: {current_price:.2f} บาท\n"
            f"เปลี่ยนแปลง: {pct_change:+.2f}%\n"
            f"(ปิดก่อนหน้า: {prev_close:.2f})"
        )

    tz = pytz.timezone("Asia/Bangkok")
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M")

    if gainers or losers:
        sections = []
        if gainers:
            sections.append(
                "🟢 <b>ราคาขึ้น</b>\n\n" + "\n\n".join(format_entry(e) for e in gainers)
            )
        if losers:
            sections.append(
                "🔴 <b>ราคาลง</b>\n\n" + "\n\n".join(format_entry(e) for e in losers)
            )
        header = f"🔔 <b>แจ้งเตือนราคาหุ้น SET</b> ({now_str})\n\n"
        message = header + "\n\n".join(sections)
        send_telegram_message(message)
        print("ส่งแจ้งเตือนแล้ว")
    else:
        message = f"ℹ️ ({now_str}) ยังไม่มีหุ้นน่าสนใจ"
        send_telegram_message(message)
        print("ไม่มีหุ้นที่เปลี่ยนแปลงเกินเกณฑ์รอบนี้ — ส่งข้อความแจ้งแล้ว")


if __name__ == "__main__":
    check_watchlist()

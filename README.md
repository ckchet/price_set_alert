# SET Stock Price Alert → Telegram

เช็คหุ้นในลิสต์ (watchlist) ทุก 30 นาที ถ้าราคาขยับขึ้น/ลงเกิน 3% เทียบกับราคาปิดก่อนหน้า
จะส่งข้อความแจ้งเตือนเข้า Telegram อัตโนมัติ

ไม่ต้องมีเซิร์ฟเวอร์หรือเปิดคอมทิ้งไว้ — ใช้ **GitHub Actions** (ฟรี) เป็นตัวรันตามตารางเวลาให้

---

## ขั้นตอนที่ 1: สร้าง Telegram Bot

1. เปิด Telegram หาแชท **@BotFather**
2. พิมพ์ `/newbot` แล้วตั้งชื่อบอทตามที่ต้องการ
3. จะได้ **Bot Token** มา (หน้าตาประมาณ `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`) เก็บไว้

## ขั้นตอนที่ 2: หา Chat ID ของตัวเอง

1. เริ่มแชทกับบอทที่สร้างไว้ (กดปุ่ม Start / ส่งข้อความอะไรก็ได้ไปหาบอท)
2. เปิดเบราว์เซอร์ไปที่ (แทน `<TOKEN>` ด้วย token จริง):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. จะเห็น JSON ที่มี `"chat":{"id": 123456789, ...}` — ตัวเลขนั้นคือ **Chat ID**

## ขั้นตอนที่ 3: เตรียมโค้ดใน GitHub

1. สร้าง repository ใหม่บน GitHub (ตั้งเป็น private ก็ได้)
2. อัปโหลดไฟล์ทั้งหมดในโฟลเดอร์นี้เข้าไป (ต้องคงโครงสร้าง `.github/workflows/set_price_alert.yml` ไว้)
3. ไปที่ repo → **Settings → Secrets and variables → Actions → New repository secret**
   เพิ่ม 2 ค่า:
   - `TELEGRAM_BOT_TOKEN` = token จากขั้นตอนที่ 1
   - `TELEGRAM_CHAT_ID` = chat id จากขั้นตอนที่ 2

## ขั้นตอนที่ 4: ทดสอบ

1. ไปที่แท็บ **Actions** ของ repo
2. เลือก workflow "SET Price Alert" → กด **Run workflow** เพื่อทดสอบรันด้วยมือก่อน
3. ถ้าตั้งค่าถูกต้อง จะเห็น log การเช็คราคา และถ้ามีหุ้นเปลี่ยนแปลงเกิน 3% จะมีข้อความเด้งเข้า Telegram

จากนั้นระบบจะรันอัตโนมัติทุก 30 นาทีตาม cron ที่ตั้งไว้ (`*/30 * * * *`)

> หมายเหตุ: GitHub Actions แบบ free tier บางครั้งดีเลย์การรันได้ 5-15 นาทีในช่วงคิวยาว
> ถ้าต้องการความแม่นยำของเวลาสูงมาก ควรใช้ VPS เล็กๆ + cron แทน

---

## แก้ไขหุ้นที่ติดตาม

รายชื่อหุ้นแยกเป็น 3 ไฟล์ (1 บรรทัดต่อ 1 ตัว ไม่ต้องเติม `.BK` ก็ได้ ระบบเติมให้อัตโนมัติ):

| ไฟล์ | ใช้สำหรับ |
|---|---|
| `watchlist_custom.txt` | หุ้นที่คุณสนใจเป็นการส่วนตัว แก้ไข/เพิ่มได้เลย |
| `watchlist_set100.txt` | หุ้นกลุ่ม SET100 — มีลิสต์เริ่มต้นให้บางส่วน **แต่ไม่ใช่รายชื่อฉบับสมบูรณ์/ล่าสุด** เพราะไฟล์ทางการต้องล็อกอินโหลด และรายชื่อเปลี่ยนทุก 6 เดือน |
| `watchlist_sethd.txt` | หุ้นกลุ่ม SETHD — ยังไม่ได้ใส่รายชื่อไว้ล่วงหน้า ต้องคัดลอกมาใส่เอง |

**วิธีเอารายชื่อ SET100 / SETHD ฉบับล่าสุดมาใส่:**

1. ล็อกอิน (สมัครฟรี) ที่เว็บ SET แล้วโหลด PDF รอบล่าสุด:
   - SET100: https://www.set.or.th/th/market/information/securities-list/constituents-list-set50-set100
   - SETHD: https://www.set.or.th/th/market/information/securities-list/constituents-list-sethd
2. หรือดูจากตารางที่ไม่ต้องล็อกอิน เช่น settrade.com:
   https://www.settrade.com/th/equities/market-data/overview?category=Index&index=SET100
3. คัดลอกชื่อย่อหุ้น (symbol) มาวางในไฟล์ `.txt` ที่เกี่ยวข้อง บรรทัดละ 1 ตัว

หุ้นที่ซ้ำกันระหว่าง 3 ไฟล์ (เช่นหุ้นที่อยู่ทั้ง watchlist ส่วนตัว และ SET100) จะถูกตัดออกให้อัตโนมัติ ไม่ซ้ำซ้อน

> อย่าลืม: ทุกครั้งที่แก้ไขไฟล์ `.txt` ต้อง commit + push ขึ้น GitHub ด้วย ไม่งั้น workflow จะยังใช้รายชื่อเดิม

## แก้ไขเกณฑ์ % แจ้งเตือน

แก้ค่า `THRESHOLD_PERCENT = 2.0` ในไฟล์ `set_price_alert.py` (ตอนนี้ตั้งไว้ที่ 2% แล้ว)

## รันบนเครื่องตัวเองแทน (ทางเลือก)

ถ้าไม่อยากใช้ GitHub Actions:

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="xxxx"
export TELEGRAM_CHAT_ID="xxxx"
python set_price_alert.py
```

แล้วตั้ง cron (Linux/Mac) หรือ Task Scheduler (Windows) ให้รันคำสั่งข้างต้นทุก 30 นาที

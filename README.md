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

## ตั้งวันหยุดพิเศษให้บอทหยุดทำงาน

บอทหยุดทำงานเองอยู่แล้วทุกเสาร์-อาทิตย์ ถ้าอยากให้หยุดเพิ่มในวันอื่น (เช่นวันหยุดนักขัตฤกษ์ ตลาดปิดพิเศษ) ไม่ต้องแก้โค้ด — แก้แค่ไฟล์ **`holidays.txt`**:

1. เปิดไฟล์ `holidays.txt`
2. เพิ่มวันที่ต้องการ 1 บรรทัดต่อ 1 วัน รูปแบบ `YYYY-MM-DD` เช่น:
   ```
   2026-08-12
   2026-12-05
   ```
3. Commit + push ขึ้น GitHub

พอถึงวันนั้น บอทจะเช็คแล้วข้ามการทำงานทั้งวันโดยอัตโนมัติ (ไม่ต้องลบวันที่ออกหลังผ่านไปแล้ว เก็บสะสมไว้ในไฟล์ได้เรื่อยๆ) — ถ้าอยากทดสอบด้วยมือในวันที่ตั้งเป็นวันหยุดไว้ ใช้ตัวเลือก `force_run` ตอนกด Run workflow ได้ตามปกติ (จะข้ามทั้งเช็ควันหยุดและเวลาตลาด)

## แก้ไขหุ้นที่ติดตาม

รายชื่อหุ้นทั้งหมดอยู่ในไฟล์เดียว **`watchlist_custom.txt`** (1 บรรทัดต่อ 1 ตัว ไม่ต้องเติม `.BK` ก็ได้ ระบบเติมให้อัตโนมัติ, บรรทัดขึ้นต้นด้วย `#` คือคอมเมนต์)

ตอนนี้ในไฟล์มีหุ้น 100 ตัว (รวมจาก SET100 + SETHD + หุ้นที่คุณสนใจส่วนตัว เข้าไว้ด้วยกันแล้ว ตัดตัวซ้ำเรียบร้อย) — จะเพิ่ม/ลบหุ้นตัวไหนก็แก้ไฟล์นี้ไฟล์เดียวได้เลย ไม่ต้องแยกไฟล์อีกต่อไป

**ถ้าต้องการอัปเดตตามรายชื่อ SET100/SETHD รอบใหม่ในอนาคต** (ตลท. ประกาศทุก 6 เดือน ม.ค./ก.ค.) หาข้อมูลได้จาก:
- SET100: https://www.set.or.th/th/market/information/securities-list/constituents-list-set50-set100
- SETHD: https://www.set.or.th/th/market/information/securities-list/constituents-list-sethd

(ต้องล็อกอินสมาชิกฟรีก่อนโหลด) แล้วนำมาผสาน/แก้ไขใน `watchlist_custom.txt` เอง หรือส่งไฟล์มาให้ช่วยแกะให้ก็ได้

> อย่าลืม: ทุกครั้งที่แก้ไขไฟล์ `.txt` ต้อง commit + push ขึ้น GitHub ด้วย ไม่งั้น workflow จะยังใช้รายชื่อเดิม

## แก้ไขเกณฑ์ % แจ้งเตือน

แก้ค่า `THRESHOLD_PERCENT = 2.0` ในไฟล์ `set_price_alert.py` (ตอนนี้ตั้งไว้ที่ 2% แล้ว)

## รันด้วย Cron บนเครื่อง/เซิร์ฟเวอร์ตัวเอง (ทางเลือกแทน GitHub Actions)

เหมาะถ้ามี Linux/Mac server หรือ VPS อยู่แล้ว และต้องการความแม่นยำของเวลามากกว่า GitHub Actions free tier

### ขั้นตอน

1. ติดตั้ง dependencies:
   ```bash
   cd /path/to/set_alert
   pip install -r requirements.txt --break-system-packages
   ```

2. ตั้งค่า Telegram credentials — คัดลอกไฟล์ `.env.example` เป็น `.env` แล้วใส่ค่าจริง:
   ```bash
   cp .env.example .env
   nano .env   # ใส่ TELEGRAM_BOT_TOKEN และ TELEGRAM_CHAT_ID ของคุณ
   ```
   ไฟล์ `.env` จะถูกโหลดอัตโนมัติตอนสคริปต์รัน (ไม่ต้อง export env var เอง) — และห้าม commit ไฟล์นี้ขึ้น git (มี `.gitignore` กันไว้ให้แล้ว)

3. แก้ path ในไฟล์ `run_check.sh` บรรทัด `PROJECT_DIR=` ให้ตรงกับตำแหน่งจริงที่วางโปรเจกต์นี้ไว้ เช่น:
   ```bash
   PROJECT_DIR="/home/user/set_alert"
   ```
   แล้วให้สิทธิ์รันไฟล์ (ทำครั้งเดียว):
   ```bash
   chmod +x run_check.sh
   ```

4. ทดสอบรันด้วยมือก่อนตั้ง cron:
   ```bash
   ./run_check.sh
   cat set_price_alert.log   # ดูผลลัพธ์
   ```

5. ตั้ง cron ให้รันทุก 30 นาที — พิมพ์ `crontab -e` แล้วเพิ่มบรรทัดนี้ (แก้ path ให้ตรงกับของคุณ):
   ```
   */30 * * * * /path/to/set_alert/run_check.sh
   ```
   หรือถ้าอยากให้รันเฉพาะช่วงเวลาตลาดเปิด (จันทร์-ศุกร์ 10:00-16:30) เพื่อประหยัดทรัพยากร:
   ```
   */30 10-16 * * 1-5 /path/to/set_alert/run_check.sh
   ```
   (สคริปต์เองก็มีการเช็คเวลาตลาดซ้ำอยู่แล้วผ่าน `ONLY_DURING_MARKET_HOURS` ดังนั้นตั้ง cron แบบไหนก็ได้ ผลลัพธ์จะไม่ต่างกันมาก)

6. เช็คว่า cron รันจริงไหม — ดู log ไฟล์ `set_price_alert.log` ที่จะถูกเขียนทับ/ต่อท้ายทุกครั้งที่รัน

### หมายเหตุสำหรับ Windows

ถ้าใช้ Windows แทน cron ให้ใช้ **Task Scheduler** สร้าง task ใหม่ ตั้ง Trigger เป็น "Repeat task every 30 minutes" และ Action เป็นการรันคำสั่ง:
```
python C:\path\to\set_alert\set_price_alert.py
```

---

## รันบนเครื่องตัวเองแบบไม่ใช้ cron (ทดสอบเฉยๆ)

```bash
pip install -r requirements.txt --break-system-packages
python set_price_alert.py
```
(ต้องมีไฟล์ `.env` ตั้งไว้แล้วตามขั้นตอนด้านบน หรือจะ `export TELEGRAM_BOT_TOKEN=...` เองก็ได้)

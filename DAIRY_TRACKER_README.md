# 🥛 Doodh Ka Hisab (Dairy) Competitor Intelligence Radar

Google Play Store par **"Doodh Ka Hisab" / Dairy Management** category ke sabhi active apps ko automatically track aur analyze karne ka complete automated system.

---

## 🌟 Key Features

1. 🔍 **Auto-Discovery Pool**:
   - `"doodh ka hisab"`, `"doodh diary"`, `"milk record"`, `"dairy hisab kitab"` jaise 13+ targeted keywords se Play Store ko scan karke sabhi apps ki master list banata hai.
2. 🎯 **Daily 10 Apps Batch Ingestion**:
   - Rozana discovery pool se 10 naye apps ko active 24/7 tracking me add karta hai jab tak poori category ke sabhi apps cover na ho jayein.
3. 🔄 **Chhota Sa Bhi Update Track**:
   - **Version change** (e.g. `1.0.4` ➡️ `1.0.5`).
   - **"What's New" (Release Notes)** me competitor ne kya naya feature likha.
   - **Rating shift** (⭐ score badha ya gira).
   - **Installs tier growth** (10k+ ➡️ 50k+).
4. 💬 **New User Reviews Tracking**:
   - Competitor ke users ke naye reviews, star rating aur feedback capture karta hai (isse aapko competitor ke negative reviews aur unke users ki complaints ka turant pata chalega).
5. 📱 **Telegram Instant Alerts**:
   - Har ek event (Naya app, version update, naya review, daily summary) ka instant Telegram alert bhejta hai.
6. 📁 **CSV / Excel Export**:
   - Ek command se sabhi competitor apps ki detailed excel sheet export karein.

---

## 🚀 Quick Setup (2 Minutes)

### 1. Dependencies Install Karein
Terminal ya PowerShell me run karein:
```powershell
py -m pip install google-play-scraper requests python-dotenv
```

### 2. Telegram Bot Setup Karein
Agar aapke paas Telegram Bot nahi hai toh 2 minute me create karein:
1. Telegram open karein aur search karein: **`@BotFather`**
2. `/newbot` send karein aur apna bot name & username choose karein.
3. BotFather aapko **HTTP API Token** dega (e.g. `123456789:ABCdefGhI...`).
4. Search karein: **`@userinfobot`** aur `/start` dabayein — ye aapko aapki **Chat ID** (e.g. `987654321`) bata dega.
5. Create kiye huye bot ko open karke ek baar `/start` click karein taaki bot aapko message bhej sake.
6. `.env` file open karein aur paste karein:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhI...
TELEGRAM_CHAT_ID=987654321
```

---

## 🎮 How to Use

### 1. Interactive Studio (Recommended)
Terminal me run karein:
```powershell
py dairy_tracker.py
```
Aapko clean interactive menu milega:
- `1` ➡️ Play Store search karke category ke saare apps pool me dalein.
- `2` ➡️ Aaj ke 10 naye apps ko active tracking me add karein.
- `3` ➡️ Sabhi active apps ke updates & release notes check karein.
- `4` ➡️ Sabhi active apps ke naye customer reviews check karein.
- `5` ➡️ Poora automated cycle ek saath chalayein.
- `6` ➡️ 24/7 background worker start karein.
- `7` ➡️ Poori list ko `dairy_competitors_list.csv` (Excel) me export karein.
- `8` ➡️ Telegram bot connection test karein.

---

### 2. Command Line Shortcuts

| Kaam | Command |
|---|---|
| **Poora cycle run karein (Discover + Add 10 + Scan)** | `py dairy_tracker.py --run` |
| **Play Store se saare apps discover karein** | `py dairy_tracker.py --discover` |
| **Next 10 apps ko tracking me jodna** | `py dairy_tracker.py --add-batch` |
| **Updates check karna** | `py dairy_tracker.py --scan-updates` |
| **Naye reviews check karna** | `py dairy_tracker.py --scan-reviews` |
| **24/7 Background daemon chalu karna** | `py dairy_tracker.py --daemon` |
| **Excel / CSV file export karna** | `py dairy_tracker.py --export` |
| **Telegram test karna** | `py dairy_tracker.py --test-telegram` |

---

## 🗄️ Database Structure (`dairy_competitors.db`)
- `discovered_pool`: Play Store se discover kiye huye sabhi apps ka pool (pending/tracked).
- `tracked_apps`: Jin apps ko active monitor kiya ja raha hai (version, changelog, rating, installs, developer, links).
- `app_history`: Har ek change ka exact timestamp aur old ➡️ new value.
- `reviews`: Capture kiye huye user reviews taaki koi duplicate alert na jaye.

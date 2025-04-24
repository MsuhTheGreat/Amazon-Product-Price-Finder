# 🛍️ Amazon Product Price Finder

The **Amazon Product Price Finder** is a Python-based automation tool designed to track prices of products listed on Amazon. It leverages web scraping and cloud APIs to monitor prices, detect meaningful price drops, and notify users — making it a powerful utility for budget-conscious shoppers or e-commerce analysts.

This project integrates data collection, transformation, comparison, alerting, and cloud-based storage, offering a robust and extensible solution for real-time price monitoring.

---

## ✨ Key Features

- 🔎 **Automated Web Scraping**  
  Uses **Selenium WebDriver** to fetch live product details (title, price, availability, etc.) directly from Amazon product pages.

- 👤 **Stealth Scraping**
  Uses **Undetected Chrome Driver** to scrape stealthily and to avoid detection by Amazon's anti-bot counter measures.

- 📉 **Price Drop Detection**  
  Compares current prices against historical data and flags any drops equal to or greater than **10%**.

- 📊 **Excel Integration**  
  Reads product item names from an `items.json` file and writes products' information into    `.xlsx` spreadsheets for offline analysis.

- 📤 **Google Sheets Sync**  
  Automatically uploads the final comparison results to a linked **Google Sheets** document using the **Google Sheets API**.

- 🔔 **Real-Time Notifications**  
  Sends alert messages through the **Alertzy API** whenever a price drop is detected, helping users to act quickly.

---

## 🧪 Tech Stack

- **Programming Language:** Python 3.x  
- **Libraries:**  
  - `selenium` – browser automation  
  - `undetected-chromedriver` – stealth scraping  
  - `pandas` – data manipulation  
  - `openpyxl` – Excel file I/O  
- **APIs & Services:**  
  - **Google Sheets API** – cloud-based storage  
  - **Alertzy API** – instant push notifications

---

## 📂 Directory Structure

```
📁 Amazon-Product-Price-Finder
├── old/                     # Files containing previous scraped data for comparison  
├── new/                     # Files containing newly scraped data
├── items.json               # JSON file containing product item names used as input for scraping
├── price_finder.py          # Main script file
├── service_account.json     # Information regarding your created service account
├── .env.example             # Example data to put in .env file
├── .gitignore               # For version control
├── .env                     # Credentials for Alertzy API, Google Sheets and some others
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/MsuhTheGreat/Amazon-Product-Price-Finder.git
cd Amazon-Product-Price-Finder
```

### 2. Create and Activate a Virtual Environment (Optional but Recommended)
```bash
python -m venv .venv
# For Windows:
.venv\Scripts\activate
# For macOS/Linux:
source .venv/bin/activate
```

### 3. Install Required Packages
```bash
pip install -r requirements.txt
```

### 4. Configure Google Sheets API
- Set up a project in [Google Cloud Console](https://console.cloud.google.com/)
- Enable **Google Sheets API**
- Download the `service_account.json` file and place it in the project directory

### 5. Set Up Alertzy
- Create an account at [Alertzy](https://alertzy.app)
- Obtain your user key and add it to your `.env` file

---

## ▶️ How to Use

1. **Prepare the .env File**  
   - Enter your  credentials in `.env` file according to `.env.example` file

2. **Run the Script**
```bash
python price_finder.py
```

3. **View the Output**  
   - Updated prices and detected drops will be written to `new/`  
   - After comparison, the same data will be written to another file in `old/` for future comparison
   - Price drop alerts will be pushed to your Alertzy device  
   - Final data will be uploaded to your connected Google Sheet

---

## 🛑 Limitations

- Amazon has anti-scraping measures. Excessive or frequent requests may trigger CAPTCHA or IP bans.
- The script currently supports only **Amazon.com**. Multi-site support is a planned feature.

---

## 🔮 Planned Enhancements

- Support **multiple sites like Alibaba, Adidas etc**
- Add **robust error logging** and retry logic
- Extend **alert support** to include email and Telegram
- Create a simple **Tkinter GUI** for user-friendly execution
- Add basic price trend visualization using `matplotlib` or `plotly`
- Schedule automatic runs using `cron` or `Windows Task Scheduler`
- Create a lightweight web dashboard using `Flask` to view results

---

## 🙌 Acknowledgments

This project was designed and developed by [@MsuhTheGreat](https://github.com/MsuhTheGreat) as a practical application of web scraping, API integration, and data automation in Python.

---

## 📄 License

TThis project is licensed under the **MIT License** – see the [LICENSE](./LICENSE) file for details.
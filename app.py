import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3

# 關閉 SSL 憑證警告資訊
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定網頁標題與佈局
st.set_page_config(page_title="原始文本撈取工具", layout="wide")
st.title("🇹🇼 中華民國總統府 - 網頁原始純文字撈取")

# 側邊欄配置
st.sidebar.header("設定抓取日期")
target_date = st.sidebar.date_input("選擇日期", datetime.today())

def get_raw_text(scraped_date):
    """
    完全不設定 class 限制，直接撈取整個 body 的純文字（已修正 utf-8 編碼）
    """
    date_str = scraped_date.strftime("%Y-%m-%d")
    base_url = f"https://www.president.gov.tw/Page/37?FDate={date_str}&EDate={date_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        res = requests.get(base_url, headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            res.encoding = 'utf-8'  # 強制指定編碼，解決之前的亂碼問題
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 直接抓取整個 body 區塊
            body = soup.find("body")
            if body:
                return body.get_text(separator="\n", strip=True)
            else:
                return "成功連線，但網頁中找不到 <body> 標籤。"
        else:
            return f"連線失敗，伺服器回應狀態碼: {res.status_code}"
    except Exception as e:
        return f"執行過程中發生連線錯誤: {str(e)}"

# 點擊執行按鈕
if st.sidebar.button("擷取原始文本"):
    with st.spinner(f"正在下載 {target_date} 的原始網頁資料..."):
        
        raw_output = get_raw_text(target_date)
        st.subheader(f"📅 {target_date} 官網原始文字內容：")
        
        st.text_area(
            label="以下為爬蟲抓到的 Raw Text", 
            value=raw_output, 
            height=600
        )
else:
    st.info("請於左側選擇日期後，點擊「擷取原始文本」按鈕。")

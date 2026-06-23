import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3

# 關閉 SSL 憑證警告資訊
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定網頁標題與佈局
st.set_page_config(page_title="原始 HTML 撈取工具", layout="wide")
st.title("🇹🇼 中華民國總統府 - 網頁全區塊 Raw HTML 撈取")

# 側邊欄配置
st.sidebar.header("設定抓取日期")
target_date = st.sidebar.date_input("選擇日期", datetime.today())

def get_full_html(scraped_date):
    """
    完全不設限，直接抓取整個網頁的 body 純文字與標籤內容
    """
    date_str = scraped_date.strftime("%Y-%m-%d")
    base_url = f"https://www.president.gov.tw/Page/37?FDate={date_str}&EDate={date_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        res = requests.get(base_url, headers=headers, timeout=15, verify=False)
        
        # 返回狀態碼與網頁前 5000 個字元（通常足以看出是否被擋）
        soup = BeautifulSoup(res.text, "html.parser")
        body = soup.find("body")
        
        status_info = f"【伺服器回應狀態碼】: {res.status_code}\n"
        status_info += f"【實際請求網址】: {res.url}\n"
        status_info += "="*50 + "\n\n"
        
        if body:
            return status_info + body.get_text(separator="\n", strip=True)
        else:
            return status_info + "網頁中連 <body> 標籤都找不到，回應內容如下：\n\n" + res.text[:2000]
            
    except Exception as e:
        return f"執行過程中發生連線錯誤: {str(e)}"

# 點擊執行按鈕
if st.sidebar.button("擷取網頁全部文本"):
    with st.spinner(f"正在下載 {target_date} 的完整網頁數據..."):
        
        raw_output = get_full_html(target_date)
        st.subheader(f"📅 {target_date} 伺服器回傳全部內容：")
        
        st.text_area(
            label="請查看下方文字，確認是否包含「每日活動行程」或「拒絕存取/驗證碼」等字眼", 
            value=raw_output, 
            height=600
        )
else:
    st.info("請點擊左側「擷取網頁全部文本」按鈕。")

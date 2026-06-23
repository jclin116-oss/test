import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib3
import re

# 關閉不安全請求的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定網頁標題與佈局
st.set_page_config(page_title="總統府行程爬蟲工具", layout="wide")
st.title("🇹🇼 中華民國總統府 - 特定日期行程擷取")

# 側邊欄配置
st.sidebar.header("篩選條件設定")
target_date = st.sidebar.date_input("選擇日期", datetime.today())

def parse_schedule_by_rules(scraped_date):
    """
    依據使用者指定的規則切分與清洗官網文本
    """
    date_str = scraped_date.strftime("%Y-%m-%d")
    base_url = f"https://www.president.gov.tw/Page/37?FDate={date_str}&EDate={date_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # 用來合併行程的字典結構：{(對象, 星期): [行程1, 行程2, ...]}
    merged_events = {
        ("總統", ""): [],
        ("副總統", ""): [],
        ("總統府", ""): []
    }
    
    global_week = ""

    try:
        res = requests.get(base_url, headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            # 強制指定回應編碼為 utf-8，解決亂碼問題
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, "html.parser")
            content_div = soup.select_one(".page_content")
            
            if content_div:
                current_role = None
                
                # 遍歷所有子節點
                for child in content_div.descendants:
                    if child.name == "h2" and "年" in child.get_text():
                        # 擷取星期
                        week_span = child.find_next("span")
                        if week_span:
                            global_week = week_span.get_text(strip=True)
                            
                    elif child.name == "h3":
                        # 擷取對象
                        role_text = child.get_text(strip=True)
                        if role_text in ["總統", "副總統", "總統府"]:
                            current_role = role_text
                            
                    elif child.name == "ul" and current_role:
                        lis = child.find_all("li")
                        for li in lis:
                            text_content = li.get_text(" ", strip=

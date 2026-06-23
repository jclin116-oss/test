import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib3

# 關閉不安全請求的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="總統府行程爬蟲工具", layout="wide")
st.title("🇹🇼 中華民國總統府 - 特定日期行程擷取")

st.sidebar.header("篩選條件設定")
target_date = st.sidebar.date_input("選擇日期", datetime.today())

def parse_schedule_by_single_date(scraped_date):
    date_str = scraped_date.strftime("%Y-%m-%d")
    base_url = f"https://www.president.gov.tw/Page/37?FDate={date_str}&EDate={date_str}"
    all_data = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        res = requests.get(base_url, headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 精準定位官網行程包裹的外殼
            # 總統府網頁中，通常以 .page_content 下的區塊呈現
            content_div = soup.select_one(".page_content")
            
            if content_div:
                # 尋找頁面上的所有對象標題（h3：總統、副總統、總統府）
                h3_elements = content_div.find_all("h3")
                
                for h3 in h3_elements:
                    role = h3.get_text(strip=True)
                    # 只處理我們關心的對象
                    if role in ["總統", "副總統", "總統府"]:
                        # 尋找 h3 緊鄰的下一個元素是否為行程清單 ul
                        next_ul = h3.find_next_sibling("ul")
                        if next_ul:
                            lis = next_ul.find_all("li")
                            for li in lis:
                                text_content = li.get_text(" ", strip=True)
                                if text_content:
                                    all_data.append({
                                        "日期": date_str,
                                        "星期": "", # 星期若抓不到則留空，避免影響主資料
                                        "對象": role,
                                        "行程內容": text_content
                                    })
    except Exception as e:
        st.error(f"連線或解析官網時發生錯誤: {e}")

    # 確保每個身分在畫面上都有對應欄位，若真無行程則補上「無公開行程」
    roles_found = [d["對象"] for d in all_data]
    for r in ["總統", "副總統", "總統府"]:
        if r not in roles_found:
            all_data.append({
                "日期": date_str,
                "星期": "",
                "對象": r,
                "行程內容": "無公開行程"
            })
        
    return all_data

if st.sidebar.button("開始同步並篩選資料"):
    with st.spinner(f"正在擷取 {target_date} 的總統府官網數據..."):
        raw_list = parse_schedule_by_single_date(target_date)
        df = pd.DataFrame(raw_list)
        
        if not df.empty:
            role_mapping = {"總統": 1, "副總統": 2, "總統府": 3}
            df["官階權重"] = df["對象"].map(role_mapping)
            df = df.sort_values(by=["官階權重"], ascending=True)
            
            display_df = df[["日期", "星期", "對象", "行程內容"]].reset_index(drop=True)
            
            st.success(f"查詢成功！已完成 {target_date} 的行程擷取。")
            st.dataframe(display_df, use_container_width=True)
            
            csv = display_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="匯出此表格為 CSV",
                data=csv,
                file_name=f"president_schedule_{target_date}.csv",
                mime="text/csv",
            )
        else:
            st.warning("未撈取到任何資料。")
else:
    st.info("請於左側選擇日期後，點擊「開始同步並篩選資料」按鈕。")

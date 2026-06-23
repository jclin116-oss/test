import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib3

# 關閉不安全請求的警告（解決 SSL 憑證驗證失敗問題）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定網頁標題與佈局
st.set_page_config(page_title="總統府行程爬蟲工具", layout="wide")
st.title("🇹🇼 中華民國總統府 - 特定日期行程擷取")

# 側邊欄配置
st.sidebar.header("篩選條件設定")

# 僅保留特定單一日期篩選
target_date = st.sidebar.date_input("選擇日期", datetime.today())

def parse_schedule_by_single_date(scraped_date):
    """
    精準請求特定日期的總統府網頁，並解析 HTML 結構
    """
    date_str = scraped_date.strftime("%Y-%m-%d")
    
    # 總統府官方實際的日期篩選參數
    base_url = f"https://www.president.gov.tw/Page/37?FDate={date_str}&EDate={date_str}"
    all_data = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # verify=False 繞過 Missing Subject Key Identifier 的 SSL 錯誤
        res = requests.get(base_url, headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            content_div = soup.select_one(".page_content")
            
            if content_div:
                current_role = None
                current_week = ""
                
                # 遍歷網頁節點提取資料
                for child in content_div.descendants:
                    if child.name == "h2" and "年" in child.get_text():
                        # 擷取星期
                        week_span = child.find_next("span")
                        if week_span:
                            current_week = week_span.get_text(strip=True)
                            
                    elif child.name == "h3":
                        # 擷取對象（總統/副總統/總統府）
                        current_role = child.get_text(strip=True)
                        
                    elif child.name == "ul" and current_role:
                        # 擷取純文字行程清單
                        lis = child.find_all("li")
                        for li in lis:
                            text_content = li.get_text(" ", strip=True)
                            
                            # 避免重複寫入
                            if not any(d['行程內容'] == text_content and d['對象'] == current_role for d in all_data):
                                all_data.append({
                                    "日期": date_str,
                                    "星期": current_week,
                                    "對象": current_role,
                                    "行程內容": text_content
                                })
    except Exception as e:
        st.error(f"連線或解析官網時發生錯誤: {e}")

    # 若當天官網無特定對象行程，自動補齊並保留官網無行程的文字說明
    roles_found = [d["對象"] for d in all_data]
    for r in ["總統", "副總統", "總統府"]:
        if r not in roles_found:
            all_data.append({
                "日期": date_str,
                "星期": current_week if current_week else "",
                "對象": r,
                "行程內容": "無公開行程"
            })
        
    return all_data

# 點擊執行
if st.sidebar.button("開始同步並篩選資料"):
    with st.spinner(f"正在擷取 {target_date} 的總統府官網數據..."):
        
        # 撈取資料
        raw_list = parse_schedule_by_single_date(target_date)
        df = pd.DataFrame(raw_list)
        
        if not df.empty:
            # 依據官階排序權重（總統 -> 副總統 -> 總統府）
            role_mapping = {"總統": 1, "副總統": 2, "總統府": 3}
            df["官階權重"] = df["對象"].map(role_mapping)
            
            # 依照官階權重升序排序
            df = df.sort_values(by=["官階權重"], ascending=True)
            
            # 清洗最終顯示欄位（移除暫存排序欄位，無連結）
            display_df = df[["日期", "星期", "對象", "行程內容"]].reset_index(drop=True)
            
            st.success(f"查詢成功！已完成 {target_date} 的行程擷取。")
            
            # 顯示純文字表格
            st.dataframe(display_df, use_container_width=True)
            
            # 下載按鈕
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

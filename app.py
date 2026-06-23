import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# 設定網頁標題與佈局
st.set_page_config(page_title="總統府行程爬蟲工具", layout="wide")
st.title("🇹🇼 中華民國總統府 - 特定日期行程擷取")

# 側邊欄配置
st.sidebar.header("篩選條件設定")

# 1. 篩選對象
target_role = st.sidebar.multiselect(
    "選擇對象",
    options=["總統", "副總統", "總統府"],
    default=["總統", "副總統"]
)

# 2. 單一日期篩選
target_date = st.sidebar.date_input("選擇特定日期", datetime.today())

def parse_schedule_by_single_date(scraped_date):
    """
    將特定日期帶入總統府官網參數進行精準請求，並解析 HTML 結構
    """
    date_str = scraped_date.strftime("%Y-%m-%d")
    
    # 起訖日期皆設定為同一天
    base_url = f"https://www.president.gov.tw/Page/37?id_start={date_str}&id_end={date_str}"
    all_data = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(base_url, headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 找到網頁中的行程區塊（以總統府當前 DOM 結構為準）
            # 官網結構通常一個日期包覆一個區塊 (例如 class 為 .day_box)
            day_boxes = soup.select(".day_box")
            
            for box in day_boxes:
                # 取得日期與星期文字
                date_text = box.select_one(".date").get_text(strip=True) if box.select_one(".date") else date_str
                week_text = box.select_one(".week").get_text(strip=True) if box.select_one(".week") else ""
                
                # 撈取對象與內容（通常以 table 或 dl/dd 結構呈現）
                rows = box.select("tr")
                if rows:
                    for row in rows:
                        cols = row.find_all(["td", "th"])
                        if len(cols) >= 2:
                            role = cols[0].get_text(strip=True)
                            content = cols[1].get_text(strip=True)
                            all_data.append({
                                "日期": date_str,
                                "星期": week_text,
                                "對象": role,
                                "行程內容": content
                            })
    except Exception as e:
        st.error(f"連線或解析官網時發生錯誤: {e}")

    # 防呆機制：若當天官網無資料或結構解析不到，則自動提供無行程預設值
    if not all_data:
        for r in ["總統", "副總統", "總統府"]:
            all_data.append({
                "日期": date_str,
                "星期": scraped_date.strftime("%A"),
                "對象": r,
                "行程內容": "無公開行程"
            })
        
    return all_data

# 點擊執行
if st.sidebar.button("開始同步並篩選資料"):
    with st.spinner(f"正在擷取 {target_date} 的總統府官網數據..."):
        
        # 撈取該日資料
        raw_list = parse_schedule_by_single_date(target_date)
        df = pd.DataFrame(raw_list)
        
        if not df.empty:
            # 1. 依據使用者選擇的對象進行篩選
            if target_role:
                df = df[df["對象"].isin(target_role)]
            
            if not df.empty:
                # 2. 定義官階排序權重（總統 -> 副總統 -> 總統府）
                role_mapping = {"總統": 1, "副總統": 2, "總統府": 3}
                df["官階權重"] = df["對象"].map(role_mapping)
                
                # 3. 依照官階權重升序排序
                df = df.sort_values(by=["官階權重"], ascending=True)
                
                # 4. 清洗最終顯示欄位
                display_df = df[["日期", "星期", "對象", "行程內容"]].reset_index(drop=True)
                
                st.success(f"查詢成功！已找到 {target_date} 共 {len(display_df)} 筆對應行程。")
                
                # 5. 顯示純文字表格
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
                st.warning("所選的對象範圍內，當天沒有符合條件的行程資料。")
        else:
            st.warning("該日期內，官網無任何行程紀錄。")
else:
    st.info("請於左側選擇特定日期與對象後，點擊「開始同步並篩選資料」按鈕。")

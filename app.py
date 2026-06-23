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
    精準解析時間與內文分離的網頁結構，並套用合併與排除規則
    """
    date_str = scraped_date.strftime("%Y-%m-%d")
    base_url = f"https://www.president.gov.tw/Page/37?FDate={date_str}&EDate={date_str}"
    all_data = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # 初始化預設結構（確保無行程時能正確顯示）
    role_data = {
        "總統": {"星期": "", "行程": []},
        "副總統": {"星期": "", "行程": []},
        "總統府": {"星期": "", "行程": []}
    }

    try:
        res = requests.get(base_url, headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            res.encoding = 'utf-8'  # 強制修正編碼
            soup = BeautifulSoup(res.text, "html.parser")
            content_div = soup.select_one(".page_content")
            
            if content_div:
                # 擷取全域星期標題
                global_week = ""
                h2_tag = content_div.select_one("h2")
                if h2_tag and h2_tag.select_one("span"):
                    global_week = h2_tag.select_one("span").get_text(strip=True)
                
                for r in role_data.keys():
                    role_data[r]["星期"] = global_week

                # 定位各對象區塊
                h3_elements = content_div.find_all("h3")
                for h3 in h3_elements:
                    role = h3.get_text(strip=True)
                    if role in role_data:
                        # 收集該對象區塊內直到下一個區塊前的所有純文字行
                        all_lines = []
                        curr = h3.next_sibling
                        while curr and curr.name != 'h3' and curr.name != 'h2':
                            if hasattr(curr, 'get_text'):
                                text = curr.get_text(separator="\n", strip=True)
                                if text:
                                    all_lines.extend([line.strip() for line in text.split("\n") if line.strip()])
                            curr = curr.next_sibling
                        
                        # 解析文字行（處理時間與內文分離、忽略新聞標題）
                        schedules = []
                        i = 0
                        while i < len(all_lines):
                            line = all_lines[i]
                            if line == "無公開行程":
                                schedules.append("無公開行程")
                                i += 1
                            elif re.match(r"^\d{2}:\d{2}", line):  # 匹配時間開頭 (支援 09:30 或 09:00～11:30)
                                time_str = line
                                # 規則：時間的下一行必定是行程主體內容
                                if i + 1 < len(all_lines):
                                    desc_str = all_lines[i+1]
                                    schedules.append(f"{time_str} {desc_str}")
                                    i += 2  # 跳過時間與已處理的內文
                                else:
                                    schedules.append(time_str)
                                    i += 1
                            else:
                                # 此行既不是時間也不是無行程，判定為新聞標題，直接忽略
                                i += 1
                        
                        if schedules:
                            role_data[role]["行程"] = schedules
                            
    except Exception as e:
        st.error(f"連線或解析官網時發生錯誤: {e}")

    # 彙整結構並依規則合併框格
    for role, data in role_data.items():
        contents = data["行程"]
        if contents:
            if len(contents) > 1 and "無公開行程" in contents:
                contents.remove("無公開行程")
            # 實作規則 2：同對象多行程以換行符號合併在同一個框格
            joined_content = "\n".join(contents)
        else:
            joined_content = "無公開行程"
            
        all_data.append({
            "日期": date_str,
            "星期": data["星期"] if data["星期"] else global_week,
            "對象": role,
            "行程內容": joined_content
        })
        
    return all_data

# 點擊執行
if st.sidebar.button("開始同步並篩選資料"):
    with st.spinner(f"正在擷取 {target_date} 的總統府官網數據..."):
        
        raw_list = parse_schedule_by_rules(target_date)
        df = pd.DataFrame(raw_list)
        
        if not df.empty:
            # 依據官階排序權重（總統 -> 副總統 -> 總統府）
            role_mapping = {"總統": 1, "副總統": 2, "總統府": 3}
            df["官階權重"] = df["對象"].map(role_mapping)
            df = df.sort_values(by=["官階權重"], ascending=True)
            
            # 清洗最終顯示欄位
            display_df = df[["日期", "星期", "對象", "行程內容"]].reset_index(drop=True)
            
            st.success(f"查詢成功！已依據指定規則完成 {target_date} 的行程擷取。")
            
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

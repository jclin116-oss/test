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
                            text_content = li.get_text(" ", strip=True)
                            
                            # 【規則 1 實作】：判斷是否為有時間的那一行或無行程
                            # 匹配格式如：09:30...、17:00...、09:00～11:30... 或 無公開行程
                            is_time_row = re.match(r"^(\d{2}:\d{2}|無公開行程)", text_content)
                            
                            if is_time_row:
                                # 移除字典中舊的空星期鍵，保持最新星期資料
                                key_to_update = (current_role, global_week)
                                
                                # 尋找或建立該對象的行程列表
                                found_key = False
                                for k in list(merged_events.keys()):
                                    if k[0] == current_role:
                                        merged_events[key_to_update] = merged_events.pop(k)
                                        merged_events[key_to_update].append(text_content)
                                        found_key = True
                                        break
                                if not found_key:
                                    merged_events[key_to_update] = [text_content]
                                    
    except Exception as e:
        st.error(f"連線或解析官網時發生錯誤: {e}")

    # 彙整並轉為 DataFrame 格式
    final_list = []
    for (role, week), contents in merged_events.items():
        # 【規則 2 實作】：若有多筆行程，用換行符號 \n 合併在同一個框格中
        if contents:
            # 移除重複的「無公開行程」文字（如果同時存在有行程與無行程的防呆殘留）
            if len(contents) > 1 and "無公開行程" in contents:
                contents.remove("無公開行程")
            joined_content = "\n".join(contents)
        else:
            joined_content = "無公開行程"
            
        final_list.append({
            "日期": date_str,
            "星期": week if week else global_week,
            "對象": role,
            "行程內容": joined_content
        })
        
    return final_list

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
            
            # 顯示純文字表格（Streamlit 表格會自動支援 \n 換行顯示）
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

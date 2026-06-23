import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib3
import re

# 關閉 SSL 憑證警告資訊
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定網頁標題與佈局
st.set_page_config(page_title="總統府行程爬蟲工具", layout="wide")
st.title("🇹🇼 中華民國總統府 - 行程解析工具")

# 側邊欄配置
st.sidebar.header("設定抓取日期")
target_date = st.sidebar.date_input("選擇日期", datetime.today())

def parse_raw_text_to_table(scraped_date):
    """
    依據純文字行規律切分，過濾非時間行程行，並合併同官階資料
    """
    date_str = scraped_date.strftime("%Y-%m-%d")
    base_url = f"https://www.president.gov.tw/Page/37?FDate={date_str}&EDate={date_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # 儲存各官階解析結果的容器
    parsed_data = {
        "總統": {"時間": [], "行程內容": []},
        "副總統": {"時間": [], "行程內容": []},
        "總統府": {"時間": [], "行程內容": []}
    }

    try:
        res = requests.get(base_url, headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, "html.parser")
            body = soup.find("body")
            
            if body:
                # 取得整頁純文字並切分成獨立的行
                raw_text = body.get_text(separator="\n", strip=True)
                lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
                
                current_role = None
                i = 0
                while i < len(lines):
                    line = lines[i]
                    
                    # 檢查是否進入目標官階區塊
                    if line in parsed_data.keys():
                        current_role = line
                        i += 1
                        continue
                    
                    # 開始處理該官階下的文字行
                    if current_role:
                        if line == "無公開行程":
                            parsed_data[current_role]["時間"].append("-")
                            parsed_data[current_role]["行程內容"].append("無公開行程")
                            i += 1
                        elif re.match(r"^\d{2}:\d{2}", line):  # 匹配時間行（如 09:30 或 09:00～11:30）
                            time_val = line
                            # 下一行若非特殊標籤，即為行程內容
                            if i + 1 < len(lines) and not (lines[i+1] in parsed_data.keys() or lines[i+1] == "無公開行程" or re.match(r"^\d{2}:\d{2}", lines[i+1])):
                                content_val = lines[i+1]
                                parsed_data[current_role]["時間"].append(time_val)
                                parsed_data[current_role]["行程內容"].append(content_val)
                                i += 2  # 跳過時間與內容行
                            else:
                                parsed_data[current_role]["時間"].append(time_val)
                                parsed_data[current_role]["行程內容"].append("")
                                i += 1
                        else:
                            # 既非時間也非無公開行程，判定為新聞標題或雜訊，直接跳過
                            i += 1
                    else:
                        i += 1
    except Exception as e:
        st.error(f"連線或解析時發生錯誤: {e}")

    # 彙整成最終清單，並依據官階權重排序
    final_rows = []
    for role in ["總統", "副總統", "總統府"]:
        times = parsed_data[role]["時間"]
        contents = parsed_data[role]["行程內容"]
        
        # 若該官階有實際行程，移除初始化或殘留的「無公開行程」防呆資料
        if len(times) > 1 and "-" in times:
            idx = times.index("-")
            times.pop(idx)
            contents.pop(idx)
            
        if times and contents:
            # 同一框格內有多筆行程時，以換行符號 \n 串接
            joined_time = "\n".join(times)
            joined_content = "\n".join(contents)
        else:
            joined_time = "-"
            joined_content = "無公開行程"
            
        final_rows.append({
            "時間": joined_time,
            "官階": role,
            "行程內容": joined_content
        })
        
    return final_rows

# 執行按鈕
if st.sidebar.button("開始同步並篩選資料"):
    with st.spinner(f"正在解析 {target_date} 的行程數據..."):
        
        result_list = parse_raw_text_to_table(target_date)
        df = pd.DataFrame(result_list)
        
        st.success(f"查詢成功！已完成 {target_date} 的行程解析。")
        
        # 顯示指定欄位順序的純文字表格
        st.dataframe(df[["時間", "官階", "行程內容"]], use_container_width=True)
        
        # 下載按鈕
        csv = df[["時間", "官階", "行程內容"]].to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="匯出此表格為 CSV",
            data=csv,
            file_name=f"president_schedule_{target_date}.csv",
            mime="text/csv",
        )
else:
    st.info("請於左側選擇日期後，點擊「開始同步並篩選資料」按鈕。")

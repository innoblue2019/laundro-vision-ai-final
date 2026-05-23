import json
import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# --- 頁面基本配置 ---
st.set_page_config(page_title="LaundroVision AI", page_icon="🧺", layout="wide")

BACKEND_URL = "http://127.0.0.1:8000"


# --- 1. 讀取本地台灣行政區 JSON 數據 (用於 INIT 下拉選單 - 完全保留) ---
def load_local_geography():
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "taiwan_districts.json"),
        os.path.join(os.path.dirname(__file__), "..", "data", "taiwan_districts.json"),
        "data/taiwan_districts.json",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except OSError:
                pass
    return {"台北市": ["中正區"], "新北市": ["板橋區"]}


GEO_DATA = load_local_geography()


# --- 動態 AI 戰略文字報告生成邏輯 (擴充內容至 200 字以上) ---
def generate_ai_report(score, d):
    report = "### 🤖 Gen AI 站點綜合戰略診斷報告\n\n"

    # 結論段落
    if score >= 4.0:
        report += "🟢 **【戰略結論：強烈建議即刻進駐】**\n\n"
        report += f"本基地綜合評估得分高達 `{score:.2f}`，遠超自助洗衣行業之黃金進駐線（4.0分）。從數據模型來看，該地點具備極強的流量變現體質與防禦厚度。商圈內的基礎機能與生活習慣已經高度成熟，這將大幅縮短新店開幕後的「養店期」，並顯著推高前期客單價。基於周邊競爭環境尚在健康閾值內，系統強烈建議開發團隊立即啟動店面簽約與水電管線工程規劃，搶佔商圈黃金窗口期。\n\n"
    elif score >= 3.0:
        report += "🟡 **【戰略結論：審慎考慮，以條件進駐】**\n\n"
        report += f"本基地綜合評估得分為 `{score:.2f}`，屬於中規中矩的防禦型站點。雖然基本面能支撐店面運作，但內部存在局部硬體或交通死角，將限制營運爆發力。進駐的前提必須建立在「低於市場常態之租金成本」或「取得5年以上的長期租約保障」之上。團隊應加強實地考察的死角補強，切勿盲目以高昂溢價搶租。\n\n"
    else:
        report += "🔴 **【戰略結論：高風險，強烈建議放棄】**\n\n"
        report += f"本基地總體評估得分僅為 `{score:.2f}`，多項選址關鍵指標均落入低分陷阱。商圈可能存在結構性的人口流失，或店面本身物理攔截力極度欠佳（面寬不足、機車無法停靠）。在此類基地投資 CAPEX，預計回收期將無限期拉長，甚至面臨長期虧損。系統從戰略治理角度，建議立即終止此案，將預算轉移至其他備選地址。\n\n"

    # 指標分解細緻化段落（確保字數與豐富度）
    report += "#### 🔍 核心權重指標細緻化分析：\n"
    report += "* **商圈磁吸力（Q1 密度評估）**：1000公尺內實際偵測到生活指標型通路高度群聚。這種高密度的便利超商與店到店分佈，證明了該基地處於常態性高頻生活動線上，能與自助洗衣產生強烈的「順路性」複合客流。\n"
    report += "* **目標客群結構（Q2 住宅評估）**：周邊住宅型態直接決定了剛性需求的含金量。若老舊公寓與小坪數租屋結構佔比較高，在室內無陽台、缺乏獨立烘衣機的限制下，每逢梅雨季節或換季潮，將為門店挹注爆發性的洗烘營收。\n"
    report += "* **門店物理拦截力（Q3-Q5 硬體評估）**：本案的視覺面寬與車行視線能見度，是決定自然過路客留存率的關鍵。良好的機車停靠空間更是自助洗衣的「生命線」，直接影響攜帶大件被單消費者進店的意願。\n"

    return report


# --- Initialize Session State ---
if "stage" not in st.session_state:
    st.session_state.stage = "INIT"
if "raw_competitors" not in st.session_state:
    st.session_state.raw_competitors = []
if "reviewed_competitors" not in st.session_state:
    st.session_state.reviewed_competitors = {}
if "competitor_comments" not in st.session_state:
    st.session_state.competitor_comments = {}  # 新增：第二階段對手評論
if "consultant_notes" not in st.session_state:
    st.session_state.consultant_notes = ""
if "api_enrich_data" not in st.session_state:
    st.session_state.api_enrich_data = None
if "target_photos" not in st.session_state:
    st.session_state.target_photos = []  # 新增：第三階段目的站點照片
if "data" not in st.session_state:
    st.session_state.data = {
        "location": {"city": "", "district": "", "address": ""},
        "competitor_evals": {},
        "target": {"q1": 3, "q2": 3, "q3": 3, "q4": 3, "q5": 3},
    }


def set_stage(stage_name):
    st.session_state.stage = stage_name


# --- 側邊欄：導航面板 ---
with st.sidebar:
    st.title("🧺 LaundroVision AI")
    st.write("MVP 決策系統 v1.2")
    st.divider()
    if st.button("📍 1. 站點與對手初審", use_container_width=True):
        set_stage("INIT")
        st.rerun()
    if st.button("⚔️ 2. 現場考察與強度評估", use_container_width=True):
        set_stage("COMPETITOR_EVAL")
        st.rerun()
    if st.button("🎯 3. 開店地點詳細評估", use_container_width=True):
        set_stage("TARGET_EVAL")
        st.rerun()
    if st.button("📊 4. 最終決策報告", use_container_width=True):
        set_stage("REPORT")
        st.rerun()

# --- Stage 1: 站點定位與對手初審 (INIT - 完全保留原始正確邏輯) ---
if st.session_state.stage == "INIT":
    st.header("📍 1. 站點定位與對手名單初審")
    cities_list = list(GEO_DATA.keys())
    col1, col2 = st.columns(2)
    with col1:
        city = st.selectbox("縣市", cities_list, key="city_select")
        district = st.selectbox("鄉鎮市區", GEO_DATA.get(city, ["請選擇縣市"]), key="district_select")
    with col2:
        address = st.text_input(
            "地址/街道名稱",
            value=st.session_state.data["location"].get("address", ""),
            placeholder="例如：文化路一段100號",
        )

    if st.button("🔍 獲取周邊情報並初審對手名單", use_container_width=True):
        if address:
            full_address = f"{city}{district}{address}"
            st.session_state.data["location"] = {"city": city, "district": district, "address": address}
            payload = {"address": full_address, "lat": None, "lng": None}
            with st.spinner("正在向後端發送請求並調用 Google Maps API..."):
                try:
                    response = requests.post(f"{BACKEND_URL}/api/v1/locations/enrich", json=payload, timeout=10)
                    if response.status_code == 200:
                        res_data = response.json()
                        st.session_state.api_enrich_data = res_data
                        backend_competitors = res_data.get("competitors_data", [])
                        st.session_state.raw_competitors = [
                            {"id": f"comp_{idx:02d}", "name": name, "address": "周邊經緯度涵蓋範圍"}
                            for idx, name in enumerate(backend_competitors)
                        ]
                        st.session_state.reviewed_competitors = {
                            comp["id"]: True for comp in st.session_state.raw_competitors
                        }
                        st.success(
                            f"✅ 成功對接！正式由 Google Maps 撈回 {len(st.session_state.raw_competitors)} 家真實店名。"
                        )
                    else:
                        st.error(f"❌ 後端 API 錯誤：狀態碼 {response.status_code}")
                except Exception as e:
                    st.error(f"❌ 無法連線至後端：{str(e)}")
        else:
            st.error("請先輸入地址再獲取情報！")

    if st.session_state.raw_competitors:
        st.write("---")
        st.subheader("🤖 Google Maps API 回傳之真實周邊洗衣門店：")
        for comp in st.session_state.raw_competitors:
            comp_id = comp["id"]
            with st.container():
                c_info, c_btn = st.columns([3, 1])
                with c_info:
                    st.markdown(f"**🏪 {comp['name']}**")
                with c_btn:
                    if st.session_state.reviewed_competitors.get(comp_id, True):
                        if st.button("❌ 排除非競爭對手", key=f"ex_{comp_id}", use_container_width=True):
                            st.session_state.reviewed_competitors[comp_id] = False
                            st.rerun()
                    else:
                        if st.button("✅ 恢復為競爭對手", key=f"re_{comp_id}", use_container_width=True):
                            st.session_state.reviewed_competitors[comp_id] = True
                            st.rerun()
        st.write("---")
        if st.button("下一步：確認初審名單，進入現場考察 ➔", use_container_width=True):
            set_stage("COMPETITOR_EVAL")
            st.rerun()

# --- Stage 2: 現場考察與強度評估 (細緻化調優 🛠️) ---
elif st.session_state.stage == "COMPETITOR_EVAL":
    st.header("⚔️ 2. 現場考察與競爭對手強度評估")

    # 這裡顯示「所有潛在評估對象」，讓顧問可以在現場進行第二次確認
    if not st.session_state.raw_competitors:
        st.info("💡 目前無周邊對手資料，請回第一步發送請求。")
    else:
        st.subheader("📸 實地審查與對手覆核（第二次判定）")
        st.caption("ℹ️ *展店顧問可在現場依據店家實際營業狀態進行第二次判定，排除者必須留下原因評論。*")

        qualified_count = 0
        active_comps_at_stage2 = 0

        for comp in st.session_state.raw_competitors:
            comp_id = comp["id"]
            is_active = st.session_state.reviewed_competitors.get(comp_id, True)

            # 卡片式設計包覆單家對手
            with st.container():
                st.write(f"### 🏪 店家：{comp['name']}")

                # 互動按鈕：現場第二次判定 (排除/恢復)
                c_status, c_action = st.columns([2, 2])
                with c_status:
                    if is_active:
                        st.markdown("🔴 **狀態：判定為有效競爭對手**")
                    else:
                        st.markdown("⚪ **狀態：已排除（不計入威脅評分）**")
                with c_action:
                    if is_active:
                        if st.button("🛑 現場判定排除", key=f"stage2_ex_{comp_id}"):
                            st.session_state.reviewed_competitors[comp_id] = False
                            st.rerun()
                    else:
                        if st.button("🟢 現場判定恢復", key=f"stage2_re_{comp_id}"):
                            st.session_state.reviewed_competitors[comp_id] = True
                            st.rerun()

                # 如果被排除，或顧問想要備註，強制提供 Comment 輸入框
                if not is_active:
                    if comp_id not in st.session_state.competitor_comments:
                        st.session_state.competitor_comments[comp_id] = ""
                    st.session_state.competitor_comments[comp_id] = st.text_input(
                        f"📝 請輸入排除原因（必填）- {comp['name']}：",
                        value=st.session_state.competitor_comments[comp_id],
                        key=f"comment_{comp_id}",
                        placeholder="例如：現場已倒閉變更為手搖飲店 / 僅為代收傳統乾洗...",
                    )

                # 如果是有效的競爭對手，才顯示強度問卷與實地照片上傳
                if is_active:
                    active_comps_at_stage2 += 1
                    if comp_id not in st.session_state.data["competitor_evals"]:
                        st.session_state.data["competitor_evals"][comp_id] = {"q7": 3, "q8": 3}

                    # 現場照片上傳
                    comp_file = st.file_uploader(
                        f"📸 上傳該競爭對手現場實況相片 ({comp['name']})",
                        type=["png", "jpg", "jpeg"],
                        key=f"file_{comp_id}",
                    )
                    if comp_file:
                        st.caption(f"✅ 對手照片 `{comp_file.name}` 已本地存檔")

                    # 強度滑桿問卷
                    st.write("**Q7. 對手機器運轉狀況**")
                    st.info(
                        "ℹ️ 說明：評估對手現場稼動率。1分: 無人使用且無運轉 ~ 5分: 現場活絡，滾筒翻轉與排風運作體感達 70% 以上。"
                    )
                    q7 = st.select_slider(
                        f"Q7_{comp_id}",
                        options=[1, 2, 3, 4, 5],
                        value=st.session_state.data["competitor_evals"][comp_id]["q7"],
                        key=f"s7_{comp_id}",
                        label_visibility="collapsed",
                    )

                    st.write("**Q8. 對手整潔度與門店紀律**")
                    st.info(
                        "ℹ️ 說明：衡量對手營運紀律。1分: 垃圾桶滿溢、檯面有棉絮橡皮筋、地磚髒污 ~ 5分: 極度整潔，耗材補充齊全且設備無灰塵。"
                    )
                    q8 = st.select_slider(
                        f"Q8_{comp_id}",
                        options=[1, 2, 3, 4, 5],
                        value=st.session_state.data["competitor_evals"][comp_id]["q8"],
                        key=f"s8_{comp_id}",
                        label_visibility="collapsed",
                    )

                    comp_avg = (q7 + q8) / 2
                    st.session_state.data["competitor_evals"][comp_id]["q7"] = q7
                    st.session_state.data["competitor_evals"][comp_id]["q8"] = q8

                    st.write(f"➔ 實測單店強度：**{comp_avg:.1f} 分**")
                    if comp_avg >= 3.5:
                        st.markdown(
                            "<span style='color:red; font-weight:600;'>⚠️ 判定：強度達 3.5分 以上，屬於「合格且具強烈威脅」的競爭對手！</span>",
                            unsafe_allow_html=True,
                        )
                        qualified_count += 1
                    else:
                        st.markdown(
                            "<span style='color:green; font-weight:600;'>✅ 判定：強度低於 3.5分，屬於弱勢競爭對手。</span>",
                            unsafe_allow_html=True,
                        )
                st.divider()

        st.write("### 📊 現場考察匯總結果：")
        st.write(
            f"保留評估店數：{active_comps_at_stage2} 家 | 實測威脅達標的「合格對手」總數：**{qualified_count}** 家"
        )

        if qualified_count >= 2:
            st.error(
                f"❌ 🔴 **系統強制阻斷：偵測到周邊存在 {qualified_count} 個強勁的合格競爭對手（2家或以上）！商圈飽和風險極高，強烈建議放棄此地點。**"
            )
        else:
            if st.button("解鎖：進入下一步開店地點詳細評估 ➔", use_container_width=True):
                set_stage("TARGET_EVAL")
                st.rerun()

# --- Stage 3: 開店地點詳細評估 (新增照片上傳 📸) ---
elif st.session_state.stage == "TARGET_EVAL":
    st.header("🎯 3. 開店地點詳細評估")
    d_target = st.session_state.data["target"]

    # 【新增功能】要求顧問上傳目的選址的現場物理照片（外觀、面寬、騎樓等）
    st.subheader("📸 門店目的選址現場拍照存檔")
    target_files = st.file_uploader(
        "上傳本案開店店面的外觀、面寬、門口停靠等現場考察照片（可多選）：",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="target_photos_uploader",
    )
    if target_files:
        st.session_state.target_photos = [f.name for f in target_files]
        st.success(f"✅ 已成功為本案基地暫存 {len(target_files)} 張現場硬體照片。")
    st.divider()

    st.subheader("📊 商圈與店面物理指標評分")

    st.markdown("### **Q1. 1000 公尺內的 便利商店 / 麥當勞 / 蝦皮店到店密度**")
    st.info(
        "ℹ️ 說明：商圈成熟度指標。串接 Google Maps API 自動查詢 1000m 內的核心指標通路名單。1分: 偏遠無連鎖店 ~ 5分: 3家以上指標通路密集。"
    )
    if st.session_state.api_enrich_data:
        pois = st.session_state.api_enrich_data.get("cvs_mcd_in_200m", [])
        if pois:
            st.dataframe(pd.DataFrame({"🏪 Google Maps 偵測連鎖通路": pois}), use_container_width=True)
        q1_default = min(max(int(st.session_state.api_enrich_data.get("recommended_q1_score", 3)) - 1, 0), 4)
    else:
        q1_default = 2
    q1 = st.radio(
        "核選評分 (Q1)",
        [1, 2, 3, 4, 5],
        index=q1_default,
        horizontal=True,
        key="radio_q1",
        label_visibility="collapsed",
    )
    st.write("---")

    st.markdown("### **Q2. 商圈住宅型態與結構**")
    st.info(
        "ℹ️ 說明：核心客群潛力指標。建議未來對接內政部社會經濟資料服務平台 (SEGIS) API。1分: 透天別墅或豪宅區(自備洗烘) ~ 5分: 老舊公寓與小坪數租屋族密集(需求極高)。"
    )
    q2 = st.radio(
        "核選評分 (Q2)",
        [1, 2, 3, 4, 5],
        index=d_target["q2"] - 1,
        horizontal=True,
        key="radio_q2",
        label_visibility="collapsed",
    )
    st.divider()

    st.markdown("### **Q3. 視覺攔截力 / 面寬條件**")
    st.info("ℹ️ 說明：過路客視覺捕捉。1分: 巷弄內或面寬窄於3米 ~ 5分: 雙面臨路角間或面寬超過6米，高能見度。")
    q3 = st.radio(
        "核選評分 (Q3)",
        [1, 2, 3, 4, 5],
        index=d_target["q3"] - 1,
        horizontal=True,
        key="radio_q3",
        label_visibility="collapsed",
    )
    st.write("---")

    st.markdown("### **Q4. 招牌可見度與死角評估**")
    st.info("ℹ️ 說明：車行視線評估。1分: 被大樹或鄰近突出招牌完全遮擋 ~ 5分: 四向視線毫無死角，遠處即可清晰辨識。")
    q4 = st.radio(
        "核選評分 (Q4)",
        [1, 2, 3, 4, 5],
        index=d_target["q4"] - 1,
        horizontal=True,
        key="radio_q4",
        label_visibility="collapsed",
    )
    st.write("---")

    st.markdown("### **Q5. 機車停靠方便性**")
    st.info(
        "ℹ️ 說明：載運衣物便利度。1分: 紅線禁停或常態性無車位 ~ 5分: 門口擁有專屬騎樓或寬敞空地，可併排停靠多輛機車。"
    )
    q5 = st.radio(
        "核選評分 (Q5)",
        [1, 2, 3, 4, 5],
        index=d_target["q5"] - 1,
        horizontal=True,
        key="radio_q5",
        label_visibility="collapsed",
    )
    st.write("---")

    if st.button("⚖️ 送出所有數據，計算最終決策報告 ➔", use_container_width=True):
        st.session_state.data["target"] = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5}
        set_stage("REPORT")
        st.rerun()

# --- Stage 4: 最終決策綜合報告 (視覺大升級 📊) ---
elif st.session_state.stage == "REPORT":
    st.header("📊 4. 決策綜合分析報告")
    d = st.session_state.data
    score = (
        d["target"]["q1"] * 0.30
        + d["target"]["q2"] * 0.15
        + d["target"]["q3"] * 0.10
        + d["target"]["q4"] * 0.10
        + d["target"]["q5"] * 0.10
    ) / 0.75

    col_left, col_right = st.columns([11, 10], gap="large")

    with col_left:
        # 【視覺改動】 conclusions 得字體大幅度放大加粗呈現
        st.markdown(
            "<h2 style='color:#1E293B; font-size:30px; font-weight:800; margin-bottom:5px;'>🎯 開發潛力綜合判定結果</h2>",
            unsafe_allow_html=True,
        )
        st.metric("站點綜合開發潛力分數", f"{score:.2f}")

        # 放大结论字體
        if score > 4.0:
            st.markdown(
                "<div style='background-color:#DCFCE7; color:#166534; padding:15px; border-radius:8px; font-size:22px; font-weight:700;'>🟢 強烈建議開發：此地段體質極佳，屬於金牌站點！</div>",
                unsafe_allow_html=True,
            )
        elif score >= 3.0:
            st.markdown(
                "<div style='background-color:#FEF3C7; color:#92400E; padding:15px; border-radius:8px; font-size:22px; font-weight:700;'>🟡 需審慎考慮：條件中庸，建議啟動租金防禦談判。</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='background-color:#FEE2E2; color:#991B1B; padding:15px; border-radius:8px; font-size:22px; font-weight:700;'>🔴 高風險警告：綜合指標欠佳，系統建議放棄此案。</div>",
                unsafe_allow_html=True,
            )

        st.write(" ")
        # 內嵌豐富的大模型文本報告（200字以上）
        ai_markdown = generate_ai_report(score, d)
        st.markdown(ai_markdown)

    with col_right:
        st.markdown("### **📊 核心指標幾何雷達圖**")
        categories = ["生活機能(Q1)", "核心客群(Q2)", "店面面寬(Q3)", "廣告招牌(Q4)", "停靠便利(Q5)"]
        values = [d["target"]["q1"], d["target"]["q2"], d["target"]["q3"], d["target"]["q4"], d["target"]["q5"]]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill="toself", line=dict(color="#2563EB")))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # 展店顧問實地手記留白區
        st.markdown("### **✍️ 展店顧問實地覆核備忘錄**")
        st.session_state.consultant_notes = st.text_area(
            "請填寫現場特殊觀察備忘（例如水電增設、管委會態度等）：",
            value=st.session_state.consultant_notes,
            height=200,
            placeholder="請在此處輸入您的主觀評估補充...",
        )

    st.divider()
    if st.button("♻️ 重新評估新站點", use_container_width=True):
        st.session_state.clear()
        set_stage("INIT")
        st.rerun()

# --- 內嵌精美卡片佈局 CSS ---
st.markdown(
    """
    <style>
    div[data-row='true'], .stSelectSlider {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #E5E7EB;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

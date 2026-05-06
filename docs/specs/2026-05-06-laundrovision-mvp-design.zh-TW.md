# LaundroVision AI MVP 詳細系統規格書 (Detailed Technical Spec)

**文件版本：** 1.1 **日期：** 2026-05-06 **狀態：** 準備實作 (Ready for Implementation)

---

## 1. 系統架構與技術棧 (System Architecture)

- **Frontend**: `Streamlit` (Python 3.11+)。負責漸進式介面與使用者狀態管理 (`st.session_state`)。
- **Backend**: `FastAPI` (Python 3.11+)。提供 RESTful API，作為前端與資料庫、外部 API、LLM 間的橋樑。
- **Database**: `PostgreSQL` + `PostGIS` 擴充。使用 `SQLAlchemy` 作為 ORM。
- **外部服務整合**:
  - **地圖圖資**: Google Maps Places API (MVP 提供 $200 免費額度) 或資料庫預載 (Seed Data) 快取。
  - **AI 生成**: OpenAI GPT-4o (或 Gemini)，負責產出文字洞察。

---

## 2. 後端 API 介面定義 (Backend API Endpoints)

FastAPI 預計實作以下核心 API 以支撐前端流程：

### 2.1 地理情報擷取 API

- **Endpoint**: `POST /api/v1/locations/enrich`
- **Input**: `{ "address": "...", "lat": 25.0, "lng": 121.5 }`
- **Logic**: 查詢 DB 快取或呼叫 Google Maps API。
- **Output**:
  ```json
  {
    "has_competitor_in_1000m": true,
    "competitors_data": [...],
    "cvs_mcd_in_200m": ["7-11", "McDonalds"],
    "has_starbucks": false
  }
  ```

### 2.2 競爭對手評估與阻斷 (Knock-out) API

- **Endpoint**: `POST /api/v1/assessments/evaluate-competitor`
- **Input**:
  `{ "q2_residential": 4, "q3_visibility": 4, "q4_signage": 3, "q5_motorcycle": 5, "q6_misc": 3, "q7_machine_status": 4, "q8_cleanliness": 5 }`
- **Logic**: 計算對手威脅分數。以 Q2 ~ Q8 (共7題) 的平均分來判斷，若 `Average(Q2~Q8) > 3.0`，判定為強敵。
- **Output**: `{ "competitor_score": 4.0, "knock_out": true, "message": "對手過於強大..." }`

### 2.3 最終分數計算 API

- **Endpoint**: `POST /api/v1/assessments/calculate-score`
- **Input**: 完整問卷 JSON (包含 Q1~Q8 分數，以及有無對手的 Flag)。
- **Logic**: 套用下方「3.2 動態權重公式」進行數學運算。
- **Output**: `{ "total_score": 4.2, "category_scores": {"audience": 4.5, "hardware": 3.8, "operations": null} }`

### 2.4 AI 洞察報告生成 API

- **Endpoint**: `POST /api/v1/reports/generate`
- **Input**: `{ "survey_data": {...}, "scores": {...}, "consultant_notes": "..." }`
- **Logic**: 將數據組裝為 Prompt 呼叫 LLM。
- **Output**: `{ "executive_summary": "本站點具備極佳客群潛力...", "radar_chart_data": [...] }`

### 2.5 財務評估 API

- **Endpoint**: `POST /api/v1/financial/calculate`
- **Input**: `{ "capex": 2000000, "rent": 50000, "estimated_customers": 1000, "unit_price": 160 }`
- **Logic**: $T = CAPEX / (Revenue - OPEX - Rent)$
- **Output**: `{ "breakeven_months": 24, "monthly_revenue": 160000 }`

---

## 3. 決策邏輯與算分公式 (Scoring Engine Rules)

根據 PRD 定義，系統依賴 **1,000 公尺內有無競爭對手** 進行動態權重切換。總分公式為：
$Final\_Score = \sum (Question\_Score_i \times Weight_i)$ （滿分 5.0 分）

### 3.1 題目定義 (Score 1~5 分) 與 UI 元件

為了優化顧問在現場使用平板電腦的操作體驗，1~5 分量表統一採用 **Streamlit 水平單選按鈕 (Horizontal Radio Buttons
`st.radio`)**：

- **Q1. 便利商店/麥當勞** (客群)：1分(無/有星巴克) ~ 5分(多家24h/麥當勞/無星巴克) - _(API 預填 + 人工覆寫 Radio Box)_
- **Q2. 商圈住宅型態** (客群)：1分(高級住宅) ~ 5分(分租套房/學生) - _(手動 Radio Box)_
- **Q3. 視覺攔截力/面寬** (硬體)：1分(巷弄/<3m) ~ 5分(三角窗/>6m) - _(手動 Radio Box)_
- **Q4. 能否設立招牌** (硬體)：1分(受阻/無法設高位) ~ 5分(無遮蔽/直招) - _(手動 Radio Box)_
- **Q5. 機車停靠便利性** (硬體)：1分(紅線/常檢舉) ~ 5分(專屬格位) - _(手動 Radio Box)_
- **Q7. 對手機器運轉狀況** (營運)：1分(無運作) ~ 5分(70%以上) - _(手動 Radio Box, 僅有對手時填寫)_
- **Q8. 對手整潔度** (營運)：1分(厚灰/雜亂) ~ 5分(極度整潔) - _(手動 Radio Box, 僅有對手時填寫)_ _(註：表單最下方將提供
  一個 Text Area 供顧問填寫「綜合文字評述」，以供 LLM 分析)_

### 3.2 動態權重配置 (Dynamic Weights Matrix)

| 評估維度     | 評估項目         | 有競爭對手 (權重%) | 無競爭對手 (權重%) |
| :----------- | :--------------- | :----------------: | :----------------: |
| **客群分析** | Q1. CVS / 麥當勞 |        30%         |        35%         |
|              | Q2. 住宅型態     |        20%         |        25%         |
| **店面硬體** | Q3. 視覺攔截力   |        10%         |        15%         |
|              | Q4. 招牌設立     |        10%         |        15%         |
|              | Q5. 機車停靠     |        10%         |        10%         |
| **營運狀態** | Q7. 機器運轉     |        10%         |        N/A         |
|              | Q8. 整潔度       |        10%         |        N/A         |
| **總計**     |                  |      **100%**      |      **100%**      |

### 3.3 燈號決策定義

- 🟢 **綠燈 (總分 > 4.0)**：優質店址，解鎖「財務評估面板」。
- 🟡 **黃燈 (總分 3.0 ~ 4.0)**：需顧問介入觀察。
- 🔴 **紅燈 (總分 < 3.0)**：高風險，建議止損。

---

## 4. UI/UX 實作流程 (Streamlit State Machine)

Streamlit 將透過 `st.session_state.stage` 變數控制「雙步驟阻斷流程 (Step-by-Step Knock-out)」：

- **Stage 1: 站點定位 (`stage == 'INIT'`)**

  - 顯示三個輸入元件：
    1. 「縣市」下拉式選單 (Dropdown)
    2. 「鄉鎮市區」下拉式選單 (Dropdown)
    3. 「地址/街道」輸入框 (Text Input)
  - 使用者送出後，呼叫 `POST /locations/enrich`，取得 API 圖資。
  - 若有對手 -> 切換至 `stage = 'COMPETITOR_EVAL'`。
  - 若無對手 -> 切換至 `stage = 'TARGET_EVAL'`。

- **Stage 2: 對手阻斷判斷 (`stage == 'COMPETITOR_EVAL'`)**

  - 畫面顯示對手綜合評估表（填寫 Q2~Q8 共 7 題）。
  - 點擊「驗證對手強度」，呼叫 `POST /evaluate-competitor`。
  - 若 `knock_out == true`：畫面亮紅燈，顯示阻斷警告，不顯示後續表單。
  - 若 `knock_out == false`：切換至 `stage = 'TARGET_EVAL'`。

- **Stage 3: 目的站點評估 (`stage == 'TARGET_EVAL'`)**

  - 依據有無對手載入對應問卷：Q1~Q5 (API 預填 Q1 並允許覆寫)。
  - 顯示「綜合文字評述 (顧問筆記)」區塊。
  - 點擊「產生報告」，呼叫 `POST /calculate-score` 與 `POST /reports/generate`。
  - 切換至 `stage = 'REPORT'`。

- **Stage 4: 報告展示與財務展開 (`stage == 'REPORT'`)**
  - 渲染雷達圖與 LLM 文字洞察。
  - 若 `total_score >= 4.0`，使用 `st.expander` 或直接渲染「財務評估區塊」，提供 CAPEX/OPEX 輸入框，點擊後呼叫
    `POST /financial/calculate` 即時展示回本月數。

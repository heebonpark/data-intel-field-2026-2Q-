import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import io
import os
import re
from core.data_handler import load_data, update_activity, log_login, backup_to_github
from core.map_generator import create_map, create_route_map, export_map_to_html

# --- Page Config ---
st.set_page_config(
    page_title="Data Intel PRO | 관리고객 현장관제",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Bridge: the map's folium popup lives in a sandboxed iframe that can't navigate
# or scroll the outer page directly, so its "바로 활동 등록하기" button posts a
# message here instead, and this listener (running in its own components iframe,
# whose window.parent is the same top-level page) scrolls the outer document.
components.html("""
<script>
window.parent.addEventListener('message', function(event) {
    if (event.data && event.data.type === 'quickRegisterScroll') {
        var el = window.parent.document.getElementById('quick_register_panel');
        if (el) { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }
    }
});
</script>
""", height=0)

# --- Theme Definitions ---
THEMES = {
    "클린 화이트 (기본)": {"bg": "#f8fafc", "sidebar": "#ffffff", "accent": "#0ea5e9", "btn1": "#2563eb", "btn2": "#3b82f6", "text": "#0f172a", "text_muted": "#475569", "border": "rgba(0, 0, 0, 0.1)"},
    "다크 네이비": {"bg": "#0f172a", "sidebar": "#1e293b", "accent": "#38bdf8", "btn1": "#2563eb", "btn2": "#3b82f6", "text": "#ffffff", "text_muted": "#cbd5e1", "border": "rgba(255, 255, 255, 0.1)"},
    "미드나잇 퍼플": {"bg": "#2e1065", "sidebar": "#3b0764", "accent": "#d8b4fe", "btn1": "#7e22ce", "btn2": "#9333ea", "text": "#ffffff", "text_muted": "#cbd5e1", "border": "rgba(255, 255, 255, 0.1)"},
    "포레스트 그린": {"bg": "#064e3b", "sidebar": "#065f46", "accent": "#34d399", "btn1": "#059669", "btn2": "#10b981", "text": "#ffffff", "text_muted": "#cbd5e1", "border": "rgba(255, 255, 255, 0.1)"},
    "옵시디언 블랙": {"bg": "#0a0a0a", "sidebar": "#171717", "accent": "#f87171", "btn1": "#dc2626", "btn2": "#ef4444", "text": "#ffffff", "text_muted": "#cbd5e1", "border": "rgba(255, 255, 255, 0.1)"}
}

if 'current_theme' not in st.session_state:
    st.session_state.current_theme = "클린 화이트 (기본)"

t = THEMES[st.session_state.current_theme]

# --- Custom CSS (Dynamic Theme Injection) ---
st.markdown(f"""
<style class="notranslate" translate="no">
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html, body, [class*="css"] {{ font-family: 'Pretendard', sans-serif; color: {t['text']} !important; }}
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{background: transparent !important;}}
.stApp {{ background-color: {t['bg']} !important; color: {t['text']} !important; }}
.sidebar .sidebar-content, section[data-testid="stSidebar"] {{ background-color: {t['sidebar']} !important; border-right: 1px solid {t['border']}; }}
h1, h2, h3 {{ font-weight: 800; letter-spacing: -0.5px; }}

/* Pill Button Styling for Sidebar */
section[data-testid="stSidebar"] .stButton>button[kind="secondary"] {{
    border-radius: 20px !important;
    border: 1px solid rgba(148, 163, 184, 0.4) !important;
    background-color: transparent !important;
    color: inherit !important;
    padding: 2px 4px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    min-height: 32px !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    line-height: 1.2 !important;
}}
section[data-testid="stSidebar"] .stButton>button[kind="primary"] {{
    border-radius: 20px !important;
    background: linear-gradient(135deg, {t['btn1']}, {t['btn2']}) !important;
    color: white !important;
    border: none !important;
    padding: 2px 4px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    min-height: 32px !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    line-height: 1.2 !important;
}}

/* Tightly pack columns in sidebar */
section[data-testid="stSidebar"] div[data-testid="column"] {{
    padding: 0 3px !important;
}}

/* Expander Styling to match screenshot */
.stExpander {{
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    margin-bottom: 0 !important;
}}
.stExpander > summary {{
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-bottom: 5px !important;
}}
.stExpander > summary p {{
    font-size: 14px !important;
    font-weight: 800 !important;
    color: {t['accent']} !important;
}}

.metric-card {{ background: {t['sidebar']}; border: 1px solid {t['border']}; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05); }}
.metric-value {{ font-size: 2rem; font-weight: 800; color: {t['accent']}; }}
.metric-label {{ font-size: 0.9rem; color: {t['text_muted']}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
.download-btn-container {{ margin-top: 20px; }}

/* Dashboard Tabs Visibility Enhancement */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: {t['sidebar']};
    border-radius: 16px;
    padding: 6px;
    gap: 8px;
    margin-bottom: 20px;
    border: 1px solid {t['border']};
}}
div[data-testid="stTabs"] [data-baseweb="tab"] {{
    flex: 1;
    display: flex;
    justify-content: center;
    border-radius: 12px;
    padding: 16px 0 !important;
    background-color: transparent;
    border: 1px solid transparent !important;
    color: {t['text_muted']} !important;
    font-size: 18px !important;
    font-weight: 800 !important;
    transition: all 0.3s ease;
}}
div[data-testid="stTabs"] [aria-selected="true"] {{
    background: linear-gradient(135deg, {t['btn1']}, {t['btn2']}) !important;
    color: white !important;
    box-shadow: 0 4px 15px -3px rgba(0, 0, 0, 0.2) !important;
    border: 1px solid {t['border']} !important;
}}
</style>
""", unsafe_allow_html=True)

# --- Session State ---
def load_and_set_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'db.csv')
    if os.path.exists(db_path):
        result = load_data(db_path)
        if isinstance(result, pd.DataFrame):
            st.session_state.processed_data = result
        else:
            st.session_state.processed_data = None
    else:
        st.session_state.processed_data = None

if 'processed_data' not in st.session_state:
    load_and_set_data()
elif st.session_state.processed_data is not None and 'activity_status' not in st.session_state.processed_data.columns:
    load_and_set_data()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'admin_branch' not in st.session_state:
    st.session_state.admin_branch = None

def button_group(key, options, cols_per_row=3):
    if key not in st.session_state:
        st.session_state[key] = options[0]
    
    for i in range(0, len(options), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            idx = i + j
            if idx < len(options):
                opt = options[idx]
                if cols[j].button(str(opt), key=f"{key}_{opt}", type="primary" if st.session_state[key] == opt else "secondary", use_container_width=True):
                    st.session_state[key] = opt
                    st.rerun()
    return st.session_state[key]

df = st.session_state.processed_data
branch_order = ["중앙", "강북", "서대문", "고양", "의정부", "남양주", "강릉", "원주"]
STATUS_OPTIONS = ["미접수", "활동중", "방문상담", "재계약", "재계약거부"]

MASTER_ADMIN_PASSWORD = "admin0303"
BRANCH_ADMIN_PASSWORDS = {
    "중앙": "451829",
    "강북": "680558",
    "서대문": "836913",
    "고양": "545482",
    "의정부": "412272",
    "남양주": "143409",
    "강릉": "791012",
    "원주": "659523",
}
LOGIN_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'login_log.csv')

def try_backup_to_github(file_path, repo_path, commit_message):
    """Best-effort GitHub backup so login/activity history survives a
    Streamlit Cloud redeploy or reboot. No-ops quietly if GITHUB_TOKEN /
    GITHUB_REPO aren't configured in st.secrets yet (e.g. running locally
    or before the admin sets them up)."""
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        repo = st.secrets.get("GITHUB_REPO")
    except Exception:
        token, repo = None, None
    if not token or not repo:
        return False
    return backup_to_github(file_path, repo_path, token, repo, commit_message)

# --- Login Screen ---
if not st.session_state.logged_in:
    st.markdown(f"""
<div class="blob blob-1"></div>
<div class="blob blob-2"></div>
<style class="notranslate" translate="no">
section[data-testid="stSidebar"] {{ display: none; }}
.stApp header {{ display: none; }}
.blob {{ position: fixed; border-radius: 50%; filter: blur(80px); opacity: 0.15; pointer-events: none; z-index: -1; }}
.blob-1 {{ width: 400px; height: 400px; background: {t['accent']}; top: -100px; left: -100px; animation: float1 8s ease-in-out infinite; }}
.blob-2 {{ width: 300px; height: 300px; background: {t['btn1']}; bottom: -80px; right: -80px; animation: float2 10s ease-in-out infinite; }}
@keyframes float1 {{ 0%,100%{{transform:translate(0,0);}} 50%{{transform:translate(40px,30px);}} }}
@keyframes float2 {{ 0%,100%{{transform:translate(0,0);}} 50%{{transform:translate(-30px,-40px);}} }}
div[data-testid="stTabs"] {{ background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 24px; padding: 35px 30px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.03); animation: fadeUp 0.7s ease-out; }}
@keyframes fadeUp {{ 0% {{ opacity: 0; transform: translateY(24px); }} 100% {{ opacity: 1; transform: translateY(0); }} }}
.stTabs [data-baseweb="tab-list"] {{ background-color: transparent; gap: 20px; justify-content: center; }}
.stTabs [data-baseweb="tab"] {{ padding-top: 10px; padding-bottom: 10px; }}
.stSelectbox>div>div, .stTextInput>div>div {{ background: rgba(255, 255, 255, 0.06) !important; border: 1px solid rgba(255, 255, 255, 0.12) !important; border-radius: 12px !important; transition: all 0.3s ease; }}
.stSelectbox>div>div:focus-within, .stTextInput>div>div:focus-within {{ border-color: {t['accent']} !important; box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.12) !important; }}
</style>
""", unsafe_allow_html=True)

    # HTML Header matching the requested design
    st.markdown(f"""
<div style="text-align: center; margin-bottom: 20px; margin-top: 5vh; animation: fadeUp 0.5s ease-out;">
    <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); color: {t['accent']}; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-bottom: 20px;">
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-top: -1px;"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
        Data Intel PRO 보안 접속
    </div>
    <h1 style="font-size: 32px; font-weight: 800; line-height: 1.2; margin-bottom: 8px; color: {t['text']}; letter-spacing: -1px;">현장 지도/방문<br>관제 시스템</h1>
    <p style="font-size: 14px; color: {t['text_muted']}; line-height: 1.5;">관리고객 유지이탈 관리 데이터를 안전하게 보호합니다.<br>현장직원은 본인 구역을 선택하고, 관리자는 비밀번호를 입력하세요.</p>
</div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Info Banner inside Streamlit flow
        st.markdown(f"""
<div style="display: flex; align-items: flex-start; gap: 10px; background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 12px; padding: 12px 14px; margin-bottom: 20px; font-size: 12.5px; color: {t['accent']}; line-height: 1.5; animation: fadeUp 0.6s ease-out;">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0; margin-top:1px"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
    <span>담당 영업구역의 데이터만 표시됩니다. 전체 권한이 필요하시면 관리자 로그인 탭을 이용하세요.</span>
</div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["👤 현장직원 로그인", "🛡️ 관리자 권한"])
        
        with tab1:
            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
            if df is not None:
                existing_branches = df['branch'].dropna().unique()
                login_branches = [b for b in branch_order if b in existing_branches] + [b for b in existing_branches if b not in branch_order]
                login_types = ["SP", "SG", "SE"]
            else:
                login_branches = branch_order
                login_types = ["SP", "SG", "SE"]
                
            l_branch = st.selectbox("소속 지사", login_branches, key="login_branch")
            l_type = st.selectbox("활동대상 구분", login_types, key="login_type")
            
            # Dependent dropdown for Zone!
            if df is not None:
                available_zones = sorted(list(df[df['branch'] == l_branch]['zone'].dropna().unique()))
                if not available_zones:
                    available_zones = ["데이터 없음"]
            else:
                available_zones = ["데이터 없음"]
                
            l_zone = st.selectbox("영업구역번호", available_zones, key="login_zone")
            
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            if st.button("🗺️ 지도 접속하기", type="primary", use_container_width=True, key="btn_user_login"):
                if l_zone == "데이터 없음" or not l_zone:
                    st.warning("선택한 지사에 구역 데이터가 없습니다.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.role = 'user'
                    st.session_state.user_info = {
                        'branch': l_branch,
                        'target_type': l_type,
                        'zone': l_zone
                    }
                    log_login(LOGIN_LOG_PATH, '현장직원', branch=l_branch, target_type=l_type, zone=l_zone)
                    try_backup_to_github(LOGIN_LOG_PATH, 'login_log.csv', f'Login: 현장직원 {l_branch}/{l_type}/{l_zone}')
                    st.rerun()
                    
        with tab2:
            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
            admin_scope_options = ["🌐 전체 (마스터 관리자)"] + branch_order
            admin_scope = st.selectbox("지사 선택", admin_scope_options, key="login_admin_branch")
            admin_pw = st.text_input("비밀번호", type="password", key="login_admin_pw", placeholder="비밀번호 입력")

            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            if st.button("🗺️ 전체 대시보드 접속", type="primary", use_container_width=True, key="btn_admin_login"):
                is_master = admin_scope == "🌐 전체 (마스터 관리자)"
                expected_pw = MASTER_ADMIN_PASSWORD if is_master else BRANCH_ADMIN_PASSWORDS.get(admin_scope)
                if admin_pw == expected_pw:
                    st.session_state.logged_in = True
                    st.session_state.role = 'admin'
                    st.session_state.admin_branch = None if is_master else admin_scope
                    login_type = '마스터관리자' if is_master else '지사관리자'
                    log_login(LOGIN_LOG_PATH, login_type, branch=('전체' if is_master else admin_scope))
                    try_backup_to_github(LOGIN_LOG_PATH, 'login_log.csv', f'Login: {login_type} {admin_scope}')
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")

    # Footer Credit
    st.markdown("""
<div style="position: fixed; bottom: 20px; right: 24px; font-size: 11px; color: rgba(148,163,184,0.5); font-weight: 500;">
    Developed by SE-EUN Daddy
</div>
    """, unsafe_allow_html=True)
                    
    st.stop()


# --- Main App (Logged In) ---
col_title, col_theme = st.columns([4, 1])
with col_title:
    st.markdown(f"<h1 style='margin-top: -15px;'>🗺️ Data Intel PRO <span style='color: {t['accent']}; font-weight: 300;'>| 관리고객 현장관제</span></h1>", unsafe_allow_html=True)
with col_theme:
    selected_theme = st.selectbox("테마 선택", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.current_theme), label_visibility="collapsed", key="theme_selector")
    if selected_theme != st.session_state.current_theme:
        st.session_state.current_theme = selected_theme
        st.rerun()

# Branch-scoped admins only ever work with their own branch's data
if st.session_state.role == 'admin' and st.session_state.admin_branch and df is not None:
    df = df[df['branch'] == st.session_state.admin_branch]

# --- Sidebar ---
with st.sidebar:
    st.markdown("<h3>👤 내 정보</h3>", unsafe_allow_html=True)
    if st.session_state.role == 'admin':
        if st.session_state.admin_branch:
            st.info(f"🛡️ {st.session_state.admin_branch} 지사 관리자로 접속 중")
        else:
            st.info("🛡️ 마스터 관리자 권한으로 접속 중")
    else:
        info = st.session_state.user_info
        st.success(f"👤 {info['branch']} | {info['target_type']} | {info['zone'].upper()}")
        
    if st.button("🔄 최신 데이터 새로고침", use_container_width=True):
        load_and_set_data()
        st.rerun()

    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_info = {}
        st.session_state.admin_branch = None
        # Clear filter states
        keys_to_clear = ['filter_type', 'filter_branch', 'filter_zone', 'filter_status', 'login_branch', 'login_type', 'login_zone', 'login_admin_pw', 'login_admin_branch', 'map_clicked_tooltip']
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()
        
    st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    
    if st.session_state.role == 'admin':
        if df is not None:
            
            with st.expander("활동대상 구분", expanded=True):
                available_types = df['target_type'].dropna().unique()
                ordered_types = ["전체"] + [t for t in ["SP", "SE", "SG"] if t in available_types] + [t for t in available_types if t not in ["SP", "SE", "SG"]]
                selected_type = button_group("filter_type", ordered_types, cols_per_row=4)
            
            # Apply Type filter for cascading options
            df_type = df if selected_type == "전체" else df[df['target_type'] == selected_type]
            
            with st.expander("지표별 마커 선택", expanded=True):
                # Map specific statuses to emojis matching the user's screenshot
                status_emoji = {
                    "사전리텐션": "🟢 사전리텐션",
                    "정지": "🔴 정지",
                    "부실": "🟠 부실",
                    "체납직권(정지)": "🟤 체납직권(정지)",
                    "방문상담": "💬 방문상담",
                    "방문활동(표지판교체)": "💬 방문활동(표지판교체)",
                    "활동중": "🔧 활동중",
                    "재계약": "🌟 재계약",
                    "재계약거부": "❌ 재계약거부"
                }
                
                raw_statuses = df_type['status'].dropna().unique()
                
                # Create the display options with emojis
                status_options = ["🔵 전체"]
                for s in raw_statuses:
                    if s in status_emoji:
                        status_options.append(status_emoji[s])
                    else:
                        status_options.append(f"⚪ {s}")
                        
                if 'filter_status' in st.session_state and st.session_state.filter_status not in status_options:
                    st.session_state.filter_status = "🔵 전체"
                    
                selected_status = button_group("filter_status", status_options, cols_per_row=2)
            
            with st.expander("담당지사/팀 선택", expanded=True):
                existing_branches = df_type['branch'].dropna().unique()
                ordered_branches = ["전체"] + [b for b in branch_order if b in existing_branches] + [b for b in existing_branches if b not in branch_order]
                
                # Reset branch if the current selected branch is no longer available
                if 'filter_branch' in st.session_state and st.session_state.filter_branch not in ordered_branches:
                    st.session_state.filter_branch = "전체"
                    
                selected_branch = button_group("filter_branch", ordered_branches, cols_per_row=4)
            
            # Apply Branch filter for cascading Zone options
            df_branch = df_type if selected_branch == "전체" else df_type[df_type['branch'] == selected_branch]
            
            with st.expander("영업구역번호 선택", expanded=True):
                zones = ["전체"] + sorted(list(df_branch['zone'].dropna().unique()))
                if 'filter_zone' in st.session_state and st.session_state.filter_zone not in zones:
                    st.session_state.filter_zone = "전체"
                selected_zone = button_group("filter_zone", zones, cols_per_row=3)
                
            # Apply Zone filter
            df_zone = df_branch if selected_zone == "전체" else df_branch[df_branch['zone'] == selected_zone]
                
    else:
        info = st.session_state.user_info
        st.success(f"👤 {info['branch']} | {info['target_type']} | {info['zone'].upper()}")
        
        if df is not None:
            # Filter df down to user's scope for the status options
            df_user = df[(df['branch'] == info['branch']) & 
                         (df['target_type'] == info['target_type']) & 
                         (df['zone'].astype(str).str.lower() == str(info['zone']).lower())]
                         
            with st.expander("지표별 마커 선택", expanded=True):
                status_emoji = {
                    "사전리텐션": "🟢 사전리텐션",
                    "정지": "🔴 정지",
                    "부실": "🟠 부실",
                    "체납직권(정지)": "🟤 체납직권(정지)",
                    "방문상담": "💬 방문상담",
                    "방문활동(표지판교체)": "💬 방문활동(표지판교체)",
                    "활동중": "🔧 활동중",
                    "재계약": "🌟 재계약",
                    "재계약거부": "❌ 재계약거부"
                }
                
                raw_statuses = df_user['status'].dropna().unique()
                status_options = ["🔵 전체"]
                for s in raw_statuses:
                    if s in status_emoji:
                        status_options.append(status_emoji[s])
                    else:
                        status_options.append(f"⚪ {s}")
                        
                if 'filter_status' in st.session_state and st.session_state.filter_status not in status_options:
                    st.session_state.filter_status = "🔵 전체"
                    
                selected_status = button_group("filter_status", status_options, cols_per_row=2)

# --- Map Display ---
if df is not None:
    if st.session_state.role == 'user':
        info = st.session_state.user_info
        df = df[df['branch'] == info['branch']]
        df = df[df['target_type'] == info['target_type']]
        df = df[df['zone'].astype(str).str.lower() == str(info['zone']).lower()]
        df_scope = df.copy()  # full assigned scope, unaffected by the marker quick-filter below
        if 'filter_status' in st.session_state and st.session_state.filter_status != "🔵 전체":
            raw_status = st.session_state.filter_status.split(" ", 1)[1]
            df = df[df['status'] == raw_status]
    else:
        if selected_branch != "전체":
            df = df[df['branch'] == selected_branch]
        if selected_zone != "전체":
            df = df[df['zone'] == selected_zone]
        if selected_type != "전체":
            df = df[df['target_type'] == selected_type]
        df_scope = df.copy()  # full filtered scope, unaffected by the marker quick-filter below
        if selected_status != "🔵 전체":
            raw_status = selected_status.split(" ", 1)[1]
            df = df[df['status'] == raw_status]
        
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>활동대상</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
    with col2:
        visit_cnt = len(df[df['status'].isin(['방문상담', '방문활동(표지판교체)'])])
        visit_label = '방문활동(표지판교체)' if len(df) > 0 and all(df['target_type'].isin(['SE', 'SG'])) else '방문상담'
        st.markdown(f"<div class='metric-card'><div class='metric-label'>{visit_label}</div><div class='metric-value' style='color:{t['accent']};'>{visit_cnt}</div></div>", unsafe_allow_html=True)
    with col3:
        renewal_cnt = len(df[df['status'] == '재계약'])
        st.markdown(f"<div class='metric-card'><div class='metric-label'>재계약</div><div class='metric-value' style='color:{t['accent']};'>{renewal_cnt}</div></div>", unsafe_allow_html=True)
    with col4:
        no_act_cnt = len(df[df['activity_status'] == '미접수'])
        st.markdown(f"<div class='metric-card'><div class='metric-label'>미활동</div><div class='metric-value' style='color:{t['text_muted']};'>{no_act_cnt}</div></div>", unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state.role == 'admin':
        tab_summary, tab_map, tab_dashboard, tab_register, tab_loginlog = st.tabs(["📈 요약 대시보드", "🗺️ 스마트 현장 지도", "📊 종합 활동 대시보드", "✏️ 활동이력 등록", "🔐 로그인 이력"])
    else:
        tab_map, tab_register = st.tabs(["🗺️ 스마트 현장 지도", "✏️ 활동이력 등록"])
        tab_summary = None
        tab_dashboard = None
        tab_loginlog = None
    
    if tab_summary is not None:
        with tab_summary:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px; padding: 10px 15px; background: rgba(56, 189, 248, 0.05); border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);">
                <h3 style="margin: 0; font-size: 16px; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 20px;">📈</span> 전사 활동 현황 요약
                </h3>
            </div>
            """, unsafe_allow_html=True)
        
            if len(df) == 0:
                st.warning("표시할 데이터가 없습니다.")
            else:
                # Calculate Progress
                total = len(df)
                completed = len(df[df['activity_status'] != '미접수'])
                progress_pct = (completed / total * 100) if total > 0 else 0
            
                sum_col1, sum_col2 = st.columns([1, 1.5])
            
                with sum_col1:
                    # Progress Gauge/Donut
                    fig_prog = go.Figure(go.Pie(
                        values=[completed, total-completed],
                        labels=['진행완료', '미진행'],
                        hole=.7,
                        marker_colors=['#38bdf8', 'rgba(255,255,255,0.05)'],
                        textinfo='none'
                    ))
                    fig_prog.update_layout(
                        showlegend=False,
                        height=250,
                        margin=dict(l=20, r=20, t=20, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        annotations=[dict(text=f"{progress_pct:.1f}%", x=0.5, y=0.5, font_size=32, font_family="Pretendard", font_color="#38bdf8", showarrow=False)]
                    )
                    st.plotly_chart(fig_prog, use_container_width=True)
                    st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:14px;'>전체 목표 대비 진행률</div>", unsafe_allow_html=True)
                
                with sum_col2:
                    # Top Performance Branches
                    branch_perf = df.groupby('branch').apply(lambda x: (len(x[x['activity_status'] != '미접수']) / len(x) * 100)).reset_index(name='pct')
                    branch_perf = branch_perf.sort_values('pct', ascending=False)
                
                    fig_branch_rank = px.bar(
                        branch_perf,
                        x='pct',
                        y='branch',
                        orientation='h',
                        color='pct',
                        color_continuous_scale=['#1e293b', '#38bdf8'],
                        labels={'pct': '진행률 (%)', 'branch': '지사'}
                    )
                    fig_branch_rank.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=20, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Pretendard", color=t['text']),
                        coloraxis_showscale=False
                    )
                    fig_branch_rank.update_xaxes(range=[0, 100], gridcolor='rgba(255,255,255,0.05)')
                    st.plotly_chart(fig_branch_rank, use_container_width=True)

                st.markdown("<br>", unsafe_allow_html=True)
            
                # Target Type-wise Summary
                type_sum_cols = st.columns(3)
                for idx, t_type in enumerate(["SP", "SG", "SE"]):
                    t_df = df[df['target_type'] == t_type]
                    if len(t_df) > 0:
                        t_total = len(t_df)
                        t_comp = len(t_df[t_df['activity_status'] != '미접수'])
                        t_pct = (t_comp / t_total * 100)
                        t_color = '#ef4444' if t_type == 'SP' else '#f59e0b' if t_type == 'SG' else '#3b82f6'
                    
                        with type_sum_cols[idx]:
                            st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 15px; text-align: center;">
                                <div style="font-size: 12px; color: #94a3b8; margin-bottom: 5px;">{t_type} 대상 진행률</div>
                                <div style="font-size: 24px; font-weight: 800; color: {t_color};">{t_pct:.1f}%</div>
                                <div style="font-size: 11px; color: #64748b;">({t_comp} / {t_total} 건)</div>
                            </div>
                            """, unsafe_allow_html=True)
    
    with tab_map:
        # Map Toolbar with Route Toggle
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px; padding: 10px 15px; background: rgba(56, 189, 248, 0.05); border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);">
            <h3 style="margin: 0; font-size: 16px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px;">🗺️</span> 스마트 방문 관제
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        col_toggle, col_style, col_info = st.columns([1.2, 1.2, 1.6])
        with col_toggle:
            toggle_label = "🚗 최적 방문 경로 자동 생성" if st.session_state.role == 'admin' else "🚗 내 구역 방문 경로 자동 생성"
            enable_routing = st.toggle(toggle_label, value=False)
            start_index = 0
        with col_style:
            map_style_options = {
                "🏙️ 프리미엄 상세 지도 (최고해상도)": "Vworld",
                "🌙 다크 모드 (심플/야간)": "CartoDB dark_matter",
                "🗺️ 표준 지도 (OSM)": "OpenStreetMap",
                "🛰️ 위성 지도 (Hybrid)": "GoogleHybrid"
            }
            selected_style_label = st.selectbox("지도 테마", list(map_style_options.keys()), label_visibility="collapsed")
            selected_tile = map_style_options[selected_style_label]
            
        with col_info:
            if enable_routing:
                st.info("가장 가까운 10곳의 최단 방문 경로를 계산하여 지도에 표시합니다.")
        
        if len(df) == 0:
            st.warning("선택하신 조건(또는 구역)에 해당하는 데이터가 없습니다.")
        else:
            if enable_routing:
                m, total_dist = create_route_map(df, start_index=start_index, max_stops=10, tiles=selected_tile)
                st.success(f"🚗 경로 생성 완료! 총 이동거리: 약 **{total_dist:.1f} km**")
            else:
                m = create_map(df, tiles=selected_tile)
            
            if not enable_routing:
                st.caption("💡 지도에 숫자가 적힌 원(그룹)은 여러 시설이 뭉쳐있는 상태입니다. 그룹을 클릭해 확대한 뒤, 완전히 벌어진 개별 마커(작은 점)를 클릭하면 아래에 빠른 활동 등록 패널이 열립니다.")

            # Map Container Styling for a cleaner look
            st.markdown("<style>#folium-map-container { border-radius: 16px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 20px rgba(0,0,0,0.2); }</style>", unsafe_allow_html=True)
            st.markdown("<div id='folium-map-container'>", unsafe_allow_html=True)
            # returned_objects limited to the clicked tooltip so marker clicks stay lightweight
            st_data = st_folium(m, width="100%", height=750, use_container_width=True, returned_objects=["last_object_clicked_tooltip"])
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='download-btn-container'>", unsafe_allow_html=True)
            html_data = export_map_to_html(m)
            st.download_button(
                label="📥 공유용 HTML 파일 다운로드",
                data=html_data,
                file_name="관리고객_유지이탈_지도공유.html",
                mime="text/html"
            )
            st.markdown("</div>", unsafe_allow_html=True)

            # Scroll anchor: the map popup's "⚡ 바로 활동 등록하기" button links here
            # via target="_parent" so a click inside the iframe scrolls this outer page.
            st.markdown("<div id='quick_register_panel'></div>", unsafe_allow_html=True)

            # --- Quick activity registration from a clicked map marker ---
            if not enable_routing:
                # The map is rebuilt on every rerun, so st_folium's own click memory
                # resets whenever an unrelated widget (e.g. the status dropdown below)
                # triggers a rerun. Persist the last real click in session_state so the
                # panel survives interacting with its own inputs.
                fresh_tooltip = st_data.get("last_object_clicked_tooltip") if st_data else None
                if fresh_tooltip:
                    st.session_state['map_clicked_tooltip'] = fresh_tooltip
                clicked_tooltip = st.session_state.get('map_clicked_tooltip')
                match = re.search(r"계약번호:(\S+)", clicked_tooltip) if clicked_tooltip else None
                if match:
                    clicked_contract_no = match.group(1)
                    hit = df[df['contract_no'] == clicked_contract_no]
                    if len(hit) > 0:
                        target_row = hit.iloc[0]
                        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 20px 0;'>", unsafe_allow_html=True)
                        st.markdown(f"<h4 style='font-size: 15px; color: {t['accent']};'>⚡ 빠른 활동 등록 — {target_row['name']} (계약번호 {target_row['contract_no']})</h4>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size:13px; color:{t['text_muted']}; margin-bottom:10px;'>📍 {target_row['address']}</div>", unsafe_allow_html=True)

                        qcol1, qcol2, qcol3 = st.columns([1, 2, 1])
                        with qcol1:
                            q_idx = STATUS_OPTIONS.index(target_row['status']) if target_row['status'] in STATUS_OPTIONS else 0
                            q_status = st.selectbox("활동상태 변경", STATUS_OPTIONS, index=q_idx, key="map_quick_status")
                        with qcol2:
                            q_default_detail = "" if target_row['activity_detail'] == '-' else target_row['activity_detail']
                            q_detail = st.text_input("세부 활동내역 (선택)", value=q_default_detail, key="map_quick_detail")
                        with qcol3:
                            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                            if st.button("💾 저장", type="primary", use_container_width=True, key="map_quick_save"):
                                if st.session_state.role == 'admin':
                                    modifier = "관리자"
                                else:
                                    u = st.session_state.user_info
                                    modifier = f"{u['branch']}-{u['zone']}"
                                current_dir = os.path.dirname(os.path.abspath(__file__))
                                db_path = os.path.join(current_dir, 'db.csv')
                                ok = update_activity(db_path, int(target_row['_row_id']), q_status, q_detail, modifier)
                                if ok:
                                    st.success(f"'{target_row['name']}' 상태가 '{q_status}'(으)로 저장되었습니다.")
                                    try_backup_to_github(db_path, 'db.csv', f'Activity update: {target_row["name"]} -> {q_status}')
                                    st.session_state.pop('map_clicked_tooltip', None)
                                    load_and_set_data()
                                    st.rerun()
                                else:
                                    st.error("저장에 실패했습니다. 데이터를 확인해주세요.")

    if tab_dashboard is not None:
        with tab_dashboard:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px; padding: 12px 18px; background: rgba(56, 189, 248, 0.08); border-radius: 14px; border: 1px solid rgba(56, 189, 248, 0.2);">
                <h3 style="margin: 0; font-size: 18px; display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 22px;">📊</span> 실시간 활동 지표 분석
                </h3>
            </div>
            """, unsafe_allow_html=True)

            if len(df) == 0:
                st.warning("표시할 데이터가 없습니다.")
            else:
                # Common plotly layout adjustments for Data Intel PRO dark theme
                plotly_bg = 'rgba(0,0,0,0)'
                plotly_font = dict(family="Pretendard", size=12, color=t['text'])
            
                # Define status colors
                status_colors = {
                    '방문상담': '#38bdf8',
                    '방문활동(표지판교체)': '#38bdf8',
                    '활동중': '#f59e0b',
                    '재계약': '#34d399',
                    '재계약거부': '#f87171',
                    '미접수': '#94a3b8'
                }
            
                # --- Top Chart: Target Type vs Activity Status ---
                if 'activity_status' not in df.columns:
                    df['activity_status'] = '미접수'
            
                df_type_summary = df.groupby(['target_type', 'activity_status']).size().reset_index(name='count')
                type_order = ["SP", "SG", "SE"]
            
                fig_top = px.bar(
                    df_type_summary,
                    x='target_type',
                    y='count',
                    color='activity_status',
                    barmode='group',
                    category_orders={'target_type': type_order},
                    color_discrete_map=status_colors,
                    labels={'target_type': '활동대상구분', 'count': '건수', 'activity_status': '활동상태'}
                )
                fig_top.update_layout(
                    plot_bgcolor=plotly_bg, paper_bgcolor=plotly_bg, font=plotly_font,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=300
                )
                fig_top.update_yaxes(gridcolor='rgba(255,255,255,0.1)', title='')
                fig_top.update_xaxes(title='')
            
                st.markdown("<h4 style='font-size: 15px; color: #38bdf8; margin-bottom: 15px; border-left: 4px solid #38bdf8; padding-left: 10px;'>1. 대상군별 활동 요약 (SP / SG / SE)</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig_top, use_container_width=True)
            
                st.markdown("<br>", unsafe_allow_html=True)
            
                st.markdown("<br><h4 style='font-size: 15px; color: #38bdf8; margin-bottom: 15px; border-left: 4px solid #38bdf8; padding-left: 10px;'>2. 지사별 성과 분석</h4>", unsafe_allow_html=True)
            
                # --- Branch-wise Bar Chart ---
                df_branch_summary = df.groupby(['branch', 'activity_status']).size().reset_index(name='count')
                fig_branch = px.bar(
                    df_branch_summary,
                    x='branch',
                    y='count',
                    color='activity_status',
                    barmode='group',
                    color_discrete_map=status_colors,
                    labels={'branch': '지사', 'count': '건수', 'activity_status': '활동상태'}
                )
                fig_branch.update_layout(
                    plot_bgcolor=plotly_bg, paper_bgcolor=plotly_bg, font=plotly_font,
                    height=350, margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
            
                col_b1, col_b2 = st.columns([1, 1])
                with col_b1:
                    st.markdown("<p style='font-size: 13px; color: #94a3b8; margin-bottom: 5px; text-align:center;'>지사별 활동 건수 (Status별)</p>", unsafe_allow_html=True)
                    st.plotly_chart(fig_branch, use_container_width=True)
            
                with col_b2:
                    st.markdown("<p style='font-size: 13px; color: #94a3b8; margin-bottom: 5px; text-align:center;'>지사별 활동 완료율 (%)</p>", unsafe_allow_html=True)
                    # Calculate completion rate per branch
                    branch_rates = df.groupby('branch').apply(lambda x: (len(x[x['activity_status'] != '미접수']) / len(x) * 100)).reset_index(name='rate')
                    fig_rate = px.bar(
                        branch_rates,
                        x='branch',
                        y='rate',
                        color='rate',
                        color_continuous_scale=['#1e293b', '#38bdf8'],
                        labels={'branch': '지사', 'rate': '완료율 (%)'}
                    )
                    fig_rate.update_layout(
                        plot_bgcolor=plotly_bg, paper_bgcolor=plotly_bg, font=plotly_font,
                        height=350, margin=dict(l=20, r=20, t=20, b=20),
                        coloraxis_showscale=False
                    )
                    fig_rate.update_yaxes(range=[0, 100], gridcolor='rgba(255,255,255,0.1)', title='')
                    st.plotly_chart(fig_rate, use_container_width=True)

                # --- Branch vs Target Type Matrix Calculation ---
                df['is_completed'] = df['activity_status'].apply(lambda x: 1 if x != '미접수' else 0)
                pivot_df = df.pivot_table(
                    index='branch', 
                    columns='target_type', 
                    values='is_completed', 
                    aggfunc=['count', 'sum'],
                    fill_value=0
                )
            
                pivot_display = pd.DataFrame()
                for t_type in ["SP", "SG", "SE"]:
                    if t_type in pivot_df['count'].columns:
                        pivot_display[f'{t_type} (전체)'] = pivot_df['count'][t_type]
                        pivot_display[f'{t_type} (완료)'] = pivot_df['sum'][t_type]
                        pivot_display[f'{t_type} (%)'] = (pivot_df['sum'][t_type] / pivot_df['count'][t_type] * 100).round(1).astype(str) + '%'

                # Keep the pivot table as well for numerical details
                st.markdown("<p style='font-size: 13px; color: #94a3b8; margin-bottom: 10px;'>지사별 대상군 세부 현황</p>", unsafe_allow_html=True)
                st.dataframe(pivot_display, use_container_width=True)
            
                st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 30px 0;'>", unsafe_allow_html=True)
            
                st.markdown("<h4 style='font-size: 15px; color: #38bdf8; margin-bottom: 15px; border-left: 4px solid #38bdf8; padding-left: 10px;'>3. 구역별 상세 진행 현황</h4>", unsafe_allow_html=True)
            
                # --- Middle Chart: Branch/Zone vs Activity Status ---
                # Group by branch, zone, activity_status
                df_bz_summary = df.groupby(['branch', 'zone', 'activity_status']).size().reset_index(name='count')
                df_bz_summary['branch_zone'] = df_bz_summary['branch'] + " - " + df_bz_summary['zone']
            
                # Sort to keep the standard order
                branch_order_dict = {b: i for i, b in enumerate(["중앙", "강북", "서대문", "고양", "의정부", "남양주", "강릉", "원주"])}
                df_bz_summary['branch_order'] = df_bz_summary['branch'].map(lambda x: branch_order_dict.get(x, 99))
                df_bz_summary = df_bz_summary.sort_values(['branch_order', 'zone'])
            
                fig_mid = px.bar(
                    df_bz_summary,
                    x='branch_zone',
                    y='count',
                    color='activity_status',
                    barmode='stack',
                    color_discrete_map=status_colors,
                    labels={'branch_zone': '지사 및 구역', 'count': '건수', 'activity_status': '활동상태'}
                )
                fig_mid.update_layout(
                    plot_bgcolor=plotly_bg, paper_bgcolor=plotly_bg, font=plotly_font,
                    showlegend=False,
                    margin=dict(l=20, r=20, t=20, b=80),
                    height=400,
                    xaxis_tickangle=-45
                )
                fig_mid.update_yaxes(gridcolor='rgba(255,255,255,0.1)', title='')
                fig_mid.update_xaxes(title='')
            
                st.plotly_chart(fig_mid, use_container_width=True)
            
                st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 30px 0;'>", unsafe_allow_html=True)
            
                # --- Bottom: Detailed Table ---
                st.markdown("""
                <h4 style="margin: 0 0 15px 0; font-size: 15px; display: flex; align-items: center; gap: 8px; color: #38bdf8;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    세부내역
                </h4>
                """, unsafe_allow_html=True)
            
                display_cols = ['contract_no', 'service_no', 'branch', 'target_type', 'zone', 'name', 'address', 'activity_status']
                if 'activity_detail' in df.columns:
                    display_cols.append('activity_detail')
                
                col_names = {
                    'contract_no': '계약번호', 'service_no': '서비스번호', 'branch': '지사',
                    'target_type': '활동대상구분', 'zone': '구역', 'name': '상호',
                    'address': '설치주소', 'activity_status': '활동유무(O/X)', 'activity_detail': '세부 활동내역'
                }
            
                df_display = df[display_cols].rename(columns=col_names).copy()
            
                # Use st.dataframe for an interactive table
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    height=300
                )

    with tab_register:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px; padding: 10px 15px; background: rgba(56, 189, 248, 0.05); border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);">
            <h3 style="margin: 0; font-size: 16px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px;">✏️</span> 담당구역 활동이력 등록
            </h3>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.role == 'admin':
            excel_cols = ['contract_no', 'service_no', 'branch', 'target_type', 'zone', 'name', 'address', 'status', 'activity_detail', 'modifier', 'modified_at']
            excel_col_names = {
                'contract_no': '계약번호', 'service_no': '서비스번호', 'branch': '지사',
                'target_type': '활동대상구분', 'zone': '구역', 'name': '상호', 'address': '설치주소',
                'status': '활동상태', 'activity_detail': '세부 활동내역', 'modifier': '수정자', 'modified_at': '최종수정일시'
            }
            excel_df = df_scope[excel_cols].rename(columns=excel_col_names)
            excel_buffer = io.BytesIO()
            excel_df.to_excel(excel_buffer, index=False, engine='openpyxl', sheet_name='활동이력')
            st.download_button(
                label="📥 활동이력 엑셀 다운로드",
                data=excel_buffer.getvalue(),
                file_name="관리고객_활동이력.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="reg_excel_download"
            )
            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        if len(df_scope) == 0:
            st.warning("등록할 대상 시설이 없습니다.")
        else:
            search_term = st.text_input("🔍 검색 (상호명 또는 계약번호)", key="reg_search", placeholder="검색어를 입력하세요")
            df_reg = df_scope.copy()
            if search_term:
                mask = (
                    df_reg['name'].str.contains(search_term, case=False, na=False) |
                    df_reg['contract_no'].astype(str).str.contains(search_term, case=False, na=False)
                )
                df_reg = df_reg[mask]
            df_reg = df_reg.reset_index(drop=True)

            if len(df_reg) == 0:
                st.warning("검색 조건에 해당하는 시설이 없습니다.")
            else:
                def _fmt_target(i):
                    r = df_reg.iloc[i]
                    return f"[{r['status']}] {r['name']} | {r['zone']} | 계약번호 {r['contract_no']}"

                picked = st.selectbox("대상 시설 선택", list(range(len(df_reg))), format_func=_fmt_target, key="reg_target")
                target_row = df_reg.iloc[picked]

                st.markdown(f"<div style='font-size:13px; color:{t['text_muted']}; margin-bottom:10px;'>📍 {target_row['address']}</div>", unsafe_allow_html=True)

                reg_col1, reg_col2 = st.columns([1, 2])
                with reg_col1:
                    current_idx = STATUS_OPTIONS.index(target_row['status']) if target_row['status'] in STATUS_OPTIONS else 0
                    new_status = st.selectbox("활동상태 변경", STATUS_OPTIONS, index=current_idx, key="reg_status")
                with reg_col2:
                    default_detail = "" if target_row['activity_detail'] == '-' else target_row['activity_detail']
                    new_detail = st.text_input("세부 활동내역 (선택)", value=default_detail, key="reg_detail")

                if st.button("💾 활동이력 저장", type="primary", use_container_width=True, key="reg_submit"):
                    if st.session_state.role == 'admin':
                        modifier = "관리자"
                    else:
                        u = st.session_state.user_info
                        modifier = f"{u['branch']}-{u['zone']}"
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    db_path = os.path.join(current_dir, 'db.csv')
                    ok = update_activity(db_path, int(target_row['_row_id']), new_status, new_detail, modifier)
                    if ok:
                        st.success(f"'{target_row['name']}' 상태가 '{new_status}'(으)로 저장되었습니다.")
                        try_backup_to_github(db_path, 'db.csv', f'Activity update: {target_row["name"]} -> {new_status}')
                        load_and_set_data()
                        st.rerun()
                    else:
                        st.error("저장에 실패했습니다. 데이터를 확인해주세요.")

            st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 25px 0;'>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='font-size: 14px; color: {t['accent']};'>🕒 최근 등록 이력 (담당구역)</h4>", unsafe_allow_html=True)

            hist = df_scope[df_scope['modified_at'].astype(str).str.strip() != '']
            if len(hist) > 0:
                hist = hist.sort_values('modified_at', ascending=False)
                hist_display = hist[['name', 'status', 'modifier', 'modified_at']].rename(columns={
                    'name': '상호', 'status': '상태', 'modifier': '수정자', 'modified_at': '수정일시'
                }).head(20)
                st.dataframe(hist_display, use_container_width=True, hide_index=True)
            else:
                st.caption("아직 등록된 활동이력이 없습니다.")

    if tab_loginlog is not None:
        with tab_loginlog:
            loginlog_scope_label = f"{st.session_state.admin_branch} 지사 관리자 전용" if st.session_state.admin_branch else "마스터 관리자 전용"
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px; padding: 10px 15px; background: rgba(56, 189, 248, 0.05); border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);">
                <h3 style="margin: 0; font-size: 16px; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 20px;">🔐</span> 로그인 이력 ({loginlog_scope_label})
                </h3>
            </div>
            """, unsafe_allow_html=True)

            try:
                backup_ready = bool(st.secrets.get("GITHUB_TOKEN")) and bool(st.secrets.get("GITHUB_REPO"))
            except Exception:
                backup_ready = False
            bcol1, bcol2 = st.columns([3, 1])
            with bcol1:
                if backup_ready:
                    st.caption("✅ GitHub 자동 백업 활성화됨 — 저장할 때마다 원격 저장소에 커밋됩니다.")
                else:
                    st.caption("⚠️ GitHub 자동 백업 미설정 — Streamlit Cloud 재배포/재부팅 시 이 로그가 사라질 수 있습니다. Secrets에 GITHUB_TOKEN/GITHUB_REPO를 등록해주세요.")
            with bcol2:
                if st.button("🔄 지금 백업", use_container_width=True, key="loginlog_manual_backup", disabled=not backup_ready):
                    ok = try_backup_to_github(LOGIN_LOG_PATH, 'login_log.csv', '수동 백업: 로그인 이력')
                    st.toast("백업 완료" if ok else "백업 실패", icon="✅" if ok else "⚠️")

            if not os.path.exists(LOGIN_LOG_PATH):
                st.caption("아직 기록된 로그인 이력이 없습니다.")
            else:
                log_df = pd.read_csv(LOGIN_LOG_PATH, encoding='utf-8-sig')
                if st.session_state.admin_branch:
                    # Branch admins only see login activity tied to their own branch
                    # (their own logins plus field staff logging in under that branch).
                    log_df = log_df[log_df['지사'] == st.session_state.admin_branch]
                log_df = log_df.sort_values('로그인시각', ascending=False).reset_index(drop=True)
                log_df['_dt'] = pd.to_datetime(log_df['로그인시각'], errors='coerce')

                fcol1, fcol2 = st.columns([1, 1])
                with fcol1:
                    type_options = ["전체"] + sorted(log_df['유형'].dropna().unique().tolist())
                    selected_log_type = st.selectbox("유형 필터", type_options, key="loginlog_type_filter")
                with fcol2:
                    valid_dates = log_df['_dt'].dropna()
                    if len(valid_dates) > 0:
                        date_range = st.date_input(
                            "기간 검색",
                            value=(valid_dates.min().date(), valid_dates.max().date()),
                            key="loginlog_date_filter"
                        )
                    else:
                        date_range = None

                log_display = log_df
                if selected_log_type != "전체":
                    log_display = log_display[log_display['유형'] == selected_log_type]
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                    log_display = log_display[
                        (log_display['_dt'].dt.date >= start_date) & (log_display['_dt'].dt.date <= end_date)
                    ]
                log_display = log_display.drop(columns=['_dt'])

                lc1, lc2, lc3 = st.columns(3)
                with lc1:
                    st.metric("총 로그인 건수", len(log_df))
                with lc2:
                    st.metric("현장직원 로그인", int((log_df['유형'] == '현장직원').sum()))
                with lc3:
                    st.metric("관리자 로그인", int(log_df['유형'].isin(['마스터관리자', '지사관리자']).sum()))

                st.dataframe(log_display, use_container_width=True, hide_index=True, height=450)

                log_excel_buffer = io.BytesIO()
                log_display.to_excel(log_excel_buffer, index=False, engine='openpyxl', sheet_name='로그인이력')
                st.download_button(
                    label="📥 로그인 이력 엑셀 다운로드 (검색결과)",
                    data=log_excel_buffer.getvalue(),
                    file_name="관리고객_로그인이력.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="loginlog_excel_download"
                )
else:
    st.info("데이터베이스 파일(db.csv)을 찾을 수 없습니다. 관리자에게 문의하세요.")

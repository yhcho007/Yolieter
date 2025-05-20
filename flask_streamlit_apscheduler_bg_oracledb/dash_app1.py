import streamlit as st
import oracledb
import psutil
import pandas as pd
import time # time.sleep 사용을 위해 import 유지
import datetime
import plotly.graph_objects as go
import plotly.express as px
from common.dbhandler import DBHandler
from common.loghandler import LogHandler


# --- Streamlit 페이지 설정 (가장 먼저 호출해야 함!) ---
st.set_page_config(layout="wide") # 화면 전체 폭 사용

log_handler = LogHandler()
logger = log_handler.getloghandler("main")
db_handler = DBHandler()
db_config = db_handler.get_db_config()


# --- 상태별 색상 매핑 ---
STATUS_COLORS = {
    "R": "grey",    # 대기상태
    "X": "blue",    # 실행중
    "S": "green",   # 완료종료
    "F": "orange",  # Fail종료 (노랑색에 가까운 주황)
    "K": "red"      # 강제종료
}

# --- CSS 스타일 Injection (페이지 설정 이후에 와야 함!) ---
st.markdown("""
<style>
/* 전체 배경 검은색 및 기본 글자색 흰색 */
body {
    background-color: black !important;
    color: white !important; /* 기본 글자색 흰색 */
}
html {
    background-color: black !important; /* HTML 요소 배경도 검은색으로 */
}

/* Streamlit 앱 컨테이너 배경색 투명 */
.stApp {
    background-color: transparent !important;
    color: white !important; /* 앱 내부 기본 글자색 흰색 */
}

/* Streamlit 요소의 기본 배경색 제거 (컨테이너, 컬럼 등) */
/* 특정 블록 요소들의 배경 투명 설정 */
.stVerticalBlock, .stHorizontalBlock, .stColumns, [data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"], [data-testid="stColumns"] {
    background-color: transparent !important;
}

/* 일반 텍스트 및 마크다운 텍스트 색상 */
/* p 태그, div, span 등 대부분의 텍스트 요소 */
/* Streamlit이 텍스트를 감싸는 다양한 요소에 적용 */
p, div, span, .stMarkdown, .stText {
     color: white !important;
}


/* 타이틀 노란색 */
h1, h2, h3, h4, h5, h6 {
    color: yellow !important;
}


/* 그래프와 테이블 영역 배경 흰색, 글자 검은색 */
/* Graph와 DataFrame/Table 컨테이너에 적용 */
.stPlotlyChart, .stDataFrame, .stTable, [data-testid="stTable"], [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
    background-color: white !important;
    color: black !important; /* 기본 글자색 검은색 */
    padding: 10px; /* 여백 추가 */
    border-radius: 5px; /* 모서리 둥글게 */
    margin-bottom: 10px; /* 아래 여백 추가 */
}

/* 테이블 테두리 검은색 */
.stDataFrame table, .stTable table, [data-testid="stTable"] table, [data-testid="stDataFrame"] table {
    border: 1px solid black !important;
}
.stDataFrame th, .stDataFrame td, .stTable th, .stTable td, [data-testid="stTable"] th, [data-testid="stTable"] td, [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td {
    border: 1px solid black !important;
    color: black !important; /* 테이블 안 글자색 검은색 강제 */
}

/* 위젯 레이블(글자) 색상 노란색으로 변경 */
[data-testid="stWidgetLabel"] label { /* label 태그에 직접 적용 */
    color: yellow !important;
}

/* 위젯 자체 (입력 필드, 드롭다운 등)의 배경색 및 글자색 */
/* 위젯의 실제 입력/표시 영역에 대한 스타일을 명확히 지정 */

/* Text Input, Date Input, Time Input, Textarea */
/* data-baseweb 속성 및 input/textarea 태그 자체에 접근 */
[data-baseweb="input"] input[type="text"],
[data-baseweb="datepicker"] input[type="text"],
[data-baseweb="timepicker"] input[type="text"],
[data-baseweb="textarea"] textarea
{
    color: black !important; /* 입력된 글자색 검은색 */
    background-color: white !important; /* 배경 흰색 */
    -webkit-text-fill-color: black !important; /* 웹킷 기반 브라우저에서 자동 완성 시 글자색 유지 */
    opacity: 1 !important; /* 투명도 강제 (일부 상태에서 흐려지는 것 방지) */
}

/* Selectbox 및 Multiselect - 현재 선택된 값이 표시되는 영역 (버튼처럼 보이는 부분) */
[data-baseweb="select"] > div:first-child,
[data-baseweb="combobox"] > div:first-child
{
    color: black !important; /* 선택된 글자색 검은색 */
    background-color: white !important; /* 배경 흰색 */
    opacity: 1 !important; /* 투명도 강제 */
}
/* Selectbox 및 Multiselect - 현재 선택된 값이 표시되는 영역 내부의 텍스트 요소 */
[data-baseweb="select"] > div:first-child span,
[data-baseweb="combobox"] > div:first-child span,
[data-baseweb="select"] [role="button"] > div, /* selected option text div */
[data-baseweb="combobox"] [role="button"] > div /* selected option text div */
{
     color: black !important; /* 텍스트 색상 검은색 */
     opacity: 1 !important; /* 투명도 강제 */
}


/* Selectbox 및 Multiselect 드롭다운 메뉴 */
div[data-baseweb="popover"] div[data-baseweb="menu"] ul,
div[data-baseweb="popover"] div[role="listbox"] /* selectbox, multiselect 드롭다운 목록 컨테이너 */
{
    background-color: white !important; /* 드롭다운 메뉴 배경 흰색 */
    color: black !important; /* 드롭다운 메뉴 글자색 검은색 */
}
/* Selectbox 및 Multiselect 드롭다운 메뉴 항목 */
div[role="option"]
{
     color: black !important; /* 드롭다운 메뉴 항목 글자색 검은색 */
     background-color: white !important; /* 드롭다운 메뉴 항목 배경 흰색 */
}


/* Selectbox 및 Multiselect 항목 호버 시 배경색 */
div[role="option"]:hover
{
    background-color: #eee !important; /* 연한 회색 배경 */
    color: black !important;
}

/* Selectbox 및 Multiselect 선택된 항목 배경색 */
div[role="option"][aria-selected="true"]
{
     background-color: lightblue !important; /* 선택된 항목 배경색 */
     color: black !important;
}

/* Date Input 캘린더 팝업 */
div[data-baseweb="calendar"] div[data-baseweb="popover"] {
    background-color: white !important; /* 캘린더 팝업 배경 */
    color: black !important; /* 캘린더 글자색 */
}


/* 멀티셀렉트에서 선택된 태그 스타일 */
div[data-baseweb="tag"] {
    background-color: lightgrey !important; /* 선택된 태그 배경색 */
    color: black !important; /* 선택된 태그 글자색 */
    opacity: 1 !important; /* 투명도 강제 */
}
div[data-baseweb="tag"] > span {
     color: black !important; /* 선택된 태그 안의 텍스트 글자색 */
     opacity: 1 !important; /* 투명도 강제 */
}


/* "-" 문자 레이블 색상 (별도 마크다운으로 처리) 및 위치 조정 */
.yellow-text {
    color: yellow !important;
    display: inline-block; /* vertical-align 적용을 위해 필요 */
    vertical-align: middle; /* 세로 중앙 정렬 시도 */
    /* 위젯의 높이 및 레이블 위치에 따라 미세 조정 필요 */
    margin-top: 1.8em; # Adjust margin top based on visual test (starts around 1.5em, need lower)
    text-align: center; /* 컬럼 내에서 중앙 정렬 */
    width: 100%; /* 컬럼 폭 전체 사용 */
}

/* 스피너 숨기기 */
[data-testid="stSpinner"] {
    display: none !important;
}

/* Streamlit 기본 메시지 컨테이너 숨기기 (예: 에러 메시지 등, 주의하여 사용) */
/* 필요하다면 주석 해제하여 테스트 */
/* [data-testid="stNotification"] {
    display: none !important;
} */


</style>
""", unsafe_allow_html=True)

# --- Session State 초기화 ---
if 'last_schedule_update_time' not in st.session_state:
    st.session_state['last_schedule_update_time'] = datetime.datetime.min
if 'last_system_update_time' not in st.session_state:
    st.session_state['last_system_update_time'] = datetime.datetime.min

# 데이터 저장용 Session State 초기화
if 'schedule_graph_data' not in st.session_state:
    st.session_state['schedule_graph_data'] = pd.DataFrame()
if 'schedule_table_data' not in st.session_state:
    st.session_state['schedule_table_data'] = pd.DataFrame()
if 'status_count_data' not in st.session_state: # 상태별 카운트 데이터는 table_df에서 계산
     st.session_state['status_count_data'] = pd.DataFrame(columns=['상태', '건수']) # 빈 데이터프레임으로 컬럼과 함께 초기화
if 'system_metrics_data' not in st.session_state:
    st.session_state['system_metrics_data'] = {}
if 'cpu_top5_data' not in st.session_state:
    st.session_state['cpu_top5_data'] = []
if 'memory_top5_data' not in st.session_state:
    st.session_state['memory_top5_data'] = []


# 위젯 상태 저장용 Session State 초기화
if 'schedule_status_filter' not in st.session_state:
    st.session_state['schedule_status_filter'] = list(STATUS_COLORS.keys())
if 'graph_type' not in st.session_state:
    st.session_state['graph_type'] = '꺽은선'
if 'start_date' not in st.session_state:
    st.session_state['start_date'] = datetime.date.today() - datetime.timedelta(days=1)
if 'start_time' not in st.session_state:
     st.session_state['start_time'] = datetime.time(0, 0)
if 'end_date' not in st.session_state:
    st.session_state['end_date'] = datetime.date.today() + datetime.timedelta(days=1)
if 'end_time' not in st.session_state:
    st.session_state['end_time'] = datetime.time(0, 0)
if 'auto_update' not in st.session_state:
    st.session_state['auto_update'] = 'OFF'


# --- Oracle DB 데이터 가져오기 함수 ---
def get_db_connection():
    """Oracle DB 연결을 반환합니다."""
    conn = None
    try:
        conn = oracledb.connect(f"{db_config['user']}/{db_config['password']}@{db_config['dsn']}")
        return conn
    except Exception as e:
        # print(f"데이터베이스 연결 오류: {e}") # print 문 제거
        return None

# show_spinner=False 추가하여 캐시 로드/업데이트 시 스피너 숨김
@st.cache_data(ttl=60, show_spinner=False) # 1분(60초) 동안 캐싱, 스피너 숨김
def fetch_schedule_data_cached(status_filter, start_dt, end_dt):
    """스케줄 현황 그래프 및 테이블 데이터를 Oracle DB에서 가져옵니다."""
    conn = get_db_connection()
    if not conn:
        # print("데이터베이스 연결 실패, 스케줄 데이터 가져오기 중단") # print 문 제거
        return pd.DataFrame(), pd.DataFrame() # 빈 데이터프레임 반환

    # 상태 필터 조건 생성
    status_condition = ""
    if status_filter:
        status_list_str = ', '.join(f"'{s}'" for s in status_filter)
        status_condition = f"AND task_status IN ({status_list_str})"

    # 시간 범위 조건 및 쿼리 문자열 생성 (바인드 변수 사용)
    start_datetime_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
    end_datetime_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')

    # 쿼리 1: 시간대별 상태 카운트 (그래프용)
    query1 = f"""
    SELECT TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24') AS hourly,
           TASK_STATUS, COUNT(TASK_STATUS) as cnt_status
    FROM task
    WHERE subprocee_starttime BETWEEN TO_TIMESTAMP(:start_time_str, 'YYYY-MM-DD HH24:MI:SS') AND TO_TIMESTAMP(:end_time_str, 'YYYY-MM-DD HH24:MI:SS')
    {status_condition}
    GROUP BY TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24'), TASK_STATUS ORDER BY TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24')
    """
    params1 = {'start_time_str': start_datetime_str, 'end_time_str': end_datetime_str}


    # 쿼리 2: 개별 스케줄 목록 (테이블/카운트 테이블용)
    query2 = f"""
    SELECT subprocee_starttime, taskname, task_status
    FROM task
    WHERE subprocee_starttime BETWEEN TO_TIMESTAMP(:start_time_str, 'YYYY-MM-DD HH24:MI:SS') AND TO_TIMESTAMP(:end_time_str, 'YYYY-MM-DD HH24:MI:SS')
    {status_condition}
    ORDER BY subprocee_starttime DESC
    """
    params2 = {'start_time_str': start_datetime_str, 'end_time_str': end_datetime_str}


    graph_df = pd.DataFrame()
    table_df = pd.DataFrame()

    try:
        cursor = conn.cursor()
        # 쿼리 1 실행
        cursor.execute(query1, params1)
        graph_data = cursor.fetchall()
        graph_cols = [col[0] for col in cursor.description]
        graph_df = pd.DataFrame(graph_data, columns=graph_cols)

        # 쿼리 2 실행
        cursor.execute(query2, params2)
        table_data = cursor.fetchall()
        table_cols = [col[0] for col in cursor.description]
        table_df = pd.DataFrame(table_data, columns=table_cols)

        cursor.close()
        # print("스케줄 데이터 가져오기 성공") # print 문 제거
    except Exception as e:
        # print(f"데이터 조회 오류: {e}") # print 문 제거
        graph_df = pd.DataFrame() # 오류 시 빈 데이터프레임 반환
        table_df = pd.DataFrame() # 오류 시 빈 데이터프레임 반환
    finally:
        if conn:
             conn.close()

    # 데이터 가공: 그래프 데이터 시간대 정렬
    if not graph_df.empty:
         graph_df['HOURLY_DT'] = pd.to_datetime(graph_df['HOURLY'], format='%Y-%m-%d %H', errors='coerce')
         graph_df = graph_df.sort_values('HOURLY_DT')
         graph_df['HOURLY_STR'] = graph_df['HOURLY_DT'].dt.strftime('%Y-%m-%d %H')

    return graph_df, table_df

# show_spinner=False 추가하여 캐시 로드/업데이트 시 스피너 숨김
@st.cache_resource(ttl=3, show_spinner=False) # 3초 동안 캐싱, 스피너 숨김
def get_system_metrics_cached():
    """시스템 전반의 메트릭스 정보를 가져옵니다."""
    # print("시스템 메트릭스 데이터 가져오기...") # print 문 제거
    metrics = {}
    try:
        metrics['CPU 사용률'] = f"{psutil.cpu_percent(interval=0.1):.1f}%"
        mem = psutil.virtual_memory()
        metrics['총 메모리 사이즈'] = f"{mem.total / (1024**3):.2f} GB"
        metrics['메모리 사용 중 사이즈'] = f"{mem.used / (1024**3):.2f} GB"
        metrics['메모리 사용가능 사이즈'] = f"{mem.available / (1024**3):.2f} GB"
        metrics['메모리 사용률'] = f"{mem.percent:.1f}%"

        try:
            disk = psutil.disk_usage('/') # Linux/macOS
        except Exception:
             try:
                 disk = psutil.disk_usage('C:/') # Windows 예시
             except Exception as disk_e:
                 # print(f"디스크 사용량 조회 오류 (경로 확인 필요): {disk_e}") # print 문 제거
                 metrics['디스크 사용률'] = "N/A (Path Error)"
                 pass

        if '디스크 사용률' not in metrics:
             try:
                metrics['디스크 사용률'] = f"{disk.percent:.1f}%"
             except UnboundLocalError:
                 metrics['디스크 사용률'] = "N/A (Not Available)"


        net_io = psutil.net_io_counters()
        metrics['네트워크 Input'] = f"{net_io.bytes_recv / (1024**2):.2f} MB" # MB 단위로 표시
        metrics['네트워크 Output'] = f"{net_io.bytes_sent / (1024**2):.2f} MB" # MB 단위로 표시

    except Exception as e:
        # print(f"시스템 메트릭스 정보 조회 오류: {e}") # print 문 제거
        default_keys = ['CPU 사용률', '메모리 사용률', '디스크 사용률', '네트워크 Input', '네트워크 Output',
                        '총 메모리 사이즈', '메모리 사용 중 사이즈', '메모리 사용가능 사이즈']
        for key in default_keys:
             if key not in metrics:
                 metrics[key] = "N/A"

    return metrics

# show_spinner=False 추가하여 캐시 로드/업데이트 시 스피너 숨김
@st.cache_resource(ttl=3, show_spinner=False) # 3초 동안 캐싱, 스피너 숨김
def get_process_info_cached(sort_by='cpu', top_n=5):
    """CPU 또는 메모리 사용량 상위 N개 프로세스 정보를 가져옵니다."""
    # print(f"{sort_by.upper()} Top 5 프로세스 데이터 가져오기...") # print 문 제거
    processes = []
    try:
        all_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'cmdline']):
            try:
                cpu_p = proc.cpu_percent(interval=0)
                mem_i = proc.memory_info()
                cmd_l = proc.cmdline()

                pinfo = {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'cpu_percent': cpu_p,
                    'memory_info': mem_i,
                    'cmdline': cmd_l,
                    'memory_mb': mem_i.rss / (1024**2)
                }
                all_processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
            except Exception as e:
                 # print(f"개별 프로세스 정보 가져오기 중 오류: {e} - PID: {proc.pid if 'proc' in locals() else 'N/A'}") # print 문 제거
                 pass

        if sort_by == 'cpu':
            sorted_processes = sorted(all_processes, key=lambda x: x.get('cpu_percent', 0.0), reverse=True)
        elif sort_by == 'memory':
            sorted_processes = sorted(all_processes, key=lambda x: x.get('memory_mb', 0.0), reverse=True)
        else:
            sorted_processes = all_processes

        for p in sorted_processes:
            cmd = p.get('cmdline')
            if cmd:
                full_cmd = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
                p['command'] = full_cmd
            else:
                p['command'] = ""

        return sorted_processes[:top_n]

    except Exception as e:
        # print(f"프로세스 정보 조회 오류: {e}") # print 문 제거
        return []


# --- 그래프 생성 함수 ---
# ... (create_schedule_graph 함수 동일) ...
def create_schedule_graph(df, graph_type, status_colors):
    """스케줄 현황 그래프를 생성합니다."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="데이터 없음",
            xaxis_title="시간대",
            yaxis_title="스케줄 건수",
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='black')
        )
        return fig

    df_sorted = df.sort_values('HOURLY_DT')

    if graph_type == '꺽은선':
         fig = px.line(df_sorted, x='HOURLY_STR', y='cnt_status', color='TASK_STATUS',
                       title='스케줄 현황 그래프',
                       labels={'HOURLY_STR': '시간대', 'cnt_status': '스케줄 건수', 'TASK_STATUS': '상태'},
                       color_discrete_map=status_colors,
                       markers=True,
                       template="plotly_white")
    else: # 막대 그래프
        fig = px.bar(df_sorted, x='HOURLY_STR', y='cnt_status', color='TASK_STATUS',
                     title='스케줄 현황 그래프',
                     labels={'HOURLY_STR': '시간대', 'cnt_status': '스케줄 건수', 'TASK_STATUS': '상태'},
                     color_discrete_map=status_colors,
                     template="plotly_white")

    fig.update_layout(
        xaxis_title="시간대",
        yaxis_title="스케줄 건수",
        font=dict(color='black'),
        xaxis=dict(tickangle=-45, tickfont=dict(color='black')),
        yaxis=dict(tickfont=dict(color='black')),
        legend=dict(font=dict(color='black')),
        hovermode="x unified",
        plot_bgcolor='white',
        paper_bgcolor='white',
    )

    return fig


# --- 테이블 표시 함수 ---
# ... (display_schedule_table, display_status_count_table, display_system_metrics_table, display_process_table 함수 동일) ...

def display_schedule_table(df):
    """스케줄 현황 테이블을 표시합니다."""
    if df.empty:
        st.write("스케줄 현황 데이터가 없습니다.")
        return

    if 'SUBPROCEE_STARTTIME' in df.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(df['SUBPROCEE_STARTTIME']):
                 df['SUBPROCEE_STARTTIME'] = df['SUBPROCEE_STARTTIME'].dt.tz_convert(None).dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                 df['SUBPROCEE_STARTTIME'] = df['SUBPROCEE_STARTTIME'].astype(str)

        except Exception as e:
             print(f"날짜/시간 포맷팅 오류: {e}")
             df['SUBPROCEE_STARTTIME'] = df['SUBPROCEE_STARTTIME'].astype(str)

    st.dataframe(df, use_container_width=True)

def display_status_count_table(df_status_counts, status_colors):
    """상태별 스케줄 카운트 테이블을 표시합니다."""
    if df_status_counts.empty:
        st.write("상태별 스케줄 카운트 데이터가 없습니다.")
        return
    if '상태' not in df_status_counts.columns or '건수' not in df_status_counts.columns:
        st.write("상태별 스케줄 카운트 데이터 형식이 올바르지 않습니다.")
        return

    status_order = list(STATUS_COLORS.keys())
    try:
        df_status_counts['상태'] = pd.Categorical(df_status_counts['상태'], categories=status_order, ordered=True)
        df_status_counts = df_status_counts.sort_values('상 상태') # '상태' 컬럼으로 정렬
    except Exception as e:
        print(f"상태 컬럼 Categorical 변환 또는 정렬 오류: {e}")
        pass

    def color_status_row(row):
        status_value = row['상태']
        color = status_colors.get(status_value, 'white')
        return [f'background-color: {color}; color: black;' for _ in row.index]

    styled_df = df_status_counts.style.apply(color_status_row, axis=1)

    st.dataframe(
        styled_df,
        use_container_width=True
    )

def display_system_metrics_table(metrics):
    """시스템 메트릭스 정보를 테이블 형태로 표시합니다."""
    if not metrics:
        st.write("시스템 메트릭스 정보를 가져올 수 없습니다.")
        return

    ordered_keys = [
        'CPU 사용률', '메모리 사용률', '디스크 사용률', '네트워크 Input', '네트워크 Output',
        '총 메모리 사이즈', '메모리 사용 중 사이즈', '메모리 사용가능 사이즈'
    ]
    metrics_list = [[key, metrics.get(key, 'N/A')] for key in ordered_keys]

    metrics_df = pd.DataFrame(metrics_list, columns=['메트릭', '값'])
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

def display_process_table(processes, sort_by):
    """프로세스 정보를 테이블 형태로 표시합니다."""
    if not processes:
         st.write(f"{sort_by.upper()} Top 5 프로세스 정보가 없습니다.")
         return

    if sort_by == 'cpu':
        df = pd.DataFrame([{
            'PID': p.get('pid', 'N/A'),
            '프로세스명': p.get('name', 'N/A'),
            'CPU 사용률 (%)': f"{p.get('cpu_percent', 0.0):.1f}",
            '커맨드': p.get('command', '')
        } for p in processes])
        st.dataframe(df, use_container_width=True)

    elif sort_by == 'memory':
        df = pd.DataFrame([{
            'PID': p.get('pid', 'N/A'),
            '프로세스명': p.get('name', 'N/A'),
            '메모리 사용량 (MB)': f"{p.get('memory_mb', 0.0):.2f}",
            '커맨드': p.get('command', '')
        } for p in processes])
        st.dataframe(df, use_container_width=True)


# --- 데이터 로딩 및 업데이트 로직 ---
def load_and_update_data():
    """
    데이터를 로드하고 필요한 경우 Session State를 업데이트합니다.
    이 함수는 메인 스크립트 실행 시마다 호출됩니다.
    캐시된 함수를 호출하며, 캐시 만료 시 실제 데이터 가져오기가 발생합니다.
    show_spinner=False로 스피너는 숨겨집니다.
    """
    current_time = datetime.datetime.now()

    # 1. 시스템 메트릭스 및 Top 5 프로세스 업데이트 (3초마다)
    system_update_interval = 3 # 초
    # 마지막 업데이트 시간 + 주기 <= 현재 시간 이면 업데이트 실행
    if st.session_state.get('last_system_update_time', datetime.datetime.min) + datetime.timedelta(seconds=system_update_interval) <= current_time:
        st.session_state['system_metrics_data'] = get_system_metrics_cached()
        st.session_state['cpu_top5_data'] = get_process_info_cached(sort_by='cpu', top_n=5)
        st.session_state['memory_top5_data'] = get_process_info_cached(sort_by='memory', top_n=5)
        st.session_state['last_system_update_time'] = current_time # 업데이트 시간 갱신
        # print("시스템 메트릭스 데이터 로드/업데이트 완료") # print 문 제거


    # 2. 스케줄 데이터 업데이트 (ON 상태일 때 1분마다 또는 필터 변경 시 즉시)
    schedule_update_interval = 60 # 초 (1분)
    # 스케줄 데이터 업데이트가 필요한 조건:
    # - 자동 업데이트 ON 상태이고 1분 주기 시간이 경과했거나
    # - 자동 업데이트 OFF 상태인데 위젯 변경으로 last_schedule_update_time이 과거(datetime.min)로 설정된 경우
    # 이 조건에 해당하면 데이터를 새로 로드합니다.

    is_schedule_update_triggered = False
    # ON 상태 시간 경과 체크
    if st.session_state.get('auto_update', 'OFF') == 'ON' and \
       st.session_state.get('last_schedule_update_time', datetime.datetime.min) + datetime.timedelta(seconds=schedule_update_interval) <= current_time:
        is_schedule_update_triggered = True
        st.session_state['last_schedule_update_time'] = current_time # ON 상태 시간 경과 시에만 갱신

    # OFF 상태 필터 변경 감지 (on_change에서 last_schedule_update_time을 datetime.min으로 설정하여 감지)
    # 또는 최초 로드 시
    if st.session_state.get('last_schedule_update_time', datetime.datetime.min) == datetime.datetime.min:
         is_schedule_update_triggered = True


    # 실제 데이터 로드가 필요한 경우 (캐시 TTL 만료, 또는 인자 변경)
    # fetch_schedule_data_cached 함수는 인자가 변경되거나 TTL이 만료되면 실제 데이터 로드를 수행합니다.
    # is_schedule_update_triggered 조건이 True일 때만 데이터를 로드하도록 로직 수정

    if is_schedule_update_triggered:
        # 시간 범위 결정 (ON/OFF 모두 켈린더 값 사용)
        start_datetime_obj = datetime.datetime.combine(st.session_state.get('start_date', datetime.date.today() - datetime.timedelta(days=1)),
                                                        st.session_state.get('start_time', datetime.time(0, 0)))
        end_datetime_obj = datetime.datetime.combine(st.session_state.get('end_date', datetime.date.today() + datetime.timedelta(days=1)),
                                                      st.session_state.get('end_time', datetime.time(0, 0)))

        # 캐시된 함수 호출 (인자 변경 또는 1분 캐시 만료 시 실제 데이터 가져옴)
        # 스피너는 show_spinner=False로 숨겨짐
        # on_change에서 last_schedule_update_time을 datetime.min으로 설정하면
        # fetch_schedule_data_cached는 인자 변경을 감지하고 캐시를 무시함.
        # ON 상태 시간 경과는 load_and_update_data가 호출될 때 last_schedule_update_time 체크로 트리거.
        # 실제 데이터가 새로 로드될 때만 session_state 업데이트?
        # -> 아니오, is_schedule_update_triggered 조건 충족 시 항상 캐시 함수 호출 및 session_state 업데이트.
        #    캐시 히트 시는 빠른 반환.

        graph_df, table_df = fetch_schedule_data_cached(
            st.session_state.get('schedule_status_filter', list(STATUS_COLORS.keys())),
            start_datetime_obj,
            end_datetime_obj
        )

        # session_state에 데이터 저장
        st.session_state['schedule_graph_data'] = graph_df
        st.session_state['schedule_table_data'] = table_df

        # 상태별 카운트 데이터 계산 및 저장
        if not table_df.empty and 'TASK_STATUS' in table_df.columns:
            st.session_state['status_count_data'] = table_df['TASK_STATUS'].value_counts().reset_index()
            st.session_state['status_count_data'].columns = ['상태', '건수']
        else:
            st.session_state['status_count_data'] = pd.DataFrame(columns=['상태', '건수'])

        # 데이터 로드/업데이트 시 last_schedule_update_time 갱신
        # on_change에서 datetime.min으로 설정한 상태는 여기서 현재 시간으로 갱신됨.
        st.session_state['last_schedule_update_time'] = current_time
        # print("스케줄 데이터 Session State 업데이트 및 시간 갱신 완료") # print 문 제거
    # else:
        # print("스케줄 데이터 업데이트 조건 미충족") # print 문 제거


# --- 메인 대시보드 레이아웃 및 로직 ---
def main():
    # st.set_page_config는 main 함수 밖에서 이미 호출됨

    # 데이터 로딩 및 업데이트 (Session State에 저장)
    # 매 스크립트 실행마다 호출되어 캐시 유효성 및 업데이트 주기 체크
    load_and_update_data()


    # --- 맨 위 헤더 (타이틀 및 실시간 시계) ---
    header_cols = st.columns([4, 1])
    with header_cols[0]:
        st.markdown("<h1>스케줄 데쉬보드</h1>", unsafe_allow_html=True)
    with header_cols[1]:
        # 실시간 시계는 매 rerun 시 현재 시간으로 업데이트
        # time.sleep(1)과 st.rerun() 조합으로 1초마다 스크립트가 실행되므로 초 단위 업데이트 가능
        current_time = datetime.datetime.now()
        st.markdown(f"<h1>{current_time.strftime('%Y-%m-%d %H:%M:%S')}</h1>", unsafe_allow_html=True)


    # --- 메인 화면 레이아웃 (세로 3:1 분할) ---
    main_cols = st.columns([3, 1])

    # --- 왼쪽 영역 (3/4) ---
    with main_cols[0]:
        st.markdown("<h3>스케줄 현황</h3>", unsafe_allow_html=True)

        # 스케줄 현황 그래프 표시 (Session State 데이터 사용)
        st.markdown("스케줄 현황 그래프") # Placeholder 대신 타이틀 재표시
        fig = create_schedule_graph(
            st.session_state.get('schedule_graph_data', pd.DataFrame()),
            st.session_state.get('graph_type', '꺽은선'),
            STATUS_COLORS
        )
        st.plotly_chart(fig, use_container_width=True)


        st.markdown("<h4>스케줄 검색 조건</h4>", unsafe_allow_html=True)

        # 스케줄 검색 조건 위젯 레이아웃 ("-" 위치 수정)
        # 총 8개 컬럼: [상태(1), 그래프 종류(1), 시작 날짜(1), 시작 시간(1), -(0.3), 끝 날짜(1), 끝 시간(1), 자동 업데이트(1)]
        filter_cols = st.columns([1, 1, 1, 1, 0.3, 1, 1, 1])

        with filter_cols[0]: # 스케줄 상태
            selected_statuses = st.multiselect(
                "스케줄 상태",
                list(STATUS_COLORS.keys()),
                default=st.session_state.get('schedule_status_filter', list(STATUS_COLORS.keys())),
                key='status_select',
                # 필터 변경 시 last_schedule_update_time을 과거로 설정하여 다음 rerun 시 데이터 로드 트리거
                on_change=lambda: st.session_state.update(schedule_status_filter=st.session_state['status_select'], last_schedule_update_time=datetime.datetime.min)
            )

        with filter_cols[1]: # 그래프 종류
            selected_graph_type = st.selectbox(
                "그래프 종류",
                ['꺽은선', '막대'],
                index=['꺽은선', '막대'].index(st.session_state.get('graph_type', '꺽은선')),
                key='graph_type_select',
                on_change=lambda: st.session_state.update(graph_type=st.session_state['graph_type_select'])
            )

        with filter_cols[2]: # 시작 날짜
            selected_start_date = st.date_input(
                "시작 날짜",
                st.session_state.get('start_date', datetime.date.today() - datetime.timedelta(days=1)),
                key='start_date_select',
                on_change=lambda: st.session_state.update(start_date=st.session_state['start_date_select'], last_schedule_update_time=datetime.datetime.min)
            )

        with filter_cols[3]: # 시작 시간
            selected_start_time = st.time_input(
                "시작 시간",
                 st.session_state.get('start_time', datetime.time(0, 0)),
                 key='time_start_select', # time_input key 변경 (date_input과 겹치지 않도록)
                 on_change=lambda: st.session_state.update(start_time=st.session_state['time_start_select'], last_schedule_update_time=datetime.datetime.min)
            )

        with filter_cols[4]: # "-" 표시 (시작 시간과 끝 날짜 사이)
             # 위젯 레이블과 입력 필드 사이의 높이를 고려하여 "-" 위치 조정
             # 이전보다 조금 더 내려서 입력 필드 라인에 가깝게 배치
             # time_input과 date_input의 높이를 보고 적절히 조정 (대략 2.5em ~ 3em 사이)
             st.markdown("<div style='height: 2.8em;'></div>", unsafe_allow_html=True) # 빈 공간 추가
             st.markdown("<span class='yellow-text'>-</span>", unsafe_allow_html=True) # 노란색 "-" 표시

        with filter_cols[5]: # 끝 날짜
            selected_end_date = st.date_input(
                "끝 날짜",
                st.session_state.get('end_date', datetime.date.today() + datetime.timedelta(days=1)),
                key='end_date_select',
                on_change=lambda: st.session_state.update(end_date=st.session_state['end_date_select'], last_schedule_update_time=datetime.datetime.min)
            )

        with filter_cols[6]: # 끝 시간
            selected_end_time = st.time_input(
                "끝 시간",
                 st.session_state.get('end_time', datetime.time(0, 0)),
                 key='time_end_select', # time_input key 변경
                 on_change=lambda: st.session_state.update(end_time=st.session_state['time_end_select'], last_schedule_update_time=datetime.datetime.min)
            )

        with filter_cols[7]: # 자동 업데이트 ON/OFF
            auto_update_state = st.selectbox(
                 "자동 업데이트",
                 ['OFF', 'ON'],
                 index=['OFF', 'ON'].index(st.session_state.get('auto_update', 'OFF')),
                 key='auto_update_select',
                 on_change=lambda: st.session_state.update(auto_update=st.session_state['auto_update_select'], last_schedule_update_time=datetime.datetime.min) # 상태 변경 시 강제 업데이트 트리거
            )


        st.markdown("<h4>스케줄 현황 테이블</h4>", unsafe_allow_html=True)
        display_schedule_table(st.session_state.get('schedule_table_data', pd.DataFrame()))


    # --- 오른쪽 영역 (1/4) ---
    with main_cols[1]:
        st.markdown("<h4>상태별 스케줄 카운트</h4>", unsafe_allow_html=True)
        display_status_count_table(st.session_state.get('status_count_data', pd.DataFrame(columns=['상태', '건수'])), STATUS_COLORS)


        st.markdown("<h4>스케줄 시스템 메트릭스</h4>", unsafe_allow_html=True)
        display_system_metrics_table(st.session_state.get('system_metrics_data', {}))


        st.markdown("<h4>CPU Top 5</h4>", unsafe_allow_html=True)
        display_process_table(st.session_state.get('cpu_top5_data', []), 'cpu')

        st.markdown("<h4>Memory Top 5</h4>", unsafe_allow_html=True)
        display_process_table(st.session_state.get('memory_top5_data', []), 'memory')


    # --- 자동 새로고침 트리거 ---
    # 1초 대기 후 스크립트 다시 실행하여 실시간 시계 및 데이터 업데이트 주기 제어
    # time.sleep()은 Streamlit 메인 스레드를 멈추지만, 1초는 일반적으로 UI가 완전히 멈췄다고
    # 인식하지 않는 선에서 주기적인 rerun을 보장합니다.
    time.sleep(1)
    st.rerun()


if __name__ == "__main__":
    main()

# 필요한 라이브러리 임포트
import streamlit as st
import oracledb
import pandas as pd
import plotly.express as px
import psutil
import time
import datetime
import sys
from common.dbhandler import DBHandler
from common.loghandler import LogHandler

# 업데이트 주기 (초)
METRICS_UPDATE_INTERVAL = 3 # 시스템 메트릭스, CPU/Memory Top5 업데이트 주기
GRAPH_UPDATE_INTERVAL = 60  # 스케줄 현황 그래프/테이블 업데이트 주기
# Clock은 모든 업데이트 시 함께 업데이트됩니다.

# 색상 설정
COLOR_MAP = {
    "R": "gray",   # 대기상태
    "X": "blue",  # 실행중
    "S": "green", # 완료종료
    "F": "yellow", # Fail종료
    "K": "red"   # 강제종료
}
log_handler = LogHandler()
logger = log_handler.getloghandler("main")

db_handler = DBHandler()
db_config = db_handler.get_db_config()

# --- Oracle DB 연결 함수 ---
def get_oracle_connection():
    try:
        # Streamlit secrets에서 연결 정보 가져오기
        conn = oracledb.connect(
            user=db_config['user'], password=db_config['password'], dsn=db_config['dsn']
        )
        return conn
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {e}")
        return None

# 데이터 가져오는 함수 (그래프용 - 쿼리 1)
def fetch_graph_data(conn, selected_statuses, start_time, end_time):
    if conn is None:
        return pd.DataFrame()

    status_filter = ""
    if selected_statuses:
        # Oracle DB는 tuple 형태의 IN 절을 지원
        status_filter = f"AND task_status IN ({', '.join([f"'{s}'" for s in selected_statuses])})"

    # datetime 객체를 Oracle TIMESTAMP로 변환하여 쿼리에 사용
    try:
        start_ts = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_ts = end_time.strftime('%Y-%m-%d %H:%M:%S')
    except AttributeError: # 날짜 선택 위젯 초기 상태 처리 (None일 수 있음)
         st.warning("날짜/시간 선택을 완료해주세요.")
         return pd.DataFrame()


    query = f"""
    SELECT TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24') AS hourly, TASK_STATUS, COUNT(TASK_STATUS) as cnt_status
    FROM task
    WHERE subprocee_starttime BETWEEN TO_TIMESTAMP(:start_ts_str, 'YYYY-MM-DD HH24:MI:SS') AND TO_TIMESTAMP(:end_ts_str, 'YYYY-MM-DD HH24:MI:SS')
    {status_filter}
    GROUP BY TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24'), TASK_STATUS
    ORDER BY TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24')
    """
    try:
        # 바인드 변수 사용
        params = {'start_ts_str': start_ts, 'end_ts_str': end_ts}
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"그래프 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame()

# 데이터 가져오는 함수 (테이블용 - 쿼리 2)
def fetch_table_data(conn, selected_statuses, start_time, end_time):
    if conn is None:
        return pd.DataFrame()

    status_filter = ""
    if selected_statuses:
        status_filter = f"AND task_status IN ({', '.join([f"'{s}'" for s in selected_statuses])})"

    try:
        start_ts = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_ts = end_time.strftime('%Y-%m-%d %H:%M:%S')
    except AttributeError:
        st.warning("날짜/시간 선택을 완료해주세요.")
        return pd.DataFrame()


    query = f"""
    SELECT subprocee_starttime, taskname, task_status
    FROM task
    WHERE subprocee_starttime BETWEEN TO_TIMESTAMP(:start_ts_str, 'YYYY-MM-DD HH24:MI:SS') AND TO_TIMESTAMP(:end_ts_str, 'YYYY-MM-DD HH24:MI:SS')
    {status_filter}
    ORDER BY subprocee_starttime DESC
    """
    try:
        # 바인드 변수 사용
        params = {'start_ts_str': start_ts, 'end_ts_str': end_ts}
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"스케줄 테이블 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame()

# 데이터 가져오는 함수 (상태별 카운트용)
def fetch_status_counts(conn, selected_statuses, start_time, end_time):
    if conn is None:
        return pd.DataFrame()

    status_filter = ""
    all_statuses = ["R", "X", "S", "F", "K"] # 모든 가능한 상태값
    # 선택된 상태가 있다면 그 상태만 필터링, 없다면 모든 상태 포함
    if selected_statuses:
        status_filter = f"AND task_status IN ({', '.join([f"'{s}'" for s in selected_statuses])})"
    # else: # 아무것도 선택 안하면 모든 상태를 포함하여 쿼리
        # status_filter = f"AND task_status IN ({', '.join([f"'{s}'" for s in all_statuses])})"


    try:
        start_ts = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_ts = end_time.strftime('%Y-%m-%d %H:%M:%S')
    except AttributeError:
        st.warning("날짜/시간 선택을 완료해주세요.")
        return pd.DataFrame()


    query = f"""
    SELECT task_status, COUNT(task_status) as count
    FROM task
    WHERE subprocee_starttime BETWEEN TO_TIMESTAMP(:start_ts_str, 'YYYY-MM-DD HH24:MI:SS') AND TO_TIMESTAMP(:end_ts_str, 'YYYY-MM-DD HH24:MI:SS')
    {status_filter}
    GROUP BY task_status
    ORDER BY task_status
    """
    try:
        # 바인드 변수 사용
        params = {'start_ts_str': start_ts, 'end_ts_str': end_ts}
        df = pd.read_sql(query, conn, params=params)
        # 데이터프레임에 모든 가능한 상태를 포함시키고, 없는 상태는 count를 0으로 채움
        # 이렇게 해야 테이블에 모든 상태가 표시되고 색상 적용이 용이함.
        full_df = pd.DataFrame({'TASK_STATUS': all_statuses})
        merged_df = pd.merge(full_df, df, on='TASK_STATUS', how='left').fillna(0)
        merged_df['COUNT'] = merged_df['COUNT'].astype(int) # Count는 정수로
        return merged_df
    except Exception as e:
        st.error(f"상태별 카운트 데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame()


# 시스템 메트릭스 가져오는 함수
def get_system_metrics():
    try:
        cpu_percent = psutil.cpu_percent(interval=None) # 논블로킹 호출
        mem_info = psutil.virtual_memory()
        # 디스크 사용량은 시스템 루트('/') 또는 'C:\' 등 플랫폼에 맞게 경로 설정
        disk_path = '/'
        if sys.platform == 'win32':
            disk_path = 'C:\\'
        disk_usage = psutil.disk_usage(disk_path)
        net_io = psutil.net_io_counters()

        metrics = {
            "CPU 사용률": f"{cpu_percent:.1f} %",
            "메모리 사용률": f"{mem_info.percent:.1f} %",
            "디스크 사용률": f"{disk_usage.percent:.1f} %",
            "네트워크 Input": f"{net_io.bytes_recv / (1024*1024):.2f} MB", # MB 단위로 표시
            "네트워크 Output": f"{net_io.bytes_sent / (1024*1024):.2f} MB", # MB 단위로 표시
            "총 메모리 사이즈": f"{mem_info.total / (1024*1024*1024):.2f} GB", # GB 단위로 표시
            "메모리 사용 중 사이즈": f"{mem_info.used / (1024*1024*1024):.2f} GB",
            "메모리 사용가능 사이즈": f"{mem_info.available / (1024*1024*1024):.2f} GB",
        }
        return metrics
    except Exception as e:
        # st.warning(f"시스템 메트릭스를 가져올 수 없습니다: {e}")
        return {}

# 프로세스 목록 및 CPU/Memory 사용량 가져오는 함수
def get_process_metrics():
    process_list = []
    try:
        # cpu_percent는 interval=None으로 설정하면 이전 호출 이후 사용량을 반환.
        # 정확한 순간 사용량을 위해선 interval > 0 으로 설정하고 블로킹 호출을 하거나,
        # 짧은 간격으로 두 번 호출하는 방식이 필요. Streamlit에선 복잡하므로 단순 호출.
        # memory_info는 rss (Resident Set Size)를 사용.
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'cmdline']):
            try:
                pinfo = proc.as_dict(attrs=['pid', 'name', 'cpu_percent', 'memory_info', 'cmdline'])
                # cmdline은 리스트 또는 문자열일 수 있음. Windows에서 문자열 가능성 고려.
                # None 값이 들어오는 경우도 처리
                cmd_parts = pinfo.get('cmdline')
                if cmd_parts is None:
                     cmd = ''
                elif isinstance(cmd_parts, list):
                    cmd = ' '.join(cmd_parts)
                else: # assume string
                    cmd = str(cmd_parts)

                # memory_info가 None인 경우 처리
                mem_rss = pinfo.get('memory_info')
                mem_rss_bytes = mem_rss.rss if mem_rss else 0

                process_list.append({
                    'PID': pinfo['pid'],
                    '프로세스명': pinfo['name'],
                    'CPU 사용률 (%)': pinfo['cpu_percent'],
                    '메모리 사용량 (Bytes)': mem_rss_bytes, # Resident Set Size
                    '커맨드': cmd
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass # 해당 프로세스에 접근할 수 없는 경우 무시
        df = pd.DataFrame(process_list)
        if not df.empty:
             df['메모리 사용량 (MB)'] = df['메모리 사용량 (Bytes)'] / (1024 * 1024) # MB로 변환
             df = df.drop(columns=['메모리 사용량 (Bytes)']) # Bytes 컬럼 제거
        return df
    except Exception as e:
        # st.warning(f"프로세스 메트릭스를 가져올 수 없습니다: {e}")
        return pd.DataFrame()

# --- HTML 테이블 생성 함수 (스타일 및 툴팁 적용) ---

# 상태별 카운트 테이블 HTML 생성
def generate_status_count_html(df):
    if df.empty:
        return "<p style='color: black; background-color: white; padding: 5px; border: 1px solid gray;'>데이터 없음</p>"

    html = "<table style='width:100%; border-collapse: collapse;'><thead><tr>"
    # Header row
    html += "<th style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>상태</th>"
    html += "<th style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>개수</th>"
    html += "</tr></thead><tbody>"

    # Data rows with status color
    for index, row in df.iterrows():
        status = row['TASK_STATUS']
        count = row['COUNT']
        color = COLOR_MAP.get(status, 'black') # 상태에 따른 색상 가져오기
        # 상태 셀에만 색상 적용
        html += f"<tr>"
        html += f"<td style='padding: 8px; border: 1px solid gray; background-color: white; color: {color};'><b>{status}</b></td>" # 상태 셀 색상 적용, 굵게
        html += f"<td style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>{count}</td>" # 개수 셀 검은색
        html += f"</tr>"

    html += "</tbody></table>"
    return html

# 스케줄 테이블 HTML 생성 (날짜 포맷 및 상태 색상 적용)
def generate_schedule_table_html(df):
    if df.empty:
        return "<p style='color: black; background-color: white; padding: 5px; border: 1px solid gray;'>데이터 없음</p>"

    html = "<table style='width:100%; border-collapse: collapse;'><thead><tr>"
    # Header row
    for col in df.columns:
        html += f"<th style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>{col}</th>"
    html += "</tr></thead><tbody>"

    # Data rows
    for index, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            cell_value = row[col]
            # Datetime 객체 포맷팅
            if isinstance(cell_value, datetime.datetime):
                 cell_value = cell_value.strftime('%Y-%m-%d %H:%M:%S')
            # None 값 처리
            elif cell_value is None:
                 cell_value = ""

            # TASK_STATUS 컬럼에 상태별 색상 적용
            cell_style = 'padding: 8px; border: 1px solid gray; background-color: white; color: black;'
            if col == 'TASK_STATUS':
                 status_color = COLOR_MAP.get(row['TASK_STATUS'], 'black')
                 cell_style = f'padding: 8px; border: 1px solid gray; background-color: white; color: {status_color};'
                 cell_value = f"<b>{cell_value}</b>" # 상태 굵게

            html += f"<td style='{cell_style}'>{cell_value}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html

# 프로세스 Top5 테이블 HTML 생성 (툴팁 적용)
def generate_process_table_html(df, type):
    if df.empty:
        return "<p style='color: black; background-color: white; padding: 5px; border: 1px solid gray;'>데이터 없음</p>"

    html = "<table style='width:100%; border-collapse: collapse;'><thead><tr>"
    # Header row
    if type == 'CPU':
        html += "<th style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>프로세스명</th><th style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>CPU 사용률 (%)</th><th style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>커맨드</th>"
    else: # Memory
        html += "<th style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>프로세스명</th><th style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>메모리 사용량 (MB)</th><th style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>커맨드</th>"
    html += "</tr></thead><tbody>"

    # Data rows
    for index, row in df.iterrows():
        html += "<tr>"
        # 프로세스명
        html += f"<td style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>{row['프로세스명']}</td>"
        # 값 (CPU 사용률 또는 메모리 사용량)
        if type == 'CPU':
             html += f"<td style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>{row['CPU 사용률 (%)']:.1f}</td>"
        else: # Memory
             html += f"<td style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>{row['메모리 사용량 (MB)']:.1f}</td>"

        # 커맨드 (툴팁 적용)
        command = row['커맨드']
        # 셀에는 일정 길이만 표시하고, 전체 내용은 툴팁으로
        display_command = command[:50] + ('...' if len(command) > 50 else '')
        # 툴팁에 표시될 내용의 HTML 특수 문자 이스케이프
        command_escaped = command.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#039;')

        html += f"<td style='padding: 8px; border: 1px solid gray; background-color: white; color: black;' title='{command_escaped}'>{display_command}</td>" # title 속성이 툴팁 역할
        html += "</tr>"

    html += "</tbody></table>"
    return html

# --- Streamlit 앱 실행 함수 ---
def run_dashboard():
    # Streamlit 페이지 설정 (전체 폭 사용)
    st.set_page_config(layout="wide")

    # CSS 스타일 주입
    # 배경색, 제목색, 표/그래프 배경색, 글씨색, 테두리 등 스타일 적용
    st.markdown("""
        <style>
        body {
            background-color: black; /* 전체 배경 검은색 */
            color: white; /* 기본 글씨색 하얀색 */
        }
        h1, h2, h3, h4, h5, h6 {
            color: yellow; /* 제목 노란색 */
        }
        /* 입력 위젯 (select, date input 등)의 스타일은 Streamlit 테마 또는 별도 CSS로 커스터마이징 필요 */
        /* 여기서는 표와 그래프 배경/글씨색에 집중 */

        /* 표 스타일 (HTML 테이블에 적용) */
        table {
            background-color: white; /* 표 배경 흰색 */
            color: black; /* 표 글씨 검은색 */
            border-collapse: collapse; /* 테두리 겹침 */
            width: 100%;
            margin-bottom: 15px; /* 표 아래 여백 */
        }
        th, td {
            padding: 8px;
            text-align: left;
            border: 1px solid gray; /* 표 테두리 회색 */
        }
        th {
            background-color: #f2f2f2; /* 헤더 배경색 (흰색 계열) */
             color: black;
        }
        tbody tr:nth-child(even) { /* 짝수 행 배경색 (필요시) */
            /* background-color: #f9f9f9; */
        }

        /* Plotly 그래프 배경 설정 */
        .js-plotly-plot {
             background-color: white !important;
             border: 1px solid gray; /* 그래프 테두리 회색 */
        }
        .modebar-container {
             background-color: white !important; /* Plotly 툴바 배경 */
             color: black !important; /* Plotly 툴바 아이콘 색상 */
        }
         .plotly .modebar-btn {
            color: black !important; /* Plotly 툴바 버튼 아이콘 색상 */
         }

         /* 데이터프레임 기본 스타일 오버라이드 (HTML 테이블 사용으로 대체) */
         /* .stDataFrame div[data-testid="StyledFullScreenButton"] {
             color: black;
         }
          .stDataFrame {
              background-color: white !important;
              color: black !important;
              border: 1px solid gray !important;
          }
          .stDataFrame th {
               background-color: #f2f2f2 !important;
               color: black !important;
               border: 1px solid gray !important;
          }
           .stDataFrame td {
               color: black !important;
               border: 1px solid gray !important;
           } */


        </style>
    """, unsafe_allow_html=True)

    # Oracle DB 연결 초기화
    conn = get_oracle_connection()
    if conn is None:
        # 연결 실패 시 오류 메시지 표시 및 앱 중단
        # init_connection 함수에서 이미 오류 메시지를 표시합니다.
        # time.sleep(5) # 오류 메시지를 볼 시간 제공 (선택 사항)
        st.stop()

    # 세션 상태 초기화 (업데이트 시간 추적용)
    if 'last_metrics_update' not in st.session_state:
        st.session_state.last_metrics_update = datetime.datetime.now()
    if 'last_graph_update' not in st.session_state:
        st.session_state.last_graph_update = datetime.datetime.now()
    # 시계는 매 턴마다 업데이트되므로 별도 타이머 불필요

    # --- 헤더 ---
    # 좌, 중, 우 3등분 (비율 조정 가능)
    header_cols = st.columns([1, 3, 1])
    with header_cols[1]:
        st.markdown("<h1 style='text-align: center; color: yellow;'>스케줄 데시보드</h1>", unsafe_allow_html=True)
    with header_cols[2]:
        # 실시간 시계 (Streamlit 턴마다 업데이트)
        current_time = datetime.datetime.now()
        st.markdown(f"<h1 style='text-align: right; color: yellow;'>{current_time.strftime('%Y-%m-%d %H:%M:%S')}</h1>", unsafe_allow_html=True)


    # --- 메인 레이아웃 (세로 3:1 비율) ---
    main_cols = st.columns([3, 1])

    # --- 왼쪽 컬럼 (비율 3) ---
    with main_cols[0]:
        st.markdown("<h3 style='color: yellow;'>스케줄 현황</h3>", unsafe_allow_html=True)

        # 스케줄 검색 조건 영역
        st.markdown("<h4>스케줄 검색 조건</h4>", unsafe_allow_html=True)
        # 컬럼 분할하여 위젯 배치
        search_cols = st.columns([2, 2, 3, 1, 3, 2]) # 상태, 그래프 종류, 시작날짜, -, 끝날짜, ON/OFF

        with search_cols[0]:
            selected_statuses = st.multiselect(
                "스케줄 상태",
                ["R", "X", "S", "F", "K"],
                default=["R", "X", "S", "F", "K"], # 기본값은 모두 선택
                key='selected_statuses' # 위젯 상태 유지를 위한 고유 키
            )
        with search_cols[1]:
            graph_type = st.selectbox(
                "그래프 종류",
                ["꺽은선", "막대"],
                key='graph_type' # 위젯 상태 유지를 위한 고유 키
            )
        with search_cols[5]:
            date_filter_on = st.selectbox(
                "날짜 필터",
                ["OFF", "ON"],
                index=0, # 기본값 'OFF'
                key='date_filter_on' # 위젯 상태 유지를 위한 고유 키
            )

        # 날짜/시간 필터 설정
        now = datetime.datetime.now()
        # 기본 시간 범위 (필터 OFF 시)
        default_start_off = now - datetime.timedelta(hours=24)
        default_end_off = now + datetime.timedelta(hours=24)

        # 필터 ON 시 기본 시간 범위 (초기 로딩 시)
        if 'start_date_on' not in st.session_state:
             st.session_state.start_date_on = (now - datetime.timedelta(hours=1)).date()
        if 'start_time_on' not in st.session_state:
             st.session_state.start_time_on = (now - datetime.timedelta(hours=1)).time()
        if 'end_date_on' not in st.session_state:
             st.session_state.end_date_on = now.date()
        if 'end_time_on' not in st.session_state:
             st.session_state.end_time_on = now.time()


        # 날짜/시간 입력 위젯 배치
        with search_cols[2]:
            start_date_input = st.date_input("시작 날짜",
                                           value=st.session_state.start_date_on if date_filter_on == "ON" else default_start_off.date(),
                                           key='start_date_widget') # 고유 키
            start_time_input = st.time_input("시작 시간",
                                           value=st.session_state.start_time_on if date_filter_on == "ON" else default_start_off.time(),
                                           step=60, # 1분 단위
                                           key='start_time_widget') # 고유 키

        search_cols[3].markdown("<h1 style='text-align: center;'>-</h1>", unsafe_allow_html=True) # 구분자 표시

        with search_cols[4]:
            end_date_input = st.date_input("끝 날짜",
                                         value=st.session_state.end_date_on if date_filter_on == "ON" else default_end_off.date(),
                                         key='end_date_widget') # 고유 키
            end_time_input = st.time_input("끝 시간",
                                         value=st.session_state.end_time_on if date_filter_on == "ON" else default_end_off.time(),
                                         step=60, # 1분 단위
                                         key='end_time_widget') # 고유 키

        # 사용자가 'ON' 상태에서 선택한 날짜/시간을 세션 상태에 저장 (rerun 시 값 유지를 위해)
        if date_filter_on == "ON":
             st.session_state.start_date_on = start_date_input
             st.session_state.start_time_on = start_time_input
             st.session_state.end_date_on = end_date_input
             st.session_state.end_time_on = end_time_input


        # 실제 데이터 필터링에 사용할 datetime 객체 결정
        if date_filter_on == "OFF":
             start_datetime_filter = datetime.datetime.combine(default_start_off.date(), default_start_off.time())
             end_datetime_filter = datetime.datetime.combine(default_end_off.date(), default_end_off.time())
        else: # ON
             start_datetime_filter = datetime.datetime.combine(start_date_input, start_time_input)
             end_datetime_filter = datetime.datetime.combine(end_date_input, end_time_input)

        # 스케줄 현황 그래프 영역
        st.markdown("<h4>스케줄 현황 그래프</h4>", unsafe_allow_html=True)
        # 그래프 업데이트를 위한 placeholder
        graph_placeholder = st.empty()


        # 스케줄 현황 테이블 영역
        st.markdown("<h4>스케줄 현황 테이블</h4>", unsafe_allow_html=True)
        # 테이블 업데이트를 위한 placeholder
        table_placeholder = st.empty()


    # --- 오른쪽 컬럼 (비율 1) ---
    with main_cols[1]:
        st.markdown("<h4 style='color: yellow;'>상태별 스케줄 카운트</h4>", unsafe_allow_html=True)
        # 상태별 카운트 테이블 업데이트를 위한 placeholder
        status_count_placeholder = st.empty()

        st.markdown("<h4 style='color: yellow;'>스케줄 시스템 메트릭스</h4>", unsafe_allow_html=True)
        # 시스템 메트릭스 업데이트를 위한 placeholder
        metrics_placeholder = st.empty()

        st.markdown("<h4 style='color: yellow;'>CPU Top5</h4>", unsafe_allow_html=True)
        # CPU Top5 테이블 업데이트를 위한 placeholder
        cpu_top5_placeholder = st.empty()

        st.markdown("<h4 style='color: yellow;'>Memory Top5</h4>", unsafe_allow_html=True)
        # Memory Top5 테이블 업데이트를 위한 placeholder
        memory_top5_placeholder = st.empty()


    # --- 데이터 업데이트 및 표시 로직 (주기적 rerun 기반) ---
    current_run_time = datetime.datetime.now()
    needs_rerun = False # 이번 실행에서 rerun이 필요한지 여부

    # 메트릭스, 상태 카운트, 프로세스 목록 업데이트 (METRICS_UPDATE_INTERVAL 주기)
    time_since_metrics_update = (current_run_time - st.session_state.last_metrics_update).total_seconds()
    if time_since_metrics_update >= METRICS_UPDATE_INTERVAL:
        # 시스템 메트릭스 가져오기 및 표시
        system_metrics = get_system_metrics()
        metrics_html = "<table style='width:100%; border-collapse: collapse;'><tr><td style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'><b>항목</b></td><td style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'><b>값</b></td></tr>"
        if system_metrics:
             for key, value in system_metrics.items():
                 metrics_html += f"<tr><td style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>{key}</td><td style='padding: 8px; border: 1px solid gray; background-color: white; color: black;'>{value}</td></tr>"
        else:
             metrics_html += "<tr><td colspan='2' style='padding: 8px; border: 1px solid gray; background-color: white; color: black; text-align: center;'>시스템 메트릭스를 가져올 수 없습니다.</td></tr>"
        metrics_html += "</table>"
        metrics_placeholder.markdown(metrics_html, unsafe_allow_html=True)

        # 프로세스 메트릭스 가져오기
        process_df = get_process_metrics()

        # CPU Top 5 표시
        if not process_df.empty:
            cpu_top5_df = process_df.sort_values(by='CPU 사용률 (%)', ascending=False).head(5)[['프로세스명', 'CPU 사용률 (%)', '커맨드']]
            cpu_top5_placeholder.markdown(generate_process_table_html(cpu_top5_df, 'CPU'), unsafe_allow_html=True)
        else:
            cpu_top5_placeholder.info("CPU Top5 데이터를 가져올 수 없습니다.")

        # Memory Top 5 표시
        if not process_df.empty:
            memory_top5_df = process_df.sort_values(by='메모리 사용량 (MB)', ascending=False).head(5)[['프로세스명', '메모리 사용량 (MB)', '커맨드']]
            memory_top5_placeholder.markdown(generate_process_table_html(memory_top5_df, 'Memory'), unsafe_allow_html=True)
        else:
            memory_top5_placeholder.info("Memory Top5 데이터를 가져올 수 없습니다.")

        # 상태별 스케줄 카운트 업데이트 (동일 타이머 사용)
        status_counts_df = fetch_status_counts(conn, selected_statuses, start_datetime_filter, end_datetime_filter)
        status_count_placeholder.markdown(generate_status_count_html(status_counts_df), unsafe_allow_html=True)


        st.session_state.last_metrics_update = current_run_time
        needs_rerun = True # 업데이트 발생했으니 rerun 필요


    # 그래프 및 스케줄 현황 테이블 업데이트 (GRAPH_UPDATE_INTERVAL 주기 또는 필터 변경 시)
    # 필터 변경은 Streamlit 위젯의 기본 동작으로 rerun을 발생시킵니다.
    # 여기서는 주기 업데이트 조건만 추가적으로 확인합니다.
    time_since_graph_update = (current_run_time - st.session_state.last_graph_update).total_seconds()
    if time_since_graph_update >= GRAPH_UPDATE_INTERVAL or not st.session_state.get('graph_displayed', False):
        # graph_displayed 상태를 사용하여 첫 로딩 시 무조건 그리도록 함
        st.session_state.graph_displayed = True

        # 그래프 데이터 가져오기
        graph_df = fetch_graph_data(conn, selected_statuses, start_datetime_filter, end_datetime_filter)

        # 그래프 그리기 (Plotly)
        if not graph_df.empty:
            # Plotly에 사용할 색상 매핑 (모든 상태 포함하여 범례 색상 일관성 유지)
            status_map = {s: COLOR_MAP.get(s, 'gray') for s in sorted(list(COLOR_MAP.keys()))}

            if graph_type == "꺽은선":
                fig = px.line(graph_df, x='HOURLY', y='CNT_STATUS', color='TASK_STATUS',
                              title='시간대별 스케줄 현황',
                              color_discrete_map=status_map)
                fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font_color='black',
                                  legend=dict(font=dict(color="black")),
                                  xaxis=dict(color="black"),
                                  yaxis=dict(color="black"))

            else: # 막대 그래프
                fig = px.bar(graph_df, x='HOURLY', y='CNT_STATUS', color='TASK_STATUS',
                             title='시간대별 스케줄 현황', barmode='group', # 'stack' 가능
                             color_discrete_map=status_map)
                fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font_color='black',
                                  legend=dict(font=dict(color="black")),
                                  xaxis=dict(color="black"),
                                  yaxis=dict(color="black"))

            graph_placeholder.plotly_chart(fig, use_container_width=True)
        else:
            graph_placeholder.info("스케줄 현황 그래프 데이터를 가져올 수 없습니다.")


        # 스케줄 현황 테이블 업데이트
        schedule_table_df = fetch_table_data(conn, selected_statuses, start_datetime_filter, end_datetime_filter)
        if not schedule_table_df.empty:
            table_placeholder.markdown(generate_schedule_table_html(schedule_table_df), unsafe_allow_html=True)
        else:
            table_placeholder.info("스케줄 현황 테이블 데이터를 가져올 수 없습니다.")

        st.session_state.last_graph_update = current_run_time
        needs_rerun = True # 업데이트 발생했으니 rerun 필요


    # --- 주기적 Rerun 타이머 ---
    # 다음 업데이트까지 남은 시간 계산
    # 각 타이머의 다음 예정 시간
    next_metrics_update_time = st.session_state.last_metrics_update + datetime.timedelta(seconds=METRICS_UPDATE_INTERVAL)
    next_graph_update_time = st.session_state.last_graph_update + datetime.timedelta(seconds=GRAPH_UPDATE_INTERVAL)

    # 가장 가까운 다음 업데이트 예정 시간
    next_update_time = min(next_metrics_update_time, next_graph_update_time)

    # 다음 업데이트까지 남은 실제 시간
    time_until_next_update = (next_update_time - current_run_time).total_seconds()

    # 남은 시간이 있다면 대기 후 rerun, 없다면 즉시 rerun 또는 짧은 대기 후 rerun
    # time_until_next_update가 음수일 수도 있으므로 (처리 시간 지연 등), 최소 대기 시간 설정
    sleep_duration = max(0.1, time_until_next_update)

    # print(f"Current: {current_run_time.strftime('%H:%M:%S')}, Next Metrics: {next_metrics_update_time.strftime('%H:%M:%S')}, Next Graph: {next_graph_update_time.strftime('%H:%M:%S')}, Sleep: {sleep_duration:.2f}s") # 디버깅용

    time.sleep(sleep_duration)
    st.rerun() # 전체 스크립트 다시 실행

# 앱 실행 엔트리 포인트
if __name__ == "__main__":
    run_dashboard()

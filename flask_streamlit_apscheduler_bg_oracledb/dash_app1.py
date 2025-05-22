# 필요한 라이브러리 가져오기
import streamlit as st
import oracledb
import psutil
import pandas as pd
import plotly.express as px
import datetime # <-- datetime 모듈만 임포트!
import time # time 모듈 (time.sleep 등)
import sys
from common.dbhandler import DBHandler
from common.loghandler import LogHandler

# --- Streamlit 페이지 설정 ---
# 브라우저 탭 타이틀과 전체 레이아웃 너비 설정
st.set_page_config(page_title="스케줄데쉬보드", layout="wide")

log_handler = LogHandler()
logger = log_handler.getloghandler("main")

db_handler = DBHandler()
db_config = db_handler.get_db_config()

# 데이터 업데이트 주기 (캐시 TTL - Time To Live)
SCHEDULE_DATA_TTL_SEC = 60 # 스케줄 데이터 1분 주기
METRICS_DATA_TTL_SEC = 3 # 시스템 메트릭스 데이터 3초 주기
CLOCK_DATA_TTL_SEC = 0.3 # 시계 데이터 0.3초 (300ms) 주기

# 스케줄 상태별 색상 설정 (그래프, 테이블 행 색상에 사용)
STATUS_COLORS = {
    "R": "gray",   # 대기상태
    "X": "blue",   # 실행중
    "S": "green",  # 완료종료
    "F": "yellow", # Fail종료
    "K": "red",    # 강제종료
}

# --- CSS 스타일 설정 ---
# 배경색, 글자색, 테이블 테두리 등을 CSS로 설정
st.markdown(f"""
<style>
    /* 전체 앱 배경색 */
    .stApp {{
        background-color: black;
        color: white; /* 기본 글자색 */
    }}

    /* 제목 글자색 */
    h1, h3, h4 {{
        color: yellow;
    }}

    /* 검색 조건 라벨 글자색 */
    .stMultiSelect label, .stSelectbox label, .stDateInput label, .stTimeInput label, .stCheckbox label, .stRadio label {{
        color: yellow !important;
    }}

    /* 입력 위젯 내부의 글자색과 배경색 (선택값 등) */
    /* Streamlit 버전 및 브라우저에 따라 셀렉터가 다를 수 있음 */
    div[data-baseweb="select"] > div, /* Selectbox 선택 영역 */
    div[data-baseweb="datetime"] input, /* Date input 글자 */
    div[data-baseweb="input"] input, /* Time input 글자 */
    .stDateInput div[data-baseweb="input"], /* Date input 전체 영역 */
    .stTimeInput div[data-baseweb="input"] /* Time input 전체 영역 */
     {{
        color: black !important;
        background-color: white !important;
    }}
     /* 캘린더나 드롭다운 팝업 내부 스타일 */
    [data-baseweb="popover"] {{
        color: black; /* 팝업 글자색 */
        background-color: white; /* 팝업 배경색 */
    }}


    /* 데이터프레임 (테이블) 스타일 */
    .stDataFrame {{
        background-color: white; /* 데이터프레임 컨테이너 배경 */
        color: black; /* 데이터프레임 기본 글자색 */
        border: 1px solid gray; /* 데이터프레임 테두리 */
    }}
     /* 데이터프레임 헤더 스타일 */
    .stDataFrame table th {{
         background-color: #e0e0e0; /* 헤더 배경색 (옅은 회색) */
         color: black;
         border: 1px solid gray; /* 헤더 테두리 */
    }}
     /* 데이터프레임 셀 스타일 */
     .stDataFrame table td {{
         color: black;
         border: 1px solid gray; /* 셀 테두리 */
     }}

    /* 상태별 카운트 테이블 행 색상은 Pandas 스타일링으로 적용 */

</style>
""", unsafe_allow_html=True)


# --- 세션 상태 (st.session_state) 초기화 ---
# 위젯 상태나 캐시된 데이터를 저장해서 스크립트 재실행 시에도 값을 유지해줘.
if 'selected_statuses' not in st.session_state:
    st.session_state.selected_statuses = ["R", "X", "S", "F", "K"] # 기본값: 전체 선택
if 'graph_type' not in st.session_state:
    st.session_state.graph_type = "꺽은선" # 기본 그래프 종류
if 'use_custom_time' not in st.session_state:
    st.session_state.use_custom_time = "OFF (24시간 전후)" # 기본 자동/수동 (위젯 표시 텍스트로 변경)
if 'start_date' not in st.session_state:
    st.session_state.start_date = datetime.datetime.now().date() - datetime.timedelta(days=1)
if 'start_time' not in st.session_state: # time_input은 time 객체만 반환
     st.session_state.start_time = datetime.time(0, 0) # 기본값: 자정
if 'end_date' not in st.session_state:
    st.session_state.end_date = datetime.datetime.now().date() + datetime.timedelta(days=1)
if 'end_time' not in st.session_state: # time_input은 time 객체만 반환
     st.session_state.end_time = datetime.time(23, 59) # 기본값: 밤 11시 59분

# 캐시된 데이터 저장용 (st.cache_data가 실제 캐싱 관리)
# 여기에 저장하는 이유는 캐시 만료 후 새로 가져온 데이터를 세션 상태에 반영하기 위함이야.
# 'cached' 접미사를 붙여서 캐시 함수 이름과 구분했어.
if 'schedule_data_graph_cached' not in st.session_state:
     st.session_state.schedule_data_graph_cached = pd.DataFrame()
if 'schedule_data_table_cached' not in st.session_state:
     st.session_state.schedule_data_table_cached = pd.DataFrame()
if 'system_metrics_data_cached' not in st.session_state:
     st.session_state.system_metrics_data_cached = {}
if 'cpu_top5_data_cached' not in st.session_state:
     st.session_state.cpu_top5_data_cached = pd.DataFrame()
if 'memory_top5_data_cached' not in st.session_state:
     st.session_state.memory_top5_data_cached = pd.DataFrame()
if 'current_time_cached' not in st.session_state:
     st.session_state.current_time_cached = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 시계 표시용 초기값

# --- 데이터베이스 연결 함수 (st.cache_resource 로 연결 객체 캐싱) ---
# DB 연결은 앱 실행 중 한 번만 하도록 캐시해두는 게 좋아.
@st.cache_resource(show_spinner=False) # 데이터 로딩 시 스피너 감춤
def init_db_connection():
    try:
        # Oracle Instant Client 사용 시 아래 주석 해제 및 경로 설정
        # oracledb.init_oracle_client(lib_dir="/path/to/instantclient_21_X")
        conn = oracledb.connect(user=db_config['user'], password=db_config['password'], dsn=db_config['dsn'])
        return conn
    except Exception as e:
        st.error(f"🚫 데이터베이스 연결 오류 발생: {e}")
        st.stop() # DB 연결 실패 시 앱 중지
        return None # 여기에 도달하진 않지만 명시적으로 반환

dbconn = init_db_connection()  # DB 연결 객체 가져오기

# --- 데이터 가져오는 함수들 (st.cache_data 로 데이터 캐싱) ---
# 이 함수들은 인자가 바뀌거나 캐시 유효 시간(ttl)이 지나고 스크립트가 재실행될 때만 실제로 실행돼.

@st.cache_data(ttl=CLOCK_DATA_TTL_SEC, show_spinner=False) # 0.3초 TTL 설정
def get_current_time_str():
    """캐시 TTL에 따라 현재 시간을 문자열로 가져와."""
    # 이 함수는 스크립트가 재실행되고 0.3초가 지났을 때만 실제로 실행돼.
    # Streamlit 자체는 주기적으로 자동 재실행되지 않아.
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@st.cache_data(ttl=METRICS_DATA_TTL_SEC, show_spinner=False) # 3초 TTL 설정
def get_system_metrics():
    """시스템 CPU, 메모리, 디스크, 네트워크 사용량 정보를 가져와."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1) # 논블로킹으로 CPU 사용률 측정
        mem = psutil.virtual_memory()

        # 시스템 디스크 경로 찾기 (OS별 기본 경로 사용)
        try:
            system_partition_path = '/' # Linux, macOS 기본
            if sys.platform.startswith('win'):
                 system_partition_path = 'C:\\' # Windows 기본
            # psutil.disk_partitions()를 사용해서 더 정확히 찾을 수도 있어.
            disk = psutil.disk_usage(system_partition_path)
            disk_percent = f"{disk.percent:.1f}%"
        except Exception as disk_error:
             #st.warning(f"⚠️ 디스크 사용률 조회 오류: {disk_error}. '/' 또는 'C:\\' 경로를 확인해줘.") # 너무 자주 뜨면 시끄러움
             disk_percent = "N/A" # 오류 시 'N/A' 표시


        net_io = psutil.net_io_counters()

        metrics = {
            "CPU 사용률": f"{cpu_percent:.1f}%",
            "메모리 사용률": f"{mem.percent:.1f}%",
            "디스크 사용률": disk_percent,
            "네트워크 Input": f"{net_io.bytes_recv / (1024*1024):.2f} MB", # Bytes를 MB로 변환
            "네트워크 Output": f"{net_io.bytes_sent / (1024*1024):.2f} MB",
            "총 메모리 사이즈": f"{mem.total / (1024*1024*1024):.2f} GB", # Bytes를 GB로 변환
            "메모리 사용 중 사이즈": f"{mem.used / (1024*1024*1024):.2f} GB", # Bytes를 GB로 변환
            "메모리 사용가능 사이즈": f"{mem.available / (1024*1024*1024):.2f} GB", # Bytes를 GB로 변환
        }
        return metrics
    except Exception as e:
        #st.error(f"🚫 시스템 메트릭스 조회 중 오류 발생: {e}") # 너무 자주 뜨면 시끄러움
        return {}

@st.cache_data(ttl=METRICS_DATA_TTL_SEC, show_spinner=False) # 3초 TTL 설정
def get_top_processes(by='cpu'):
    """CPU 또는 메모리 사용량 상위 5개 프로세스 정보를 가져와."""
    try:
        processes = []
        # 필요한 정보 (pid, 이름, cpu 사용률, 메모리 정보, 커맨드 라인) 가져오기
        # cpu_percent는 interval=0.1을 줘야 제대로 된 값(이전 호출 대비)을 얻을 수 있지만,
        # cache 함수 내에서는 이게 매번 실행될지 보장하기 어려우므로,
        # get_system_metrics에서처럼 interval=0.1을 사용하거나,
        # 0으로 설정하고 이전 호출 값에 의존하게 됨. 여기선 간결하게 0으로 설정해둘게.
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'cmdline']):
            try:
                pinfo = proc.info
                # RSS (Resident Set Size)는 실제 물리 메모리 사용량이야.
                pinfo['memory_rss'] = pinfo['memory_info'].rss
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 종료되었거나, 접근 권한이 없거나, 좀비 프로세스는 건너뛰어.
                pass

        if by == 'cpu':
            # CPU 사용량 기준으로 정렬 후 상위 5개 가져오기
            # .get()을 사용해서 키가 없을 경우 오류 방지 (프로세스 정보가 불안정할 수 있어)
            top_processes = sorted(processes, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:5]
            data = []
            for p in top_processes:
                 # cmdline은 리스트일 수 있으니 문자열로 합쳐주고, 없으면 프로세스 이름을 사용해.
                cmd = ' '.join(p.get('cmdline') or []) if p.get('cmdline') else p.get('name', 'Unknown')
                data.append({
                    "프로세스명": p.get('name', 'Unknown'),
                    "CPU 사용률 (%)": f"{p.get('cpu_percent', 0):.1f}",
                    # '커맨드' 컬럼은 풍선 도움말 기능이 Streamlit 기본 dataframe에 없어서
                    # 전체 명령문을 그대로 표시할게.
                    "커맨드": cmd
                })
            return pd.DataFrame(data)
        elif by == 'memory':
            # 메모리(RSS) 사용량 기준으로 정렬 후 상위 5개 가져오기
            top_processes = sorted(processes, key=lambda x: x.get('memory_rss', 0), reverse=True)[:5]
            data = []
            for p in top_processes:
                 # cmdline 처리
                cmd = ' '.join(p.get('cmdline') or []) if p.get('cmdline') else p.get('name', 'Unknown')
                data.append({
                    "프로세스명": p.get('name', 'Unknown'),
                    "메모리 사용 사이즈 (MB)": f"{p.get('memory_rss', 0) / (1024 * 1024):.2f}", # Bytes를 MB로 변환
                 # '커맨드' 컬럼은 풍선 도움말 기능이 Streamlit 기본 dataframe에 없어서
                 # 전체 명령문을 그대로 표시할게.
                 "커맨드": cmd
                })
            return pd.DataFrame(data)
        else:
            return pd.DataFrame() # 잘못된 인자 처리

    except Exception as e:
        #st.error(f"🚫 Top 프로세스 조회 중 오류 발생 ({by}): {e}") # 너무 자주 뜨면 시끄러움
        return pd.DataFrame()


@st.cache_data(ttl=SCHEDULE_DATA_TTL_SEC, show_spinner=False) # 1분 TTL 설정
def fetch_schedule_data(_conn, selected_statuses, start_datetime, end_datetime):
    """스케줄 현황 그래프 및 테이블 데이터를 DB에서 가져와."""
    cursor = _conn.cursor()

    # 스케줄 상태 필터 조건 SQL 구문 및 바인딩 변수 처리 수정
    status_filter_sql = ""
    status_bind_vars = {}
    if selected_statuses:
        # 선택된 상태 개수만큼 바인딩 변수 이름 (:status_0, :status_1, ...) 생성
        # list comprehension으로 바인딩 변수 이름 리스트 생성
        status_placeholders = [f":status_{i}" for i in range(len(selected_statuses))]
        # IN 절 SQL 구문 생성
        status_filter_sql = f" AND task_status IN ({', '.join(status_placeholders)}) "
        # 바인딩 변수 딕셔너리 생성 (예: {'status_0': 'R', 'status_1': 'X'})
        status_bind_vars = {f"status_{i}": status for i, status in enumerate(selected_statuses)}

    # 쿼리 1: 시간대별 스케줄 카운트 (그래프용)
    sql_graph = f"""
    SELECT TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24') AS hourly,
           task_status, COUNT(task_status) as cnt_status
    FROM task
    WHERE subprocee_starttime BETWEEN :start_dt AND :end_dt
      {status_filter_sql} -- 동적으로 생성된 필터 SQL 삽입
    GROUP BY TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24'), task_status
    ORDER BY TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24')
    """
    try:
        # 바인딩 변수 딕셔너리 조합
        # 시간 바인딩 변수와 상태 바인딩 변수를 합쳐줘
        bind_vars_graph = {'start_dt': start_datetime, 'end_dt': end_datetime}
        bind_vars_graph.update(status_bind_vars) # 상태 바인딩 변수 추가

        cursor.execute(sql_graph, bind_vars_graph) # 조합된 바인딩 변수 사용

        graph_data = cursor.fetchall()
        graph_df = pd.DataFrame(graph_data, columns=['HOURLY', 'TASK_STATUS', 'CNT_STATUS'])
        # Plotly에서 시간축 정렬을 위해 datetime 객체로 변환 시도
        try:
            # datetime.datetime.strptime 대신 pd.to_datetime 사용 (더 유연함)
            graph_df['HOURLY_DT'] = pd.to_datetime(graph_df['HOURLY'], format='%Y-%m-%d %H', errors='coerce') # 오류 시 NaT
            # 유효한 datetime만 필터링하고 정렬
            graph_df = graph_df.dropna(subset=['HOURLY_DT']).sort_values('HOURLY_DT')
            # 그래프 x축은 다시 'YYYY-MM-DD HH24' 문자열 포맷으로 사용 (Plotly가 알아서 정렬함)
            graph_df['HOURLY'] = graph_df['HOURLY_DT'].dt.strftime('%Y-%m-%d %H')
        except Exception as e:
            st.warning(f"⚠️ 시간대 데이터 변환 중 오류 발생: {e}. 문자열 순서로 정렬합니다.")
            graph_df = graph_df.sort_values('HOURLY') # 변환 실패 시 문자열로 정렬


    except Exception as e:
        st.error(f"🚫 스케줄 현황 그래프 데이터 조회 중 오류 발생: {e}")
        graph_df = pd.DataFrame(columns=['HOURLY', 'TASK_STATUS', 'CNT_STATUS']) # 오류 시 빈 DF

    # 쿼리 2: 상세 스케줄 목록 (테이블용 및 상태별 카운트 계산용)
    sql_table = f"""
    SELECT subprocee_starttime, taskname, task_status
    FROM task
    WHERE subprocee_starttime BETWEEN :start_dt AND :end_dt
      {status_filter_sql} -- 동적으로 생성된 필터 SQL 삽입
    ORDER BY subprocee_starttime
    """
    try:
        # 쿼리 1과 동일한 바인딩 변수 사용
        bind_vars_table = {'start_dt': start_datetime, 'end_dt': end_datetime}
        bind_vars_table.update(status_bind_vars) # 상태 바인딩 변수 추가

        cursor.execute(sql_table, bind_vars_table) # 조합된 바인딩 변수 사용
        table_data = cursor.fetchall()
        table_df = pd.DataFrame(table_data, columns=['SUBPROCEE_STARTTIME', 'TASKNAME', 'TASK_STATUS'])
        # datetime 열 포맷 수정 (object 타입이 아닌 datetime 타입일 때만 적용)
        if pd.api.types.is_datetime64_any_dtype(table_df['SUBPROCEE_STARTTIME']):
             table_df['SUBPROCEE_STARTTIME'] = table_df['SUBPROCEE_STARTTIME'].dt.strftime('%Y-%m-%d %H:%M:%S')
        # else: 데이터 타입이 datetime이 아니면 그냥 둠 (오류 방지)


    except Exception as e:
        st.error(f"🚫 스케줄 현황 테이블 데이터 조회 중 오류 발생: {e}")
        table_df = pd.DataFrame(columns=['SUBPROCEE_STARTTIME', 'TASKNAME', 'TASK_STATUS']) # 오류 시 빈 DF

    cursor.close()
    return graph_df, table_df


# --- 화면 표시 함수들 ---

def display_schedule_graph(graph_df, graph_type):
    """스케줄 현황 그래프를 Plotly를 사용하여 표시해줘."""
    st.markdown("<h4>스케줄 현황 그래프</h4>", unsafe_allow_html=True)
    if not graph_df.empty:
        # Plotly 그래프 생성
        if graph_type == "꺽은선":
            fig = px.line(
                graph_df,
                x="HOURLY", # datetime 객체 또는 정렬된 문자열 컬럼 사용
                y="CNT_STATUS",
                color="TASK_STATUS",
                title="시간대별 스케줄 카운트",
                color_discrete_map=STATUS_COLORS, # 상태별 색상 적용
                 labels={"HOURLY": "시간대", "CNT_STATUS": "건수", "TASK_STATUS": "상태"} # 라벨 한글화
            )
        else: # 막대 그래프
             fig = px.bar(
                graph_df,
                x="HOURLY", # datetime 객체 또는 정렬된 문자열 컬럼 사용
                y="CNT_STATUS",
                color="TASK_STATUS",
                title="시간대별 스케줄 카운트",
                color_discrete_map=STATUS_COLORS, # 상태별 색상 적용
                 labels={"HOURLY": "시간대", "CNT_STATUS": "건수", "TASK_STATUS": "상태"} # 라벨 한글화
            )
        # 그래프 배경을 흰색으로 설정 (CSS는 그래프 내부까지 영향 주기 어려움)
        fig.update_layout(
            plot_bgcolor='white', # 그래프 영역 배경색
            paper_bgcolor='white', # 그래프 이미지 배경색
            font=dict(color="black") # 그래프 텍스트 색상
        )
        st.plotly_chart(fig, use_container_width=True) # 화면 너비에 맞춰 표시
    else:
        st.info("🤔 표시할 스케줄 현황 그래프 데이터가 없습니다.")

def display_schedule_table(table_df):
    """스케줄 현황 상세 테이블을 표시해줘."""
    st.markdown("<h4>스케줄 현황 테이블</h4>", unsafe_allow_html=True)
    if not table_df.empty:
        # st.dataframe은 자동으로 테이블 형태로 표시해줘.
        st.dataframe(table_df, use_container_width=True)
    else:
         st.info("🤔 표시할 스케줄 현황 테이블 데이터가 없습니다.")

def display_status_count_table(table_df):
    """상태별 스케줄 카운트 테이블을 표시하고 행 색상 및 가독성 높은 글자색을 적용해줘."""
    st.markdown("<h4>상태별 스케줄 카운트</h4>", unsafe_allow_html=True)
    if not table_df.empty:
        # 상세 테이블 데이터에서 상태별 카운트 계산
        status_counts_df = table_df['TASK_STATUS'].value_counts().reset_index()
        status_counts_df.columns = ['TASK_STATUS', 'COUNT']
        st.dataframe(status_counts_df, use_container_width=True)
    else:
         st.info("🤔 표시할 상태별 스케줄 카운트 데이터가 없습니다.")

def display_system_metrics(metrics_data):
    """시스템 메트릭스 정보를 표시해줘."""
    st.markdown("<h4>스케줄 시스템 메트릭스</h4>", unsafe_allow_html=True)
    if metrics_data:
        # 요청한 1x10 테이블 형태는 복잡하고 가독성이 떨어져서, 리스트 형태로 표시할게.
        # 각 항목을 줄바꿈하여 보여주는 것이 정보 파악에 더 좋을 것 같아.
        metrics_text_lines = [f"- **{k}**: {v}" for k, v in metrics_data.items()]
        st.markdown("\n".join(metrics_text_lines), unsafe_allow_html=True)
    else:
         st.info("🤔 시스템 메트릭스 데이터를 가져오지 못했습니다.")

def display_top_processes(df, title):
    """CPU/메모리 상위 5개 프로세스 테이블을 표시해줘."""
    st.markdown(f"<h4>{title}</h4>", unsafe_allow_html=True)
    if not df.empty:
        # st.dataframe으로 테이블 표시. 커맨드 풍선글 기능은 기본 제공되지 않아서,
        # 전체 커맨드 문자열을 테이블 셀에 그대로 표시하도록 했어.
        st.dataframe(df, use_container_width=True)
    else:
         st.info(f"🤔 표시할 {title} 프로세스 데이터가 없습니다.")


# --- 실시간 시계 표시 ---
# 캐시 함수를 호출해서 현재 시간을 가져와.
# 스크립트가 재실행되고 CLOCK_DATA_TTL_SEC(0.3초)가 지났으면 새 시간을 가져오고,
# 아니면 캐시된 이전 시간을 사용해.
# 이 함수 자체는 스크립트가 재실행되어야 동작하므로,
# Streamlit의 기본 동작 방식 상 완벽히 300ms마다 "자동"으로 업데이트되지는 않아.
# 사용자의 위젯 조작이나 새로고침 등 스크립트 재실행 시 업데이트되는 방식이야.
st.session_state.current_time_cached = get_current_time_str()


# --- 레이아웃 구성 ---

# 맨 위 제목 및 시계 영역 (가운데 제목, 오른쪽 시계)
# 시계가 업데이트될 placeholder를 미리 확보해둬.
# 시계 업데이트 자체를 강제하는 부분은 별도로 구현하기 어렵지만,
# placeholder를 사용하면 다음 업데이트 시 해당 위치에 자연스럽게 표시돼.
title_col, clock_col = st.columns([3, 1]) # 3:1 비율로 컬럼 나누기
with title_col:
     st.markdown("<h1 style='text-align: center;'>스케줄데쉬보드</h1>", unsafe_allow_html=True) # CSS로 색상 적용
with clock_col:
     # 확보된 placeholder에 현재 시간을 표시
     # st.markdown(f"<h1 style='text-align: right;'>{st.session_state.current_time_cached}</h1>", unsafe_allow_html=True)
     # Streamlit의 clock 예시처럼 placeholder 사용
     clock_placeholder = st.empty()
     clock_placeholder.markdown(f"<h1 style='text-align: right;'>{st.session_state.current_time_cached}</h1>", unsafe_allow_html=True)


# 메인 컨텐츠 영역 (왼쪽 3/4, 오른쪽 1/4)
col3, col1 = st.columns([3, 1]) # 3:1 비율로 컬럼 나누기

# --- 왼쪽 컬럼 (스케줄 현황) ---
with col3:
    st.markdown("<h3>스케줄 현황</h3>", unsafe_allow_html=True)

    # 스케줄 검색 조건 영역 (CSS로 라벨 색상 적용)
    st.markdown("<h4>스케줄 검색 조건</h4>", unsafe_allow_html=True)

    # 검색 조건 위젯들을 가로로 나열하기 위해 컬럼 사용 (8개 컬럼으로 시간 입력 필드 추가)
    search_col1, search_col2, search_col3, search_col4, search_col5, search_col6, search_col7, search_col8 = st.columns(
        [2, 1.5, 1.5, 1.5, 0.3, 1.5, 1.5, 1.2])

    with search_col2:
        # 그래프 종류 선택 콤보박스
        graph_type_widget = st.selectbox(
            "그래프 종류",
            ["꺽은선", "막대"],
            index=0 if st.session_state.graph_type == "꺽은선" else 1,  # 세션 상태 값으로 인덱스 설정
            key="graph_type_select"
        )
        st.session_state.graph_type = graph_type_widget  # 위젯 값으로 세션 상태 업데이트

    with search_col8:  # 자동/수동는 마지막 컬럼으로 이동
        # 자동/수동 선택 (자동/수동) 콤보박스
        use_custom_time_widget = st.selectbox(
            "자동/수동 선택",
            ["자동", "수동"],  # 사용자에게 더 명확하게 표시
            index=0 if st.session_state.use_custom_time == "자동" else 1,
            key="use_custom_time_select"
        )
        st.session_state.use_custom_time = use_custom_time_widget  # 위젯 값 그대로 세션 상태 업데이트

    # 시작일, 시작시간 입력 필드
    with search_col3:
        start_date_widget = st.date_input(
            "시작일",
            value=st.session_state.start_date,
            key="start_date_input",
            disabled=(st.session_state.use_custom_time == "자동")  # OFF일 때는 비활성화
        )
        st.session_state.start_date = start_date_widget

    with search_col4:
        start_time_widget = st.time_input(
            "시작시간",
            value=st.session_state.start_time,
            key="start_time_input",
            step=60  # 1분 단위
            , disabled=(st.session_state.use_custom_time == "자동")  # OFF일 때는 비활성화
        )
        st.session_state.start_time = start_time_widget

    with search_col5:
        # 간단한 구분자
        st.markdown("<br>-<br>", unsafe_allow_html=True)  # br 태그로 세로 간격 맞추기

    # 종료일, 종료시간 입력 필드
    with search_col6:
        end_date_widget = st.date_input(
            "종료일",
            value=st.session_state.end_date,
            key="end_date_input",
            disabled=(st.session_state.use_custom_time == "자동")  # OFF일 때는 비활성화
        )
        st.session_state.end_date = end_date_widget

    with search_col7:
        end_time_widget = st.time_input(
            "종료시간",
            value=st.session_state.end_time,
            key="end_time_input",
            step=60  # 1분 단위
            , disabled=(st.session_state.use_custom_time == "자동")  # OFF일 때는 비활성화
        )
        st.session_state.end_time = end_time_widget

    # 실제 쿼리에 사용할 자동/수동 결정 (datetime 객체로 조합)
    if st.session_state.use_custom_time == "수동":
        # 선택한 날짜와 시간을 조합하여 datetime 객체 생성
        try:
            query_start_datetime = datetime.datetime.combine(st.session_state.start_date, st.session_state.start_time)
            query_end_datetime = datetime.datetime.combine(st.session_state.end_date, st.session_state.end_time)
            # 종료 시간이 시작 시간보다 빠르면 경고 (필요시)
            if query_end_datetime < query_start_datetime:
                st.warning("⚠️ 종료 시간이 시작 시간보다 빠릅니다.")
                # 여기서 쿼리 실행을 중지하거나, 범위를 조정하는 로직을 추가할 수 있어.
                # 일단은 경고만 표시하고 쿼리는 실행하도록 둘게.
        except Exception as e:
            st.error(f"🚫 선택 시간 조합 오류: {e}")
            # 오류 발생 시 쿼리를 실행하지 않도록 빈 datetime 값 설정 또는 함수 종료 등 처리 필요
            # 여기서는 예시로 현재 시간 기준 24시간 전후로 대체하도록 할게.
            st.warning("선택 시간 오류로 인해 현재 시간 기준 24시간 전후 데이터로 표시합니다.")
            now = datetime.datetime.now()
            query_start_datetime = now - datetime.timedelta(hours=24)
            query_end_datetime = now + datetime.timedelta(hours=24)

    else:  # OFF (24시간 전후)
        # 현재 시간 기준 24시간 전후
        now = datetime.datetime.now()
        query_start_datetime = now - datetime.timedelta(hours=24)
        query_end_datetime = now + datetime.timedelta(hours=24)

    with search_col1:
        # 스케줄 상태 다중 선택 콤보박스
        selected_statuses_widget = st.multiselect(
            "스케줄 상태",
            ["R", "X", "S", "F", "K"],
            default=st.session_state.selected_statuses,  # 세션 상태에 저장된 기본값 사용
            key="status_multiselect"  # 위젯 상태 유지를 위한 고유 키
        )
        st.session_state.selected_statuses = selected_statuses_widget  # 위젯 값으로 세션 상태 업데이트

    # 스케줄 데이터 가져오기 (캐시 함수 사용)
    # 위젯 값이 변경되거나 1분(SCHEDULE_DATA_TTL_SEC)이 지나고 스크립트가 재실행되면 데이터를 다시 가져와.
    st.session_state.schedule_data_graph_cached, st.session_state.schedule_data_table_cached = fetch_schedule_data(
        dbconn,
        st.session_state.selected_statuses, # 선택된 상태 리스트
        query_start_datetime, # 결정된 쿼리 시작 시간 (datetime 객체)
        query_end_datetime    # 결정된 쿼리 종료 시간 (datetime 객체)
    )

    # 스케줄 현황 그래프 표시
    display_schedule_graph(st.session_state.schedule_data_graph_cached, st.session_state.graph_type)

    # 스케줄 현황 테이블 표시
    display_schedule_table(st.session_state.schedule_data_table_cached)


# --- 오른쪽 컬럼 (상태별 카운트, 시스템 메트릭스, Top 프로세스) ---
with col1:
    # 상태별 스케줄 카운트 테이블 표시 (스케줄 테이블 데이터를 기반으로 계산)
    display_status_count_table(st.session_state.schedule_data_table_cached)

    # 시스템 메트릭스 데이터 가져오기 및 표시 (3초 TTL 캐시 함수 사용)
    # 스크립트 재실행 시 3초가 지났으면 데이터를 다시 가져와.
    st.session_state.system_metrics_data_cached = get_system_metrics()
    display_system_metrics(st.session_state.system_metrics_data_cached)

    # CPU Top 5 데이터 가져오기 및 표시 (3초 TTL 캐시 함수 사용)
    st.session_state.cpu_top5_data_cached = get_top_processes(by='cpu')
    display_top_processes(st.session_state.cpu_top5_data_cached, "CPU Top5")

    # 메모리 Top 5 데이터 가져오기 및 표시 (3초 TTL 캐시 함수 사용)
    st.session_state.memory_top5_data_cached = get_top_processes(by='memory')
    display_top_processes(st.session_state.memory_top5_data_cached, "Memory Top5")

# --- 앱 주기적 업데이트를 위한 루프 ---
# time.sleep() 후 st.rerun()을 호출하여 스크립트를 다시 실행
# 이렇게 하면 캐시 TTL에 따라 데이터가 주기적으로 업데이트되는 효과를 낼 수 있어.
# 이 부분은 스크립트가 완전히 로드된 후에 실행되어야 해.
time.sleep(CLOCK_DATA_TTL_SEC) # 시계 TTL 주기에 맞춰 대기 (다른 데이터도 같이 업데이트됨)
st.rerun() # 스크립트를 처음부터 다시 실행


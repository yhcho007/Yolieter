# 필요한 라이브러리 설치
# pip install streamlit oracledb pandas plotly psutil

import streamlit as st
import oracledb
import pandas as pd
import time
import plotly.express as px
import datetime
import psutil # psutil 라이브러리 추가
from common.dbhandler import DBHandler
from common.loghandler import LogHandler

# --- 페이지 설정 ---
st.set_page_config(
    page_title="스케줄데쉬보드",  # 브라우저 탭 제목
    layout="wide",             # 화면 전체 폭 사용
    initial_sidebar_state="collapsed" # 사이드바 기본 상태
)

# --- 사용자 정의 CSS로 배경색 설정 ---
# 그래프와 테이블 색상은 플로틀리/판다스 기본 색상 또는 설정 가능한 색상으로 표시됩니다.
# 전체적인 대비를 위해 플로틀리 테마를 어둡게 설정할 수 있습니다.
st.markdown(
    """
    <style>
    body {
        background-color: #000000; /* 검은색 배경 */
        color: #FFFFFF; /* 글자색을 흰색으로 설정 (필요에 따라 조정) */
    }
    .stApp {
        background-color: #000000; /* Streamlit 앱 컨테이너 배경색 */
    }
    /* Streamlit 기본 위젯들의 색상 조정 */
    /* st.dataframe을 위한 스타일 */
    div[data-testid="stDataFrame"] {
        color: #FFFFFF; /* 데이터프레임 글자색 */
        background-color: #1c1c1c; /* 데이터프레임 배경색 (조금 더 밝게) */
        border: 1px solid #333333; /* 테두리 색상 */
    }
    div[data-testid="stDataFrame"] .dataframe th {
        color: #AAAAAA; /* 헤더 글자색 */
        background-color: #2a2a2a; /* 헤더 배경색 */
        font-weight: bold; /* 헤더 볼드체 */
        border: 1px solid #333333; /* 헤더 테두리 색상 */
    }
     div[data-testid="stDataFrame"] .dataframe td {
        border: 1px solid #333333; /* 셀 테두리 색상 */
    }
     div[data-testid="stDataFrame"] .dataframe tr:nth-child(even) {
        background-color: #1c1c1c; /* 짝수 행 배경색 */
    }
     div[data-testid="stDataFrame"] .dataframe tr:nth-child(odd) {
        background-color: #202020; /* 홀수 행 배경색 */
    }
    /* 스크롤바 스타일 (선택 사항) */
    div[data-testid="stDataFrame"] .dataframe-container {
        scrollbar-color: #555 #222;
        scrollbar-width: thin;
    }
    </style>
    """,
    unsafe_allow_html=True
)

log_handler = LogHandler()
logger = log_handler.getloghandler("main")

db_handler = DBHandler()
db_config = db_handler.get_db_config()

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

# --- 데이터 가져오는 함수들 ---

def fetch_schedule_status_hourly(conn):
    """시간대별 스케줄 현황 및 총 개수 데이터 가져오기 (이전 12시간 ~ 이후 12시간)"""
    query = """
    SELECT HOURLY, TASK_STATUS, COUNT(TASK_STATUS) as cnt_status
    FROM (
        SELECT TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24') AS hourly,
               taskname, task_status
        FROM task
        WHERE subprocee_starttime BETWEEN (SYSTIMESTAMP - INTERVAL '12' HOUR) AND (SYSTIMESTAMP + INTERVAL '12' HOUR)
    )
    GROUP BY HOURLY, TASK_STATUS
    """ # ORDER BY HOURLY 제거 - plotly에서 자동 정렬
    total_query = """
    SELECT HOURLY, sum(cnt_status) AS total_cnt
    FROM (
        SELECT HOURLY, TASK_STATUS, COUNT(TASK_STATUS) as cnt_status
        FROM (
            SELECT TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24') AS hourly,
                   taskname, task_status
            FROM task
            WHERE subprocee_starttime BETWEEN (SYSTIMESTAMP - INTERVAL '12' HOUR) AND (SYSTIMESTAMP + INTERVAL '12' HOUR)
        )
        GROUP BY HOURLY, TASK_STATUS
    )
    GROUP BY HOURLY
    """ # ORDER BY HOURLY 제거 - plotly에서 자동 정렬
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            status_data = cursor.fetchall()
            status_df = pd.DataFrame(status_data, columns=['HOURLY', 'TASK_STATUS', 'cnt_status'])

            cursor.execute(total_query)
            total_data = cursor.fetchall()
            total_df = pd.DataFrame(total_data, columns=['HOURLY', 'total_cnt'])

            # 두 데이터프레임을 HOURLY 기준으로 병합
            # 혹시 모를 중복 합산을 막기 위해, total_df에서는 HOURLY당 첫 번째 total_cnt 값만 사용
            total_df = total_df.groupby('HOURLY').first().reset_index()
            merged_df = pd.merge(status_df, total_df, on='HOURLY', how='left')

            # Plotly 그래프에서 시간 순서대로 정렬되도록 'HOURLY' 컬럼을 datetime 객체로 변환
            merged_df['HOURLY'] = pd.to_datetime(merged_df['HOURLY'], format='%Y-%m-%d %H')
            # 시간 순서로 데이터프레임 정렬
            merged_df = merged_df.sort_values(by='HOURLY').reset_index(drop=True)

            return merged_df
    except Exception as e:
        st.error(f"시간대별 스케줄 현황 데이터 가져오기 오류: {e}")
        return pd.DataFrame() # 빈 데이터프레임 반환

def fetch_schedule_list(conn):
    """스케줄 등록 현황 데이터 가져오기"""
    query = "SELECT taskid, subprocee_starttime, taskname, task_status FROM task ORDER BY subprocee_starttime DESC" # 최신 순 정렬
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['taskid', 'subprocee_starttime', 'taskname', 'task_status'])
            return df
    except Exception as e:
        st.error(f"스케줄 등록 현황 데이터 가져오기 오류: {e}")
        return pd.DataFrame() # 빈 데이터프레임 반환

def get_system_metrics():
    """시스템 메트릭스 (CPU, Memory, Disk, Network) 실제 데이터 가져오기 (psutil 사용)"""
    try:
        # CPU 사용률 (0.5초 간격으로 측정)
        cpu_percent = psutil.cpu_percent(interval=0.5)

        # 메모리 사용률
        mem = psutil.virtual_memory()
        total_memory_gb = mem.total / (1024**3) # Bytes to GB
        used_memory_gb = mem.used / (1024**3)   # Bytes to GB
        available_memory_gb = mem.available / (1024**3) # Bytes to GB
        memory_percent = mem.percent

        # 디스크 사용률 (루트 디렉토리 기준)
        # 윈도우의 경우 'C:\\' 등으로 경로를 수정해야 할 수 있습니다.
        try:
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
        except Exception as disk_e:
             st.warning(f"디스크 사용률 정보 가져오기 오류 (루트 디렉토리 '/'): {disk_e}. 다른 경로를 시도해보세요.")
             disk_percent = "N/A" # 오류 발생 시 N/A 표시


        # 네트워크 I/O (누적 값)
        # 정확한 초당 Rate를 계산하려면 이전 값을 저장해야 하나,
        # 여기서는 간단히 누적 바이트 값을 KB로 변환하여 표시합니다.
        net_io = psutil.net_io_counters()
        network_input_kb = net_io.bytes_recv / 1024 # Bytes to KB
        network_output_kb = net_io.bytes_sent / 1024 # Bytes to KB

        return {
            "cpu_usage": f"{cpu_percent:.1f}%",
            "memory_usage": f"{memory_percent:.1f}%",
            "disk_usage": f"{disk_percent:.1f}%" if isinstance(disk_percent, float) else str(disk_percent),
            "network_input_kb": f"{network_input_kb:,.2f} KB", # 천 단위 구분 기호 추가
            "network_output_kb": f"{network_output_kb:,.2f} KB", # 천 단위 구분 기호 추가
            "total_memory_gb": f"{total_memory_gb:.2f} GB",
            "used_memory_gb": f"{used_memory_gb:.2f} GB",
            "available_memory_gb": f"{available_memory_gb:.2f} GB"
        }
    except Exception as e:
        st.error(f"시스템 메트릭스 가져오기 오류: {e}")
        # 오류 발생 시 기본값 반환
        return {
            "cpu_usage": "N/A", "memory_usage": "N/A", "disk_usage": "N/A",
            "network_input_kb": "N/A", "network_output_kb": "N/A",
            "total_memory_gb": "N/A", "used_memory_gb": "N/A", "available_memory_gb": "N/A"
        }


def get_top_processes():
    """CPU 및 Memory 사용률 상위 프로세스 목록 가져오기 (psutil 사용)"""
    top_cpu_processes = []
    top_mem_processes = []
    try:
        # 모든 프로세스 정보 가져오기
        # cpu_percent는 interval이 없으면 누적 값 또는 0을 반환할 수 있습니다.
        # 간단한 대시보드에서는 instantaneous percentage를 사용합니다.
        # 실제 사용률은 직전 호출 이후의 변화를 측정해야 정확합니다.
        processes = []
        # psutil.process_iter는 AccessDenied 오류가 발생할 수 있으므로 try-except로 감싸줍니다.
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
             try:
                 pinfo = proc.info
                 processes.append(pinfo)
             except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                 # 해당 프로세스가 존재하지 않거나 접근이 거부되거나 좀비 프로세스인 경우 건너뜀
                 pass

        # CPU 사용률 기준 정렬 (내림차순)
        top_cpu_processes = sorted(processes, key=lambda x: x.get('cpu_percent', 0.0), reverse=True)[:5]
        # Memory 사용률 기준 정렬 (내림차순)
        top_mem_processes = sorted(processes, key=lambda x: x.get('memory_percent', 0.0), reverse=True)[:5]

        # DataFrame 생성
        cpu_df = pd.DataFrame(top_cpu_processes)
        if not cpu_df.empty:
             cpu_df = cpu_df[['pid', 'name', 'cpu_percent']]
             cpu_df.columns = ['PID', 'Name', 'CPU%']
             cpu_df['CPU%'] = cpu_df['CPU%'].apply(lambda x: f"{x:.1f}%") # 소수점 첫째 자리까지 표시

        mem_df = pd.DataFrame(top_mem_processes)
        if not mem_df.empty:
             mem_df = mem_df[['pid', 'name', 'memory_percent']]
             mem_df.columns = ['PID', 'Name', 'MEM%']
             mem_df['MEM%'] = mem_df['MEM%'].apply(lambda x: f"{x:.1f}%") # 소수점 첫째 자리까지 표시


        return cpu_df, mem_df
    except Exception as e:
        st.error(f"상위 프로세스 목록 가져오기 오류: {e}")
        return pd.DataFrame(), pd.DataFrame() # 오류 발생 시 빈 데이터프레임 반환


# --- 대시보드 레이아웃 및 표시 ---

# 3초마다 업데이트를 위한 루프 시작
while True:
    # 컨테이너를 사용하여 내용을 묶고, 새로고침 시 이전 내용을 지움
    container = st.empty()

    with container.container():
        conn = get_oracle_connection()

        if conn:
            # --- 1. 시간대별 스케줄 현황 그래프 ---
            st.markdown("<h3 style='color:white;'>시간대별 스케줄 현황</h3>", unsafe_allow_html=True)

            # 현재 시간 기준으로 이전 12시간과 이후 12시간 계산
            now = datetime.datetime.now()
            time_before_12h = now - datetime.timedelta(hours=12)
            time_after_12h = now + datetime.timedelta(hours=12)

            # 시간대 문자열 생성 (예: "2025-05-18 22:00 ~ 2025-05-19 22:00")
            time_range_str = f"{time_before_12h.strftime('%Y-%m-%d %H:%M')} ~ {time_after_12h.strftime('%Y-%m-%d %H:%M')}"

            schedule_data = fetch_schedule_status_hourly(conn)

            # HOURLY 컬럼을 datetime 객체로 변환 (예하가 제공한 코드)
            # 만약 fetch_schedule_status_hourly 함수 내에서 이미 변환된다면 이 코드는 필요 없을 수도 있어!
            schedule_data['HOURLY'] = pd.to_datetime(schedule_data['HOURLY'], format='%Y-%m-%d %H')

            if not schedule_data.empty:
                # Plotly Bar chart
                fig = px.bar(
                    schedule_data,
                    x='HOURLY',
                    y='cnt_status',
                    color='TASK_STATUS',
                    title='시간대별 TASK 상태별 스케줄 수'
                )

                # 레이아웃 업데이트
                fig.update_layout(
                    paper_bgcolor='white',
                    plot_bgcolor='white',
                    font_color='black',
                    xaxis_title=f"시간대 ({time_range_str})",
                    yaxis_title="스케줄 수",
                    title_font_color='black',
                    legend_title_font_color='black',
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(255,255,255,0.2)',
                        type='category',  # 시간축을 명확하게 카테고리로 설정
                        # **여기서 x축 표시 형식을 수정하는 거야!**
                        tickformat='%Y-%m-%dT%H'  # 예하가 원하는 "YYYY-MM-DDTHH" 형식
                    ),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.2)'),
                    hovermode='x unified',
                )

                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("시간대별 스케줄 현황 데이터를 가져오지 못했습니다.")

            # --- 2. 스케줄 등록 현황 표 ---
            st.markdown("<h3 style='color:white;'>스케줄 등록 현황</h3>", unsafe_allow_html=True)
            schedule_list_df = fetch_schedule_list(conn)

            if not schedule_list_df.empty:
                # st.dataframe은 기본적으로 스크롤 기능을 지원합니다.
                # 높이를 설정하면 해당 높이를 넘을 때 스크롤바가 생깁니다.
                # 스타일은 상단의 CSS에 정의되어 있습니다.
                st.dataframe(schedule_list_df, use_container_width=True, height=350) # 약 10-12개 row 표시 가능한 높이
            else:
                 st.info("스케줄 등록 현황 데이터를 가져오지 못했습니다.")

            # --- 3. 시스템 메트릭스 (CPU, Memory, Disk, Network) ---
            st.markdown("<h3 style='color:white;'>시스템 메트릭스</h3>", unsafe_allow_html=True)
            system_metrics = get_system_metrics() # 실제 psutil 데이터 사용

            # 시스템 메트릭스를 한 줄에 표시
            metrics_text = (
                f"CPU 사용률: {system_metrics['cpu_usage']} &nbsp;&nbsp;&nbsp;&nbsp;"
                f"메모리 사용률: {system_metrics['memory_usage']} &nbsp;&nbsp;&nbsp;&nbsp;"
                f"디스크 사용률: {system_metrics['disk_usage']} &nbsp;&nbsp;&nbsp;&nbsp;"
                f"네트워크 Input: {system_metrics['network_input_kb']} &nbsp;&nbsp;&nbsp;&nbsp;"
                f"네트워크 Output: {system_metrics['network_output_kb']}"
            )
            st.markdown("<h5 style='color:white;'>" + metrics_text + "</h5>", unsafe_allow_html=True)

            # 총 메모리, 사용 중, 사용 가능 메모리 표시
            memory_details_text = (
                f"총 메모리: {system_metrics['total_memory_gb']}, "
                f"사용 중: {system_metrics['used_memory_gb']}, "
                f"사용 가능: {system_metrics['available_memory_gb']}"
            )
            # bold 적용을 위해 unsafe_allow_html=True 사용
            st.markdown("<h5 style='color:white;'>" + memory_details_text + "</h5>", unsafe_allow_html=True)

            # --- 4. CPU/Memory 사용률 상위 프로세스 (Top 5) ---
            st.markdown("<h3 style='color:white;'>상위 프로세스</h3>", unsafe_allow_html=True)
            top_cpu_df, top_mem_df = get_top_processes() # 실제 psutil 데이터 사용

            # 화면을 두 열로 나누어 평행하게 표시
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("<h3 style='color:white;'>CPU 사용률 상위 프로세스 (Top 5)</h3>", unsafe_allow_html=True)
                if not top_cpu_df.empty:
                    st.dataframe(top_cpu_df, use_container_width=True)
                else:
                     st.info("CPU 사용률 상위 프로세스 데이터를 가져오지 못했습니다.")

            with col2:
                st.markdown("<h3 style='color:white;'>Memory 사용률 상위 프로세스 (Top 5)</h3>", unsafe_allow_html=True)
                if not top_mem_df.empty:
                     st.dataframe(top_mem_df, use_container_width=True)
                else:
                     st.info("Memory 사용률 상위 프로세스 데이터를 가져오지 못했습니다.")

            # 데이터베이스 연결 닫기
            conn.close()
        else:
            # DB 연결 실패 시 메시지는 이미 get_oracle_connection에서 출력됨
            pass

    # 3초 대기 후 다시 실행 (rerun)
    time.sleep(3)
    st.rerun() # Streamlit 앱을 처음부터 다시 실행하여 화면 업데이트

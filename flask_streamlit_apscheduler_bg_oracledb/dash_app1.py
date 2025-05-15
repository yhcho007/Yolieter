# 필요한 라이브러리들을 가져와요
'''
실행방법 : streamlit run app_dashboard.py
접속 :
  Local URL: http://localhost:8501
  Network URL: http://<예하의 로컬 네트워크 IP>:8501

'''
import streamlit as st
import psutil # 시스템 정보 가져오는 라이브러리
import oracledb # Oracle DB 연동 라이브러리
import pandas as pd
import time
from datetime import datetime
import plotly.express as px # 그래프 그리는 라이브러리

# Oracle DB 연결 설정 (!!! 예하의 실제 DB 정보로 수정해야 해 !!!)
# TNS_ADMIN 환경 변수로 tnsnames.ora 파일 경로를 설정했다면 dsn에 별칭만 넣어도 돼.
# 아니면 'hostname:port/servicename' 형태의 easy connect 문자열을 사용해줘.
# oracledb.init_oracle_client(lib_dir="/경로/to/oracle/instantclient") # Instant Client 사용 시 필요
db_config = {
    'user': 'your_username',       # 예하의 DB 사용자 이름
    'password': 'your_password',   # 예하의 DB 비밀번호
    'dsn': 'your_dsn'              # 예: 'localhost:1521/ORCL', 'your_tns_alias'
}

# --- 기존 예하 코드에서 가져온 DB 관련 함수 ---

# 데이터베이스에서 작업을 가져오는 함수
def fetch_tasks(connection):
    """DB에서 TASK 테이블의 작업 목록을 가져옵니다 (상태 'S' 제외)."""
    try:
        query = "SELECT taskid, taskname, subprocee_starttime, task_status FROM TESTCHO.TASK WHERE task_status != 'S'"
        df = pd.read_sql(query, connection)
        df.columns = map(str.lower, df.columns) # 컬럼 이름을 소문자로 통일
        return df
    except Exception as e:
        st.error(f"작업 목록 가져오기 중 에러 발생: {e}")
        return pd.DataFrame() # 에러 시 빈 데이터프레임 반환


# --- psutil 라이브러리를 사용한 시스템 정보 함수 ---
def get_cpu_usage():
    """현재 CPU 사용률을 반환 (%)."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        return cpu_percent
    except Exception as e:
        st.error(f"CPU 사용률 확인 중 에러 발생: {e}")
        return None

def get_memory_usage():
    """현재 시스템 메모리 사용 정보를 딕셔너리로 반환."""
    try:
        mem = psutil.virtual_memory()
        return {
            'total': mem.total,
            'available': mem.available,
            'percent': mem.percent,
            'used': mem.used
        }
    except Exception as e:
        st.error(f"메모리 사용률 확인 중 에러 발생: {e}")
        return None

# 바이트 단위를 사람이 읽기 쉬운 형태로 변환
def bytes_to_gb(bytes_value):
    """바이트를 기가바이트로 변환."""
    if bytes_value is None:
        return "N/A"
    gb = bytes_value / (1024 ** 3)
    return f"{gb:.2f} GB"

def bytes_to_mb(bytes_value):
    """바이트를 메가바이트로 변환."""
    if bytes_value is None:
        return "N/A"
    mb = bytes_value / (1024 ** 2)
    return f"{mb:.2f} MB"


def get_top_cpu_processes(limit=5):
    """CPU 사용률이 높은 상위 N개의 프로세스 정보를 리스트로 반환."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            pinfo = proc.info
            if pinfo.get('cpu_percent') is not None:
                 processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception as e:
             # print(f"프로세스 정보 가져오기 중 에러: {e} for PID {pinfo.get('pid', 'N/A')}") # 디버깅용
             pass

    processes = sorted(processes, key=lambda p: p.get('cpu_percent', -1.0), reverse=True)

    return processes[:limit]

# --- Streamlit 웹 대시보드 구성 ---

# 페이지 제목 설정
st.title('작업 및 시스템 모니터링 대시보드')

# --- 사용자 정의 CSS로 배경색 등 스타일 설정 ---
# 배경을 검정색으로 설정하고, 기본 글씨 색상은 흰색으로 유지해서 그래프 라벨 등이 잘 보이게 할게요.
# 시스템 메트릭스 글씨는 아래 코드에서 별도로 노란색으로 설정할 거예요.
st.markdown(
    """
    <style>
    /* 전체 배경을 검정색으로 */
    .stApp {
        background-color: #000000;
        color: #FFFFFF; /* 기본 글씨 색상을 흰색으로 */
    }

    /* Plotly 그래프 내부 배경을 투명하게 또는 검정색으로 설정 */
    /* Plotly 설정에서 paper_bgcolor를 검정색으로 설정하는 것이 더 효과적 */

    /* 테이블 헤더 색상 (선택 사항: 노란색으로 유지할 경우) */
    .dataframe thead th {
        color: #FFFF00 !important; /* 노란색 */
    }
     /* 테이블 셀 텍스트 색상 (기본 흰색 유지) */
     .dataframe tbody td {
        color: #FFFFFF !important; /* 흰색 */
    }
      /* 테이블 인덱스 색상 (기본 흰색 유지) */
    .dataframe tbody th {
        color: #FFFFFF !important; /* 흰색 */
    }

    /* st.metric 라벨 색상 변경 (Streamlit 내부 구조에 따라 어려울 수 있음) */
    /* .stMetricLabel { color: #FFFF00 !important; } */
    /* .stMetricValue { color: #FFFF00 !important; } */
    /* Streamlit 버전이나 구조에 따라 CSS 클래스명이 달라지거나 적용이 안 될 수 있어요 */
    /* 여기서는 st.metric은 기본 스타일로 두고, 다른 텍스트는 노란색으로 설정할게요 */


    </style>
    """,
    unsafe_allow_html=True # HTML 스타일 적용 허용
)


# --- 대시보드 레이아웃 구성 ---

# 자동 새로고침 주기 설정 (초)
refresh_interval = 3 # 3초마다 새로고침 (더 빠르게)

# 정보를 표시할 컨테이너 생성 (여기에 정보를 계속 덮어쓸 거예요)
info_placeholder = st.empty()

# --- 메인 루프: 주기적으로 정보를 가져와서 표시 ---
print("대시보드 정보 갱신 시작...") # 서버 로그에만 출력

while True:
    # placeholder 안의 내용을 지우고 새로 채워넣어요.
    with info_placeholder.container():
        # 시스템 메트릭스 부분을 노란색 텍스트로 표시
        st.markdown("<h2 style='color:#FFFF00;'>시스템 메트릭스</h2>", unsafe_allow_html=True)

        # --- 시스템 메트릭스 표시 ---
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # st.write 는 기본 흰색으로 나올 거예요. 노란색으로 하려면 markdown 사용
        st.markdown(f"<p style='color:#FFFF00;'>마지막 업데이트: {current_time}</p>", unsafe_allow_html=True)


        # st.metric 은 내부 스타일이 복잡해서 CSS로 색상 변경이 어려울 수 있어요.
        # 여기서는 기본 스타일로 두고, 중요한 정보는 노란색 텍스트로 다시 표시하거나 합니다.
        # 예시로 metric은 기본 색상으로 두고, 추가 텍스트만 노란색으로 할게요.
        cpu_percent = get_cpu_usage()
        if cpu_percent is not None:
            st.metric(label="CPU 사용률", value=f"{cpu_percent}%")
            # 노란색 텍스트로 추가 정보 표시
            # st.markdown(f"<p style='color:#FFFF00;'>CPU: {cpu_percent}%</p>", unsafe_allow_html=True)


        mem_info = get_memory_usage()
        if mem_info:
            st.metric(label="메모리 사용률", value=f"{mem_info['percent']}%", help=f"사용 중: {bytes_to_gb(mem_info['used'])}, 전체: {bytes_to_gb(mem_info['total'])}")
            # 노란색 텍스트로 추가 정보 표시
            st.markdown(f"<p style='color:#FFFF00;'>총 메모리: {bytes_to_gb(mem_info['total'])}, 사용 중: {bytes_to_gb(mem_info['used'])}, 사용 가능: {bytes_to_gb(mem_info['available'])}</p>", unsafe_allow_html=True)


        # 상위 프로세스 헤더도 노란색으로
        st.markdown("<h3 style='color:#FFFF00;'>CPU 사용률 상위 프로세스 (Top 5)</h3>", unsafe_allow_html=True)
        top_processes = get_top_cpu_processes(limit=5)
        if top_processes:
            df_top_proc = pd.DataFrame(top_processes)
            if not df_top_proc.empty:
                 df_top_proc['cpu_percent'] = df_top_proc['cpu_percent'].apply(lambda x: f"{x:.1f}%" if x is not None else "N/A")
                 df_top_proc['memory_info'] = df_top_proc['memory_info'].apply(lambda x: bytes_to_mb(x.rss) if x and x.rss is not None else "N/A")
                 df_top_proc = df_top_proc.rename(columns={
                     'pid': 'PID',
                     'name': '이름',
                     'cpu_percent': 'CPU %',
                     'memory_info': '메모리 (MB)'
                 })
                 display_cols = ['PID', '이름', 'CPU %', '메모리 (MB)']
                 # st.dataframe 테이블 자체의 텍스트 색상은 위에 CSS로 흰색으로 설정되어 있어요.
                 # 테이블 내용까지 노란색으로 바꾸려면 CSS를 더 복잡하게 수정해야 할 수 있어요.
                 st.dataframe(df_top_proc[display_cols], use_container_width=True)
            else:
                 st.info("실행 중인 프로세스 정보를 가져올 수 없습니다.")
        else:
            st.info("상위 CPU 프로세스 정보를 가져오는 데 실패했습니다.")


        st.header("작업 현황") # 작업 현황 헤더는 기본 흰색 유지

        # --- 작업 현황 표시 (DB에서 가져옴) ---
        try:
            with oracledb.connect(**db_config) as connection:
                tasks_df = fetch_tasks(connection)

            if not tasks_df.empty:
                st.write("데이터베이스에서 가져온 작업 목록:") # 이 텍스트는 기본 흰색

                # 작업 목록 테이블로 표시 (텍스트 색상은 CSS에 따라 흰색)
                st.dataframe(tasks_df, use_container_width=True)

                # --- 작업 상태별 막대 그래프 ---
                st.subheader("작업 상태별 개수") # 서브헤더는 기본 흰색 유지
                status_counts = tasks_df['task_status'].value_counts().reset_index()
                status_counts.columns = ['상태', '개수'] # 컬럼 이름 변경

                # Plotly로 막대 그래프 생성
                fig = px.bar(status_counts,
                             x='상태',
                             y='개수',
                             title='작업 상태별 개수', # 그래프 제목
                             text='개수') # 막대 위에 개수 표시

                # 그래프 레이아웃 및 스타일 설정
                fig.update_layout(
                    paper_bgcolor='#000000', # 그래프 전체 배경을 검정색으로
                    plot_bgcolor='rgba(0,0,0,0)', # 그래프 플롯 영역 배경 투명하게 (선택 사항)
                    font_color="#FFFFFF", # 기본 글씨 색상 흰색 (그래프 라벨, 제목 등에 적용)
                    title_font_color="#FFFFFF", # 그래프 제목 색상 흰색
                    xaxis=dict(
                        title='상태', # X축 라벨 (그래프 라벨)
                        color='#FFFFFF', # X축 라벨 색상 흰색
                        linecolor='#FFFF00', # X축 선 색상 노란색
                        tickfont=dict(color='#FFFF00') # X축 눈금(숫자) 글씨 색상 노란색
                    ),
                    yaxis=dict(
                        title='개수', # Y축 라벨 (그래프 라벨)
                        color='#FFFFFF', # Y축 라벨 색상 흰색
                        linecolor='#FFFF00', # Y축 선 색상 노란색
                        tickfont=dict(color='#FFFF00') # Y축 눈금(숫자) 글씨 색상 노란색
                    ),
                     # 막대 위에 표시되는 텍스트 색상 (개수)
                     # 이 텍스트 색상은 font_color나 text_font_color 설정에 따름
                     # fig.update_traces 에서 text_font_color를 설정할 수도 있음
                )
                 # 막대 색상 설정 (녹색) 및 막대 위 텍스트 위치
                fig.update_traces(marker_color='#00FF00', textposition='outside') # 막대 색 녹색, 텍스트 위치 바깥쪽

                # Streamlit에 그래프 표시
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("데이터베이스에서 가져올 작업이 없습니다.")

        except oracledb.Error as e:
             st.error(f"데이터베이스 연결 또는 쿼리 중 에러 발생: {e}")
        except Exception as e:
            st.error(f"작업 현황 처리 중 예상치 못한 에러 발생: {e}")


        # --- 잠시 대기 후 다시 루프 실행 ---
        time.sleep(refresh_interval)

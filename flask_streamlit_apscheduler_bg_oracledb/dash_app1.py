import streamlit as st
import psutil
import oracledb
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
from sqlalchemy import create_engine
from common.dbhandler import DBHandler
from common.loghandler import LogHandler

log_handler = LogHandler()
logger = log_handler.getloghandler("main")

db_handler = DBHandler()
db_config = db_handler.get_db_config()

db_url = f"oracle+oracledb://{db_config['user']}:{db_config['password']}@{db_config['dsn']}"
engine = create_engine(db_url)

def fetch_tasks_sqlalchemy():
    try:
        query = "SELECT taskid, taskname, subprocee_starttime, task_status FROM TESTCHO.TASK WHERE task_status != 'S'"
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
            df.columns = map(str.lower, df.columns)
            return df
    except Exception as e:
        st.error(f"작업 목록 가져오기 중 에러 발생: {e}")
        return pd.DataFrame()

def get_cpu_usage():
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        return cpu_percent
    except Exception as e:
        st.error(f"CPU 사용률 확인 중 에러 발생: {e}")
        return None

def get_memory_usage():
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

def bytes_to_gb(bytes_value):
    if bytes_value is None:
        return "N/A"
    gb = bytes_value / (1024 ** 3)
    return f"{gb:.2f} GB"

def bytes_to_mb(bytes_value):
    if bytes_value is None:
        return "N/A"
    mb = bytes_value / (1024 ** 2)
    return f"{mb:.2f} MB"

def get_top_cpu_processes(limit=5):
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            pinfo = proc.info
            if pinfo.get('cpu_percent') is not None:
                 processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception as e:
             pass

    processes = sorted(processes, key=lambda p: p.get('cpu_percent', -1.0), reverse=True)
    return processes[:limit]

st.title('작업 및 시스템 모니터링 대시보드')

st.markdown(
    """
    <style>
    .stApp {
        background-color: #000000;
        color: #FFFFFF;
    }
    .dataframe thead th {
        color: #FFFF00 !important;
    }
     .dataframe tbody td {
        color: #FFFFFF !important;
    }
     .dataframe tbody th {
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

refresh_interval = 3

info_placeholder = st.empty()

while True:
    with info_placeholder.container():
        st.header("스케줄 현황")

        try:
            tasks_df = fetch_tasks_sqlalchemy()

            if not tasks_df.empty:
                if 'subprocee_starttime' in tasks_df.columns and pd.api.types.is_datetime64_any_dtype(tasks_df['subprocee_starttime']):
                    tasks_df['start_hour'] = tasks_df['subprocee_starttime'].dt.hour
                    hourly_counts = tasks_df['start_hour'].value_counts().sort_index().reset_index()
                    hourly_counts.columns = ['시간', '개수']

                    fig_hourly = px.bar(hourly_counts,
                                        x='시간',
                                        y='개수',
                                        title='', # 제목 없음
                                        text='개수')

                    fig_hourly.update_layout(
                        paper_bgcolor='#000000',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font_color="#FFFFFF",
                        xaxis=dict(
                            title='시간',
                            color='#FFFFFF',
                            linecolor='#FFFF00',
                            tickfont=dict(color='#FFFF00')
                        ),
                        yaxis=dict(
                            title='개수',
                            color='#FFFFFF',
                            linecolor='#FFFF00',
                            tickfont=dict(color='#FFFF00')
                        ),
                         title_font_color='#FFFFFF'
                    )
                    fig_hourly.update_traces(marker_color='#00FF00', textposition='outside')

                    st.plotly_chart(fig_hourly, use_container_width=True)
                else:
                     st.warning("시간대별 스케줄 카운트를 위한 'subprocee_starttime' 컬럼이 유효하지 않거나 datetime 형식이 아닙니다.")


                st.write("데이터베이스에서 가져온 작업 목록:")
                st.dataframe(tasks_df, use_container_width=True)

            else:
                st.info("데이터베이스에서 가져올 작업이 없습니다.")

        except Exception as e:
            st.error(f"작업 현황 처리 중 예상치 못한 에러 발생: {e}")

        st.markdown("<h2 style='color:#FFFF00;'>시스템 메트릭스</h2>", unsafe_allow_html=True)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"<p style='color:#FFFF00;'>마지막 업데이트: {current_time}</p>", unsafe_allow_html=True)

        # 2x2 테이블 형태로 CPU 사용률과 메모리 사용률 표시
        cpu_percent = get_cpu_usage()
        mem_info = get_memory_usage()

        # 데이터를 담을 DataFrame 생성
        # 첫 번째 행: 라벨, 두 번째 행: 값 (이게 2x2 형태를 가장 잘 표현)
        metric_data = {
            'Metric': ['CPU 사용률', '메모리 사용률'],
            'Value': [
                f"{cpu_percent}%" if cpu_percent is not None else "N/A",
                f"{mem_info['percent']}%" if mem_info else "N/A"
            ]
        }
        df_metrics = pd.DataFrame(metric_data)

        # 2x2 테이블처럼 보이도록 DataFrame 표시
        # 기본 CSS에 따라 헤더는 노란색, 값은 흰색으로 나올 거예요.
        st.dataframe(df_metrics, hide_index=True, use_container_width=True)

        if mem_info:
             st.markdown(f"<p style='color:#FFFF00; font-size: 14px;'>총 메모리: {bytes_to_gb(mem_info['total'])}, 사용 중: {bytes_to_gb(mem_info['used'])}, 사용 가능: {bytes_to_gb(mem_info['available'])}</p>", unsafe_allow_html=True)


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
                 st.dataframe(df_top_proc[display_cols], use_container_width=True)
            else:
                 st.info("실행 중인 프로세스 정보를 가져올 수 없습니다.")
        else:
            st.info("상위 CPU 프로세스 정보를 가져오는 데 실패했습니다.")

        time.sleep(refresh_interval)

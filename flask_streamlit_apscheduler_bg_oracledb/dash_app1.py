import streamlit as st
import oracledb
import pandas as pd
import psutil
import time
from datetime import datetime, timedelta
import altair as alt
from streamlit_autorefresh import st_autorefresh
import numpy as np
from common.dbhandler import DBHandler
from common.loghandler import LogHandler

# ✨ 페이지 설정: 화면 전체 폭 사용 및 브라우저 탭 제목 설정
st.set_page_config(layout="wide", page_title="스케줄데쉬보드")

# ✨ 자동 새로고침 설정 (3초 간격) - 이게 대시보드를 계속 최신 상태로 유지해 줄 거야!
st_autorefresh(interval=3000, key="dashboard_refresh")

# ✨ 커스텀 CSS로 스타일 적용 (검은 배경, 글자색, 그래프/표 색상 대비 등)
st.markdown(
    """
    <style>
    /* 전체 배경색 */
    body {
        background-color: #121212; /* 아주 어두운 회색 (거의 검은색) */
        color: #e0e0e0; /* 밝은 회색 글자색 */
    }
    /* 스트림릿 메인 영역 배경색 */
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
    }
     /* 제목 및 텍스트 색상 */
    h1, h2, h3, h4, h5, h6, label, .st-bc, .st-bo, .st-bt, .st-bw, .st-bx, .st-by, .st-bz, .st-cr, .st-cs, .st-ct, .st-cu, .st-cv, .st-cw {
        color: #ffffff !important; /* 흰색 */
    }
    /* 표 헤더 색상 */
    .dataframe thead th {
        background-color: #3700b3 !important; /* 보라색 계열 */
        color: #ffffff !important;
        font-weight: bold !important;
    }
    /* 표 본문 색상 */
    .dataframe tbody tr {
        background-color: #1f1f1f !important; /* 약간 밝은 어두운 회색 */
        color: #bbbbbb !important; /* 약간 어두운 밝은 회색 */
    }
     /* 표 본문 짝수 행 배경색 */
    .dataframe tbody tr:nth-child(even) {
        background-color: #333333 !important; /* 좀 더 밝은 어두운 회색 */
    }
    /* 표 본문 홀수 행 배경색 */
    .dataframe tbody tr:nth-child(odd) {
        background-color: #1f1f1f !important;
    }
    /* 표 테두리 색상 */
    .dataframe, .dataframe th, .dataframe td {
        border-color: #6200ee !important; /* 보라색 테두리 */
    }
    /* plotly 그래프 배경 투명하게 */
    .st-emotion-cache-16z0x3n, .st-emotion-cache-18ni7f0, .st-emotion-cache-vj1z9k {
        background-color: rgba(0,0,0,0) !important; /* 배경 투명 */
    }
     /* 알테어 차트 배경 투명하게 */
    .st-emotion-cache-vj1z9k {
         background-color: rgba(0,0,0,0) !important; /* 배경 투명 */
    }
     /* 알테어 툴팁 배경색 및 글자색 (조절 필요시) */
    .vg-tooltip {
        background-color: #333333 !important; /* 어두운 배경 */
        color: #ffffff !important; /* 밝은 글자 */
        border: 1px solid #6200ee !important;
    }
    /* 알테어 차트 라벨 및 축 색상 */
    .mark-text, .mark-rule, .mark-axis text, .mark-axis line, .mark-axis path {
         fill: #e0e0e0 !important; /* 밝은 회색 */
         stroke: #e0e0e0 !important; /* 밝은 회색 */
    }
    .mark-axis text {
        /* 축 라벨 폰트 사이즈 조정 (필요시) */
        /* font-size: 12px; */
    }


    /* 전체적으로 글씨 좀 더 크게 (필요시 조절) */
    .st-emotion-cache-1avcm0c, .st-emotion-cache-1g0bnhg, .st-emotion-cache-1hynsf2, .st-emotion-cache-10q1wdv, .st-emotion-cache-1gh52i {
        font-size: 15px !important;
    }

    /* CPU/Memory 등 메트릭스 표시 스타일 */
    .metric-container {
        display: flex;
        justify-content: space-around; /* 항목 간 간격 균등 분배 */
        align-items: center;
        padding: 10px;
        margin-bottom: 20px;
        background-color: #1f1f1f; /* 어두운 배경 */
        border-radius: 8px;
        flex-wrap: wrap; /* 화면 좁아지면 줄 바꿈 */
        border: 1px solid #03dac6; /* 청록색 테두리 */
    }
    .metric-item {
        margin: 5px 10px; /* 항목 간 여백 */
        text-align: center;
    }
    .metric-label {
        font-size: 14px;
        color: #bbbbbb; /* 밝은 회색 레이블 */
        margin-bottom: 3px;
    }
    .metric-value {
        font-size: 18px;
        font-weight: bold;
        color: #03dac6; /* 청록색 값 */
    }
     /* 메모리 상세 정보 스타일 */
    .memory-details-container {
        display: flex;
        justify-content: center; /* 중앙 정렬 */
        align-items: center;
        padding: 10px;
        margin-bottom: 20px;
        background-color: #1f1f1f; /* 어두운 배경 */
        border-radius: 8px;
        flex-wrap: wrap; /* 화면 좁아지면 줄 바꿈 */
        border: 1px solid #cf6679; /* 붉은색 계열 테두리 */
    }
     .memory-item {
        margin: 5px 10px; /* 항목 간 여백 */
        font-size: 16px;
        color: #e0e0e0; /* 밝은 글자색 */
     }
     .memory-item strong {
        color: #ffcc00; /* 노란색 강조 */
     }

    </style>
    """,
    unsafe_allow_html=True
)

log_handler = LogHandler()
logger = log_handler.getloghandler("main")

db_handler = DBHandler()
conn = db_handler.get_db_connection(logger)

# ✨ 데이터 가져오는 함수 (Query 1, Query 2, Query 3 모두 실행)
# 이 함수는 새로고침될 때마다 실행돼서 최신 데이터를 가져옴.
def fetch_data(conn):
    if not conn:
        return None, None, None, "DB 연결 실패"

    # 시간대 필터링은 쿼리 자체에 포함되어 있어.
    # Query 1: TASK_STATUS 별 건수
    query1 = """
    SELECT HOURLY, TASK_STATUS, COUNT(TASK_STATUS) as cnt_status
    FROM (
        SELECT TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24:MI') AS hourly,
               taskname,
               task_status
        FROM task
        WHERE subprocee_starttime BETWEEN (SYSTIMESTAMP - INTERVAL '12' HOUR) AND (SYSTIMESTAMP + INTERVAL '12' HOUR)
    )
    GROUP BY HOURLY, TASK_STATUS
    ORDER BY HOURLY, TASK_STATUS
    """

    # Query 2: 스케줄 목록
    query2 = """
    SELECT taskid, subprocee_starttime, taskname, task_status
    FROM task
    ORDER BY subprocee_starttime DESC
    """ # 최신 작업부터 보여주도록 정렬

    # Query 3: 시간대별 총 건수
    query3 = """
    SELECT HOURLY, SUM(cnt_status) AS total_cnt
    FROM (
        SELECT TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24:MI') AS hourly,
               taskname, task_status, COUNT(TASK_STATUS) as cnt_status
        FROM task
        WHERE subprocee_starttime BETWEEN (SYSTIMESTAMP - INTERVAL '12' HOUR) AND (SYSTIMESTAMP + INTERVAL '12' HOUR)
        GROUP BY TO_CHAR(subprocee_starttime,'YYYY-MM-DD HH24:MI'), taskname, task_status -- 내부 그룹핑
    )
    GROUP BY HOURLY
    ORDER BY HOURLY -- 시간대별 정렬 추가
    """


    df_schedule_status = None
    df_task_list = None
    df_total_count = None
    error_message = None

    try:
        with conn.cursor() as cursor:
            # Query 1 실행
            cursor.execute(query1)
            rows1 = cursor.fetchall()
            cols1 = [col[0] for col in cursor.description]
            df_schedule_status = pd.DataFrame(rows1, columns=cols1)

            # Query 2 실행
            cursor.execute(query2)
            rows2 = cursor.fetchall()
            cols2 = [col[0] for col in cursor.description]
            df_task_list = pd.DataFrame(rows2, columns=cols2)

            # Query 3 실행
            cursor.execute(query3)
            rows3 = cursor.fetchall()
            cols3 = [col[0] for col in cursor.description]
            df_total_count = pd.DataFrame(rows3, columns=cols3)

    except Exception as e:
        error_message = f"데이터 쿼리 실패: {e}"
        st.error(error_message)


    # 'HOURLY' 컬럼을 datetime 형식으로 변환하여 정렬 가능하게 함
    # (Altair에서 시간 축으로 인식하게 하려면 이 형식이 좋음)
    if df_schedule_status is not None and not df_schedule_status.empty:
        # Oracle에서 가져온 컬럼 이름은 대문자일 수 있습니다.
        if 'HOURLY' in df_schedule_status.columns:
            df_schedule_status['HOURLY_dt'] = pd.to_datetime(df_schedule_status['HOURLY'], format='%Y-%m-%d %H:%M')
            df_schedule_status = df_schedule_status.sort_values('HOURLY_dt').drop(columns='HOURLY_dt')
             # 컬럼 이름 소문자로 변경하여 Altair와 호환성 높이기
            df_schedule_status.columns = [col.lower() for col in df_schedule_status.columns]
        else: # 소문자 컬럼으로 이미 와 있다면
            df_schedule_status['hourly_dt'] = pd.to_datetime(df_schedule_status['hourly'], format='%Y-%m-%d %H:%M')
            df_schedule_status = df_schedule_status.sort_values('hourly_dt').drop(columns='hourly_dt')


    if df_total_count is not None and not df_total_count.empty:
         if 'HOURLY' in df_total_count.columns:
             df_total_count['HOURLY_dt'] = pd.to_datetime(df_total_count['HOURLY'], format='%Y-%m-%d %H:%M')
             df_total_count = df_total_count.sort_values('HOURLY_dt').drop(columns='HOURLY_dt')
             # 컬럼 이름 소문자로 변경
             df_total_count.columns = [col.lower() for col in df_total_count.columns]
         else: # 소문자 컬럼으로 이미 와 있다면
             df_total_count['hourly_dt'] = pd.to_datetime(df_total_count['hourly'], format='%Y-%m-%d %H:%M')
             df_total_count = df_total_count.sort_values('hourly_dt').drop(columns='hourly_dt')


    # 그래프를 위해 Query 1과 Query 3 결과를 합치기
    df_for_chart = pd.DataFrame() # 기본적으로 빈 데이터프레임으로 초기화
    chart_data_available = False

    if df_schedule_status is not None and not df_schedule_status.empty:
         # Query 1 결과 컬럼 이름 조정 (count)
         df_schedule_status_renamed = df_schedule_status.rename(columns={'cnt_status': 'count'})
         df_for_chart = pd.concat([df_for_chart, df_schedule_status_renamed])
         chart_data_available = True


    if df_total_count is not None and not df_total_count.empty:
         # Query 3 결과 컬럼 이름 조정 (count) 및 'TASK_STATUS' 컬럼 추가 ('TOTAL' 값으로)
         df_total_count_renamed = df_total_count.rename(columns={'total_cnt': 'count'})
         df_total_count_renamed['task_status'] = 'TOTAL'
         df_for_chart = pd.concat([df_for_chart, df_total_count_renamed])
         chart_data_available = True


    # 합친 후 시간대 기준으로 다시 정렬 (안정성을 위해)
    if chart_data_available:
         print('chart_data_available')
         df_for_chart['hourly_dt'] = pd.to_datetime(df_for_chart['hourly'], format='%Y-%m-%d %H:%M')
         df_for_chart = df_for_chart.sort_values('hourly_dt').drop(columns='hourly_dt')

         # Altair에서 사용할 숫자 컬럼이 숫자 타입인지 확인 (안전 장치)
         df_for_chart['count'] = pd.to_numeric(df_for_chart['count'], errors='coerce')
         df_for_chart.dropna(subset=['count'], inplace=True) # 숫자로 변환 실패한 행 제거
         if df_for_chart.empty:
             print('df_for_chart.empty')
             chart_data_available = False # 유효한 데이터가 없으면 플래그 변경


    return df_for_chart if chart_data_available else pd.DataFrame(), df_task_list, error_message

# ✨ 시스템 메트릭스 가져오는 함수
def get_system_metrics():
    # interval을 0으로 주면 함수 호출 시점의 값을 즉시 반환 (캐싱하지 않음)
    cpu_percent = psutil.cpu_percent(interval=0.1) # 짧은 간격으로 측정
    memory = psutil.virtual_memory()
    # Windows의 경우 'C:', Linux/macOS의 경우 '/'
    disk_percent = None
    try:
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
    except Exception as e:
         # st.warning(f"디스크 사용률 정보 가져오기 실패: {e}. 루트 파티션('/') 확인 필요.") # 운영 시 메시지 숨김
         pass # 오류 발생 시 None으로 처리

    net_io = psutil.net_io_counters()

    # 바이트를 KB로 변환
    bytes_to_kb = lambda b: b / 1024 if b is not None else 0

    metrics = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk_percent,
        "net_input_kb": bytes_to_kb(net_io.bytes_recv),
        "net_output_kb": bytes_to_kb(net_io.bytes_sent),
        "total_memory_gb": memory.total / (1024**3),
        "used_memory_gb": memory.used / (1024**3),
        "available_memory_gb": memory.available / (1024**3),
    }
    return metrics

# ✨ 상위 프로세스 가져오는 함수
@st.cache_data(ttl=3) # 프로세스 목록은 3초마다 캐시 갱신
def get_top_processes(num=5):
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name', 'cpu_percent', 'memory_percent'])
            # cpu_percent는 interval 동안의 평균이므로, 즉시 값을 보려면 interval=0을 주거나,
            # 측정 시점의 스냅샷을 사용해야 하지만 psutil의 cpu_percent는 기본적으로 blocking.
            # 여기서는 간편하게 마지막 측정값 사용.
            if pinfo.get('cpu_percent') is not None:
                 pinfo['cpu_percent'] = round(pinfo['cpu_percent'], 1) # 소수점 첫째자리까지

            if pinfo.get('memory_percent') is not None:
                 pinfo['memory_percent'] = round(pinfo['memory_percent'], 1) # 소수점 첫째자리까지

            processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # 프로세스가 사라지거나 접근 권한이 없을 때 발생 가능
            pass
        except Exception as e:
             # st.warning(f"프로세스 정보 가져오기 오류: {e}") # 운영 시 메시지 숨김
             pass # 오류 발생 시 무시


    # CPU 사용률 기준 정렬 (None 값 필터링 및 처리)
    top_cpu_processes = sorted(
        [p for p in processes if p.get('cpu_percent') is not None],
        key=lambda x: x['cpu_percent'], reverse=True
    )[:num]
    # Memory 사용률 기준 정렬 (None 값 필터링 및 처리)
    top_memory_processes = sorted(
         [p for p in processes if p.get('memory_percent') is not None],
        key=lambda x: x['memory_percent'], reverse=True
    )[:num]

    # 데이터프레임으로 변환
    df_top_cpu = pd.DataFrame(top_cpu_processes)
    df_top_memory = pd.DataFrame(top_memory_processes)

    # 컬럼 이름 변경
    if not df_top_cpu.empty:
        df_top_cpu.columns = ['PID', '프로세스 이름', 'CPU (%)', '메모리 (%)']
    else: # 데이터가 없을 경우 빈 컬럼으로 데이터프레임 생성 (표 헤더 표시 위함)
        df_top_cpu = pd.DataFrame(columns=['PID', '프로세스 이름', 'CPU (%)', '메모리 (%)'])

    if not df_top_memory.empty:
        df_top_memory.columns = ['PID', '프로세스 이름', 'CPU (%)', '메모리 (%)']
    else: # 데이터가 없을 경우 빈 컬럼으로 데이터프레임 생성
        df_top_memory = pd.DataFrame(columns=['PID', '프로세스 이름', 'CPU (%)', '메모리 (%)'])


    return df_top_cpu, df_top_memory

# ✨ 대시보드 그리기 함수
def draw_dashboard(df_for_chart, df_task_list, system_metrics, df_top_cpu, df_top_memory):
    # 대시보드 제목 제거 요청에 따라 st.title 제거

    st.markdown("## 시간대별 스케줄 현황")

    # df_for_chart가 비어있지 않고 유효한 데이터가 있는지 확인
    if not df_for_chart.empty:
         # Altair 차트 생성
        chart = alt.Chart(df_for_chart).mark_line(point=True).encode(
            x=alt.X('hourly', axis=alt.Axis(title='시간대', format='%m-%d %H:%M')), # 시간대 축
            y=alt.Y('count', title='스케줄 건수'), # 건수 축
            color=alt.Color('task_status', title='상태',
                            # 보색에 가까운 색상 스케일 지정
                            scale=alt.Scale(domain=list(df_for_chart['task_status'].unique()),
                                            range=['#ffcc00', '#03dac6', '#cf6679', '#6200ee', '#bb86fc', '#ffffff'] # TOTAL 라인 색상 추가 (흰색)
                                           )),
            tooltip=['hourly', 'task_status', 'count'] # 마우스 오버 시 정보 표시
        ).properties(
            title='시간대별 상태별 스케줄 건수 및 총합',
        ).interactive() # 확대/축소 가능하게 설정

        st.altair_chart(chart, use_container_width=True) # 화면 폭에 맞춰 표시

    else:
        st.info("지난 12시간 및 향후 12시간 내 스케줄 데이터가 없거나 가져오지 못했습니다.")


    st.markdown("## 스케줄 등록 현황")
    if df_task_list is not None and not df_task_list.empty:
        # 컬럼 이름 보기 좋게 변경 (선택 사항)
        df_task_list.columns = ['Task ID', '시작 시간', 'Task 이름', '상태']
        # 시작 시간 포맷 변경 (datetime 객체인 경우)
        if pd.api.types.is_datetime64_any_dtype(df_task_list['시작 시간']):
             df_task_list['시작 시간'] = df_task_list['시작 시간'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # 표 표시 및 10건 초과 시 스크롤바 자동 생성 (height로 조절)
        st.dataframe(df_task_list, height=400, use_container_width=True) # use_container_width=True로 폭 맞춤
    elif df_task_list is not None and df_task_list.empty:
        st.info("스케줄 목록 데이터가 없습니다.")
    else:
        st.warning("스케줄 목록 데이터를 가져오지 못했습니다.")

    st.markdown("## 시스템 메트릭스")
    if system_metrics:
        # 시스템 메트릭스를 한 줄에 표시
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-item">
                    <div class="metric-label">CPU 사용률</div>
                    <div class="metric-value">{system_metrics.get('cpu_percent', 'N/A'):.1f}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">메모리 사용률</div>
                    <div class="metric-value">{system_metrics.get('memory_percent', 'N/A'):.1f}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">디스크 사용률</div>
                    <div class="metric-value">{system_metrics.get('disk_percent', 'N/A'):.1f}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">네트워크 Input</div>
                    <div class="metric-value">{system_metrics.get('net_input_kb', 'N/A'):.2f} KB</div>
                </div>
                 <div class="metric-item">
                    <div class="metric-label">네트워크 Output</div>
                    <div class="metric-value">{system_metrics.get('net_output_kb', 'N/A'):.2f} KB</div>
                </div>
            </div>
            """, unsafe_allow_html=True
        )

        # 메모리 상세 정보를 한 줄에 표시
        st.markdown(
             f"""
            <div class="memory-details-container">
                 <div class="memory-item">총 메모리: <strong>{system_metrics.get('total_memory_gb', 'N/A'):.2f} GB</strong></div>
                 <div class="memory-item">사용 중: <strong>{system_metrics.get('used_memory_gb', 'N/A'):.2f} GB</strong></div>
                 <div class="memory-item">사용 가능: <strong>{system_metrics.get('available_memory_gb', 'N/A'):.2f} GB</strong></div>
            </div>
             """, unsafe_allow_html=True
        )


    st.markdown("## 상위 프로세스")
    # CPU 사용률 상위 5개, Memory 사용률 상위 5개 프로세스를 평행하게 표시
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### CPU 사용률 상위 프로세스 (Top 5)")
        if not df_top_cpu.empty: # 데이터프레임이 비어있지 않을 때만 표시
            st.dataframe(df_top_cpu, height=250, use_container_width=True) # 적당한 높이 지정, 폭 맞춤
        else:
            st.info("CPU 사용률 상위 프로세스 정보를 가져오지 못했거나 표시할 프로세스가 없습니다.")

    with col2:
        st.markdown("### Memory 사용률 상위 프로세스 (Top 5)")
        if not df_top_memory.empty: # 데이터프레임이 비어있지 않을 때만 표시
            st.dataframe(df_top_memory, height=250, use_container_width=True) # 적당한 높이 지정, 폭 맞춤
        else:
             st.info("메모리 사용률 상위 프로세스 정보를 가져오지 못했거나 표시할 프로세스가 없습니다.")


# ✨ 메인 실행 부분
if __name__ == "__main__":
    # 데이터 가져오기 (세 번째 쿼리 결과도 함께 가져옴)
    df_for_chart, df_task_list, db_error = fetch_data(conn)

    # DB 연결 또는 쿼리 오류 메시지가 있다면 표시
    if db_error:
        # fetch_data 함수 안에서 이미 에러를 표시했지만, 혹시 모를 상황 대비
        # st.error(f"데이터 로드 중 오류 발생: {db_error}")
        pass # 이미 함수 안에서 표시하므로 여기서 다시 표시할 필요 없음

    # 시스템 메트릭스 가져오기
    system_metrics = get_system_metrics()

    # 상위 프로세스 가져오기
    df_top_cpu, df_top_memory = get_top_processes() # 캐싱 데코레이터 적용됨

    # 대시보드 그리기 (데이터가 성공적으로 로드되었을 때만 시각화)
    # fetch_data에서 오류가 나더라도 None이 반환되므로 draw_dashboard 함수 안에서 처리하도록 함.
    draw_dashboard(df_for_chart, df_task_list, system_metrics, df_top_cpu, df_top_memory)

    # @st.cache_resource를 사용했기 때문에 여기서 conn.close()를 명시적으로 호출할 필요는 없어.
    # 스트림릿 세션이 종료될 때 자동으로 처리될 가능성이 높아.

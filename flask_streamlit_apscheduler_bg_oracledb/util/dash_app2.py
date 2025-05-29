import streamlit as st
import pandas as pd
import plotly.express as px
import oracledb
import time

# 데이터베이스 연결 정보
DB_CONFIG = {'user': 'testcho', 'password': '1234', 'dsn': '127.0.0.1:1521/FREE'}

# Streamlit 애플리케이션 설정
st.set_page_config(layout="wide", page_title="작업 모니터링 대시보드")
st.markdown('<style>body{background-color: black; color: white;}</style>', unsafe_allow_html=True)

# UI 구성
col1, col2 = st.columns([6, 4])

# 왼쪽 패널 (가로 6)
with col1:
    top, middle, bottom = st.container(), st.container(), st.container()

    # 검색 조건 영역
    with middle:
        st.subheader("설정 및 검색")
        enabled = st.toggle("ON/OFF")
        start_date = st.date_input("시작일", value=pd.to_datetime("today"))
        end_date = st.date_input("종료일", value=pd.to_datetime("today"))
        status = st.selectbox("종류", ["전체", "대기", "진행중", "완료", "실패", "강제종료"])
        id_input = st.text_input("ID")
        requester = st.text_input("요청자")
        search_btn = st.button("조회")

    # 데이터 조회 함수
    def fetch_data(enabled):
        conn = oracledb.connect(**DB_CONFIG)
        cursor = conn.cursor()
        if enabled:
            query = """SELECT * FROM 작업 WHERE 작업시간 BETWEEN SYSDATE - 1 AND SYSDATE + 1"""
        else:
            query = """SELECT * FROM 작업 WHERE 작업시간 BETWEEN TO_DATE(:start, 'YYYY-MM-DD') 
                       AND TO_DATE(:end, 'YYYY-MM-DD')"""
        cursor.execute(query)
        data = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
        conn.close()
        return data

    # 데이터 표시 (그래프)
    with top:
        if search_btn or enabled:
            data = fetch_data(enabled)
            fig = px.bar(data, x="작업시간", y="카운트", color="상태")
            st.plotly_chart(fig)

    # 데이터 표시 (테이블)
    with bottom:
        if search_btn or enabled:
            st.subheader("쿼리 결과")
            st.dataframe(data)

# 오른쪽 패널 (가로 4)
with col2:
    top_table, mid_table, low_table1, low_table2 = st.container(), st.container(), st.container(), st.container()

    # 종류별 카운트
    with top_table:
        st.subheader("작업 종류별 카운트")
        if search_btn or enabled:
            grouped_data = data.groupby("상태").size().reset_index(name="카운트")
            st.dataframe(grouped_data)

    # 진행중인 TASK
    with mid_table:
        st.subheader("진행중 TASK 상세")
        if search_btn or enabled:
            running_tasks = data[data["상태"] == "진행중"]
            st.dataframe(running_tasks[["PID", "메모리 사용율", "CPU 부하"]])

    # 시스템 정보 (메모리 사용량 TOP 5)
    with low_table1:
        st.subheader("메모리 사용율 TOP 5")
        memory_data = pd.DataFrame({"PID": [101, 202, 303, 404, 505], "메모리 사용율": [78, 65, 59, 45, 30], "cmdline": ["cmd1", "cmd2", "cmd3", "cmd4", "cmd5"]})
        st.dataframe(memory_data)

    # 시스템 정보 (CPU 부하 TOP 5)
    with low_table2:
        st.subheader("CPU 부하 TOP 5")
        cpu_data = pd.DataFrame({"PID": [101, 202, 303, 404, 505], "CPU 부하": [90, 85, 78, 70, 65], "cmdline": ["cmd1", "cmd2", "cmd3", "cmd4", "cmd5"]})
        st.dataframe(cpu_data)

# 실시간 업데이트
while True:
    if enabled:
        data = fetch_data(enabled)
        time.sleep(10)
    time.sleep(3)

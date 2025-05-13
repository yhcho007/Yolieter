'''
기동 : streamlit run streamlit_app.py
stramlet 페이지 확인 : http://localhost:8501

'''
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

def run_streamlit():
    """Streamlit application to display tasks."""
    st.title("Task Monitor")

    # 필터 입력 폼
    st.sidebar.header("Filter Tasks")
    taskname_filter = st.sidebar.text_input("Task Name")
    starttime_filter = st.sidebar.text_input("Start Time (YYYYMMDDHHMISS)")
    endtime_filter = st.sidebar.text_input("End Time (YYYYMMDDHHMISS)")
    limit_filter = st.sidebar.number_input("Limit", min_value=1, value=10)

    # GET 요청으로 데이터 가져오기
    params = {}
    if taskname_filter:
        params['taskname'] = taskname_filter
    if starttime_filter:
        params['starttime'] = starttime_filter
    if endtime_filter:
        params['endtime'] = endtime_filter
    if limit_filter:
        params['limit'] = limit_filter

    response = requests.get("http://localhost:5000/tasks", params=params)
    if response.status_code == 200:
        tasks = response.json()
        if tasks:
            # 데이터프레임으로 변환 후 표시
            df = pd.DataFrame(tasks)
            st.write("### Tasks List")
            st.dataframe(df)

            # 막대 그래프 생성
            df['subprocee_starttime'] = pd.to_datetime(df['subprocee_starttime'])
            df['hour'] = df['subprocee_starttime'].dt.floor('H')  # 시간 단위로 그룹화

            # 상태별 카운트
            status_counts = df['task_status'].value_counts().reset_index()
            status_counts.columns = ['task_status', 'count']

            # 막대 그래프 표시
            st.write("### Task Status Count")
            fig, ax = plt.subplots()
            ax.bar(status_counts['task_status'], status_counts['count'])
            ax.set_xlabel('Task Status')
            ax.set_ylabel('Count')
            ax.set_title('Count of Tasks by Status')
            st.pyplot(fig)

        else:
            st.write("No tasks found.")
    else:
        st.write("Failed to fetch tasks.")

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
# 캘린더 라이브러리 (예: streamlit-calendar)는 별도 설치 필요
# pip install streamlit-calendar
# from streamlit_calendar import calendar # 설치했다면 이 줄의 주석을 풀어줘

# --- Streamlit 페이지 기본 설정 ---
# layout="wide"로 설정하면 화면 전체 폭을 사용하게 돼서 데쉬보드 만들 때 좋아! 😊
st.set_page_config(layout="wide", page_title="스케줄 및 시스템 데쉬보드")


# --- 좌측 메뉴 (사이드바) ---
# st.sidebar를 사용하면 자동으로 화면 좌측에 메뉴가 생겨!
st.sidebar.title("🏡 메뉴") # 이모지를 넣어주면 좀 더 보기 좋겠지?
st.sidebar.markdown("---") # 구분선

menu_selection = st.sidebar.selectbox(
    "원하는 메뉴를 선택하세요:",
    ["내작업", "내알림", "전체 작업 모니터링", "스케줄 현황", "성과 지표", "서버자원 현황"]
)

st.sidebar.markdown("---")
st.sidebar.write("© 2025 우리 회사") # 회사 이름이나 저작권 정보 같은 거 넣어줘도 좋겠지?


# --- 우측 메인 영역 ---
# 선택된 메뉴에 따라 보여줄 내용을 조건문으로 분기할 거야.

if menu_selection == "내작업":
    st.title("🛠️ 내 작업 현황")

    # --- 상단 영역 (50% 차지 예정) ---
    st.header("검색 조건 및 작업 목록")

    # 검색 조건을 위한 콤보박스들
    # st.columns를 사용하면 요소를 좌우로 나란히 배치할 수 있어.
    col_task_search1, col_task_search2 = st.columns(2)
    with col_task_search1:
        # key는 같은 종류의 위젯이 여러 개 있을 때 구분하기 위해 필요해.
        task_gubun = st.selectbox("구분 선택:", ["개발", "운영", "기획", "전체"], key="my_task_gubun_select")
    with col_task_search2:
        task_status = st.selectbox("상태 선택:", ["진행중", "완료", "대기", "취소", "전체"], key="my_task_status_select")

    st.write(f"👇 아래는 **{task_gubun}** 구분의 **{task_status}** 상태 작업 목록이야.")

    # TODO: 여기에 oracledb에서 내 작업 데이터를 가져오는 실제 코드를 넣어야 해.
    # 예시 데이터프레임 (실제 데이터로 교체 필요)
    task_data = {
        '구분': ['개발', '운영', '개발', '기획', '개발', '운영'],
        '제목': ['데쉬보드 개발 마무리', '주간 서버 점검', '결제 API 연동', '다음 스프린트 계획', '긴급 배포', '장비 재부팅'],
        '상태': ['진행중', '완료', '대기', '진행중', '완료', '대기'],
        '담당자': ['예하', '김철수', '예하', '박영희', '김철수', '김철수'],
        '시작일': ['2025-05-26', '2025-05-29', '2025-06-01', '2025-06-01', '2025-05-28', '2025-05-30'],
        '마감일': ['2025-06-15', '2025-05-29', '2025-06-10', '2025-06-10', '2025-05-28', '2025-05-30']
    }
    df_my_tasks = pd.DataFrame(task_data)

    # 검색 조건에 따라 데이터 필터링 (예시)
    filtered_df_my_tasks = df_my_tasks[df_my_tasks['담당자'] == '예하'].copy() # '내' 작업만 필터링
    if task_gubun != "전체":
        filtered_df_my_tasks = filtered_df_my_tasks[filtered_df_my_tasks['구분'] == task_gubun]
    if task_status != "전체":
        filtered_df_my_tasks = filtered_df_my_tasks[filtered_df_my_tasks['상태'] == task_status]

    # 테이블로 검색 결과 표시
    st.dataframe(filtered_df_my_tasks, use_container_width=True) # 화면 폭에 맞게 자동으로 크기 조절

    st.markdown("---") # 상단/하단 구분선

    # --- 하단 영역 (50% 차지 예정) ---
    st.header("나의 작업 일정")
    # TODO: 여기에 내 작업 일정을 캘린더에 표시하는 코드를 넣어야 해.
    # 'streamlit-calendar' 라이브러리를 사용하면 편리해!
    # 작업 데이터를 캘린더 이벤트 형식 (title, start, end 등)으로 변환하는 과정이 필요해.
    # 예시: 완료되지 않은 작업만 일정으로 표시
    task_calendar_events = [
        {'title': row['제목'], 'start': row['시작일'], 'end': row['마감일'], 'color': 'blue'}
        for index, row in filtered_df_my_tasks.iterrows()
        if row['상태'] in ['진행중', '대기']
    ]
    st.write("🗓️ 여기에 나의 작업 일정을 보여주는 캘린더가 표시될 거야.")
    # 예시 캘린더 코드 (라이브러리 설치 및 사용법 확인 후 주석 해제)
    # calendar(events=task_calendar_events, options={"initialView": "dayGridMonth", "locale": "ko"})


elif menu_selection == "내알림":
    st.title("🔔 내 알림")

    # --- 상단 영역 (50% 차지 예정) ---
    st.header("검색 조건 및 알림 목록")

    # 검색 조건을 위한 콤보박스들
    col_noti_search1, col_noti_search2 = st.columns(2)
    with col_noti_search1:
        noti_gubun = st.selectbox("구분 선택:", ["시스템", "작업", "결제", "기타", "전체"], key="my_noti_gubun_select")
    with col_noti_search2:
        noti_status = st.selectbox("상태 선택:", ["확인 안 함", "확인 완료", "전체"], key="my_noti_status_select")

    st.write(f"👇 아래는 **{noti_gubun}** 구분의 **{noti_status}** 상태 알림 목록이야.")

    # TODO: 여기에 oracledb에서 내 알림 데이터를 가져오는 실제 코드를 넣어야 해.
    # 예시 데이터프레임 (실제 데이터로 교체 필요)
    noti_data = {
        '구분': ['시스템', '작업', '결제', '시스템', '작업', '기타'],
        '제목': ['서버1 CPU 사용량 높음', '데쉬보드 개발 완료', '프로젝트 A 결제 요청', 'DB 연결 오류', '일정 변경 안내', '새로운 공지사항'],
        '내용': ['CPU 사용률이 80%를 초과했습니다.', '담당 작업이 완료되었습니다.', '김철수님에게 결제 요청이 도착했습니다.', '데이터베이스 연결에 문제가 발생했습니다.', '회의 시간이 30분 연기되었습니다.', '전사 공지사항을 확인하세요.'],
        '상태': ['확인 안 함', '확인 완료', '확인 안 함', '확인 안 함', '확인 완료', '확인 안 함'],
        '발생 시간': ['2025-05-29 11:55', '2025-05-29 10:30', '2025-05-29 12:05', '2025-05-29 11:00', '2025-05-28 17:00', '2025-05-29 09:00']
    }
    df_my_notifications = pd.DataFrame(noti_data)

    # '발생 시간' 컬럼을 datetime 객체로 변환
    df_my_notifications['발생 시간'] = pd.to_datetime(df_my_notifications['발생 시간'])

    # 검색 조건에 따라 데이터 필터링 (예시)
    filtered_df_my_notifications = df_my_notifications.copy()
    if noti_gubun != "전체":
        filtered_df_my_notifications = filtered_df_my_notifications[filtered_df_my_notifications['구분'] == noti_gubun]
    if noti_status != "전체":
        filtered_df_my_notifications = filtered_df_my_notifications[filtered_df_my_notifications['상태'] == noti_status]

    # 발생 시간 기준으로 최신순 정렬
    filtered_df_my_notifications = filtered_df_my_notifications.sort_values(by='발생 시간', ascending=False)

    # 테이블로 검색 결과 표시
    st.dataframe(filtered_df_my_notifications, use_container_width=True)

    st.markdown("---") # 상단/하단 구분선

    # --- 하단 영역 (50% 차지 예정) ---
    st.header("알림 발생 건수 (캘린더)")
    # TODO: 여기에 날짜별 알림 건수를 캘린더에 표시하는 코드를 넣어야 해.
    # 알림 데이터를 날짜별로 집계하고, 이를 캘린더 이벤트 형식으로 변환해야 해.
    # 예시: 날짜별 알림 건수 집계 및 캘린더 이벤트 생성
    # '발생 시간'에서 날짜만 추출
    df_my_notifications['발생 날짜'] = df_my_notifications['발생 시간'].dt.date
    noti_counts_by_date = df_my_notifications['발생 날짜'].value_counts().reset_index()
    noti_counts_by_date.columns = ['날짜', '건수']
    noti_calendar_events = [
        {'title': f"알림: {row['건수']} 건", 'start': row['날짜'].strftime('%Y-%m-%d'), 'allDay': True, 'color': 'red'}
        for index, row in noti_counts_by_date.iterrows()
    ]

    st.write("📅 여기에 날짜별 알림 발생 건수를 보여주는 캘린더가 표시될 거야.")
    # 예시 캘린더 코드 (라이브러리 설치 및 사용법 확인 후 주석 해제)
    # calendar(events=noti_calendar_events, options={"initialView": "dayGridMonth", "locale": "ko"})


elif menu_selection == "전체 작업 모니터링":
    st.title("📊 전체 작업 모니터링")

    # TODO: 현재 시간 기준으로 ±24시간 데이터를 가져오는 실제 로직 구현
    now = datetime.datetime.now()
    time_24h_ago = now - datetime.timedelta(hours=24)
    time_24h_later = now + datetime.timedelta(hours=24)

    st.write(f"⏳ **기준 시간:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    st.write(f"⏱️ **조회 기간:** {time_24h_ago.strftime('%Y-%m-%d %H:%M:%S')} ~ {time_24h_later.strftime('%Y-%m-%d %H:%M:%S')}")

    # --- 상단 영역 (50% 차지 예정) ---
    st.header("최근 작업 현황 (±24시간)")
    # TODO: 해당 기간의 실제 전체 작업 현황 데이터를 oracledb에서 가져와 표시
    # 예시 데이터프레임 (실제 데이터로 교체 필요)
    overall_task_data = {
        '작업 ID': [101, 102, 103, 104, 105, 106, 107, 108],
        '작업명': ['보고서 자동 생성', 'DB 일일 백업', '웹로그 분석 스크립트', '회원 데이터 정제', '푸시 알림 발송', '주간 보고서 메일 발송', '서버 재시작', '배치 작업 A'],
        '상태': ['완료', '진행중', '실패', '완료', '대기', '완료', '실패', '진행중'],
        '담당자': ['시스템', '시스템', '예하', '김철수', '시스템', '시스템', '김철수', '예하'],
        '시작 시간': ['2025-05-28 23:00:00', '2025-05-29 11:00:00', '2025-05-29 09:30:00', '2025-05-29 05:00:00', '2025-05-29 13:00:00', '2025-05-29 08:00:00', '2025-05-29 01:00:00', '2025-05-29 12:30:00'],
        '종료 시간': ['2025-05-29 01:00:00', '', '2025-05-29 09:35:00', '2025-05-29 06:30:00', '', '2025-05-29 08:10:00', '2025-05-29 01:05:00', '']
    }
    df_overall_tasks = pd.DataFrame(overall_task_data)
     # 시간 컬럼을 datetime 객체로 변환
    df_overall_tasks['시작 시간'] = pd.to_datetime(df_overall_tasks['시작 시간'])
    df_overall_tasks['종료 시간'] = pd.to_datetime(df_overall_tasks['종료 시간'])

    # 현재 시간 기준 ±24시간 필터링 (예시)
    df_overall_tasks_filtered_time = df_overall_tasks[
        (df_overall_tasks['시작 시간'] >= time_24h_ago) &
        (df_overall_tasks['시작 시간'] <= time_24h_later)
    ]


    st.dataframe(df_overall_tasks_filtered_time, use_container_width=True)

    st.markdown("---") # 상단/하단 구분선

    # --- 하단 영역 (50% 차지 예정) ---
    st.header("작업 현황 그래프")
    # TODO: 상단 테이블 데이터를 기반으로 다양한 그래프 생성 (예: 상태별 작업 건수, 시간대별 작업 수 등)
    # 예시: 상태별 작업 건수 그래프
    status_counts_overall = df_overall_tasks_filtered_time['상태'].value_counts().reset_index()
    status_counts_overall.columns = ['상태', '건수']

    fig_status_overall = px.bar(status_counts_overall, x='상태', y='건수', title='📊 상태별 작업 건수 (±24시간)', color='상태')
    st.plotly_chart(fig_status_overall, use_container_width=True)

    # TODO: 시간대별 작업 시작 수 같은 그래프도 추가하면 유용하겠지?


elif menu_selection == "스케줄 현황":
    st.title("📅 전체 스케줄 현황")

    # TODO: 현재 시간 기준으로 ±15일 데이터를 가져오는 실제 로직 구현
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=15)
    end_date = today + datetime.timedelta(days=15)

    st.write(f"⏱️ **조회 기간:** **{start_date.strftime('%Y-%m-%d')}** ~ **{end_date.strftime('%Y-%m-%d')}**")

    st.header("전체 스케줄 캘린더")
    # TODO: 해당 기간의 실제 전체 스케줄 데이터를 oracledb에서 가져와 캘린더에 표시
    # 'streamlit-calendar' 같은 라이브러리 사용을 추천해!
    # 스케줄 데이터를 캘린더 이벤트 형식으로 변환하는 과정이 필요해.
    st.write("🗓️ 여기에 전체 스케줄을 보여주는 캘린더가 표시될 거야.")
    # 예시: 더미 스케줄 데이터
    all_schedule_events_dummy = [
        {'title': '팀 회의', 'start': (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d'), 'color': 'green'},
        {'title': '프로젝트 A 마감', 'start': (today + datetime.timedelta(days=5)).strftime('%Y-%m-%d'), 'allDay': True, 'color': 'purple'},
        {'title': '워크샵', 'start': (today + datetime.timedelta(days=10)).strftime('%Y-%m-%d'), 'end': (today + datetime.timedelta(days=12)).strftime('%Y-%m-%d'), 'color': 'orange'},
         {'title': 'DB 점검 예정', 'start': (today - datetime.timedelta(days=3)).strftime('%Y-%m-%d'), 'allDay': True, 'color': 'red'},
    ]

    # 예시 캘린더 코드 (라이브러리 설치 및 사용법 확인 후 주석 해제)
    # calendar(events=all_schedule_events_dummy, options={"initialView": "dayGridMonth", "locale": "ko"})


elif menu_selection == "성과 지표":
    st.title("📈 성과 지표")

    # TODO: 성과 지표 계산 및 데이터 로딩 실제 로직 구현
    # 계산 기준 날짜 (최근 1주, 1달)
    now = datetime.datetime.now()
    one_week_ago = now - datetime.timedelta(weeks=1)
    one_month_ago = now - datetime.timedelta(days=30) # 대략 1달

    st.write(f"⏱️ **데이터 기준:** 현재 (**{now.strftime('%Y-%m-%d %H:%M:%S')}**)")

    # --- 상단 영역 (약 33.3%) ---
    st.header("평균 작업 시간")
    # TODO: 실제 평균 작업 시간 데이터 가져오기 (지난 1주, 1달) 및 그래프 표시
    # 예시 데이터 (실제 데이터로 교체 필요)
    avg_time_data = {
        '기간': ['최근 1주', '최근 1달'],
        '평균 소요 시간 (분)': [45, 60] # 예시 데이터 (분 단위)
    }
    df_avg_time = pd.DataFrame(avg_time_data)
    fig_avg_time = px.bar(df_avg_time, x='期間', y='平均 소요 시간 (분)', title='⏳ 작업 1건당 평균 소요 시간', color='期間')
    st.plotly_chart(fig_avg_time, use_container_width=True)

    st.markdown("---")

    # --- 중간 영역 (약 33.3%) ---
    st.header("평균 작업 건수")
    # TODO: 실제 평균 작업 건수 데이터 가져와 표시
    # 어떤 기간의 평균인지 명확히 하면 좋겠지? (예: 일 평균, 주 평균 등)
    # 간단히 숫자로 표시하거나, 추세를 보여주는 그래프로 표시할 수 있어.
    st.write("📈 특정 기간 동안 처리된 작업 건수의 평균을 보여주는 지표야.")
    # 예시로 Metric 표시
    col_metric1, col_metric2 = st.columns(2)
    with col_metric1:
        st.metric(label="일 평균 작업 건수 (최근 1달)", value="12.5 건", delta="쉬는 날 제외 계산 필요", delta_color="off") # delta는 변화량 표시
    with col_metric2:
        st.metric(label="주 평균 작업 건수 (최근 1달)", value="62 건", delta="-5 건 (지난달 대비)", delta_color="inverse")


    st.markdown("---")

    # --- 하단 영역 (약 33.3%) ---
    st.header("부서별 작업 처리 현황")
    # TODO: 실제 부서별 작업 건수 데이터 가져와 그래프 표시
    # 예시 데이터 (실제 데이터로 교체 필요)
    dept_task_counts = {
        '부서': ['개발팀', '운영팀', '기획팀', '영업팀', 'IT 지원팀'],
        '처리 작업 건수 (최근 1달)': [50, 30, 20, 10, 15]
    }
    df_dept_tasks = pd.DataFrame(dept_task_counts)
    fig_dept_tasks = px.bar(df_dept_tasks, x='부서', y='처리 작업 건수 (최근 1달)', title='🏢 부서별 작업 처리 건수 (최근 1달)', color='부서')
    st.plotly_chart(fig_dept_tasks, use_container_width=True)


elif menu_selection == "서버자원 현황":
    st.title("☁️ 서버 자원 현황")

    st.write("💻 현재 서버의 자원 사용 현황을 모니터링하는 화면이야.")

    # TODO: 실제 서버 자원 데이터를 가져오는 실제 로직 구현 (CPU, Memory, Disk)
    # 이 데이터는 실시간 또는 주기적으로 업데이트되어야 할 수 있어.
    # Streamlit 앱 외부에서 데이터를 수집하고, 앱에서는 그 데이터를 읽어오는 방식이 일반적이야.

    # --- 상단 영역 (약 33.3%) ---
    st.header("메모리 사용 현황")
    # TODO: 메모리 사용률 그래프 및 표 표시
    # 예시 데이터 (실제 데이터로 교체 필요)
    mem_data = {
        '항목': ['총 메모리', '사용 중', '여유 공간'],
        '크기 (GB)': [64, 48, 16]
    }
    df_mem = pd.DataFrame(mem_data)

    # 그래프와 표를 옆에 나란히 배치
    col_mem_graph, col_mem_table = st.columns([3, 2]) # 그래프를 좀 더 넓게 (3:2 비율)

    with col_mem_graph:
        fig_mem = px.pie(df_mem, values='크기 (GB)', names='항목', title='🧠 메모리 사용량')
        st.plotly_chart(fig_mem, use_container_width=True)

    with col_mem_table:
         st.subheader("상세")
         st.dataframe(df_mem, use_container_width=True) # 표로 상세 데이터 표시


    st.markdown("---")

    # --- 중간 영역 (약 33.3%) ---
    st.header("CPU 사용 현황")
    # TODO: CPU 사용률 그래프 및 표 표시
    # 예시 데이터 (시간대별 사용률 추이 그래프가 일반적이야. 실제 데이터를 시간과 사용률로 구성해줘.)
    cpu_usage_data = {
        '시간': pd.to_datetime(['2025-05-29 11:00', '2025-05-29 11:10', '2025-05-29 11:20', '2025-05-29 11:30', '2025-05-29 11:40', '2025-05-29 11:50', '2025-05-29 12:00']),
        '사용률 (%)': [35, 40, 38, 45, 42, 48, 55] # 예시 데이터
    }
    df_cpu = pd.DataFrame(cpu_usage_data)

    col_cpu_graph, col_cpu_table = st.columns([3, 2])

    with col_cpu_graph:
        fig_cpu = px.line(df_cpu, x='시간', y='사용률 (%)', title='📈 CPU 사용률 추이')
        # 시간 축 포맷을 보기 좋게 설정할 수 있어.
        fig_cpu.update_layout(xaxis_title="시간", yaxis_title="사용률 (%)")
        st.plotly_chart(fig_cpu, use_container_width=True)

    with col_cpu_table:
        st.subheader("최근 값")
        # 최신 데이터 몇 개만 보여주는 표
        st.dataframe(df_cpu.tail(5).sort_values(by='시간', ascending=False), use_container_width=True)


    st.markdown("---")

    # --- 하단 영역 (약 33.3%) ---
    st.header("디스크 사용 현황")
    # TODO: 디스크 사용률 그래프 및 표 표시
    # 예시 데이터 (실제 데이터로 교체 필요)
    disk_data = {
        '드라이브': ['C:', 'D:', 'E:'],
        '총 용량 (GB)': [500, 1000, 2000],
        '사용 중 (GB)': [350, 700, 500],
        '여유 공간 (GB)': [150, 300, 1500]
    }
    df_disk = pd.DataFrame(disk_data)
    # 사용률 계산
    df_disk['사용률 (%)'] = (df_disk['사용 중 (GB)'] / df_disk['총 용량 (GB)']) * 100

    col_disk_graph, col_disk_table = st.columns([3, 2])

    with col_disk_graph:
        # 디스크별 사용률 막대 그래프
        fig_disk = px.bar(df_disk, x='드라이브', y='사용률 (%)', title='🗄️ 디스크 사용률', range_y=[0, 100], color='드라이브')
        st.plotly_chart(fig_disk, use_container_width=True)

    with col_disk_table:
        st.subheader("상세")
        # 상세 데이터를 보여주는 표
        st.dataframe(df_disk[['드라이브', '총 용량 (GB)', '사용 중 (GB)', '여유 공간 (GB)', '사용률 (%)']], use_container_width=True)


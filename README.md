# 디렉토리
## flask_streamlit_apscheduler_bg_oracledb
이 프로젝트는 원하는 시간에 원하는 기능을 수행하도록 미리 등록하고 모니터링하기 위한 목적으로, Task, Task시작시간을 등록하고(main.py), 등록된 Task를 시작시간에 기동시키며(sch.py), Task를 실행(app.py) 합니다. 또, Task 등록(R),실행(I),완료(S,E),죽임(K) 상태를 모니터링(dash_app.py) 합니다. 
python으로 개발하였고, 사용한 패키지는 Oracle 데이터베이스에 TASK 테이블 CRUD를 위해 oracledb를 사용하고, RESTful API 제공을 위해 Flask, Flask_restx 를 사용하였으며, Streamlit, Poltly, pandas 을 통해 데쉬보드를 제공합니다. 백그라운드로 Task를 기동시키기 위해 schedule, Popen, subprocess 사용하고, Task 단계별 알림을 위해 Mattermost 로 알림을 제공합니다.

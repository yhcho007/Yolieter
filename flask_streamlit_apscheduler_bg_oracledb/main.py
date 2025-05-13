# flask 서버 기동 :  python main.py
# streamlit 서버 기동 :  streamlit run main.py
# swagger 페이지 : http://localhost:5000/swagger
# streamlit 페이지 : http://localhost:8501
# 시간범위 검색 : GET /tasks?starttime=20250510010101&endtime=20250510110101
"
POST 요청 예 :
curl -X POST http://localhost:5000/tasks \
-H "Content-Type: application/json" \
-d '{
    "taskname": "Sample Task",
    "subprocee_starttime": "2025-05-10 01:01:01",
    "task_status": "Pending"
}'

GET 요청 예 :
모든 작업 가져오기
curl -X GET "http://localhost:5000/tasks"

날짜 범위로 필터링
curl -X GET "http://localhost:5000/tasks?starttime=20250510010101&endtime=20250510110101"

"
from flask import Flask, request, jsonify
from flask_restplus import Api, Resource, fields
import oracledb
import pandas as pd
import subprocess
import requests
import streamlit_app  # Streamlit 앱을 임포트
import signal
import os
import sys

app = Flask(__name__)
api = Api(app, version='1.0', title='Task Management API',
          description='A simple API for managing tasks in Oracle DB')

# 데이터베이스 연결 정보
DB_USER = 'your_username'
DB_PASSWORD = 'your_password'
DB_DSN = 'your_dsn'

# API 모델 정의
task_model = api.model('Task', {
    'taskname': fields.String(required=True, description='Task Name'),
    'subprocee_starttime': fields.String(required=True, description='Start Time (YYYY-MM-DD HH24:MI:SS)'),
    'task_status': fields.String(required=True, description='Task Status')
})

def get_db_connection():
    return oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)

@api.route('/tasks')
class TaskResource(Resource):
    @api.expect(task_model)
    @api.response(201, 'Task registered successfully.')
    @api.response(400, 'Invalid input.')
    def post(self):
        """Register a new task"""
        data = request.json
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO SCH taskname, subprocee_starttime, task_status) VALUES (:taskid, :taskname, TO_DATE(:subprocee_starttime, 'YYYY-MM-DD HH24:MI:SS'), :task_status)",
                    taskname=data['taskname'],
                    subprocee_starttime=data['subprocee_starttime'],
                    task_status=data['task_status']
                )
                connection.commit()
        return jsonify({"message": "Task registered successfully."}), 201

    @api.response(200, 'Success')
    @api.response(404, 'No tasks found.')
    def get(self):
        """Get tasks with optional filters"""
        taskid = request.args.get('taskid')
        taskname = request.args.get('taskname')
        starttime = request.args.get('starttime')  # YYYYMMDDHHMISS 형식
        endtime = request.args.get('endtime')      # YYYYMMDDHHMISS 형식
        limit = request.args.get('limit', default='all')

        query = "SELECT taskid, taskname, subprocee_starttime, task_status FROM SCH WHERE 1=1"
        params = {}

        if taskid:
            query += " AND taskid = :taskid"
            params['taskid'] = taskid
        if taskname:
            query += " AND taskname = :taskname"
            params['taskname'] = taskname
        if starttime:
            starttime_formatted = f"{starttime[:4]}-{starttime[4:6]}-{starttime[6:8]} {starttime[8:10]}:{starttime[10:12]}:{starttime[12:14]}"
            query += " AND subprocee_starttime >= TO_DATE(:starttime, 'YYYY-MM-DD HH24:MI:SS')"
            params['starttime'] = starttime_formatted
        if endtime:
            endtime_formatted = f"{endtime[:4]}-{endtime[4:6]}-{endtime[6:8]} {endtime[8:10]}:{endtime[10:12]}:{endtime[12:14]}"
            query += " AND subprocee_starttime < TO_DATE(:endtime, 'YYYY-MM-DD HH24:MI:SS')"
            params['endtime'] = endtime_formatted
        if limit != 'all':
            query += " AND ROWNUM <= :limit"
            params['limit'] = int(limit)

        with get_db_connection() as connection:
            tasks = pd.read_sql(query, connection, params=params)

        if tasks.empty:
            return jsonify({"message": "No tasks found."}), 404

        return jsonify(tasks.to_dict(orient='records'))

def run_sch_background():
    """Run the Python script in the background."""
    try:
        process = subprocess.Popen(
            ["python", "sch.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False
        )
        return process
    except FileNotFoundError:
        print(f"Error: sch.py file not found.")
        return None

def kill_processes(process):
    """모든 프로세스를 종료합니다."""
    if process:
        print(f"Killing background process with PID: {process.pid}")
        process.terminate()  # 백그라운드 프로세스 종료
        process.wait()       # 프로세스가 종료될 때까지 대기

    # 추가 프로세스 종료
    try:
        # app.py 프로세스 종료
        app_processes = subprocess.check_output("ps aux | grep 'app.py' | grep -v grep", shell=True)
        for line in app_processes.decode().splitlines():
            pid = int(line.split()[1])  # PID 추출
            os.kill(pid, signal.SIGTERM)  # 프로세스 종료
            print(f"Killed app.py process with PID: {pid}")

        # streamlit_app.py 프로세스 종료
        streamlit_processes = subprocess.check_output("ps aux | grep 'streamlit_app.py' | grep -v grep", shell=True)
        for line in streamlit_processes.decode().splitlines():
            pid = int(line.split()[1])  # PID 추출
            os.kill(pid, signal.SIGTERM)  # 프로세스 종료
            print(f"Killed streamlit_app.py process with PID: {pid}")

    except Exception as e:
        print(f"Error while killing processes: {e}")

def signal_handler(sig, frame):
    """신호 처리기: 프로세스가 종료될 때 모든 프로세스를 종료합니다."""
    print("Signal received, terminating processes...")
    kill_processes(background_process)
    sys.exit(0)

if __name__ == "__main__":
    # 종료 신호 처리 등록
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill 명령

    background_process = run_sch_background()
    if background_process:
        print(f"Background script sch.py is running. Process ID: {background_process.pid}")
    else:
        print("Failed to start the background script.")

    # Flask 애플리케이션을 별도로 실행
    app.run(debug=True)

    # Streamlit 애플리케이션 실행
    streamlit_app.run_streamlit()

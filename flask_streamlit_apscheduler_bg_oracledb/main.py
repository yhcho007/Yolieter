# flask 서버 기동 :  python main.py
# dash_app 서버 기동 :  dash_app run main.py
# swagger 페이지 : http://localhost:5000/swagger
# dash_app 페이지 : http://localhost:8501
# 시간범위 검색 : GET /tasks?starttime=20250510010101&endtime=20250510110101
'''
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

'''
from flask import Flask, request, jsonify, make_response
from flask_restx import Api, Resource, fields
import pandas as pd
import subprocess
import signal
import sys
import oracledb
from common.dbhandler import DBHandler
from common.loghandler import LogHandler

log_handler = LogHandler()
logger = log_handler.getloghandler("main")

db_handler = DBHandler()
dbconn = db_handler.get_db_connection(logger)

app_name = "TaskScheduleApp"
app_version = "1.0.0"
app = Flask(__name__)
# Api 초기화는 그대로!
api = Api(app, version=app_version, title='Task Management API',
          description='Oracle DB에 작업을 관리하는 간단 API야!') # 설명도 좀 더 친근하게 바꿔봤어!

# API 모델 정의 (이것도 그대로 쓰면 돼!)
task_model = api.model('Task', {
    'taskname': fields.String(required=True, description='작업 이름'),
    'subprocee_starttime': fields.String(required=True, description='시작 시간 (YYYY-MM-DD HH24:MI:SS 형식)'),
    'task_status': fields.String(required=True, description='작업 상태')
})

# 백그라운드 프로세스 객체를 저장할 변수
background_process = None

@app.route('/health', methods=['GET'])
def health_check():
    # 여기에서 애플리케이션의 실제 상태를 확인하는 로직을 추가할 수 있어.
    # 예를 들어 데이터베이스 연결, 외부 서비스 상태 등등...

    # 모든 체크가 성공했다고 가정하고 'UP' 상태를 반환할게.
    # 만약 문제가 있다면 'DOWN'으로 바꾸고 HTTP 상태 코드도 503 등으로 설정할 수 있어.
    app_status = "UP"
    status_code = 200 # OK

    # 좀 더 상세한 정보를 포함하고 싶으면 이렇게 딕셔너리 형태로 반환하면 좋아.
    # (Spring Boot Actuator처럼)
    response_payload = {
        "status": app_status,
        "details": {
            # 여기에 각 컴포넌트의 상태를 추가할 수 있어.
            # 예: "database": {"status": "UP", "message": "Connection successful"}
            # 예: "external_api": {"status": "UP", "responseTime": "50ms"}
            "service": {"status": "UP", "message": "Service is running"}
        }
    }

    # Flask에서 JSON 응답을 보낼 때는 jsonify 함수를 사용하는 게 좋아.
    # Reddit에서도 JSON 형태 반환을 추천하더라고 [[5]](https://www.reddit.com/r/flask/comments/1kolnus/why_does_my_flask_health_endpoint_show_nothing_at/).
    return jsonify(response_payload), status_code


# API 리소스 정의 (이 부분도 그대로!)
@api.route('/tasks')
class TaskResource(Resource):
    @api.expect(task_model)
    @api.response(201, '작업이 성공적으로 등록되었어!')
    @api.response(400, '입력 형식이 잘못되었네.')
    def post(self):
        """새 작업을 등록하는 API"""
        global dbconn
        data = request.json
        if not data:
             return make_response(jsonify({"message": "요청 본문이 비어있거나 JSON 형식이 아니야."}), 400)

        # 필수 필드 확인
        if not all(k in data for k in ('taskname', 'subprocee_starttime', 'task_status')):
             return make_response(jsonify({"message": "필수 정보(taskname, subprocee_starttime, task_status)가 부족해."}), 400)

        try:
            if dbconn is None:
                 return make_response(jsonify({"message": "데이터베이스 연결에 실패했어."}), 500)

            with dbconn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO TESTCHO.TASK (taskname, subprocee_starttime, task_status) VALUES (:taskname, TO_DATE(:subprocee_starttime, 'YYYY-MM-DD HH24:MI:SS'), :task_status)",
                    taskname=data['taskname'],
                    subprocee_starttime=data['subprocee_starttime'],
                    task_status=data['task_status']
                )
                dbconn.commit()
            return make_response(jsonify({"message": "작업이 성공적으로 등록되었어!"}), 201)
        except oracledb.Error as e:
            logger.info(f"데이터베이스 오류: {e}")
            return make_response(jsonify({"message": f"데이터베이스 작업 중 오류가 발생했어: {e}"}), 500)
        except Exception as e:
             logger.info(f"예상치 못한 오류 발생: {e}")
             return make_response(jsonify({"message": f"작업 등록 중 예상치 못한 오류가 발생했어: {e}"}), 500)



    @api.response(200, '성공!')
    @api.response(404, '작업을 찾지 못했어.')
    @api.doc(params={ # Swagger UI에 파라미터 설명을 추가할 수 있어!
        'taskid': {'description': 'Task ID로 필터링 (단일)', 'type': 'string'},
        'taskname': {'description': 'Task 이름으로 필터링', 'type': 'string'},
        'starttime': {'description': '시작 시간 (YYYYMMDDHHMISS)', 'type': 'string'},
        'endtime': {'description': '종료 시간 (YYYYMMDDHHMISS)', 'type': 'string'},
        'limit': {'description': '결과 개수 제한 (기본값: all)', 'type': 'integer'} # limit은 integer로 받는 게 좋아!
    })
    def get(self):
        global dbconn
        """조건에 맞는 작업을 가져오는 API"""
        taskid = request.args.get('taskid')
        taskname = request.args.get('taskname')
        starttime = request.args.get('starttime')  # YYYYMMDDHHMISS 형식
        endtime = request.args.get('endtime')      # YYYYMMDDHHMISS 형식
        limit_str = request.args.get('limit', default='all') # 문자열로 받아서 처리

        query = "SELECT taskid, taskname, subprocee_starttime, task_status FROM TESTCHO.TASK WHERE 1=1"
        params = {}

        if taskid:
            query += " AND taskid = :taskid"
            params['taskid'] = taskid
        if taskname:
            query += " AND taskname = :taskname"
            params['taskname'] = taskname
        if starttime:
            # 입력 형식 확인 (최소한 길이)
            if len(starttime) == 14:
                # YYYY-MM-DD HH24:MI:SS 형식으로 변환
                starttime_formatted = f"{starttime[:4]}-{starttime[4:6]}-{starttime[6:8]} {starttime[8:10]}:{starttime[10:12]}:{starttime[12:14]}"
                query += " AND subprocee_starttime >= TO_DATE(:starttime, 'YYYY-MM-DD HH24:MI:SS')"
                params['starttime'] = starttime_formatted
            else:
                # 시간 형식 오류 처리
                return make_response(jsonify({"message": "starttime 형식이 YYYYMMDDHHMISS 여야 해!"}), 400)

        if endtime:
             # 입력 형식 확인 (최소한 길이)
             if len(endtime) == 14:
                endtime_formatted = f"{endtime[:4]}-{endtime[4:6]}-{endtime[6:8]} {endtime[8:10]}:{endtime[10:12]}:{endtime[12:14]}"
                query += " AND subprocee_starttime < TO_DATE(:endtime, 'YYYY-MM-DD HH24:MI:SS')"
                params['endtime'] = endtime_formatted
             else:
                # 시간 형식 오류 처리
                return make_response(jsonify({"message": "endtime 형식이 YYYYMMDDHHMISS 여야 해!"}), 400)

        if limit_str != 'all':
            try:
                limit = int(limit_str)
                query += " AND ROWNUM <= :limit"
                query += " ORDER BY taskid ASC"
                params['limit'] = limit
            except ValueError:
                 return make_response(jsonify({"message": "limit은 'all' 이거나 숫자로 입력해야 해!"}), 400)

        try:
            if dbconn is None:
                 return make_response(jsonify({"message": "데이터베이스 연결에 실패했어."}), 500)

            # pandas.read_sql은 oracledb 커넥션 객체를 직접 받을 수 있어.
            tasks = pd.read_sql(query, dbconn, params=params)

            if tasks.empty:
                # 200 OK with empty list vs 404 Not Found 중 어떤 것이 좋을지는 API 설계에 따라 달라.
                # 예시 코드에선 404를 반환했으니 그대로 404로 갈게!
                return make_response(jsonify({"message": "조건에 맞는 작업을 찾지 못했어."}), 404)

            tasks['SUBPROCEE_STARTTIME'] = tasks['SUBPROCEE_STARTTIME'].dt.strftime('%Y-%m-%d %H:%M:%S')

            return make_response(jsonify(tasks.to_dict(orient='records')), 200)
        except oracledb.Error as e:
            logger.info(f"데이터베이스 오류: {e}")
            return make_response(jsonify({"message": f"데이터베이스 작업 중 오류가 발생했어: {e}"}), 500)
        except Exception as e:
             logger.info(f"예상치 못한 오류 발생: {e}")
             return make_response(jsonify({"message": f"작업 조회 중 예상치 못한 오류가 발생했어: {e}"}), 500)

# sch.py를 백그라운드로 실행하는 함수
def run_sch_background():
    """sch.py 파이썬 스크립트를 백그라운드로 실행합니다."""
    try:
        logger.info("sch.py 백그라운드 실행 시도...")
        # stdout, stderr을 파이프로 연결해서 나중에 읽거나, 파일로 리다이렉트할 수 있어.
        # 여기선 간단히 DEVNULL로 버리도록 했어.
        process = subprocess.Popen(
            ["python", "sch.py"], # sys.executable을 사용하면 현재 파이썬 환경으로 실행돼서 좋아!
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False # shell=False가 더 안전한 방법이야
        )
        logger.info(f"sch.py 백그라운드 프로세스 실행됨 (PID: {process.pid})")
        return process
    except FileNotFoundError:
        logger.info(f"오류: sch.py 파일을 찾을 수 없어.")
        return None
    except Exception as e:
        logger.info(f"sch.py 백그라운드 실행 중 오류 발생: {e}")
        return None

# 프로세스들을 종료하는 함수 (시그널 핸들러 등에서 호출될 수 있어)
def kill_processes(process):
    """백그라운드 프로세스 및 관련 프로세스를 종료합니다."""
    logger.info("종료 시그널 수신. 프로세스 정리 시작...")
    if process and process.poll() is None: # 프로세스가 아직 실행 중인지 확인
        logger.info(f"백그라운드 sch.py 프로세스 (PID: {process.pid}) 종료 시도...")
        try:
            process.terminate() # 부드러운 종료 시도
            process.wait(timeout=10) # 최대 10초 대기
            logger.info("sch.py 프로세스 종료 완료.")
        except subprocess.TimeoutExpired:
            logger.info("sch.py 프로세스 종료 시간 초과. 강제 종료 시도...")
            process.kill() # 강제 종료
            process.wait()
            logger.info("sch.py 프로세스 강제 종료 완료.")
        except Exception as e:
            logger.info(f"sch.py 프로세스 종료 중 오류 발생: {e}")
    elif process and process.poll() is not None:
         logger.info(f"sch.py 프로세스 (PID: {process.pid})는 이미 종료되었어.")
    else:
         logger.info("실행 중인 sch.py 백그라운드 프로세스가 없었어.")

    logger.info("프로세스 정리 완료.")


# SIGINT (Ctrl+C) 및 SIGTERM 시그널 핸들러 정의
def signal_handler(sig, frame):
    logger.info(f"시그널 {sig} 수신, 종료 시작.")
    global background_process
    kill_processes(background_process)
    logger.info("애플리케이션 종료.")
    sys.exit(0)

# 시그널 핸들러 등록
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == '__main__':
    # Flask 앱 시작 전에 sch.py 백그라운드 실행
    background_process = run_sch_background()

    logger.info("Flask 서버 시작 중...")
    # Flask 앱 실행
    app.run(debug=False, host='0.0.0.0', port=5000)



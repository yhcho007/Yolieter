'''
pip install croniter
'''
from flask import Flask, request, jsonify
import requests
import oracledb
import os
import datetime
from functools import wraps
from croniter import croniter # croniter 라이브러리 임포트!

# === 설정 정보 (예하 환경에 맞게 수정해주세요) ===
# Oracle DB 연결 정보 (환경 변수 사용 권장)
DB_USER = os.environ.get('ORACLE_DB_USER', 'YOUR_DB_USER') # 실제 DB 사용자 이름으로 변경
DB_PASSWORD = os.environ.get('ORACLE_DB_PASSWORD', 'YOUR_DB_PASSWORD') # 실제 DB 비밀번호로 변경
DB_CONNECT_STRING = os.environ.get('ORACLE_DB_CONNECT_STRING', 'YOUR_HOST:YOUR_PORT/YOUR_SERVICE_NAME') # 실제 DB 접속 정보로 변경 (예: 'localhost:1521/xe')

# 사용자 인증 서버 URL
AUTH_SERVER_URL = 'https://127.0.0.1:9119' # 실제 인증 서버 URL로 변경

# 태스크 정보를 저장할 Oracle DB 테이블 이름
TASKS_TABLE = 'SCHEDULE_TASKS' # 실제 테이블 이름으로 변경

# === DB 연결 함수 ===
def get_db_connection():
    """Oracle DB 연결을 생성합니다."""
    try:
        # oracledb 1.4 이상 버전에서는 기본적으로 connection pooling을 사용하지 않습니다.
        # 필요하다면 connection pool 설정을 고려하세요.
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_CONNECT_STRING)
        return connection
    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        return None

# === 사용자 인증 데코레이터 ===
def validate_user(f):
    """
    요청 헤더의 'x-user-id' 값을 사용하여 사용자 권한을 확인하는 데코레이터입니다.
    인증 서버에 GET 요청을 보내 200 응답을 받으면 통과, 아니면 401 에러를 반환합니다.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get('x-user-id')
        if not user_id:
            # x-user-id 헤더가 없을 경우
            return jsonify({"status": "error", "message": "Header 'x-user-id'가 누락되었습니다."}), 401

        # 인증 서버에 사용자 ID를 파라미터로 보내 권한 확인 (인증 서버 API 명세에 맞게 수정 필요)
        # 예시에서는 쿼리 파라미터로 user_id를 보낸다고 가정합니다.
        validation_url = f"{AUTH_SERVER_URL}?x-user-id={user_id}"
        try:
            # 주의: verify=False는 개발/테스트 용도로만 사용하세요. 실제 운영 환경에서는 보안 문제가 발생할 수 있습니다.
            # 인증 서버에 유효한 SSL 인증서가 있거나, 내부 통신 시 다른 인증/보안 방법을 사용해야 합니다.
            response = requests.get(validation_url, verify=False) # 예시를 위해 verify=False 추가, 실제 사용 시 주의!

            if response.status_code != 200:
                # 인증 서버 응답 코드가 200이 아니면 권한 없음
                return jsonify({"status": "error", "message": "api 사용 권한이 없습니다."}), 401

        except requests.exceptions.RequestException as e:
            # 인증 서버 연결 실패 시
            print(f"사용자 인증 서버 요청 실패: {e}")
            # 인증 서버 연결 실패도 보안상 권한 없음으로 처리하는 것이 일반적일 수 있습니다.
            return jsonify({"status": "error", "message": "사용자 인증 중 오류가 발생했습니다."}), 401 # 또는 500

        # 인증 성공 시 원래 요청 처리 함수 실행
        return f(*args, **kwargs)
    return decorated_function

# === Flask 애플리케이션 초기화 ===
app = Flask(__name__)

# === API 엔드포인트 정의 ===

@app.route('/health', methods=['GET'])
def health_check():
    """간단한 헬스 체크 API"""
    # DB 연결 상태 등 추가적인 상태 체크 로직을 여기에 넣을 수 있습니다.
    # 예시에서는 DB 연결 상태도 함께 체크합니다.
    db_status = "UP"
    db_error = None
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
        else:
            db_status = "DOWN"
            db_error = "데이터베이스에 연결할 수 없습니다."
    except Exception as e:
        db_status = "DOWN"
        db_error = str(e)

    if db_status == "UP":
        return jsonify({"status": "UP", "db_status": db_status}), 200
    else:
        return jsonify({"status": "DEGRADED", "db_status": db_status, "db_error": db_error}), 503 # 서비스 이용 불가

@app.route('/tasks', methods=['POST'])
@validate_user # 사용자 인증 데코레이터 적용
def create_task():
    """
    새로운 태스크를 설정하고 DB에 저장하는 API (인증 필요)
    요청 JSON 예시:
    {
        "taskname": "매일보고서생성",
        "startconfition": "0 9 * * *", # Crontab 형식
        "taskcontents": "python /app/scripts/generate_report.py",
        "requestor": "예하",
        "modifier": "예하",
        "result": "Pending",
        "useyn": "Y"
    }
    """
    task_data = request.get_json()
    if not task_data:
        return jsonify({
            "status": "error",
            "message": "요청 본문에 작업 정보를 JSON 형태로 포함해야 합니다."
        }), 400

    # 필수 필드 확인 (taskcontents, result, useyn 등은 기본값 설정 가능)
    required_fields = ['taskname', 'startconfition', 'requestor']
    for field in required_fields:
        # startconfition은 비어있어도 될 수 있지만, 여기서는 필수라고 가정합니다.
        if field not in task_data or task_data[field] is None: # 빈 문자열도 허용하려면 or not task_data[field] 제거
             return jsonify({"status": "error", "message": f"필수 필드 '{field}'가 누락되었습니다."}), 400

    # startconfition이 Crontab 형식인지 기본적인 유효성 검사 (옵션)
    # try:
    #     croniter(task_data['startconfition'])
    # except Exception:
    #      return jsonify({"status": "error", "message": "'startconfition' 필드가 유효한 Crontab 형식이 아닙니다."}), 400


    # DB 저장을 위한 데이터 준비
    now = datetime.datetime.now()
    insert_data = {
        'taskname': task_data.get('taskname'),
        'startconfition': task_data.get('startconfition'),
        'taskcontents': task_data.get('taskcontents', ''), # 기본값 빈 문자열
        'requestor': task_data.get('requestor'),
        'modifier': task_data.get('modifier', task_data.get('requestor')), # modifier가 없으면 requestor 사용
        'result': task_data.get('result', 'Pending'), # 기본값 'Pending'
        'createdate': task_data.get('createdate', now), # 요청에 없으면 현재 시간 사용 (Oracle TIMESTAMP 또는 DATE 컬럼에 맞게 형변환 필요)
        'modifieddate': task_data.get('modifieddate', now), # 요청에 없으면 현재 시간 사용 (Oracle TIMESTAMP 또는 DATE 컬럼에 맞게 형변환 필요)
        'useyn': task_data.get('useyn', 'Y').upper() # 기본값 'Y', 대문자로 저장
    }

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "데이터베이스에 연결할 수 없습니다."}), 500

    cursor = conn.cursor()
    try:
        # Oracle DB의 createdate/modifieddate 컬럼 타입에 따라 바인딩 방식 조정 필요
        # 예: TIMESTAMP 타입을 사용하는 경우 Python datetime 객체 그대로 바인딩 가능
        # 예: DATE 타입을 사용하는 경우 date() 객체나 문자열로 변환 필요
        sql = f"""
        INSERT INTO {TASKS_TABLE} (taskname, startconfition, taskcontents, requestor, modifier, result, createdate, modifieddate, useyn)
        VALUES (:taskname, :startconfition, :taskcontents, :requestor, :modifier, :result, :createdate, :modifieddate, :useyn)
        """
        cursor.execute(sql, insert_data)
        conn.commit()
        return jsonify({"status": "success", "message": "작업이 성공적으로 저장되었습니다.", "taskname": insert_data['taskname']}), 201
    except oracledb.IntegrityError as e:
         # 예: taskname이 Primary Key이고 중복된 경우
         print(f"DB 무결성 제약 조건 위반: {e}")
         conn.rollback()
         return jsonify({"status": "error", "message": "이미 존재하는 작업 이름입니다. 다른 이름을 사용해주세요.", "details": str(e)}), 409 # Conflict
    except Exception as e:
        conn.rollback() # 에러 발생 시 롤백
        print(f"DB 저장 실패: {e}")
        return jsonify({"status": "error", "message": f"데이터 저장 중 에러가 발생했습니다: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/tasks', methods=['GET'])
@validate_user # 사용자 인증 데코레이터 적용
def list_tasks():
    """
    태스크 목록을 조회하는 API (인증 필요)
    쿼리 파라미터로 taskname, requestor, modifier, startdate, enddate를 받습니다.
    taskname, requestor, modifier, 또는 (startdate와 enddate 쌍) 중 최소 하나는 필수 입력입니다.
    startdate, enddate 형식: YYYYMMDD24HHMISS
    startconfition은 Crontab 형식이며, 날짜 필터링 시 해당 범위 내 실행 시간을 계산하여 반환합니다.
    """
    taskname_param = request.args.get('taskname')
    requestor_param = request.args.get('requestor')
    modifier_param = request.args.get('modifier')
    startdate_str = request.args.get('startdate')
    enddate_str = request.args.get('enddate')

    # 최소 하나 이상의 검색 조건 필수 확인: taskname, requestor, modifier 또는 (startdate와 enddate 둘 다)
    date_range_provided = (startdate_str is not None and enddate_str is not None)
    if not any([taskname_param, requestor_param, modifier_param, date_range_provided]):
        return jsonify({
            "status": "error",
            "message": "taskname, requestor, modifier, 또는 startdate/enddate 쌍 중 최소 하나는 검색 조건으로 입력해야 합니다."
        }), 400

    startdate_dt = None
    enddate_dt = None

    # 날짜 범위 필터링이 필요한 경우 날짜 형식 파싱
    if date_range_provided:
         try:
             # 요청받은 날짜 문자열을 datetime 객체로 변환
             # startdate_dt는 croniter의 시작점이 되므로, 범위를 포함하려면 1초 빼거나 조정이 필요할 수 있습니다.
             # 여기서는 범위의 시작점 자체를 기준으로 계산하도록 합니다.
             startdate_dt = datetime.datetime.strptime(startdate_str, '%Y%m%d%H%M%S')
             enddate_dt = datetime.datetime.strptime(enddate_str, '%Y%m%d%H%M%S')

             # enddate가 startdate보다 이전이면 에러
             if enddate_dt < startdate_dt:
                 return jsonify({
                     "status": "error",
                     "message": "enddate는 startdate보다 같거나 이후여야 합니다."
                 }), 400

         except ValueError:
             # 날짜 형식 오류 시 클라이언트에게 알림
             return jsonify({
                 "status": "error",
                 "message": "startdate 또는 enddate의 날짜 형식이 유효하지 않습니다. YYYYMMDD24HHMISS 형식을 사용하세요."
             }), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "데이터베이스에 연결할 수 없습니다."}), 500

    cursor = conn.cursor()
    try:
        # DB 쿼리: useyn='Y' 이고 taskname/requestor/modifier 조건에 맞는 태스크 선택
        # startconfition (Crontab) 및 필요한 정보들을 가져옵니다.
        sql = f"SELECT taskname, requestor, modifier, startconfition FROM {TASKS_TABLE} WHERE useyn = 'Y'"
        params = {}
        conditions = []

        # taskname, requestor, modifier 조건 추가 (LIKE 검색)
        if taskname_param:
            conditions.append("taskname LIKE :taskname_param")
            params['taskname_param'] = f"%{taskname_param}%"
        if requestor_param:
            conditions.append("requestor LIKE :requestor_param")
            params['requestor_param'] = f"%{requestor_param}%"
        if modifier_param:
            conditions.append("modifier LIKE :modifier_param")
            params['modifier_param'] = f"%{modifier_param}%"

        # 조건들을 AND로 연결
        if conditions:
            sql += " AND " + " AND ".join(conditions)

        # 결과 정렬 (옵션)
        sql += " ORDER BY taskname" # 예시로 taskname으로 정렬

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        final_results = []

        # 가져온 데이터 순회하며 처리
        for row in rows:
            task_name, req, mod, start_conf = row

            # 날짜 범위 필터링이 필요한 경우 (startdate와 enddate가 모두 제공된 경우)
            if date_range_provided:
                if start_conf and isinstance(start_conf, str):
                    try:
                        # croniter 객체 생성. 기준 시간(base_time)을 startdate_dt로 설정
                        # 이렇게 하면 croniter는 base_time 이후의 첫 실행 시간부터 계산 시작
                        iter = croniter(start_conf, startdate_dt)

                        # enddate_dt 범위까지 실행 시간 찾기
                        while True:
                            try:
                                # 다음 실행 시간 계산
                                next_occurrence_dt = iter.get_next(datetime.datetime)

                                # 계산된 실행 시간이 enddate_dt 범위 내에 있는지 확인
                                if next_occurrence_dt <= enddate_dt:
                                    # 범위 내에 있으면 결과에 추가
                                    final_results.append({
                                        "taskname": task_name,
                                        "requestor": req,
                                        "modifier": mod,
                                        # 실행 시간을 YYYYMMDD24HHMISS 형식의 문자열로 변환하여 반환
                                        "launchdate": next_occurrence_dt.strftime('%Y%m%d%H%M%S')
                                    })
                                else:
                                    # 계산된 시간이 enddate 범위를 벗어나면 이 태스크는 더 이상 검색할 필요 없음
                                    break
                            except StopIteration:
                                # 더 이상 계산 가능한 실행 시간이 없으면 종료
                                break
                            except Exception as e:
                                # croniter 계산 중 에러 발생 시
                                print(f"경고: 태스크 '{task_name}' Crontab '{start_conf}' 계산 중 에러 발생: {e}")
                                # 이 태스크는 건너뛰거나 오류 표시
                                final_results.append({
                                     "taskname": task_name,
                                     "requestor": req,
                                     "modifier": mod,
                                     "launchdate": f"Invalid Crontab: {start_conf}"
                                })
                                break # 에러가 나면 이 태스크는 다음 실행 시간 계산 중단

                    except Exception as e:
                        # croniter 객체 생성 자체에서 에러 발생 (예: 잘못된 Crontab 형식)
                        print(f"경고: 태스크 '{task_name}' Crontab '{start_conf}' 형식이 잘못되었습니다: {e}")
                        # 이 태스크는 결과에 포함하지 않거나 오류 표시
                        final_results.append({
                             "taskname": task_name,
                             "requestor": req,
                             "modifier": mod,
                             "launchdate": f"Invalid Crontab Format: {start_conf}"
                        })
                else:
                     # startconfition 필드가 없거나 문자열이 아닌 경우 (크론탭 계산 불가)
                     print(f"경고: 태스크 '{task_name}'에 유효한 startconfition이 없습니다.")
                     final_results.append({
                          "taskname": task_name,
                          "requestor": req,
                          "modifier": mod,
                          "launchdate": "No Crontab Provided"
                     })


            # 날짜 범위 필터링이 필요 없는 경우
            else:
                 # 날짜 계산 없이 기본 정보만 결과에 추가, launchdate는 None
                 final_results.append({
                     "taskname": task_name,
                     "requestor": req,
                     "modifier": mod,
                     "launchdate": None # 날짜 필터링 요청이 없으므로 launchdate 없음
                 })


        return jsonify({"status": "success", "data": final_results}), 200

    except Exception as e:
        print(f"DB 조회 실패: {e}")
        return jsonify({"status": "error", "message": f"데이터베이스 조회 중 에러가 발생했습니다: {e}"}), 500
    finally:
        cursor.close()
        conn.close()


# === 애플리케이션 실행 ===
if __name__ == '__main__':
    # 이 블록은 직접 스크립트를 실행할 때만 작동합니다.
    # 실제 배포 시에는 Gunicorn, uWSGI 등의 WSGI 서버를 사용하세요.
    print("Flask 태스크 API 서버 시작 준비 중...")
    print(f"인증 서버 URL: {AUTH_SERVER_URL}")
    print(f"Oracle DB 테이블: {TASKS_TABLE}")
    print("주의: DB 연결 정보와 인증 서버 URL을 환경 변수 또는 설정 파일로 관리하는 것이 좋습니다.")
    print("croniter 라이브러리가 필요합니다: pip install croniter")
    print("인증 서버 URL이 127.0.0.1:9119 HTTPS 이므로, 인증서 문제 발생 시 requests.get의 verify=False 옵션을 제거하거나 유효한 인증서 설정을 하세요.")


    # app.run(debug=True, host='0.0.0.0', port=5000)
    # debug=True는 개발 환경에서만 사용하세요.
    # 실제 WSGI 서버(Gunicorn 등)를 사용하는 예시:
    # gunicorn --bind 0.0.0.0:5000 app:app


import schedule  # schedule 라이브러리 가져오기
import time      # time 모듈 가져오기 (sleep 함수 사용)
import sys
import pandas as pd
import subprocess
from datetime import datetime
from common.loghandler import LogHandler
from common.dbhandler import DBHandler

log_handler = LogHandler()
logger = log_handler.getloghandler("sch")

db_handler = DBHandler()
dbconn = db_handler.get_db_connection(logger)

# 데이터베이스에서 작업을 가져오는 함수
def fetch_tasks():
    global dbconn
    query = "SELECT taskid, taskname, subprocee_starttime, task_status FROM TESTCHO.TASK WHERE task_status != 'S'"
    # Oracle DATE/TIMESTAMP 컬럼을 datetime 객체로 가져오는지 확인 필요 (oracledb 기본 동작 확인)
    return pd.read_sql(query, dbconn)

# 작업 상태를 업데이트하는 함수
def update_task_status(taskid, status):
    global dbconn
    with dbconn.cursor() as cursor:
        cursor.execute("""
            UPDATE TESTCHO.TASK
            SET task_status = :status,
                changed_at = CURRENT_TIMESTAMP
            WHERE taskid = :taskid
        """, status=status, taskid=taskid)
        dbconn.commit()

# app.py 스크립트를 subprocess로 실행하는 함수
def run_app_py(taskid):
    """Run the app.py script with taskid as an argument."""
    taskid_str = str(taskid)
    logger.info(f"app.py 실행 시도: taskid={taskid_str}")
    process = subprocess.Popen(["python", "app.py", taskid_str],
                            start_new_session=True, # 새 세션에서 실행하여 부모 프로세스와 분리
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    logger.info(f"app.py 프로세스 시작 PID: {process.pid}")
    return process

# 데이터베이스에서 작업을 확인하고 필요한 작업을 실행하는 함수
# 이 함수가 스케줄러에 의해 주기적으로 호출될 거예요.
def check_and_run_tasks():
    try:
        current_time = datetime.now() # datetime 객체로 현재 시간을 가져와 비교하는 게 더 정확해요.
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"{current_time_str}|작업 확인 시작...")

        tasks = fetch_tasks()
        logger.info(f"{current_time_str}|확인된 작업 목록: {len(tasks)}개")
        logger.debug(f"{current_time_str}|확인된 작업 데이터:\n{tasks}")

        for index, row in tasks.iterrows():
            logger.debug(f"row({index}):{row}")
            if isinstance(row['subprocee_starttime'], datetime) and row['subprocee_starttime'] >= current_time:
                task_id = row['taskid']
                logger.info(f"조건 만족 작업 발견: taskid={task_id}, 시작 시간={row['subprocee_starttime']}")
                # 작업 상태를 'I' (In progress)로 업데이트
                update_task_status(task_id, 'I')
                logger.info(f"taskid={task_id} 상태 'I'로 업데이트 완료")

                # app.py 실행
                process = run_app_py(task_id)

            elif not isinstance(row['subprocee_starttime'], datetime):
                logger.warning(
                    f"taskid={row['taskid']}의 subprocee_starttime 형식이 datetime이 아닙니다: {type(row['subprocee_starttime'])}")

    except Exception as e:
        logger.error(f"작업 확인 및 실행 중 에러 발생: {e}", exc_info=True)
        # 에러 발생 시 DB 연결이 끊어졌을 수 있으니, 다음 실행 때 재연결될 거예요.


def main():
    logger.info("sch scheduler (schedule 라이브러리 사용) 서버 시작 중...")

    # schedule 라이브러리를 사용하여 check_and_run_tasks 함수를 1초마다 실행하도록 예약
    # APScheduler의 add_job 대신 이 문법을 사용해요.
    schedule.every(1).seconds.do(check_and_run_tasks)

    logger.info('스케줄러 시작! (schedule 라이브러리 사용 중)')
    logger.info('Ctrl+C 를 누르면 종료돼요.')

    # schedule 라이브러리는 run_pending()을 계속 호출해줘야 예약된 작업을 실행해요.
    try:
        while True:
            schedule.run_pending() # 예약된 작업 중에 실행할 게 있으면 실행
            time.sleep(1)         # 너무 바쁘게 돌지 않도록 1초 쉬기

    except (KeyboardInterrupt, SystemExit):
        # Ctrl+C 등으로 프로그램을 종료할 때
        logger.info("스케줄러 종료 중...")
        logger.info('스케줄러 종료.')

if __name__ == "__main__":
    main()

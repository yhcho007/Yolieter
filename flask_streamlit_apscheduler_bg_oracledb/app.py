import oracledb
import pandas as pd
from datetime import datetime
import sys
import signal
from common.loghandler import LogHandler
from common.dbhandler import DBHandler

log_handler = LogHandler()
logger = log_handler.getloghandler("app")

db_handler = DBHandler()
dbconn = db_handler.get_db_connection(logger)

# 전역 변수로 taskid와 connection 정의
taskid = None

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


def fetch_data(taskid):
    global dbconn
    query = "SELECT * FROM TESTCHO.TASK WHERE taskid = :taskid"
    return pd.read_sql(query, dbconn, params={'taskid': taskid})

def save_to_csv(dataframe):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}.csv"
    dataframe.to_csv(filename, index=False)
    logger.info(f"Data saved to {filename}")

def signal_handler(sig, frame):
    """신호 처리기: 프로세스가 종료될 때 상태 업데이트."""
    global dbconn
    if dbconn:
        update_task_status(dbconn, taskid, 'K')
    logger.info("Process terminated. Status updated to 'K'.")
    sys.exit(0)

def main(taskid_input):
    global taskid, dbconn
    taskid = taskid_input


    # 종료 신호 처리 등록
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill 명령

    try:
        # 데이터 가져오기
        data = fetch_data(dbconn, taskid)

        # CSV 파일로 저장
        save_to_csv(data)

        # 상태 업데이트
        update_task_status(dbconn, taskid, 'S')
    finally:
        # 종료 시 상태 업데이트
        if dbconn:
            update_task_status(dbconn, taskid, 'E')
            dbconn.close()

if __name__ == "__main__":
    # 커맨드라인 인자로 taskid를 가져옴
    if len(sys.argv) != 2:
        logger.info("Usage: python app.py <taskid>")
        sys.exit(1)

    taskid = sys.argv[1]
    main(taskid)

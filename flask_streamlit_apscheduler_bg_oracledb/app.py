import oracledb
import pandas as pd
from datetime import datetime
import sys
import signal
from common.loghandler import LogHandler

log_handler = LogHandler()
logger = log_handler.getloghandler("app")

# 전역 변수로 taskid와 connection 정의
taskid = None
connection = None

def update_task_status(connection, taskid, status):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE task 
            SET task_status = :status, 
                changed_at = CURRENT_TIMESTAMP 
            WHERE taskid = :taskid
        """, status=status, taskid=taskid)
        connection.commit()


def fetch_data(connection, taskid):
    query = "SELECT * FROM SCH WHERE taskid = :taskid"
    return pd.read_sql(query, connection, params={'taskid': taskid})

def save_to_csv(dataframe):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}.csv"
    dataframe.to_csv(filename, index=False)
    logger.info(f"Data saved to {filename}")

def signal_handler(sig, frame):
    """신호 처리기: 프로세스가 종료될 때 상태 업데이트."""
    global connection
    if connection:
        update_task_status(connection, taskid, 'K')
    logger.info("Process terminated. Status updated to 'K'.")
    sys.exit(0)

def main(taskid_input):
    global taskid, connection
    taskid = taskid_input

    # 데이터베이스 연결
    connection = connection = oracledb.connect(user="testcho", password="1234", dsn="127.0.0.1:1521/FREE")

    # 종료 신호 처리 등록
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill 명령

    try:
        # 데이터 가져오기
        data = fetch_data(connection, taskid)

        # CSV 파일로 저장
        save_to_csv(data)

        # 상태 업데이트
        update_task_status(connection, taskid, 'S')
    finally:
        # 종료 시 상태 업데이트
        if connection:
            update_task_status(connection, taskid, 'E')
            connection.close()

if __name__ == "__main__":
    # 커맨드라인 인자로 taskid를 가져옴
    if len(sys.argv) != 2:
        logger.info("Usage: python app.py <taskid>")
        sys.exit(1)

    taskid = sys.argv[1]
    main(taskid)

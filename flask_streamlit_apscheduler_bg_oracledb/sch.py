import oracledb
import pandas as pd
import subprocess
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

def fetch_tasks(connection):
    query = "SELECT taskid, taskname, subprocee_starttime, task_status FROM SCH WHERE task_status != 'S'"
    return pd.read_sql(query, connection)

def update_task_status(connection, taskid, status):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE task 
            SET task_status = :status, 
                changed_at = CURRENT_TIMESTAMP 
            WHERE taskid = :taskid
        """, status=status, taskid=taskid)
        connection.commit()

def run_app_py(taskid):
    """Run the app.py script with taskid as an argument."""
    process = subprocess.Popen(["python3", "app.py", taskid],
                            start_new_session=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)  # taskid를 인자로 전달
    return process

def check_and_run_tasks():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with oracledb.connect(user='your_username', password='your_password', dsn='your_dsn') as connection:
        tasks = fetch_tasks(connection)
        
        for _, row in tasks.iterrows():
            if row['subprocee_starttime'].strftime("%Y-%m-%d %H:%M:%S") >= current_time:
                process = run_app_py(row['taskid'])  # taskid를 인자로 넘김
                update_task_status(connection, row['taskid'], 'I')

def main():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_run_tasks, 'interval', seconds=1)
    scheduler.start()
    
    try:
        print("Scheduler started. Monitoring tasks...")
        while True:
            pass  # 계속 실행
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()

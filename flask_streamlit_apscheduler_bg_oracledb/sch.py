import schedule
import time
import sys
import pandas as pd
import subprocess
import threading
from datetime import datetime
from common.loghandler import LogHandler
from common.dbhandler import DBHandler

log_handler = LogHandler()
logger = log_handler.getloghandler("sch")

db_handler = DBHandler()
dbconn = db_handler.get_db_connection(logger)

# Set to track active task threads by task_id
active_task_threads = set()
# Lock for thread-safe access to active_task_threads
thread_lock = threading.Lock()


def fetch_tasks():
    global dbconn
    # Select tasks ready to run (status 'R') and whose start time is now or in the past
    query = ("SELECT taskid, taskname, subprocee_starttime, task_status FROM TESTCHO.TASK " +
             "WHERE task_status = 'R' AND subprocee_starttime BETWEEN SYSDATE AND (SYSDATE + INTERVAL '5' SECOND")
    try:
        tasks_df = pd.read_sql(query, dbconn)
        return tasks_df
    except Exception as e:
        logger.error(f"fetch_tasks query failed: {e}", exc_info=True)
        return pd.DataFrame()


def update_task_status(taskid, status):
    global dbconn
    try:
        with dbconn.cursor() as cursor:
            cursor.execute("""
                UPDATE TESTCHO.TASK
                SET task_status = :status,
                    changed_at = CURRENT_TIMESTAMP
                WHERE taskid = :taskid
            """, status=status, taskid=taskid)
            dbconn.commit()
            logger.info(f"taskid={taskid} status updated to '{status}'")
    except Exception as e:
        logger.error(f"Failed to update status for taskid={taskid}: {e}", exc_info=True)


def run_app_py(taskid):
    """Run the app.py script with taskid as argument."""
    try:
        taskid_str = str(taskid)
        logger.info(f"Attempting to run app.py for taskid={taskid_str}")

        process = subprocess.Popen(["python", "app.py", taskid_str],
                                   start_new_session=True,  # Run in new session to detach
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        logger.info(f"app.py process started with PID: {process.pid} (taskid={taskid})")
        return process

    except FileNotFoundError:
        logger.error(f"Error: app.py script not found. (taskid={taskid})", exc_info=True)
    except Exception as e:
        logger.error(f"run_app_py failed for taskid={taskid}: {e}", exc_info=True)
    return None


def task_worker(task_data):
    """Thread worker function to process a single task."""

    task_id = task_data['TASKID']
    start_time = task_data['SUBPROCEE_STARTTIME']

    logger.info(f"Thread for taskid={task_id} started. Scheduled time: {start_time}")

    try:
        now = datetime.now()
        if now < start_time:
            wait_seconds = (start_time - now).total_seconds()
            if wait_seconds > 0:
                logger.info(f"taskid={task_id} waiting for {wait_seconds:.2f} seconds...")
                time.sleep(wait_seconds)
                logger.info(f"taskid={task_id} wait complete.")

        logger.info(f"taskid={task_id} execution time reached or passed. Preparing to run.")

        # Update status to 'In progress'
        update_task_status(task_id, 'I')

        # Run the subprocess
        process = run_app_py(task_id)

        if process:
            logger.info(f"app.py execution started for taskid={task_id}. PID: {process.pid}")
        else:
            logger.error(f"app.py execution failed to start for taskid={task_id}.")

    except Exception as e:
        logger.error(f"Error processing taskid={task_id}: {e}", exc_info=True)
    finally:
        # Remove task_id from active set upon thread completion
        with thread_lock:
            if task_id in active_task_threads:
                active_task_threads.remove(task_id)
                logger.info(f"taskid={task_id} removed from active set.")

        logger.info(f"Thread for taskid={task_id} finished.")


def check_and_run_tasks():
    """Fetches ready tasks and starts a thread for each."""
    try:
        tasks = fetch_tasks()

        if not tasks.empty:
            for index, row in tasks.iterrows():
                task_id = row['TASKID']

                with thread_lock:
                    if task_id not in active_task_threads:
                        thread = threading.Thread(target=task_worker, args=(row,))
                        thread.daemon = True  # Allow main thread to exit even if this thread is running
                        thread.start()
                        active_task_threads.add(task_id)
                        logger.info(f"Started new thread for taskid={task_id}.")

        # Log the number of tasks currently being handled by threads
        with thread_lock:
            if len(active_task_threads) > 0:
                logger.info(f"===== Number of active task threads: {len(active_task_threads)} =====")

    except Exception as e:
        logger.error(f"Error in check_and_run_tasks: {e}", exc_info=True)


def main():
    logger.info("sch scheduler (using schedule library) starting...")

    # Schedule check_and_run_tasks to run every 5 seconds
    schedule.every(5).seconds.do(check_and_run_tasks)

    logger.info('Scheduler started!')
    logger.info('Press Ctrl+C to exit.')

    # Keep the main thread alive to run the scheduler
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)  # Check schedule every 1 second

    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler shutting down...")
        logger.info('Scheduler stopped.')
    finally:
        if dbconn:
            try:
                dbconn.close()
                logger.info("Database connection closed.")
            except Exception as e:
                logger.error(f"Error closing DB connection: {e}", exc_info=True)


if __name__ == "__main__":
    main()

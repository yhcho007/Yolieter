'''
API 서버 실행: python dash_app.py
브라우저에서 http://localhost:8501로 이동하여 애플리케이션 확인.

'''
import dash
from dash import dcc, html, dash_table
import pandas as pd
import requests
import plotly.express as px
import psutil
import json
from common.loghandler import LogHandler
from common.dbhandler import DBHandler

log_handler = LogHandler()
logger = log_handler.getloghandler("dash")

db_handler = DBHandler()
dbconn = db_handler.get_db_connection(logger)

app = dash.Dash(__name__)

def fetch_tasks(params):
    """Fetch tasks from the API."""
    response = requests.get("http://127.0.0.1:5000/tasks", params=params)
    if response.status_code == 200:
        return response.json()
    return []

def post_task(data):
    """Post a new task to the API."""
    response = requests.post("http://127.0.0.1:5000/tasks", json=data)
    if response.status_code == 200:
        return response.json()
    return {"error": "Failed to post task"}

def get_system_metrics():
    """Get system metrics like CPU, memory, and disk usage."""
    cpu_usage = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    memory_usage = memory_info.percent
    disk_info = psutil.disk_usage('/')
    disk_usage = disk_info.percent
    app_process_count = len([p for p in psutil.process_iter() if p.name() == "python.exe" and "app.py" in p.cmdline()])
    
    # 가장 많이 CPU를 사용하는 프로세스 10개
    cpu_processes = sorted([(p.info['pid'], p.info['name'], p.info['cpu_percent']) for p in psutil.process_iter(['pid', 'name', 'cpu_percent'])], key=lambda x: x[2], reverse=True)[:10]
    
    # 가장 많이 메모리를 사용하는 프로세스 10개
    memory_processes = sorted([(p.info['pid'], p.info['name'], p.info['memory_info'].rss / (1024 * 1024)) for p in psutil.process_iter(['pid', 'name', 'memory_info'])], key=lambda x: x[2], reverse=True)[:10]

    # 네트워크 사용량
    net_io = psutil.net_io_counters()
    network_usage = {
        'bytes_sent': net_io.bytes_sent,
        'bytes_recv': net_io.bytes_recv
    }

    return cpu_usage, app_process_count, memory_usage, disk_usage, cpu_processes, memory_processes, network_usage

app.layout = html.Div([
    html.H1("Task Monitor"),
    
    html.Div([
        dcc.Input(id='taskname-input', type='text', placeholder='Task Name'),
        dcc.Input(id='starttime-input', type='text', placeholder='Start Time (YYYY-MM-DD HH:MM:SS)'),
        dcc.Input(id='status-input', type='text', placeholder='Task Status'),
        html.Button('Submit Task', id='submit-task-button', n_clicks=0),
    ]),

    html.Div(id='post-task-response', style={'margin-top': '20px', 'margin-bottom': '20px'}),

    dcc.Graph(id='task-status-count'),
    dash_table.DataTable(id='task-table'),
    html.Div(id='system-metrics'),
])

@app.callback(
    [dash.dependencies.Output('task-status-count', 'figure'),
     dash.dependencies.Output('task-table', 'data'),
     dash.dependencies.Output('system-metrics', 'children'),
     dash.dependencies.Output('post-task-response', 'children')],
    [dash.dependencies.Input('submit-task-button', 'n_clicks')],
    [dash.dependencies.State('taskid-input', 'value'),
     dash.dependencies.State('taskname-input', 'value'),
     dash.dependencies.State('starttime-input', 'value'),
     dash.dependencies.State('status-input', 'value')]
)
def update_output(n_clicks, taskid, taskname, starttime, status):
    # 새로운 작업 추가
    if n_clicks > 0 and taskid and taskname and starttime and status:
        task_data = {
            "taskid": taskid,
            "taskname": taskname,
            "subprocee_starttime": starttime,
            "task_status": status
        }
        post_response = post_task(task_data)
        post_response_message = f"Task posted: {json.dumps(post_response)}"
    else:
        post_response_message = ""

    # 기존 작업 가져오기
    params = {}
    tasks = fetch_tasks(params)

    # 막대 그래프 생성
    if tasks:
        df = pd.DataFrame(tasks)
        df['subprocee_starttime'] = pd.to_datetime(df['subprocee_starttime'])
        df['hour'] = df['subprocee_starttime'].dt.floor('H')
        status_counts = df['task_status'].value_counts().reset_index()
        status_counts.columns = ['task_status', 'count']
        fig = px.bar(status_counts, x='task_status', y='count',
                     labels={'task_status': 'Task Status', 'count': 'Count'},
                     title='Count of Tasks by Status')
    else:
        fig = px.bar(title='No tasks found.')

    # 테이블 데이터 설정
    table_data = tasks if tasks else []

    # 시스템 메트릭스 가져오기
    cpu_usage, app_process_count, memory_usage, disk_usage, cpu_processes, memory_processes, network_usage = get_system_metrics()
    
    metrics = f"""
    - CPU 사용률: {cpu_usage}%
    - app.py 프로세스 개수: {app_process_count}
    - 메모리 사용률: {memory_usage}%
    - 디스크 사용량: {disk_usage}%
    - 전송된 바이트: {network_usage['bytes_sent']}
    - 수신된 바이트: {network_usage['bytes_recv']}
    """

    # CPU 프로세스 데이터
    cpu_process_df = pd.DataFrame(cpu_processes, columns=['PID', 'Name', 'CPU Usage (%)'])
    
    # 메모리 프로세스 데이터
    memory_process_df = pd.DataFrame(memory_processes, columns=['PID', 'Name', 'Memory Usage (MB)'])

    return fig, table_data, metrics + cpu_process_df.to_string(index=False) + "\n" + memory_process_df.to_string(index=False), post_response_message

if __name__ == '__main__':
    app.run(debug=False)

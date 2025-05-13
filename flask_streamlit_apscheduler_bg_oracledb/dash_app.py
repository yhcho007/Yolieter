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

app = dash.Dash(__name__)

def fetch_tasks(params):
    """Fetch tasks from the API."""
    response = requests.get("http://localhost:5000/tasks", params=params)
    if response.status_code == 200:
        return response.json()
    return []

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
    
    dcc.Input(id='taskname-filter', type='text', placeholder='Task Name'),
    dcc.Input(id='starttime-filter', type='text', placeholder='Start Time (YYYYMMDDHHMISS)'),
    dcc.Input(id='endtime-filter', type='text', placeholder='End Time (YYYYMMDDHHMISS)'),
    dcc.Input(id='limit-filter', type='number', value=10, placeholder='Limit'),

    html.Button('Submit', id='submit-button', n_clicks=0),

    dcc.Graph(id='task-status-count'),
    dash_table.DataTable(id='task-table'),
    html.Div(id='system-metrics'),
])

@app.callback(
    [dash.dependencies.Output('task-status-count', 'figure'),
     dash.dependencies.Output('task-table', 'data'),
     dash.dependencies.Output('system-metrics', 'children')],
    [dash.dependencies.Input('submit-button', 'n_clicks')],
    [dash.dependencies.State('taskname-filter', 'value'),
     dash.dependencies.State('starttime-filter', 'value'),
     dash.dependencies.State('endtime-filter', 'value'),
     dash.dependencies.State('limit-filter', 'value')]
)
def update_output(n_clicks, taskname, starttime, endtime, limit):
    params = {}
    if taskname:
        params['taskname'] = taskname
    if starttime:
        params['starttime'] = starttime
    if endtime:
        params['endtime'] = endtime
    if limit:
        params['limit'] = limit

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

    return fig, table_data, metrics + cpu_process_df.to_string(index=False) + "\n" + memory_process_df.to_string(index=False)

if __name__ == '__main__':
    app.run_server(debug=True)

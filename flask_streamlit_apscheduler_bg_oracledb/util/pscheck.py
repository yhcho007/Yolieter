import psutil
import time

def find_python_processes_by_cmdline():
    """
    command 라인에 'python' 문자열이 포함된 실행 중인 프로세스들을 찾고,
    해당 프로세스들의 PID, 이름, command 라인 정보를 반환합니다.
    """
    python_processes_info = [] # 'python' command 라인을 가진 프로세스 정보를 담을 리스트

    # 모든 실행 중인 프로세스 정보를 가져오되, pid, name, cmdline 만 요청해요.
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pinfo = proc.info

            # 'cmdline' 정보가 있고, 비어있지 않으면 확인 시작
            # 'cmdline'은 보통 리스트 형태라 먼저 문자열로 합쳐서 검색할 거야.
            # 만약 pinfo['cmdline']이 None 이나 빈 리스트일 경우를 대비해요.
            if pinfo['cmdline']:
                 # command line 리스트를 하나의 문자열로 합쳐요.
                 # Windows에서는 cmdline이 빈 문자열인 경우가 있어서 join 전에 확인하거나
                 # join 결과를 확인하는 것이 안전해요.
                 full_cmdline = ' '.join(pinfo['cmdline'])

                 # 합쳐진 command line 문자열 안에 'python'이 포함되어 있는지 확인해요.
                 # 대소문자 구분 없이 찾고 싶다면 .lower()를 사용할 수 있어.
                 if 'python' in full_cmdline:
                     python_processes_info.append({
                         'pid': pinfo['pid'],
                         'name': pinfo['name'],
                         'cmdline': full_cmdline # 합쳐진 command line 문자열 그대로 저장
                     })
            # else:
                # logger.debug(f"PID {pinfo.get('pid', 'N/A')} 의 cmdline 정보가 없습니다.") # 디버깅용

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # 프로세스가 사라졌거나 접근 권한이 없는 경우 건너뛰어요.
            pass
        except Exception as e:
             # 혹시 다른 예상치 못한 에러가 발생할 수도 있으니 로깅하는 게 좋아.
             pid = pinfo.get('pid', 'N/A') if 'pinfo' in locals() else 'N/A'
             print(f"PID {pid} 프로세스 정보 처리 중 에러 발생: {e}")


    # 'python' command 라인을 가진 프로세스 정보 리스트를 반환해요.
    return python_processes_info

# 이제 함수를 사용해서 'python' command 라인을 가진 프로세스들을 찾아보자!
if __name__ == "__main__":
    print("'python' command line을 가진 프로세스 확인 중...")

    try:
        # find_python_processes_by_cmdline 함수를 호출해서 결과를 가져와요.
        python_processes = find_python_processes_by_cmdline()

        # 찾은 프로세스 목록을 출력해요.
        if python_processes:
            print(f"\n'python' command line을 가진 프로세스가 실행 중입니다. 정보:")
            print("-" * 60) # 출력 포맷 길이를 좀 늘렸어.
            # 헤더 출력
            print(f"{'PID':<5} {'이름':<15} Command Line")
            print("-" * 60)
            # 각 프로세스 정보 출력
            for proc_info in python_processes:
                print(f"{proc_info['pid']:<5} {proc_info['name']:<15} {proc_info['cmdline']}")
                # print(f"  PID: {proc_info['pid']}")
                # print(f"  이름: {proc_info['name']}")
                # print(f"  Command Line: {proc_info['cmdline']}")
                # print("-" * 40)
            print("-" * 60)
        else:
            print("\n'python' command line을 가진 프로세스가 실행 중이지 않습니다.")

        # 필요하다면 잠시 대기해서 여러 번 확인해볼 수도 있어.
        # time.sleep(5)

    except KeyboardInterrupt:
        print("\n프로세스 확인 종료.")
    except Exception as e:
        print(f"프로세스 확인 중 예상치 못한 에러 발생: {e}")


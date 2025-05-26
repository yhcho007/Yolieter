from datetime import datetime, date, time, timedelta
import calendar

def generate_schedule_times(
    start_date: date,
    end_date: date,
    start_time: time,
    frequency: str, # 'daily', 'weekly', 'monthly' 중 하나
    specific_months: list[int] | None = None, # 스케줄을 적용할 특정 월 목록 (1-12). None이면 모든 월에 적용.
    specific_weekdays: list[int] | None = None, # 스케줄을 적용할 특정 요일 목록 (0=월, 6=일). frequency가 'weekly'이면 필수.
    specific_days_of_month: list[int] | None = None # 스케줄을 적용할 특정 날짜 목록 (1-31).
) -> list[datetime]:
    """
    주어진 조건에 따라 스케줄 시작 시간 목록을 생성합니다.

    Args:
        start_date: 스케줄 시작 날짜 (inclusive).
        end_date: 스케줄 종료 날짜 (inclusive).
        start_time: 스케줄 시작 시간 (datetime.time 객체).
        frequency: 스케줄 빈도 ('daily', 'weekly', 'monthly').
        specific_months: 스케줄을 적용할 특정 월 목록 (1-12). None이면 모든 월에 적용.
        specific_weekdays: 스케줄을 적용할 특정 요일 목록 (0=월, 6=일).
                           frequency가 'weekly'이고 None이면 에러 반환. 다른 빈도에서는 요일 필터로 사용될 수 있음.
        specific_days_of_month: 스케줄을 적용할 특정 날짜 목록 (1-31).
                                  None이면 frequency에 따라 다르게 적용.
                                  'daily': 모든 날. 'monthly': 매월 1일.

    Returns:
        생성된 datetime 객체들의 목록. 조건에 맞지 않으면 빈 목록 반환.
    """
    # 날짜 유효성 검사
    if start_date > end_date:
        print("시작 날짜가 종료 날짜보다 늦어요.")
        return []

    # weekly 빈도 선택 시 specific_weekdays 필수 확인
    if frequency == 'weekly' and specific_weekdays is None:
        print("주간 빈도('weekly')를 선택한 경우 specific_weekdays 목록은 반드시 지정해야 합니다. (예: [0, 4] for 월, 금)")
        return []

    schedule_times = []
    current_date = start_date

    # 시작 날짜부터 종료 날짜까지 하루씩 순회
    while current_date <= end_date:
        # 1. 특정 월 필터 적용
        if specific_months is not None and current_date.month not in specific_months:
            current_date += timedelta(days=1)
            continue # 해당 월이 아니면 다음 날로 건너뛰기

        # 2. 빈도 및 일자/요일 필터 적용
        is_scheduled_day = False

        if frequency == 'daily':
            # '매일' 또는 '매일 특정 복수 개의 일'
            if specific_days_of_month is None:
                # '매일' (월 필터만 통과하면 OK)
                is_scheduled_day = True
            elif current_date.day in specific_days_of_month:
                # '매일 특정 복수 개의 일' (지정된 날짜에 해당하는지 체크)
                 is_scheduled_day = True

        elif frequency == 'weekly':
             # '매주 특정 복수개의 주' (지정된 요일에 해당하는지 체크)
             # specific_weekdays는 weekly 빈도에서 필수이므로 None 체크는 위에서 이미 함
            if current_date.weekday() in specific_weekdays:
                 is_scheduled_day = True

        elif frequency == 'monthly':
            # '매 월' 또는 '매 월 특정 복수 개의 일'
            if specific_days_of_month is None:
                # '매 월' (특정 일 지정 없음) - 매월 1일
                if current_date.day == 1:
                    is_scheduled_day = True
            elif current_date.day in specific_days_of_month:
                # '매 월 특정 복수 개의 일' (지정된 날짜에 해당하는지 체크)
                is_scheduled_day = True

        # 3. 스케줄 조건에 맞는 날짜이면 시간 추가
        if is_scheduled_day:
            # 현재 날짜와 지정된 시작 시간을 합쳐 datetime 객체 생성
            schedule_times.append(datetime.combine(current_date, start_time))

        # 다음 날짜로 이동
        current_date += timedelta(days=1)

    return schedule_times

# --- 사용 예시 ---

# 예시 1: 2024년 6월 1일부터 6월 10일까지 매일 오전 9시
print("--- 예시 1: 매일 오전 9시 (2024-06-01 ~ 2024-06-10) ---")
times1 = generate_schedule_times(
    start_date=date(2024, 6, 1),
    end_date=date(2024, 6, 10),
    start_time=time(9, 0),
    frequency='daily'
)
for t in times1:
    print(t)

print("\n")

# 예시 2: 2024년 6월 1일부터 6월 30일까지 매주 월요일(0), 금요일(4) 오후 3시
print("--- 예시 2: 매주 월, 금 오후 3시 (2024-06-01 ~ 2024-06-30) ---")
times2 = generate_schedule_times(
    start_date=date(2024, 6, 1),
    end_date=date(2024, 6, 30),
    start_time=time(15, 0),
    frequency='weekly',
    specific_weekdays=[0, 4] # 월요일(0), 금요일(4)
)
for t in times2:
    print(t)

print("\n")

# 예시 3: 2024년 6월 1일부터 2024년 8월 31일까지 매월 1일, 15일 저녁 7시
print("--- 예시 3: 매월 1일, 15일 저녁 7시 (2024-06-01 ~ 2024-08-31) ---")
times3 = generate_schedule_times(
    start_date=date(2024, 6, 1),
    end_date=date(2024, 8, 31),
    start_time=time(19, 0),
    frequency='monthly',
    specific_days_of_month=[1, 15]
)
for t in times3:
    print(t)

print("\n")

# 예시 4: 2024년 1월 1일부터 2025년 12월 31일까지 1월, 4월, 7월, 10월의 매주 화요일(1), 목요일(3) 오전 10시
print("--- 예시 4: 1,4,7,10월의 매주 화, 목 오전 10시 (2024-01-01 ~ 2025-12-31) ---")
times4 = generate_schedule_times(
    start_date=date(2024, 1, 1),
    end_date=date(2025, 12, 31),
    start_time=time(10, 0),
    frequency='weekly',
    specific_months=[1, 4, 7, 10], # 1, 4, 7, 10월만
    specific_weekdays=[1, 3] # 화요일(1), 목요일(3)
)
for t in times4:
    print(t)

print("\n")

# 예시 5: 2024년 7월 1일부터 7월 10일까지 매일 오후 2시 (7월만 해당)
print("--- 예시 5: 매일 오후 2시 (2024-07-01 ~ 2024-07-10) - 특정 월(7월) 지정 ---")
times5 = generate_schedule_times(
    start_date=date(2024, 7, 1),
    end_date=date(2024, 7, 10),
    start_time=time(14, 0),
    frequency='daily',
    specific_months=[7] # 7월만 포함
)
for t in times5:
    print(t)

print("\n")

# 예시 6: 2024년 6월 1일부터 2024년 8월 31일까지 6월과 8월의 매월 15일 오전 11시
print("--- 예시 6: 6월, 8월의 매월 15일 오전 11시 (2024-06-01 ~ 2024-08-31) ---")
times6 = generate_schedule_times(
    start_date=date(2024, 6, 1),
    end_date=date(2024, 8, 31),
    start_time=time(11, 0),
    frequency='monthly',
    specific_months=[6, 8], # 6월, 8월만 포함
    specific_days_of_month=[15] # 15일
)
for t in times6:
    print(t)

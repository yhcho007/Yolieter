import logging
import logging.handlers
import os
import datetime

class LogHandler:
    def __init__(self):
        self.log_dir = "logs"


    # main 모듈 loghandler
    def getloghandler(self, log_name):
        # 로그 파일 이름 (날짜별로 생성)
        log_file_name = os.path.join(self.log_dir,
                                     log_name + datetime.datetime.now().strftime("%Y%m%d") + ".log")

        # 로그 디렉터리 생성 (존재하지 않을 경우)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # 로그 포맷 설정
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # FileHandler 생성
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file_name,
            when="midnight",  # 매일 자정 파일 생성
            interval=1,  # 1일 단위로 파일 생성
            encoding="utf-8"
        )

        # 포맷터 설정
        file_handler.setFormatter(formatter)

        # 로거 생성
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # FileHandler 추가
        logger.addHandler(file_handler)

        # 로그 메시지 출력
        logger.info("테스트 로그 메시지")

        return logger





# 로그 메시지 기록
#logger.info('This is a log message.')
#logger.warning('This is a warning message.')
#logger.error('This is an error message.')
import oracledb

class DBHandler:

    def __init__(self):
        self.log_dir = "logs"
        self.db_config = {
            'user': 'testcho',
            'password': '1234',
            'dsn': '127.0.0.1:1521/FREE'
        }

    def get_db_config(self):
        return self.db_config

    def get_db_connection(self,logger):
        """데이터베이스 연결을 가져오는 함수"""
        try:
            connection = oracledb.connect(
                user=self.db_config['user'], password=self.db_config['password'], dsn=self.db_config['dsn'])
            return connection
        except Exception as e:
            logger.info(f"DB 연결 오류: {e}")
            return None
# Task Management System

이 프로젝트는 Oracle 데이터베이스와 통신하여 작업을 관리하는 API를 제공합니다. Flask를 사용하여 RESTful API를 구현하고, Streamlit을 통해 사용자 인터페이스를 제공합니다. 또한, 백그라운드 작업을 처리하기 위해 `sch.py` 스크립트를 사용합니다.

## 구성 요소

### 1. main.py

`main.py`는 Flask 애플리케이션의 메인 파일로, 다음과 같은 기능을 제공합니다:

- **RESTful API**: 작업을 등록하고 조회할 수 있는 API 엔드포인트를 제공합니다.
- **백그라운드 프로세스 실행**: `sch.py`를 백그라운드에서 실행합니다.
- **신호 처리**: 프로세스가 종료될 때 관련된 모든 프로세스를 종료합니다.

#### 사용법

```bash
python main.py

# Red Hat Universal Base Image (UBI) 9와 Python 3.12가 포함된 이미지를 사용해!
FROM registry.access.redhat.com/ubi9/python-312:latest

LABEL description="Openshift 배포용 Python Flask 앱 with Gunicorn"
LABEL maintainer="당신의 이름 또는 이메일" # 네 정보를 다시 넣어줘!

# oracledb가 필요로 할 수 있는 라이브러리 (필요 없을 수도 있지만 일단 넣어두자!)
RUN yum update -y && \
    yum install -y openssl-libs && \
    yum clean all

# 컨테이너 안에서 작업할 기본 디렉토리를 설정해줘. 네 요청대로 /app/ 이야!
WORKDIR /app/

# requirements.txt 파일을 /app/ 디렉토리로 복사하고 Python 패키지들을 설치해.
# Gunicorn이 requirements.txt에 포함되어 있어야 해! (전에 추가했지? 😉)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 네 애플리케이션 코드(main.py)를 컨테이너 안으로 복사해.
COPY main.py /app/
# Dash 앱이나 sch.py는 이 컨테이너의 주 목적이 아니므로 여기서는 복사하지 않아.

# Flask 앱이 외부와 통신할 포트를 명시해줘. Gunicorn이 5000번으로 실행될 거야!
EXPOSE 5000

# 컨테이너가 시작될 때 실행될 명령어를 설정해.
# Gunicorn으로 main.py 파일 안의 'app' 객체를 실행하도록 해!
# 0.0.0.0:5000 포트로 들어오는 요청을 받을 거야.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "main:app"]

# Openshift 환경 관련 주의사항은 동일해!
# HEALTHCHECK (선택 사항이지만 Openshift에서 중요!)
# 앱이 제대로 떠있는지 Gunicorn 포트로 확인하는 헬스 체크야.
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD curl -f http://localhost:5000/ || exit 1

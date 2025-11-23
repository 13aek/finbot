# 기본 Python 이미지 (slim 절대 사용 금지 — torch 빌드 실패)
FROM python:3.11

# 컨테이너 내부 작업 디렉토리
WORKDIR /app

# -------------------------------
# 🔥 필수 시스템 패키지 설치
# -------------------------------
# torch, transformers, datasets, lxml, pyarrow, mysqlclient 등
# 모든 패키지가 빌드될 수 있게 필요한 의존성들을 설치한다.
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    liblzma-dev \
    default-libmysqlclient-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------
# 🔥 torch를 별도 설치 (CPU 버전)
# --------------------------------
# requirements.txt에 torch가 포함되어 있으면 빌드 실패 가능성 매우 큼.
# CPU 전용 wheel을 명확하게 지정해서 설치한다.
RUN pip install --no-cache-dir torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu

# --------------------------------
# 나머지 requirements 설치
# --------------------------------
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------
# 프로젝트 전체 복사
# --------------------------------
COPY . /app/

# --------------------------------
# Gunicorn 실행 (Django WSGI)
# --------------------------------
CMD ["gunicorn", "finbot.wsgi:application", "--bind", "0.0.0.0:8000"]

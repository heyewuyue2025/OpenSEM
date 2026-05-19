FROM python:3.11-slim

# 构建时传入 1 以安装 R、lavaan（默认开启：生产要求容器内稳定可用）
ARG WITH_LAVAAN=1

WORKDIR /app

RUN if [ "$WITH_LAVAAN" = "1" ]; then \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        r-base \
        r-base-dev \
        build-essential \
        libcurl4-openssl-dev \
        libssl-dev \
        libxml2-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && Rscript -e "install.packages('lavaan', repos='https://cloud.r-project.org/')" \
    ; fi

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# rpy2 依赖 R；仅在 WITH_LAVAAN=1 时安装，保证 lite 构建无需 R 也能成功。
COPY requirements-lavaan.txt .
RUN if [ "$WITH_LAVAAN" = "1" ]; then \
    pip install --no-cache-dir -r requirements-lavaan.txt \
    ; fi

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

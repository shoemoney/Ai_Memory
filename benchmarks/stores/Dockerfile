FROM python@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c
COPY requirements.txt /membench-stores-requirements.txt
RUN pip install --no-cache-dir -r /membench-stores-requirements.txt
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUNBUFFERED=1
WORKDIR /code

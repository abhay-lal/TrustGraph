FROM apache/airflow:2.9.1

USER root
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install --no-cache-dir \
    pycountry \
    rapidfuzz \
    pandas \
    requests \
    neo4j \
    qdrant-client \
    sqlalchemy \
    psycopg2-binary \
    openai \
    numpy

FROM python:3.12-slim

WORKDIR /app

COPY . /app

COPY zscalercert.pem /cert/zscalercert.pem

RUN pip config set global.cert "/cert/zscalercert.pem"

RUN pip install -r requirements.txt

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

FROM python:3.6.5-slim-stretch

WORKDIR /usr/src/app

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./wildfly-monitor.py .
COPY ./monitor.py .

CMD [ "python", "./wildfly-monitor.py" ]

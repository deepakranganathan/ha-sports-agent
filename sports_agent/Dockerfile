FROM ghcr.io/home-assistant/base-python:3.12-alpine3.23

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY src ./src
COPY teams.json ./teams.default.json

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

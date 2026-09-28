# Runsite Web Service image for brAIndance
FROM python:3.12-slim

WORKDIR /app

COPY . .

ENV QUIZ_APP_HOST=0.0.0.0 \
    QUIZ_APP_PORT=8080 \
    QUIZ_NO_BROWSER=1

# Runsite health checks / expects the service on port 8080
EXPOSE 8080

CMD ["python", "testapp.py"]
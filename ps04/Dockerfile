FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY static ./static
ENV PS04_DATA_DIR=/data PS04_HOST=0.0.0.0 PS04_PORT=8000
VOLUME /data
EXPOSE 8000
# PS04_SECRET, PS04_ADMIN_EMAIL, PS04_ADMIN_PASSWORD must be supplied at run time
# (the app refuses to start without PS04_SECRET).
CMD ["python", "-m", "app", "serve"]

# PLACEHOLDER for the ingestion worker. It only proves that the image builds and
# starts. Installing dependencies and the real entrypoint arrive with the first
# code, batch 1.1.
FROM python:3.12-slim

# Never run as root inside the container.
RUN useradd --create-home --uid 10001 app
USER app
WORKDIR /home/app

CMD ["python", "-c", "print('PetrIA-Ingest: placeholder image, no app yet')"]

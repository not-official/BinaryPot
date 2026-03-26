FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r honeypot/requirements.txt

# Expose FastAPI (8000) and SSH honeypot (22)
# EXPOSE 8000 22
EXPOSE 22

ENV PYTHONUNBUFFERED=1

# Run honeypot and FastAPI together
# CMD ["bash", "-c", "python honeypot.py & exec uvicorn api:app --host 0.0.0.0 --port 8000"]
CMD ["bash", "-c", "python honeypot.py"]

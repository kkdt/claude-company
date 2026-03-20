FROM python:3.12-slim

WORKDIR /app

COPY pip.conf /etc/pip.conf
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/
COPY static/ static/
COPY employees.csv .

RUN mkdir -p data

EXPOSE 8080

CMD ["python", "app.py"]

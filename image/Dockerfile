FROM python:3-alpine
WORKDIR /service
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . ./
ENTRYPOINT ["python3", "photos.py"]
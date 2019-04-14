FROM python:3.7
MAINTAINER Nurlan Farajov "coolinuxoid@gmail.com"
ADD app/. /app
WORKDIR /app
RUN pip3 install -r requirements.txt
ENTRYPOINT ["python3"]
CMD ["app.py"]

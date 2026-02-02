FROM python:3.11
COPY . /app
WORKDIR /app
RUN pip install -e .
ENV INPERSO_FETCH_TYPE=""
CMD ["sh", "-c", "inperso-retrieve $INPERSO_FETCH_TYPE"]

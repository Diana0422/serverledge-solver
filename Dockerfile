# syntax=docker/dockerfile:1
FROM python:3.9-alpine

WORKDIR /usr/serverledge-solver

COPY requirements.txt requirements.txt
COPY config.properties config.properties
COPY src/proto src/proto

RUN apk update
RUN apk add glpk-dev
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY src ./src

RUN python3 -m grpc_tools.protoc -I src/proto --python_out=. --pyi_out=. --grpc_python_out=. src/proto/*.proto --experimental_allow_proto3_optional

EXPOSE 2500
CMD python3 -u src/__main__.py
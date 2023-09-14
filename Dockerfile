# syntax=docker/dockerfile:1
FROM python:3.9

WORKDIR /usr/src

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY src/proto proto
# RUN python3 -m grpc_tools.protoc -I proto --python_out=. --pyi_out=. --grpc_python_out=. proto/*.proto --experimental_allow_proto3_optional

COPY src .

EXPOSE 2500
CMD python3 -u __main__.py
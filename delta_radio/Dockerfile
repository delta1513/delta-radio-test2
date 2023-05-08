# syntax=docker/dockerfile:1
FROM python:3.10-alpine

WORKDIR /delta_radio
COPY . .

WORKDIR /
RUN apk add --no-cache git gcc musl-dev linux-headers pkgconfig ffmpeg ffmpeg-dev libsm-dev opus-dev libvpx-dev libsrtp-dev
RUN pip install -r delta_radio/requirements.txt

CMD ["python", "-m", "delta_radio"]

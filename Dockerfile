FROM node:16-alpine as jsbuilder
WORKDIR /usr/src/js
COPY example/package.json example/package-lock.json /usr/src/js/
RUN npm install
COPY example/vite.config.js /usr/src/js/
COPY example/frontend /usr/src/js/frontend
RUN npm run build

# -----

FROM python:3.10.11-slim-bullseye

WORKDIR /usr/src/app

ENV PYTHONUNBUFFERED="true"

COPY example/requirements.txt .
RUN pip install -r requirements.txt

COPY example/ ./

COPY --from=jsbuilder /usr/src/js/build /usr/src/app/build

RUN python ./manage.py collectstatic --noinput --clear

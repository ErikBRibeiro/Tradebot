FROM continuumio/miniconda3:24.3.0-0 AS anaconda-build

RUN /opt/conda/bin/conda install jupyter -y --quiet

RUN mkdir /opt/notebooks && \
    chmod -R 777 /opt/notebooks

WORKDIR /opt/notebooks

COPY tradebot_alpha.ipynb .
COPY src src

RUN ["/opt/conda/bin/jupyter", "nbconvert", "--to", "script", "tradebot_alpha.ipynb" ]

FROM python:3.9-alpine

LABEL Maintainer="Valmir Barbosa"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --from=anaconda-build /opt/notebooks/tradebot_alpha.py .
COPY --from=anaconda-build /opt/notebooks/src src

RUN mkdir data

EXPOSE 8000

CMD ["python", "tradebot_alpha.py"]

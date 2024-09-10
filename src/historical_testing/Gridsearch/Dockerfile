FROM continuumio/miniconda3:24.3.0-0 AS anaconda-build

RUN /opt/conda/bin/conda install jupyter -y --quiet

RUN mkdir /opt/notebooks && \
    chmod -R 777 /opt/notebooks

WORKDIR /opt/notebooks

COPY gridsearch.ipynb .

RUN ["/opt/conda/bin/jupyter", "nbconvert", "--to", "script", "gridsearch.ipynb" ]


FROM python:3.10-slim

LABEL Maintainer="TradeBot"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY --from=anaconda-build /opt/notebooks/gridsearch.py .

RUN mkdir data

EXPOSE 8000

CMD ["python3", "gridsearch.py"]

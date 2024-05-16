# Use a imagem base do Ubuntu
FROM ubuntu:latest

# Atualize os pacotes do sistema operacional
RUN apt-get update -y && apt-get upgrade -y

# Instale dependências necessárias
RUN apt-get install -y wget bzip2

# Defina o diretório de trabalho
WORKDIR /tmp

# Baixe o instalador do Anaconda
RUN wget https://repo.anaconda.com/archive/Anaconda3-2021.05-Linux-x86_64.sh

# Execute o instalador do Anaconda
RUN bash Anaconda3-2021.05-Linux-x86_64.sh -b

# Adicione o Anaconda ao PATH
ENV PATH /root/anaconda3/bin:$PATH

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# COPY ./tradebot_alpha.ipynb /tmp/tradebot_alpha.ipynb

RUN conda install -y -c conda-forge notebook

# Verifique a instalação
RUN conda --version

# jupyter nbconvert --to script tradebot_alpha.ipynb

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações gerais
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

if not API_KEY or not API_SECRET:
    raise ValueError("API Key ou API Secret não encontrada. Verifique o arquivo .env.")

SYMBOL = "BTCUSDT"
QUANTITY = 0.0011  # A quantidade de BTC transacionada fixa
INTERVAL = '5m'  # O intervalo de tempo das velas
SETUP = "9.1"  # Identificador do setup de trading

import os
import asyncio
import json
import time
from datetime import datetime, timedelta
import websockets
from dotenv import load_dotenv
import pandas as pd


class Deriv:
    def __init__(self):
        load_dotenv()
        
        self.app_id = os.getenv('DERIV_APP_ID', '1089')
        self.ws_url = f"wss://ws.derivws.com/websockets/v3?app_id={self.app_id}"
        
        # Tokens
        self.token_demo = os.getenv('DERIV_TOKEN_DEMO')
        self.token_real = os.getenv('DERIV_TOKEN_REAL')
        
        self.active_token = None
        self.account_type = None

        self.symbol = 'R_100'
        self.timeframe_str = '1h'
        self.timeframe_sec = self._parse_timeframe(self.timeframe_str)
        self.days = 365 * 4
        self.csv_filename = f'{self.symbol.lower()}_{self.timeframe_str}_historical_data.csv'
        self.data = None

        # Testa a conexão ao instanciar a classe
        
    def _parse_timeframe(self, tf: str) -> int:
        multipliers = {'m': 60, 'h': 3600, 'd': 86400}
        try:
            return int(tf[:-1]) * multipliers[tf[-1].lower()]
        except (KeyError, ValueError):
            raise ValueError(f"Timeframe inválido: {tf}")

    def set_account_mode(self, mode: str):
        """Define qual token usar (demo ou real)"""
        mode = mode.lower()
        if mode == 'real':
            if not self.token_real:
                raise ValueError("DERIV_TOKEN_REAL não encontrado no .env")
            self.active_token = self.token_real
        elif mode == 'demo':
            if not self.token_demo:
                raise ValueError("DERIV_TOKEN_DEMO não encontrado no .env")
            self.active_token = self.token_demo
        else:
            raise ValueError("Modo inválido. Use 'demo' ou 'real'.")
            
        self.account_type = mode
        print(f"✅ Modo alterado para: {mode.upper()}")

    async def test_connection(self):
        """Testa a conexão e autenticação com o token ativo (demo ou real)"""
        if not self.token_demo and not self.token_real:
            print("⚠️ Nenhum token encontrado no .env")
            return False

        # Tenta primeiro com DEMO, depois com REAL se não tiver demo
        token_to_test = self.token_demo or self.token_real
        mode = "demo" if self.token_demo else "real"

        try:
            async with websockets.connect(self.ws_url) as ws:
                print(f"🔗 Conectado ao WebSocket (App ID: {self.app_id})")

                # Autorização
                await ws.send(json.dumps({"authorize": token_to_test}))
                auth_response = json.loads(await ws.recv())

                if 'error' in auth_response:
                    err = auth_response['error']
                    print(f"❌ Falha na autenticação ({mode.upper()}): {err.get('message')}")
                    print(f"Código do erro: {err.get('code')}")
                    return False

                account = auth_response.get('authorize', {})
                print(f"✅ Conexão + Autenticação OK!")
                print(f"   Conta: {account.get('loginid')} | Moeda: {account.get('currency')} | Saldo: {account.get('balance')}")
                print(f"   Modo testado: {mode.upper()}\n")
                return True

        except Exception as e:
            print(f"❌ Erro na conexão: {e}")
            return False

    async def execute_trade(self, symbol: str, contract_type: str, stake: float, duration: int, duration_unit: str = 'm'):
        if not self.active_token:
            raise RuntimeError("Chame set_account_mode('demo' ou 'real') antes de operar.")

        async with websockets.connect(self.ws_url) as ws:
            # Autenticação
            await ws.send(json.dumps({"authorize": self.active_token}))
            auth_response = json.loads(await ws.recv())

            if 'error' in auth_response:
                print(f"Erro de autenticação: {auth_response['error']['message']}")
                return None

            account_info = auth_response['authorize']

            # Envia ordem
            trade_request = {
                "buy": 1,
                "price": stake,
                "parameters": {
                    "amount": stake,
                    "basis": "stake",
                    "contract_type": contract_type.upper(),
                    "currency": account_info['currency'],
                    "duration": duration,
                    "duration_unit": duration_unit,
                    "symbol": symbol
                }
            }

            await ws.send(json.dumps(trade_request))
            trade_response = json.loads(await ws.recv())

            if 'error' in trade_response:
                print(f"Erro na ordem: {trade_response['error']['message']}")
                return None

            receipt = trade_response['buy']
            print(f"✅ Ordem executada! ID: {receipt['transaction_id']}")
            return receipt

    def fetch_deriv_data(self, symbol: str = None, days: int = None, timeframe: str = None):
        """Busca dados históricos (não precisa de autenticação)"""
        if symbol: 
            self.symbol = symbol
        if days: 
            self.days = days
        if timeframe:
            self.timeframe_str = timeframe
            self.timeframe_sec = self._parse_timeframe(timeframe)

        self.csv_filename = f'{self.symbol.lower()}_{self.timeframe_str}_historical_data.csv'

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days)
        
        all_candles = asyncio.run(self._ws_fetch_loop(
            int(start_date.timestamp()), 
            int(end_date.timestamp())
        ))

        if not all_candles:
            print("Nenhum dado recebido.")
            return

        df = pd.DataFrame(all_candles)
        df.rename(columns={
            'epoch': 'Open time', 
            'open': 'Open', 
            'high': 'High', 
            'low': 'Low', 
            'close': 'Close'
        }, inplace=True)
        
        if 'tick_volume' in df.columns:
            df.rename(columns={'tick_volume': 'Volume'}, inplace=True)
        else:
            df['Volume'] = 0.0

        df['Open time'] = pd.to_datetime(df['Open time'], unit='s')
        df = df[['Open time', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df[ ['Open', 'High', 'Low', 'Close', 'Volume'] ] = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)

        df.drop_duplicates(subset=['Open time'], inplace=True)
        df.sort_values('Open time', inplace=True)
        df.reset_index(drop=True, inplace=True)

        df.to_csv(self.csv_filename, index=False)
        self.data = df
        print(f"✅ Dados salvos em: {self.csv_filename} ({len(df)} candles)")
        return df

    async def _ws_fetch_loop(self, start_ts: int, end_ts: int):
        candles = []
        current_start = start_ts

        async with websockets.connect(self.ws_url) as ws:
            while current_start < end_ts:
                request = {
                    "ticks_history": self.symbol,
                    "start": str(current_start),
                    "end": str(end_ts),
                    "style": "candles",
                    "granularity": self.timeframe_sec,
                    "count": 5000
                }
                await ws.send(json.dumps(request))
                response = json.loads(await ws.recv())

                if 'error' in response:
                    print(f"Erro ao buscar candles: {response['error']['message']}")
                    break

                chunk = response.get('candles', [])
                if not chunk:
                    break

                candles.extend(chunk)
                current_start = chunk[-1]['epoch'] + self.timeframe_sec
                await asyncio.sleep(0.2)  # evitar rate limit

        return candles
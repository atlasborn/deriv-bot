import os
import asyncio
import json
from dotenv import load_dotenv
import websockets


class DerivAPIClient:
    def __init__(self, app_id: str):
        self.app_id = int(app_id.strip())
        self.ws = None
        self.req_id = 0

    async def connect(self):
        """Conecta ao WebSocket da Deriv"""
        url = f"wss://ws.derivws.com/websockets/v3?app_id={self.app_id}"
        self.ws = await websockets.connect(url)
        print(f"✅ Conectado ao WebSocket (App ID: {self.app_id})")

    async def send_request(self, req: dict):
        """Envia requisição e aguarda resposta"""
        self.req_id += 1
        req["req_id"] = self.req_id

        await self.ws.send(json.dumps(req))
        response = await self.ws.recv()
        return json.loads(response)

    async def authorize(self, token: str):
        """Autoriza a sessão"""
        req = {"authorize": token}
        return await self.send_request(req)

    async def close(self):
        """Fecha a conexão"""
        if self.ws:
            await self.ws.close()
            print("🔌 Conexão WebSocket fechada.")


async def testar_conexao_deriv():
    load_dotenv()

    token = os.getenv("DERIV_TOKEN")
    app_id = os.getenv("DERIV_APP_ID")

    if not token:
        print("❌ ERRO: DERIV_TOKEN não encontrado no arquivo .env")
        return

    if not app_id:
        print("⚠️  DERIV_APP_ID não encontrado. Usando 1089 (teste)")
        app_id = "1089"

    client = DerivAPIClient('1089')

    try:
        await client.connect()

        print("🔑 Autorizando conta...")
        auth_response = await client.authorize(token.strip())

        if "error" in auth_response:
            print(f"❌ Erro na autorização: {auth_response['error']['message']}")
            return

        authorize = auth_response.get("authorize", {})

        print("\n" + "=" * 70)
        print("🎉 CONEXÃO E AUTENTICAÇÃO BEM-SUCEDIDAS!")
        print("=" * 70)
        print(f"Login ID:      {authorize.get('loginid')}")
        print(f"Moeda:         {authorize.get('currency')}")
        print(f"Saldo:         {authorize.get('balance')}")
        print(f"País:          {authorize.get('country')}")
        print(f"Nome:          {authorize.get('fullname') or 'N/A'}")
        print("=" * 70)

        # Exemplo extra: ping para testar conexão
        ping_resp = await client.send_request({"ping": 1})
        print(f"🏓 Ping response: {ping_resp.get('ping')}")

    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(testar_conexao_deriv())
from src.deriv import Deriv
from src.data_manager import DataManager, DataProcessor
import asyncio
import os
from src.ai import Models


async def home():
    deriv = Deriv()
    bot = Models('')
    predict = bot.predict(history)
    deriv.set_account_mode('demo')
    deriv.execute_trade(
        symbol='',
        contract_type=predict.contract_type,
        stake=1,
        duration=20,
        duration_unit='m'

    )
    
if __name__ == '__main__':
    asyncio.run(home())

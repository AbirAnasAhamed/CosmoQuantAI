import logging
import asyncio
from app.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class WallHunterFuturesStrategy(BaseStrategy):
    def __init__(self, bot_record, exchange_service):
        super().__init__(bot_record, exchange_service)
        # ফিউচার কনফিগারেশন লোড করা হচ্ছে
        self.config = bot_record.config
        self.leverage = self.config.get('leverage', 10)
        self.margin_mode = self.config.get('margin_mode', 'cross')
        self.reduce_only = self.config.get('reduce_only', True)
        self.market_symbol = bot_record.market

    async def initialize(self):
        """বট স্টার্ট হওয়ার সময় লেভারেজ এবং মার্জিন সেট করবে"""
        try:
            logger.info(f"[{self.bot_record.name}] Setting up Futures Market: Leverage {self.leverage}x, Mode: {self.margin_mode}")
            
            # CCXT এর মাধ্যমে এক্সচেঞ্জে ফিউচার সেটিংস পাঠানো
            await self.exchange_service.set_leverage(self.leverage, self.market_symbol)
            await self.exchange_service.set_margin_mode(self.margin_mode, self.market_symbol)
            
            # কলিং প্যারেন্ট ইনিশিয়ালাইজেশন
            await super().initialize()
            
        except Exception as e:
            logger.error(f"Failed to initialize Futures Settings for {self.market_symbol}: {str(e)}")
            raise e

    async def execute_trade(self, side, amount, price=None):
        """ফিউচার অর্ডারের জন্য স্পেসিফিক এক্সিকিউশন লজিক"""
        try:
            # ফিউচার মার্কেটের জন্য অতিরিক্ত প্যারামিটার (যেমন: Reduce-Only)
            extra_params = {}
            
            # যদি স্টপ-লস বা টেক-প্রফিট অর্ডার হয়, তবে reduceOnly অ্যাড করা হবে
            if self.reduce_only and side in ['sell', 'short_cover']:
                extra_params['reduceOnly'] = True

            logger.info(f"Executing Futures Order -> Side: {side}, Amount: {amount}, Params: {extra_params}")
            
            if price:
                order = await self.exchange_service.create_limit_order(
                    symbol=self.market_symbol, 
                    side=side, 
                    amount=amount, 
                    price=price, 
                    params=extra_params
                )
            else:
                order = await self.exchange_service.create_market_order(
                    symbol=self.market_symbol, 
                    side=side, 
                    amount=amount, 
                    params=extra_params
                )
            return order
            
        except Exception as e:
            logger.error(f"Futures Order Execution Failed: {str(e)}")
            return None

from web3 import Web3
import logging
import os

logger = logging.getLogger(__name__)

class ChainService:
    def __init__(self):
        # পাবলিক ফ্রি RPC ব্যবহার করছি (Cloudflare)
        self.rpc_url = "https://cloudflare-eth.com"
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.whale_threshold = 50  # 50 ETH এর বেশি হলে 'Smart Money' ধরব

    def get_smart_money_score(self):
        """
        Analyze recent block for whale activity (Smart Money).
        Returns a score between -1.0 (Bearish/Sell) to 1.0 (Bullish/Buy)
        """
        if not self.web3.is_connected():
            logger.error("❌ Blockchain Connection Failed")
            return 0

        try:
            # লেটেস্ট ব্লক আনব
            latest_block = self.web3.eth.get_block('latest', full_transactions=True)
            transactions = latest_block.transactions

            whale_volume = 0
            tx_count = 0
            
            # ব্লকের প্রথম ৫০টি ট্রানজেকশন চেক করব (বেশি করলে স্লো হবে)
            for tx in transactions[:50]:
                value_eth = float(self.web3.from_wei(tx['value'], 'ether'))
                
                if value_eth > self.whale_threshold:
                    whale_volume += value_eth
                    tx_count += 1
            
            # লজিক: যদি হোয়েল ভলিউম বেশি থাকে, স্মার্ট মানি অ্যাক্টিভ
            # কিন্তু ডিরেকশন (বাই/সেল) পাবলিক RPC দিয়ে বোঝা কঠিন, তাই আমরা ভলিউম ইনটেনসিটি ব্যবহার করব
            # হাই ভলিউম = হাই ইমপ্যাক্ট (আপাতত পজিটিভ হিসেবে ধরছি লিকুইডিটির জন্য)
            
            normalized_score = min(whale_volume / 500, 1.0) # 500 ETH ভলিউম হলে ১.০ স্কোর
            return round(normalized_score, 2)

        except Exception as e:
            logger.error(f"Smart Money Error: {e}")
            return 0

chain_service = ChainService()

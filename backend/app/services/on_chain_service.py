class OnChainService:
    def calculate_pressure(self, inflow: float, outflow: float) -> str:
        """
        Determines the market pressure based on inflow vs outflow.
        """
        if inflow > outflow:
            return "High Sell Pressure"  # Negative Sentiment
        elif outflow > inflow:
            return "Strong Buying Pressure"  # Positive Sentiment
        return "Neutral"

    def get_latest_metrics(self, symbol: str):
        """
        Returns mock/simulated data for now.
        """
        # Mock data simulation
        import random
        
        inflow = random.uniform(100.0, 500.0)
        outflow = random.uniform(100.0, 500.0)
        
        status = self.calculate_pressure(inflow, outflow)
        
        return {
            "symbol": symbol,
            "exchange_inflow_volume": round(inflow, 2),
            "exchange_outflow_volume": round(outflow, 2),
            "net_flow_status": status,
            "timestamp": "2023-10-27T10:00:00Z" # Mock timestamp, normally use datetime.now()
        }

on_chain_service = OnChainService()

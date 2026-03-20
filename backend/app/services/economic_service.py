from datetime import date

class EconomicDataService:
    def get_latest_indicators(self):
        """
        Returns structured macro-economic data.
        Currently using mock data as per requirements, but ready for API integration.
        """
        # Mock Data following the requested structure
        # Logic:
        # - CPI: Inflation. Lower is Bullish (good for liquidity/rates).
        # - NFP: Employment. Higher is generally Bullish for economy but might be Bearish for rates (Fed tightening).
        #   However, prompts usually simplify: Strong Econ = Bullish Stocks. OR Bad Econ = Fed Pivot (Bullish Crypto).
        #   The prompt specifically says: "Bullish: Better than expected (e.g., Lower Inflation). Bearish: Worse than expected (e.g., Higher Unemployment)."
        #   Wait, "Higher Unemployment" as Bearish example implies user thinks Unemployment = Bad.
        #   And "Lower Inflation" as Bullish example.
        #   So I will follow this convention in my mental model, but since I am just returning data + "Impact" string,
        #   and the specific logic of green/red is in the frontend using Actual vs Forecast comparisons.
        
        # Structure:
        # { "event": "...", "actual": "...", "forecast": "...", "previous": "...", "impact": "High", "date": "...", "status": "..." }

        return [
            {
                "event": "CPI (YoY)",
                "actual": "3.2%",
                "forecast": "3.3%",
                "previous": "3.4%",
                "impact": "High",
                "date": "2026-02-12",
                "status": "Published"
            },
            {
                "event": "Core Inflation Rate",
                "actual": "2.8%",
                "forecast": "3.0%",
                "previous": "3.1%",
                "impact": "High",
                "date": "2026-02-12",
                "status": "Published"
            },
            {
                "event": "Non-Farm Payrolls",
                "actual": "180K",
                "forecast": "170K",
                "previous": "150K",
                "impact": "High",
                "date": "2026-02-06",
                "status": "Published"
            },
            {
                "event": "Unemployment Rate",
                "actual": "4.1%",
                "forecast": "4.2%",
                "previous": "4.3%",
                "impact": "Medium",
                "date": "2026-02-06",
                "status": "Published"
            },
            {
                "event": "Fed Interest Rate",
                "actual": None,
                "forecast": "5.25%",
                "previous": "5.50%",
                "impact": "High",
                "date": "2026-03-20",
                "status": "Upcoming"
            },
            {
                "event": "GDP Growth Rate",
                "actual": None,
                "forecast": "2.4%",
                "previous": "2.1%",
                "impact": "High",
                "date": "2026-03-28",
                "status": "Upcoming"
            },
            {
                "event": "PPI (Producer Price Index)",
                "actual": "0.4%",
                "forecast": "0.3%",
                "previous": "0.2%",
                "impact": "Medium",
                "date": "2026-02-15",
                "status": "Published"
            }
        ]

economic_service = EconomicDataService()

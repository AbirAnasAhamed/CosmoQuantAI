
import asyncio
import queue
from datetime import datetime
from typing import List, Dict, Optional, Callable
from .events import Event, EventType, MarketEvent, SignalEvent, OrderEvent, FillEvent
from fastapi import WebSocket

class DataHandler:
    """
    Simulates a live market feed by dripping historical data.
    For this implementation, we will generate synthetic random walk data
    to verify the event loop.
    """
    def __init__(self, symbol: str, events: asyncio.Queue):
        self.symbol = symbol
        self.events = events
        self.continue_backtest = True

    async def stream_data(self):
        """
        Generates synthetic market data and puts it into the queue.
        """
        price = 100.0
        import random
        
        # Simulate 100 bars for testing
        for i in range(100):
            if not self.continue_backtest:
                break
                
            await asyncio.sleep(1) # Simulate time delay for "Live" feeling
            
            # Random Walk
            move = random.uniform(-1.0, 1.0)
            price += move
            
            # Create Market Event
            event = MarketEvent(
                symbol=self.symbol,
                date=datetime.now(),
                open_price=price,
                high=price + 0.5,
                low=price - 0.5,
                close=price + 0.1,
                volume=random.randint(100, 1000)
            )
            
            await self.events.put(event)

class EventDrivenEngine:
    def __init__(self, symbol: str, websocket: WebSocket = None):
        self.events = asyncio.Queue()
        self.symbol = symbol
        self.data_handler = DataHandler(symbol, self.events)
        self.websocket = websocket
        self.running = False

    async def run(self):
        """
        Main Event Loop.
        """
        self.running = True
        
        # Start Data Feed in background
        asyncio.create_task(self.data_handler.stream_data())
        
        print("Starting Event Loop...")
        if self.websocket:
            await self.websocket.send_json({"type": "SYSTEM", "message": "Simulation Started"})

        while self.running:
            try:
                event = await self.events.get()
            except asyncio.QueueEmpty:
                continue

            if event is None:
                break

            if event.type == EventType.MARKET:
                await self.handle_market_event(event)
            elif event.type == EventType.SIGNAL:
                await self.handle_signal_event(event)

            elif event.type == EventType.ORDER:
                await self.handle_order_event(event)

            elif event.type == EventType.FILL:
                await self.handle_fill_event(event)

    # ... (handlers remain unchanged) ...

    def stop(self):
        self.running = False
        try:
            self.events.put_nowait(None)
        except asyncio.QueueFull:
            pass

    async def handle_market_event(self, event: MarketEvent):
        # 1. Send Market Data to Frontend
        if self.websocket:
            await self.websocket.send_json({
                "type": "MARKET",
                "symbol": event.symbol,
                "price": event.close,
                "time": event.date.isoformat()
            })
            
        # 2. Simulate Strategy interacting (Simple Moving Average Logic Placeholder)
        # For demonstration: Generate a random signal every 5th market event
        import random
        if random.random() > 0.8:
            signal_type = "LONG" if random.random() > 0.5 else "SHORT"
            signal = SignalEvent(
                strategy_id="SimStrategy",
                symbol=event.symbol,
                datetime=datetime.now(),
                signal_type=signal_type
            )
            await self.events.put(signal)

    async def handle_signal_event(self, event: SignalEvent):
        if self.websocket:
            await self.websocket.send_json({
                "type": "LOG",
                "message": f"Signal Received: {event.signal_type} on {event.symbol}"
            })
            
        # Simulate Portfolio Manager generating an Order
        order = OrderEvent(
            symbol=event.symbol,
            order_type="MKT",
            quantity=1, # Fixed qty
            direction="BUY" if event.signal_type == "LONG" else "SELL"
        )
        await self.events.put(order)

    async def handle_order_event(self, event: OrderEvent):
         if self.websocket:
            await self.websocket.send_json({
                "type": "LOG",
                "message": f"Order Placed: {event.direction} {event.quantity} {event.symbol}"
            })
         
         # Simulate Execution Handler filling the order immediately
         # In real life, this would go to a broker API
         fill = FillEvent(
             timestamp=datetime.now(),
             symbol=event.symbol,
             exchange="SIM_EXCHANGE",
             quantity=event.quantity,
             direction=event.direction,
             fill_cost=100.0, # Simplified
             commission=1.5
         )
         await self.events.put(fill)

    async def handle_fill_event(self, event: FillEvent):
        if self.websocket:
            await self.websocket.send_json({
                "type": "FILL",
                "symbol": event.symbol,
                "direction": event.direction,
                "quantity": event.quantity,
                "price": event.fill_cost,
                "commission": event.commission
            })
            await self.websocket.send_json({
                "type": "LOG",
                "message": f"Order Filled: {event.direction} {event.quantity} @ {event.fill_cost}"
            })
            
    def stop(self):
        self.running = False

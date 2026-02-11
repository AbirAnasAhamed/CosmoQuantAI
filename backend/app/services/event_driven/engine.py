import asyncio
import queue
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
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
        self.current_time = datetime.now() # Start time

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
                
            # Simulate time passing (1 second per event)
            self.current_time += timedelta(seconds=1)
            
            # Random Walk
            move = random.uniform(-1.0, 1.0)
            price += move
            
            # Create Market Event
            event = MarketEvent(
                symbol=self.symbol,
                date=self.current_time,
                open_price=price,
                high=price + 0.5,
                low=price - 0.5,
                close=price + 0.1,
                volume=random.randint(100, 1000)
            )
            
            await self.events.put(event)
            # No sleep here! Speed is controlled by the Engine.

class EventDrivenEngine:
    def __init__(self, symbol: str, websocket: WebSocket = None):
        self.events = asyncio.Queue()
        self.symbol = symbol
        self.data_handler = DataHandler(symbol, self.events)
        self.websocket = websocket
        self.running = False
        self.speed_multiplier: Optional[float] = None # None or 0 means Max Speed
        self.last_event_time: Optional[datetime] = None
        self.data_task: Optional[asyncio.Task] = None

    def set_speed(self, speed: float):
        """
        Updates the playback speed dynamically.
        0 or None means "Max Speed" (no delay).
        1.0 means Real-time (1 second in data = 1 second in reality).
        10.0 means 10x speed (1 second in data = 0.1 second in reality).
        """
        if speed <= 0:
            self.speed_multiplier = None
        else:
            self.speed_multiplier = speed
        print(f"Speed set to: {self.speed_multiplier if self.speed_multiplier else 'MAX'}", flush=True)

    async def process_command(self, command: Dict[str, Any]):
        """
        Handles commands from WebSocket or API.
        """
        if command.get("type") == "UPDATE_SPEED":
            speed = float(command.get("speed", 0))
            self.set_speed(speed)
            await self._send({"type": "SYSTEM", "message": f"Speed set to {speed}x"})

    async def _send(self, data: Dict[str, Any]):
        """Helper to send WebSocket messages safely."""
        if self.websocket:
            try:
                await self.websocket.send_json(data)
            except Exception as e:
                print(f"Error sending WS message: {e}", flush=True)

    async def run(self):
        """
        Main Event Loop.
        """
        self.running = True
        self.last_event_time = None
        
        # Start Data Feed in background
        self.data_task = asyncio.create_task(self.data_handler.stream_data())
        
        print("Starting Event Loop...", flush=True)
        await self._send({"type": "SYSTEM", "message": "Simulation Started"})

        while self.running:
            try:
                # Check for new events
                # Use a timeout to allow checking for other things if needed, though get() is fine
                event = await self.events.get()
            except asyncio.QueueEmpty:
                continue

            if event is None:
                break
            
            # --- Throttle Logic ---
            if hasattr(event, 'date') and event.date:
                current_event_time = event.date
                
                if self.last_event_time and self.speed_multiplier:
                    # Calculate simulation time difference
                    sim_diff = (current_event_time - self.last_event_time).total_seconds()
                    
                    if sim_diff > 0:
                        # Calculate real sleep time
                        real_sleep = sim_diff / self.speed_multiplier
                        await asyncio.sleep(real_sleep)
                
                self.last_event_time = current_event_time
            # ----------------------

            if event.type == EventType.MARKET:
                await self.handle_market_event(event)
            elif event.type == EventType.SIGNAL:
                await self.handle_signal_event(event)

            elif event.type == EventType.ORDER:
                await self.handle_order_event(event)

            elif event.type == EventType.FILL:
                await self.handle_fill_event(event)

        print("Event Loop Finished.", flush=True)
        await self._send({"type": "SYSTEM", "message": "Simulation Finished"})

    # ... (handlers remain unchanged) ...

    def stop(self):
        print("Stopping Event Loop...", flush=True)
        self.running = False
        
        if self.data_task:
            self.data_task.cancel()

        # Drain the queue to ensure immediate stop
        while not self.events.empty():
            try:
                self.events.get_nowait()
            except asyncio.QueueEmpty:
                break
                
        try:
            self.events.put_nowait(None)
        except asyncio.QueueFull:
            pass

    async def handle_market_event(self, event: MarketEvent):
        # 1. Send Market Data to Frontend
        await self._send({
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
        await self._send({
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
         await self._send({
            "type": "LOG",
            "message": f"Order Placing: {event.direction} {event.quantity} {event.symbol}"
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
        await self._send({
            "type": "FILL",
            "symbol": event.symbol,
            "direction": event.direction,
            "quantity": event.quantity,
            "price": event.fill_cost,
            "commission": event.commission
        })
        await self._send({
            "type": "LOG",
            "message": f"Order Filled: {event.direction} {event.quantity} @ {event.fill_cost}"
        })
            
    def stop(self):
        self.running = False

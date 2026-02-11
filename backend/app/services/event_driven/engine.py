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

class SimulationStrategy:
    """
    A simple strategy for the simulation engine that supports hot-reloading parameters.
    """
    def __init__(self):
        # Default Parameters
        self.params = {
            "stop_loss": 0.01,   # 1%
            "take_profit": 0.02, # 2%
            "buy_probability": 0.2 # 20% chance to buy on signal check
        }
        print(f"Strategy Initialized with: {self.params}", flush=True)

    def update_parameters(self, new_params: dict):
        """
        Updates parameters safely.
        """
        for key, value in new_params.items():
            if key in self.params:
                # Basic validation (e.g. correct type)
                try:
                    # Convert to float if it's a number
                    if isinstance(self.params[key], float):
                        self.params[key] = float(value)
                    else:
                        self.params[key] = value
                    print(f"Updated {key} to {self.params[key]}", flush=True)
                except ValueError:
                    print(f"Invalid value for {key}: {value}", flush=True)
            else:
                print(f"Ignoring unknown parameter: {key}", flush=True)

    def calculate_signal(self, event: MarketEvent) -> Optional[SignalEvent]:
        """
        Determines if a signal should be generated based on current market data and parameters.
        """
        import random
        
        # Simple Logic: Randomly generate signal based on buy_probability
        # in a real strategy, this would check indicators
        if random.random() < self.params["buy_probability"]:
            signal_type = "LONG" if random.random() > 0.5 else "SHORT"
            
            return SignalEvent(
                strategy_id="SimHotReload",
                symbol=event.symbol,
                datetime=datetime.now(),
                signal_type=signal_type,
                strength=1.0
            )
        return None

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
        
        # Pause & Step Control
        self.is_paused = False
        self.step_trigger = asyncio.Event()

        # Strategy Instance
        self.strategy = SimulationStrategy()

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
        cmd_type = command.get("type")
        
        if cmd_type == "UPDATE_SPEED":
            speed = float(command.get("speed", 0))
            self.set_speed(speed)
            await self._send({"type": "SYSTEM", "message": f"Speed set to {speed}x"})
            
        elif cmd_type == "PAUSE":
            self.pause()
            await self._send({"type": "SYSTEM", "message": "Simulation Paused"})
            
        elif cmd_type == "RESUME":
            self.resume()
            await self._send({"type": "SYSTEM", "message": "Simulation Resumed"})
            
        elif cmd_type == "STEP":
            self.step()

        elif cmd_type == "UPDATE_PARAMS":
            new_params = command.get("params", {})
            self.strategy.update_parameters(new_params)
            await self._send({"type": "SYSTEM", "message": f"Strategy Params Updated: {new_params}"})

    async def _send(self, data: Dict[str, Any]):
        """Helper to send WebSocket messages safely."""
        if self.websocket:
            try:
                await self.websocket.send_json(data)
            except Exception as e:
                print(f"Error sending WS message: {e}", flush=True)

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False
        self.step_trigger.set()

    def step(self):
        self.step_trigger.set()

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
            # --- Pause Logic ---
            if self.is_paused:
                await self._send({"type": "PAUSED_STATE", "value": True}) # Notify UI
                await self.step_trigger.wait()
                self.step_trigger.clear()
                await self._send({"type": "PAUSED_STATE", "value": False}) 
            # -------------------

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
        self.is_paused = False # Unpause to allow exit
        self.step_trigger.set() # Wake up if waiting
        
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
            
        # 2. Simulate Strategy interacting via Strategy Class
        signal = self.strategy.calculate_signal(event)
        if signal:
             await self.events.put(signal)

    async def handle_signal_event(self, event: SignalEvent):
        await self._send({
            "type": "LOG",
            "message": f"Signal Received: {event.signal_type} on {event.symbol}"
        })
            
        # Simulate Portfolio Manager generating an Order
        # Use simple risk logic relative to current price or hardcoded
        # Here we just blindly follow signal
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
             fill_cost=100.0, # Simplified (should use current price but for sim we use placeholder)
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

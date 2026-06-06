import asyncio
import websockets
import json
import pandas as pd
import os
import time
from datetime import datetime
import argparse

# Configuration
SYMBOL = "btcusdt"
DEPTH_LEVELS = 20
UPDATE_SPEED = "100ms"
CHUNK_SIZE = 20000

# Calculate paths relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data", "raw", "l2_snapshots")

async def collect_l2_data(target_rows: int, symbol: str = SYMBOL):
    url = f"wss://stream.binance.com:9443/ws/{symbol}@depth{DEPTH_LEVELS}@{UPDATE_SPEED}"
    
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    buffer = []
    total_collected = 0
    chunk_index = 0
    chunk_files = []

    print(f"[{datetime.now()}] Starting L2 Collector for {symbol.upper()}")
    print(f"Target: {target_rows:,} rows. Saving to: {DATA_DIR}")

    try:
        async with websockets.connect(url) as websocket:
            while total_collected < target_rows:
                msg = await websocket.recv()
                data = json.loads(msg)
                
                # Format the data
                timestamp = pd.Timestamp.now()
                row = {"timestamp": timestamp}
                
                # Extract Top 20 Bids and Asks
                bids = data.get("bids", [])
                asks = data.get("asks", [])
                
                for i in range(DEPTH_LEVELS):
                    if i < len(bids):
                        row[f"bid_price_{i+1}"] = float(bids[i][0])
                        row[f"bid_volume_{i+1}"] = float(bids[i][1])
                    else:
                        row[f"bid_price_{i+1}"] = None
                        row[f"bid_volume_{i+1}"] = None
                        
                    if i < len(asks):
                        row[f"ask_price_{i+1}"] = float(asks[i][0])
                        row[f"ask_volume_{i+1}"] = float(asks[i][1])
                    else:
                        row[f"ask_price_{i+1}"] = None
                        row[f"ask_volume_{i+1}"] = None

                buffer.append(row)
                total_collected += 1

                # Save chunk if buffer is full or target reached
                if len(buffer) >= CHUNK_SIZE or total_collected >= target_rows:
                    chunk_index += 1
                    df = pd.DataFrame(buffer)
                    chunk_filename = os.path.join(DATA_DIR, f"{symbol}_temp_chunk_{session_id}_{chunk_index}.parquet")
                    df.to_parquet(chunk_filename, index=False)
                    chunk_files.append(chunk_filename)
                    print(f"[{datetime.now()}] Saved chunk {chunk_index} ({len(buffer)} rows). Total: {total_collected:,}/{target_rows:,}")
                    buffer.clear() # Clear memory
                    
    except asyncio.CancelledError:
        print("Collection task was cancelled.")
    except Exception as e:
        print(f"Error during WebSocket collection: {e}")

    # Merge Process
    if chunk_files:
        print(f"[{datetime.now()}] Target reached. Merging {len(chunk_files)} chunks...")
        try:
            dfs = [pd.read_parquet(f) for f in chunk_files]
            final_df = pd.concat(dfs, ignore_index=True)
            
            final_filename = os.path.join(DATA_DIR, f"{symbol.upper()}_L2_{target_rows}_{session_id}.parquet")
            final_df.to_parquet(final_filename, index=False)
            print(f"[{datetime.now()}] Final file saved successfully: {final_filename}")
            
            # Cleanup
            print("Cleaning up temporary chunk files...")
            for f in chunk_files:
                try:
                    os.remove(f)
                except Exception as e:
                    print(f"Failed to delete {f}: {e}")
            print("Cleanup complete.")
            
        except Exception as e:
            print(f"Error during merge process: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="L2 Orderbook Data Collector")
    parser.add_argument("--target", type=int, default=200000, help="Total number of rows to collect")
    parser.add_argument("--symbol", type=str, default="btcusdt", help="Trading pair symbol")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(collect_l2_data(args.target, args.symbol))
    except KeyboardInterrupt:
        print("\nCollector stopped manually.")

"""
Bracket Order Service
=====================
Entry order fill হওয়ার পর স্বয়ংক্রিয়ভাবে opposite Take-Profit এবং Stop-Loss order place করে।
Trailing Stop (Native & Synthetic) সাপোর্ট করে।
Background asyncio task হিসেবে চলে — main request কে block করে না।
"""

import asyncio
import logging
from app.services.exchange_pool import get_or_create_exchange
from app.core.security import decrypt_key
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)

class BracketOrderService:
    @staticmethod
    async def monitor_and_execute_bracket(
        api_key_record,
        entry_order_id: str,
        symbol: str,
        side: str,          # Entry side ('buy' or 'sell')
        amount: float,
        is_futures: bool,
        tp_config: dict = None,
        sl_config: dict = None,
        trailing_config: dict = None,
        initial_entry_price: float = 0.0,
        user_id: int = 0,
    ):
        try:
            decrypted_api_key = decrypt_key(api_key_record.api_key)
            decrypted_secret  = decrypt_key(api_key_record.secret_key)
            raw_pp = getattr(api_key_record, 'passphrase', None)
            passphrase = decrypt_key(raw_pp) if raw_pp else None

            exchange = await get_or_create_exchange(
                api_key_id=api_key_record.id,
                exchange_name=api_key_record.exchange,
                decrypted_api_key=decrypted_api_key,
                decrypted_secret=decrypted_secret,
                is_futures=is_futures,
                passphrase=passphrase
            )

            timeout_mins = 5
            if tp_config and tp_config.get('timeout_mins'):
                timeout_mins = tp_config['timeout_mins']

            timeout_iters = int((timeout_mins * 60) / 2)

            logger.info(f"🛡️ Bracket Monitor started | Order: {entry_order_id} | Symbol: {symbol}")

            filled_amount  = 0.0
            average_price  = 0.0
            order_closed   = False

            for _ in range(timeout_iters):
                await asyncio.sleep(2)
                try:
                    order_status = await exchange.fetch_order(entry_order_id, symbol)
                    status = order_status.get('status', '').lower()

                    if status in ('closed', 'filled'):
                        filled_amount = float(order_status.get('filled') or amount)
                        average_price = float(order_status.get('average') or order_status.get('price') or initial_entry_price)
                        order_closed = True
                        break
                    elif status in ('canceled', 'cancelled', 'expired', 'rejected'):
                        filled = float(order_status.get('filled') or 0.0)
                        if filled > 0:
                            filled_amount = filled
                            average_price = float(order_status.get('average') or order_status.get('price') or initial_entry_price)
                            order_closed = True
                        break
                    elif status in ('open', 'new'):
                        filled = float(order_status.get('filled') or 0.0)
                        if filled >= amount * 0.99:
                            filled_amount = filled
                            average_price = float(order_status.get('average') or order_status.get('price') or initial_entry_price)
                            order_closed = True
                            break
                except Exception as poll_e:
                    logger.debug(f"Bracket Monitor poll error (non-fatal): {poll_e}")

            if not order_closed:
                if filled_amount > 0:
                    order_closed = True
                else:
                    logger.warning(f"⏰ Bracket Monitor: Entry {entry_order_id} timed out. Aborting.")
                    return

            logger.info(f"🎯 Bracket Monitor: Entry filled {filled_amount} @ {average_price}. Spawning Bracket...")

            # Calculate Prices
            tp_side = 'sell' if side.lower() == 'buy' else 'buy'
            final_amount = float(exchange.amount_to_precision(symbol, filled_amount)) if hasattr(exchange, 'amount_to_precision') else filled_amount
            
            tp_price = None
            sl_price = None

            if tp_config:
                val = float(tp_config.get('value', 0))
                mode = tp_config.get('mode', 'percentage')
                if mode == 'percentage':
                    pct = val / 100.0
                    tp_price = average_price * (1 + pct) if tp_side == 'sell' else average_price * (1 - pct)
                else:
                    tp_price = average_price + val if tp_side == 'sell' else average_price - val
                tp_price = float(exchange.price_to_precision(symbol, tp_price)) if hasattr(exchange, 'price_to_precision') else tp_price

            if sl_config:
                val = float(sl_config.get('value', 0))
                mode = sl_config.get('mode', 'percentage')
                if mode == 'percentage':
                    pct = val / 100.0
                    sl_price = average_price * (1 - pct) if tp_side == 'sell' else average_price * (1 + pct)
                else:
                    sl_price = average_price - val if tp_side == 'sell' else average_price + val
                sl_price = float(exchange.price_to_precision(symbol, sl_price)) if hasattr(exchange, 'price_to_precision') else sl_price

            # Execute OCO / Trailing logic
            placed_orders = []
            tp_id = None
            sl_id = None
            is_sl_synthetic = False

            # 1. Native Trailing Stop
            if trailing_config and trailing_config.get('mode') == 'native':
                trail_pct = float(trailing_config.get('trail_percent', 1.0))
                activation = trailing_config.get('activation_price')
                
                trail_params = {}
                if is_futures:
                    trail_params['reduceOnly'] = True
                
                trail_params['trailingPercent'] = trail_pct
                if activation:
                    trail_params['trailingTriggerPrice'] = activation
                    
                try:
                    res = await exchange.create_order(symbol, 'trailing_stop_market', tp_side, final_amount, None, trail_params)
                    placed_orders.append(("Native Trailing Stop", res.get('id')))
                except Exception as e:
                    logger.error(f"Native Trailing failed: {e}")
            
            # 2. Bracket (TP + SL)
            elif tp_price or sl_price:
                # Place TP
                if tp_price:
                    try:
                        tp_params = {'reduceOnly': True} if is_futures else {}
                        if tp_config.get('order_type', 'Limit').lower() == 'limit':
                            tp_params['postOnly'] = True
                            res = await exchange.create_limit_order(symbol, tp_side, final_amount, tp_price, tp_params)
                        else:
                            tp_params['triggerPrice'] = tp_price
                            res = await exchange.create_order(symbol, 'market', tp_side, final_amount, None, tp_params)
                        tp_id = res.get('id')
                        placed_orders.append(("Take Profit", tp_id))
                    except Exception as e:
                        logger.error(f"TP placement failed: {e}")
                
                # Place SL
                if sl_price:
                    try:
                        sl_params = {'reduceOnly': True} if is_futures else {}
                        sl_params['triggerPrice'] = sl_price
                        res = await exchange.create_order(symbol, 'market', tp_side, final_amount, None, sl_params)
                        sl_id = res.get('id')
                        placed_orders.append(("Stop Loss", sl_id))
                    except Exception as e:
                        err_str = str(e).lower()
                        if not is_futures and ('insufficient' in err_str or 'balance' in err_str):
                            # Spot balance locked by TP. Fallback to synthetic SL
                            logger.info(f"Spot balance locked by TP. Activating Synthetic OCO for SL: {sl_price}")
                            is_sl_synthetic = True
                            placed_orders.append(("Stop Loss", "Synthetic (Monitoring)"))
                        else:
                            logger.error(f"SL placement failed: {e}")

                # Spawn Synthetic OCO Monitor
                if tp_id or sl_id or is_sl_synthetic:
                    asyncio.create_task(BracketOrderService.synthetic_oco_monitor(
                        exchange, symbol, tp_id, sl_id, is_sl_synthetic, sl_price, tp_side, final_amount
                    ))
                    
            # 3. Synthetic Trailing (Fallback)
            if trailing_config and trailing_config.get('mode') == 'synthetic':
                asyncio.create_task(BracketOrderService.synthetic_trailing_monitor(
                    exchange, symbol, tp_side, final_amount, average_price,
                    float(trailing_config.get('trail_percent', 1.0)),
                    trailing_config.get('activation_price'),
                    is_futures
                ))
                placed_orders.append(("Synthetic Trailing Monitor", "Started"))

            # Notify
            if user_id and placed_orders:
                from app.db.session import SessionLocal
                db = SessionLocal()
                try:
                    msg = f"🎯 *Bracket Orders Placed!*\nExchange: {api_key_record.exchange.capitalize()}\nPair: `{symbol}`\n"
                    for label, oid in placed_orders:
                        msg += f"• {label}: `{oid}`\n"
                    await NotificationService.send_message(db, user_id, msg)
                except Exception as notify_err:
                    logger.warning(f"Bracket notification failed (non-fatal): {notify_err}")
                finally:
                    db.close()

        except Exception as main_e:
            logger.error(f"Bracket Monitor critical failure: {main_e}", exc_info=True)

    @staticmethod
    async def synthetic_oco_monitor(exchange, symbol, tp_id, sl_id, is_sl_synthetic, sl_price, tp_side, amount):
        """
        Background loop to manage OCO logic if Native OCO is not used.
        1. If both TP and SL are placed, checks if one is filled, then cancels the other.
        2. If SL is synthetic (Spot balance lock), monitors ticker for SL hit, then cancels TP and fires SL market.
        """
        logger.info(f"🔄 Synthetic OCO Monitor started for {symbol}")
        try:
            for _ in range(60 * 24 * 7): # Monitor for up to 7 days, checking every 5 seconds
                await asyncio.sleep(5)
                
                # Check TP status
                tp_filled = False
                if tp_id:
                    try:
                        tp_stat = await exchange.fetch_order(tp_id, symbol)
                        if tp_stat.get('status', '').lower() in ('closed', 'filled'):
                            tp_filled = True
                            if sl_id:
                                logger.info(f"OCO: TP {tp_id} filled. Canceling SL {sl_id}")
                                await exchange.cancel_order(sl_id, symbol)
                            return # OCO complete
                    except Exception as e:
                        pass # Ignore temporary network errors
                
                # Check SL status
                if sl_id:
                    try:
                        sl_stat = await exchange.fetch_order(sl_id, symbol)
                        if sl_stat.get('status', '').lower() in ('closed', 'filled'):
                            if tp_id:
                                logger.info(f"OCO: SL {sl_id} filled. Canceling TP {tp_id}")
                                await exchange.cancel_order(tp_id, symbol)
                            return # OCO complete
                    except Exception as e:
                        pass
                
                # Handle Synthetic SL
                if is_sl_synthetic and sl_price:
                    try:
                        ticker = await exchange.fetch_ticker(symbol)
                        current_price = ticker['last']
                        
                        sl_hit = False
                        if tp_side == 'sell' and current_price <= sl_price: # Long position
                            sl_hit = True
                        elif tp_side == 'buy' and current_price >= sl_price: # Short position
                            sl_hit = True
                            
                        if sl_hit:
                            logger.info(f"🚨 Synthetic OCO SL triggered! Price {current_price}. Canceling TP and executing market order.")
                            if tp_id:
                                await exchange.cancel_order(tp_id, symbol)
                            await exchange.create_market_order(symbol, tp_side, amount)
                            return # OCO complete
                    except Exception as e:
                        logger.debug(f"OCO Synthetic SL poll error: {e}")
                        
        except Exception as e:
            logger.error(f"Synthetic OCO Monitor failed: {e}")

    @staticmethod
    async def synthetic_trailing_monitor(exchange, symbol, tp_side, amount, entry_price, trail_percent, activation_price, is_futures):
        """
        Background loop tracking the max/min price to execute a synthetic trailing stop.
        """
        logger.info(f"🔄 Synthetic Trailing started for {symbol}. Trail: {trail_percent}%")
        try:
            high_watermark = entry_price
            low_watermark = entry_price
            is_active = False if activation_price else True
            base_asset = symbol.split('/')[0] if '/' in symbol else symbol.replace('USDT', '')
            
            for _ in range(60 * 24 * 7):
                await asyncio.sleep(5)
                try:
                    # LIVENESS CHECK: Ensure position/balance still exists before executing
                    if is_futures:
                        try:
                            positions = await exchange.fetch_positions([symbol])
                            pos = positions[0] if positions else None
                            if not pos or float(pos.get('contracts', 0)) == 0:
                                logger.info("Position already closed manually. Aborting trailing stop.")
                                return
                        except Exception:
                            pass # If fetch_positions fails, proceed to ticker check safely
                    else:
                        try:
                            if tp_side == 'sell': # We are long, so we need base_asset balance
                                balance = await exchange.fetch_balance()
                                free_amount = float(balance.get(base_asset, {}).get('free', 0))
                                if free_amount < amount * 0.99:
                                    logger.info("Base asset already sold manually. Aborting trailing stop.")
                                    return
                        except Exception:
                            pass

                    # Price tracking
                    ticker = await exchange.fetch_ticker(symbol)
                    current_price = ticker['last']
                    
                    if not current_price:
                        continue
                        
                    # Check activation
                    if not is_active:
                        if (tp_side == 'sell' and current_price >= activation_price) or \
                           (tp_side == 'buy' and current_price <= activation_price):
                            is_active = True
                            high_watermark = current_price
                            low_watermark = current_price
                        else:
                            continue

                    # Update watermarks
                    if tp_side == 'sell':
                        if current_price > high_watermark:
                            high_watermark = current_price
                        trail_trigger = high_watermark * (1 - trail_percent / 100.0)
                        if current_price <= trail_trigger:
                            logger.info(f"🚨 Synthetic Trailing triggered! Price {current_price} <= {trail_trigger}")
                            params = {'reduceOnly': True} if is_futures else {}
                            await exchange.create_market_order(symbol, tp_side, amount, params)
                            return
                    else:
                        if current_price < low_watermark:
                            low_watermark = current_price
                        trail_trigger = low_watermark * (1 + trail_percent / 100.0)
                        if current_price >= trail_trigger:
                            logger.info(f"🚨 Synthetic Trailing triggered! Price {current_price} >= {trail_trigger}")
                            params = {'reduceOnly': True} if is_futures else {}
                            await exchange.create_market_order(symbol, tp_side, amount, params)
                            return
                            
                except Exception as loop_e:
                    logger.debug(f"Synthetic Trailing poll error: {loop_e}")
                    
        except Exception as e:
            logger.error(f"Synthetic Trailing monitor failed: {e}")

bracket_order_service = BracketOrderService()

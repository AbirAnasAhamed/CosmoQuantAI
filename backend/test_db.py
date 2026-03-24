from app.db.session import SessionLocal
from app.models import Bot
import json

db = SessionLocal()
bot = db.query(Bot).filter(Bot.id==27).first()
if bot:
    print('STRATEGY_MODE:', bot.config.get('strategy_mode', 'NOT_FOUND'))
    print('TRADING_MODE:', bot.config.get('trading_mode', 'NOT_FOUND'))
else:
    print('Bot not found')
db.close()

# OmniTrade AI Core - Apex Architecture Blueprint
## "God-Tier" Distributed System (v2.0.0)

This document outlines the directory structure for the microservices architecture.

### Directory Tree

```
omnitrade-core/
├── backend/
│   ├── core/                   # System-wide Core Utilities
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic Settings & Env Management
│   │   ├── logger.py           # Structured JSON Logging
│   │   ├── exceptions.py       # Custom Exception Classes
│   │   └── security.py         # Encryption & Key Management
│   │
│   ├── db/                     # Infrastructure & Persistence
│   │   ├── __init__.py
│   │   ├── database.py         # TimescaleDB & Redis Connection Pools
│   │   ├── models.py           # SQLAlchemy/ORM Models
│   │   └── schema.sql          # Hypertable Initialization Scripts
│   │
│   ├── nexus/                  # Universal Data Nexus (UDN)
│   │   ├── __init__.py
│   │   ├── cex_stream.py       # CCXT WebSocket Managers (Binance)
│   │   ├── macro_client.py     # Fred API & News Scrapers
│   │   └── sentiment.py        # Twitter/Reddit Ingestion
│   │
│   ├── web3_node/              # Blockchain Monitor
│   │   ├── __init__.py
│   │   ├── rpc_client.py       # Web3.py Async Client
│   │   ├── whale_watcher.py    # Large Transaction Monitor
│   │   └── dex_liquidity.py    # Uniswap Pool Tracking
│   │
│   ├── brain/                  # ML Core & Feature Lab
│   │   ├── __init__.py
│   │   ├── feature_eng.py      # Technical Indicators (Numba Optimized)
│   │   ├── models/
│   │   │   ├── lstm_price.py   # Time-Series Model
│   │   │   └── ppo_agent.py    # RL Decision Maker
│   │   └── xai_shap.py         # SHAP Explainer Module
│   │
│   ├── strategy/               # Logic Engine
│   │   ├── __init__.py
│   │   ├── registry.py         # Strategy Loader
│   │   ├── scalping.py         # Order Book Imbalance Strategy
│   │   ├── arbitrage.py        # Stat-Arb & Pairs Trading
│   │   └── risk_guard.py       # Global Kill Switch & Circuit Breaker
│   │
│   ├── execution/              # Order Management
│   │   ├── __init__.py
│   │   ├── router.py           # Smart Order Router (TWAP/VWAP)
│   │   └── paper_sim.py        # Slippage & Fee Simulation
│   │
│   ├── main.py                 # Application Entry Point (Orchestrator)
│   └── requirements.txt        # Python Dependencies
│
├── frontend/                   # React Command Center (Existing)
│   ├── src/
│   └── public/
│
├── docker-compose.yml          # Container Orchestration
└── .env                        # Secrets (Excluded from Git)
```

### Infrastructure Stack
- **Language**: Python 3.11+ (AsyncIO)
- **Database**: TimescaleDB (PostgreSQL 14+)
- **Cache**: Redis 7.0 (Cluster Mode)
- **ML Framework**: PyTorch + Stable-Baselines3
- **Blockchain**: Web3.py + Infura/Alchemy

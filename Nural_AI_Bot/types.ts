
export enum MarketState {
  OPEN = 'OPEN',
  CLOSED = 'CLOSED',
  PRE_MARKET = 'PRE_MARKET',
  AFTER_HOURS = 'AFTER_HOURS'
}

export interface TickerData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: string;
}

export interface MarketSnapshot {
  volatilityIndex: number;
  atr: number;
  trend: number;
}

export interface Trade {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  amount: number;
  price: number;
  timestamp: string;
  status: 'FILLED' | 'PENDING' | 'CANCELLED';
  pnl?: number;
  confidence: number;
  leverage?: number;
  marketSnapshot?: MarketSnapshot;
}

export interface IndicatorData {
  time: string;
  price: number;
  ma7: number;
  ma25: number;
  rsi: number;
  macd: number;
  signal: number;
}

export interface AiAnalysisResult {
  decision: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  reasoning: string;
  riskAssessment: string;
  shapValues?: { feature: string; impact: number }[];
}

export interface LogEntry {
  id: string;
  timestamp: string;
  module: 'UDN' | 'FEATURE_LAB' | 'BRAIN' | 'EXECUTION';
  level: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  message: string;
}

export interface OHLCData {
  time: string; // epoch or string date
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BacktestTrade {
  id: number;
  time: string;
  type: 'BUY' | 'SELL';
  price: number;
  size: number;
  pnl?: number;
  balance: number;
}

export interface BacktestMetrics {
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  maxDrawdown: number;
  totalReturn: number;
  sharpeRatio: number;
  cagr: number;
}

export interface TradingBot {
  id: string;
  name: string;
  pair: string;
  strategy: 'Scalping' | 'Grid' | 'Arbitrage' | 'Swing' | 'HFT' | 'Ensemble (Full Swarm)';
  status: 'RUNNING' | 'PAUSED' | 'STOPPED';
  pnl: number;
  winRate: number;
  tradesToday: number;
  uptime: string;
  allocation: number;
  // Vertex AI Integration Fields
  modelVersion?: string;
  lastTraining?: string;
  computeNode?: string;
}

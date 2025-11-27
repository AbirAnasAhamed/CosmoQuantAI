import apiClient from './client';

interface BacktestRequest {
    symbol: string;
    timeframe: string;
    strategy: string;
    initial_cash: number;
    start_date?: string; // Optional string "YYYY-MM-DD"
    end_date?: string;   // Optional string "YYYY-MM-DD"
    params: Record<string, any>;
}

// সিঙ্ক ফাংশন আপডেট: start_date প্যারামিটার যোগ
export const syncMarketData = async (symbol: string, timeframe: string, startDate?: string, endDate?: string) => {
    // ডিফল্ট URL
    let url = `/market-data/sync?symbol=${symbol}&timeframe=${timeframe}`;

    // প্যারামিটার যোগ
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;

    const response = await apiClient.post(url);
    return response.data;
};

// রান ফাংশন আপডেট (ইন্টারফেস আগেই আপডেট করেছি, শুধু পাঠানো নিশ্চিত করা)
export const runBacktestApi = async (payload: BacktestRequest) => {
    const response = await apiClient.post('/backtest/run', payload);
    return response.data;
};

// ৩. এক্সচেঞ্জ লিস্ট পাওয়ার জন্য
export const getExchangeList = async () => {
    const response = await apiClient.get('/exchanges');
    return response.data;
};

// ৪. নির্দিষ্ট এক্সচেঞ্জের মার্কেট/সিম্বল পাওয়ার জন্য
export const getExchangeMarkets = async (exchangeId: string) => {
    const response = await apiClient.get(`/markets/${exchangeId}`);
    return response.data;
};

// ৫. নতুন স্ট্র্যাটেজি আপলোড করার জন্য
export const uploadStrategyFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/strategies/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};
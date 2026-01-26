import apiClient from './client';

export interface PerformanceMetrics {
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    total_trades: number;
    total_pnl: number;
    start_date?: string;
    end_date?: string;
}

export const getPerformanceMetrics = async (startDate?: string, endDate?: string): Promise<PerformanceMetrics> => {
    const params: any = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await apiClient.get('/analytics/performance', { params });
    return response.data;
};

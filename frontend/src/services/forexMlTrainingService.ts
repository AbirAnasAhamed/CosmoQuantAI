import apiClient from './client';

export interface ForexTrainingJob {
    id: string;
    symbol: string;
    timeframe: string;
    algorithm: string;
    market_type: string;
    status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'PAUSED';
    progress: number;
    logs: string[];
    output_model_id?: string;
    error_message?: string;
    created_at: string;
    updated_at?: string;
    completed_at?: string;
}

export interface ForexTrainingConfig {
    symbol: string;
    timeframe: string;
    algorithm: string;
    config: {
        epochs: number;
        broker?: string;
        market_session_features?: boolean;
        ignore_weekend_gaps?: boolean;
        macroeconomic_calendar?: boolean;
        tick_volume_profiler?: boolean;
        cot_data?: boolean;
        currency_correlation?: boolean;
        yield_differentials?: boolean;
        use_automl?: boolean;
        is_ensemble?: boolean;
        base_models?: string[];
        meta_model?: string;
        target_rows?: number;
    };
}

export const forexMlTrainingService = {
    startTraining: async (config: ForexTrainingConfig): Promise<ForexTrainingJob> => {
        const response = await apiClient.post('/forex-model-training/train', config);
        return response.data;
    },

    getJobs: async (): Promise<ForexTrainingJob[]> => {
        const response = await apiClient.get('/forex-model-training/jobs');
        return response.data;
    },

    getJobStatus: async (jobId: string): Promise<ForexTrainingJob> => {
        const response = await apiClient.get(`/forex-model-training/jobs/${jobId}`);
        return response.data;
    },

    cancelTraining: async (jobId: string): Promise<ForexTrainingJob> => {
        const response = await apiClient.post(`/forex-model-training/jobs/${jobId}/cancel`);
        return response.data;
    },

    getInstruments: async (): Promise<{name: string, display_name: string}[]> => {
        const response = await apiClient.get('/forex-model-training/instruments');
        return response.data;
    },

    deleteDataset: async (symbol: string): Promise<{status: string, message: string}> => {
        const response = await apiClient.delete(`/forex-model-training/dataset/${symbol}`);
        return response.data;
    }
};

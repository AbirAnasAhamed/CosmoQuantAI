import apiClient from './client';
import { SavedIndicator } from '@/types';

export const indicatorService = {
    getAll: async (): Promise<SavedIndicator[]> => {
        const response = await apiClient.get<SavedIndicator[]>('/v1/indicators/');
        return response.data;
    },

    create: async (data: SavedIndicator): Promise<SavedIndicator> => {
        const response = await apiClient.post<SavedIndicator>('/v1/indicators/', data);
        return response.data;
    },

    delete: async (id: number): Promise<void> => {
        await apiClient.delete(`/v1/indicators/${id}`);
    },

    getTemplates: async (): Promise<SavedIndicator[]> => {
        const response = await apiClient.get<SavedIndicator[]>('/v1/indicators/templates');
        return response.data;
    }
};

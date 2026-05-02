import api from './api';
import { CustomMLModel } from '@/types';

export const mlModelsService = {
    // Get all custom models for the user
    getModels: async (): Promise<CustomMLModel[]> => {
        const response = await api.get('/ml-models');
        return response.data;
    },

    // Create a new model and upload its first version
    createModel: async (
        name: string,
        modelType: string,
        version: number,
        description: string,
        file: File
    ): Promise<CustomMLModel> => {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('model_type', modelType);
        formData.append('version', version.toString());
        formData.append('description', description);
        formData.append('file', file);

        const response = await api.post('/ml-models', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    // Upload a new version for an existing model
    uploadVersion: async (
        modelId: string,
        version: number,
        description: string,
        file: File
    ): Promise<CustomMLModel> => {
        const formData = new FormData();
        formData.append('version', version.toString());
        formData.append('description', description);
        formData.append('file', file);

        const response = await api.post(`/ml-models/${modelId}/versions`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    // Set active version for a model
    setActiveVersion: async (modelId: string, versionId: string): Promise<CustomMLModel> => {
        const response = await api.put(`/ml-models/${modelId}/active-version`, {
            active_version_id: versionId
        });
        return response.data;
    },

    // Delete a model
    deleteModel: async (modelId: string): Promise<void> => {
        await api.delete(`/ml-models/${modelId}`);
    }
};

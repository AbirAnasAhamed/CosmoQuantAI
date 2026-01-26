import apiClient from './client';

export interface ApiKeyPayload {
    exchange: string;
    name: string; // ✅ New field
    api_key: string;
    secret_key: string;
    passphrase?: string;
}

// ✅ ফিক্স: পাথগুলো '/users' এবং '/v1' সহ আপডেট করা হয়েছে

export const fetchApiKeys = async () => {
    // আগে ছিল: '/api-keys' অথবা '/users/api-keys'
    // এখন হবে:
    const response = await apiClient.get('/users/api-keys');
    return response.data;
};

export const saveApiKey = async (data: ApiKeyPayload) => {
    const response = await apiClient.post('/users/api-keys', data);
    return response.data;
};

export const deleteApiKey = async (keyId: number) => {
    const response = await apiClient.delete(`/users/api-keys/${keyId}`);
    return response.data;
};

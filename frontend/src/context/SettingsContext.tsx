import React, { createContext, useState, useContext, useEffect, ReactNode, useCallback } from 'react';
import { fetchApiKeys, saveApiKey as apiSaveApiKey } from '@/services/settings';
import { fetchCurrentUser } from '@/services/auth';
import { useToast } from './ToastContext';

// ✅ আপডেট: 'id' ফিল্ড যোগ করা হয়েছে
export interface ApiKeyConfig {
    id?: number; // ডাটাবেস ID
    apiKey: string;
    secretKey: string;
    isEnabled: boolean;
    isSaved?: boolean;
}

export interface UserProfile {
    fullName: string;
    email: string;
    username: string;
    timezone: string;
    currency: string;
}

interface SettingsContextType {
    apiKeys: Record<string, ApiKeyConfig>;
    updateLocalApiKeyInput: (exchange: string, config: Partial<ApiKeyConfig>) => void;
    saveApiKeyToBackend: (exchange: string) => Promise<void>;
    isLoading: boolean;
    userProfile: UserProfile;
    updateUserProfile: (profile: Partial<UserProfile>) => void;
    is2faEnabled: boolean;
    set2faEnabled: (enabled: boolean) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const { showToast } = useToast();
    const [isLoading, setIsLoading] = useState(false);

    const [apiKeys, setApiKeys] = useState<Record<string, ApiKeyConfig>>({
        'Binance': { apiKey: '', secretKey: '', isEnabled: false, isSaved: false },
        'KuCoin': { apiKey: '', secretKey: '', isEnabled: false, isSaved: false },
    });

    const [userProfile, setUserProfile] = useState<UserProfile>({
        fullName: 'Loading...',
        email: '...',
        username: '...',
        timezone: 'UTC',
        currency: 'USD'
    });

    const [is2faEnabled, set2faEnabled] = useState(false);

    const loadUserData = useCallback(async () => {
        const token = localStorage.getItem('accessToken');
        if (!token) return;

        try {
            const [keysFromDB, userData] = await Promise.all([
                fetchApiKeys().catch(() => []),
                fetchCurrentUser().catch(() => null)
            ]);

            // ✅ আপডেট: API Key এর ID সহ সেট করা হচ্ছে
            if (keysFromDB && Array.isArray(keysFromDB)) {
                setApiKeys(prev => {
                    const newKeys = { ...prev };
                    keysFromDB.forEach((k: any) => {
                        if (newKeys[k.exchange]) {
                            newKeys[k.exchange] = {
                                id: k.id, // এই ID টি এখন স্টোর হবে
                                apiKey: k.api_key,
                                secretKey: '••••••••',
                                isEnabled: k.is_enabled,
                                isSaved: true
                            };
                        }
                    });
                    return newKeys;
                });
            }

            if (userData) {
                setUserProfile({
                    fullName: userData.full_name || 'Trader',
                    email: userData.email,
                    username: userData.email.split('@')[0],
                    timezone: 'UTC',
                    currency: 'USD'
                });
            }

        } catch (error) {
            console.error("Error loading user data", error);
        }
    }, []);

    useEffect(() => {
        loadUserData();
    }, [loadUserData]);

    const updateLocalApiKeyInput = (exchange: string, updates: Partial<ApiKeyConfig>) => {
        setApiKeys(prev => ({
            ...prev,
            [exchange]: { ...prev[exchange], ...updates }
        }));
    };

    const saveApiKeyToBackend = async (exchange: string) => {
        const config = apiKeys[exchange];
        if (!config.apiKey || !config.secretKey || config.secretKey === '••••••••') {
            showToast('Please enter valid API and Secret keys', 'warning');
            return;
        }

        setIsLoading(true);
        try {
            // সেভ করার পর আমরা রি-ফেচ করতে পারি অথবা রেসপন্স থেকে ID নিতে পারি
            // সিম্পল রাখার জন্য আপাতত রি-ফেচ বা ম্যানুয়াল আইডি সেট করা যেতে পারে, 
            // তবে এখানে লোডিং শেষ হলে আবার loadUserData কল করা ভালো আইডি পাওয়ার জন্য।
            await apiSaveApiKey({
                exchange: exchange,
                api_key: config.apiKey,
                secret_key: config.secretKey
            });

            showToast(`${exchange} API keys connected successfully!`, 'success');

            // ডাটা সেভ হওয়ার পর ID পাওয়ার জন্য রি-ফেচ
            loadUserData();

        } catch (error: any) {
            console.error(error);
            showToast('Failed to save API keys.', 'error');
        } finally {
            setIsLoading(false);
        }
    };

    const updateUserProfile = (updates: Partial<UserProfile>) => {
        setUserProfile(prev => ({ ...prev, ...updates }));
    };

    return (
        <SettingsContext.Provider value={{
            apiKeys,
            updateLocalApiKeyInput,
            saveApiKeyToBackend,
            isLoading,
            userProfile,
            updateUserProfile,
            is2faEnabled,
            set2faEnabled
        }}>
            {children}
        </SettingsContext.Provider>
    );
};

export const useSettings = (): SettingsContextType => {
    const context = useContext(SettingsContext);
    if (context === undefined) {
        throw new Error('useSettings must be used within a SettingsProvider');
    }
    return context;
};


import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';

export interface ApiKeyConfig {
    apiKey: string;
    secretKey: string;
    isEnabled: boolean;
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
    updateApiKey: (exchange: string, config: ApiKeyConfig) => void;
    userProfile: UserProfile;
    updateUserProfile: (profile: Partial<UserProfile>) => void;
    is2faEnabled: boolean;
    set2faEnabled: (enabled: boolean) => void;
}

const defaultProfile: UserProfile = {
    fullName: 'ABIR AHAMED',
    email: 'abir.ahamed@example.com',
    username: 'abirahamed',
    timezone: 'America/New_York',
    currency: 'USD'
};

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [apiKeys, setApiKeys] = useState<Record<string, ApiKeyConfig>>(() => {
        try {
            const saved = localStorage.getItem('apiKeys');
            return saved ? JSON.parse(saved) : {
                'Binance': { apiKey: 'live_mock_api_key_for_binance_xxxx', secretKey: 'live_mock_secret_key_for_binance_yyyy', isEnabled: true },
                'KuCoin': { apiKey: '', secretKey: '', isEnabled: false },
            };
        } catch {
            return {
                'Binance': { apiKey: 'live_mock_api_key_for_binance_xxxx', secretKey: 'live_mock_secret_key_for_binance_yyyy', isEnabled: true },
                'KuCoin': { apiKey: '', secretKey: '', isEnabled: false },
            };
        }
    });

    const [userProfile, setUserProfile] = useState<UserProfile>(() => {
        try {
            const saved = localStorage.getItem('userProfile');
            return saved ? JSON.parse(saved) : defaultProfile;
        } catch {
            return defaultProfile;
        }
    });

    const [is2faEnabled, set2faEnabledState] = useState(() => {
        try {
            return localStorage.getItem('is2faEnabled') === 'true';
        } catch {
            return false;
        }
    });

    useEffect(() => {
        localStorage.setItem('apiKeys', JSON.stringify(apiKeys));
    }, [apiKeys]);

    useEffect(() => {
        localStorage.setItem('userProfile', JSON.stringify(userProfile));
    }, [userProfile]);

    useEffect(() => {
        localStorage.setItem('is2faEnabled', String(is2faEnabled));
    }, [is2faEnabled]);

    const updateApiKey = (exchange: string, config: ApiKeyConfig) => {
        setApiKeys(prev => ({ ...prev, [exchange]: config }));
    };

    const updateUserProfile = (updates: Partial<UserProfile>) => {
        setUserProfile(prev => ({ ...prev, ...updates }));
    };
    
    const set2faEnabled = (enabled: boolean) => {
        set2faEnabledState(enabled);
    };

    return (
        <SettingsContext.Provider value={{ apiKeys, updateApiKey, userProfile, updateUserProfile, is2faEnabled, set2faEnabled }}>
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

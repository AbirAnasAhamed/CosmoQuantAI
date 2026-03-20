
import React, { useState, useRef, useEffect } from 'react';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import { useTheme } from '@/context/ThemeContext';
import { useToast } from '@/context/ToastContext';
import { useSettings, ApiKeyConfig } from '@/context/SettingsContext';
import { marketDataService } from '@/services/marketData';
import { notificationService } from '@/services/notification';
import { updateUserSecurity, uploadUserAvatar } from '@/services/auth';

// Icons
const PlusIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg xmlns="http://www.w3.org/2000/svg" className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
    </svg>
);

const TrashIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg xmlns="http://www.w3.org/2000/svg" className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
);

const Settings: React.FC<{ initialSection?: string | null }> = ({ initialSection }) => {
    const { theme, setTheme } = useTheme();
    const { showToast } = useToast();
    const {
        userProfile, updateUserProfile,
        apiKeys, saveApiKeyToBackend, deleteApiKey,
        is2faEnabled, set2faEnabled, isLoading
    } = useSettings();

    // Profile State
    const [fullName, setFullName] = useState(userProfile.fullName);
    const [email, setEmail] = useState(userProfile.email);
    const [username, setUsername] = useState(userProfile.username);
    const [timezone, setTimezone] = useState(userProfile.timezone);
    const [currency, setCurrency] = useState(userProfile.currency);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');


    const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleAvatarClick = () => {
        fileInputRef.current?.click();
    };

    const handleAvatarChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        // Simple validation
        if (file.size > 1024 * 1024) {
            showToast('File size must be less than 1MB', 'error');
            return;
        }

        setIsUploadingAvatar(true);
        try {
            const updatedUser = await uploadUserAvatar(file);
            updateUserProfile({ avatar_url: updatedUser.avatar_url });
            showToast('Avatar updated successfully!', 'success');
        } catch (error) {
            showToast('Failed to upload avatar.', 'error');
            console.error(error);
        } finally {
            setIsUploadingAvatar(false);
        }
    };

    // API Key Modal State
    const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
    const [exchangeCredentials, setExchangeCredentials] = useState<Record<string, { name: string, fields: string[] }>>({});
    const [isLoadingExchanges, setIsLoadingExchanges] = useState(false);

    // New Key Form State
    const [selectedExchange, setSelectedExchange] = useState('');
    const [connectionName, setConnectionName] = useState('');
    const [newKeyFields, setNewKeyFields] = useState<Record<string, string>>({});

    // Notification State
    const [notificationSettings, setNotificationSettings] = useState({
        telegram_bot_token: '',
        telegram_chat_id: '',
        is_enabled: false
    });
    const [isSavingNotifications, setIsSavingNotifications] = useState(false);
    const [isTestingNotification, setIsTestingNotification] = useState(false);

    // Refs
    const profileRef = useRef<HTMLDivElement>(null);
    const billingRef = useRef<HTMLDivElement>(null);
    const securityRef = useRef<HTMLDivElement>(null);
    const apiKeysRef = useRef<HTMLDivElement>(null);
    const notificationRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setFullName(userProfile.fullName);
        setEmail(userProfile.email);
        setUsername(userProfile.username);
        setTimezone(userProfile.timezone);
        setCurrency(userProfile.currency);
    }, [userProfile]);

    useEffect(() => {
        setTimeout(() => {
            let targetRef: React.RefObject<HTMLDivElement> | null = null;
            switch (initialSection) {
                case 'profile': targetRef = profileRef; break;
                case 'billing': targetRef = billingRef; break;
                case 'api-keys': targetRef = apiKeysRef; break;
                case 'notifications': targetRef = notificationRef; break;
            }
            if (targetRef?.current) {
                targetRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 100);
    }, [initialSection]);

    // Fetch exchange info on modal open
    useEffect(() => {
        if (isKeyModalOpen && Object.keys(exchangeCredentials).length === 0) {
            setIsLoadingExchanges(true);
            marketDataService.getExchangeCredentials()
                .then(data => setExchangeCredentials(data))
                .catch(err => console.error(err))
                .finally(() => setIsLoadingExchanges(false));
        }
    }, [isKeyModalOpen]);

    // Fetch Notification Settings
    useEffect(() => {
        notificationService.getSettings()
            .then(data => {
                if (data) {
                    setNotificationSettings({
                        telegram_bot_token: data.telegram_bot_token || '',
                        telegram_chat_id: data.telegram_chat_id || '',
                        is_enabled: data.is_enabled
                    });
                }
            })
            .catch(console.error);
    }, []);

    // Security State
    const [clientIP, setClientIP] = useState<string>('');
    const [allowedIPs, setAllowedIPs] = useState<string[]>([]);
    const [isWhitelistEnabled, setIsWhitelistEnabled] = useState(false);
    const [newIP, setNewIP] = useState('');
    const [isSavingSecurity, setIsSavingSecurity] = useState(false);

    useEffect(() => {
        setAllowedIPs(userProfile.allowed_ips || []);
        setIsWhitelistEnabled(userProfile.is_ip_whitelist_enabled || false);
    }, [userProfile]);

    useEffect(() => {
        fetch('https://api.ipify.org?format=json')
            .then(res => res.json())
            .then(data => setClientIP(data.ip))
            .catch(err => console.error("Failed to fetch IP", err));
    }, []);

    const handleAddIP = () => {
        if (newIP && !allowedIPs.includes(newIP)) {
            setAllowedIPs([...allowedIPs, newIP]);
            setNewIP('');
        }
    };

    const handleRemoveIP = (ip: string) => {
        setAllowedIPs(allowedIPs.filter(i => i !== ip));
    };

    const handleSaveSecurity = async () => {
        setIsSavingSecurity(true);
        try {
            await updateUserSecurity({
                allowed_ips: allowedIPs,
                is_ip_whitelist_enabled: isWhitelistEnabled
            });
            updateUserProfile({ allowed_ips: allowedIPs, is_ip_whitelist_enabled: isWhitelistEnabled });
            showToast('Security settings saved!', 'success');
        } catch (error) {
            showToast('Failed to save security settings.', 'error');
        } finally {
            setIsSavingSecurity(false);
        }
    };

    const handleThemeChange = () => setTheme(theme === 'dark' ? 'light' : 'dark');
    const isDarkMode = theme === 'dark';

    const handleSaveChanges = () => {
        if (fullName === userProfile.fullName) return;
        setSaveStatus('saving');
        setTimeout(() => {
            updateUserProfile({ fullName, email, username, timezone, currency });
            setSaveStatus('saved');
            showToast('Profile settings saved!', 'success');
            setTimeout(() => setSaveStatus('idle'), 2000);
        }, 1000);
    };

    const handleSaveNewKey = async () => {
        if (!selectedExchange || !connectionName) {
            showToast("Please select an exchange and name this connection.", "warning");
            return;
        }

        const requiredFields = exchangeCredentials[selectedExchange]?.fields || [];
        for (const field of requiredFields) {
            if (!newKeyFields[field]) {
                showToast(`Please enter your ${field}.`, "warning");
                return;
            }
        }

        await saveApiKeyToBackend({
            exchange: selectedExchange,
            name: connectionName,
            apiKey: newKeyFields['apiKey'] || '',
            secretKey: newKeyFields['secret'] || '',
            // ✅ FIX: Check both 'password' and 'passphrase' keys
            passphrase: newKeyFields['password'] || newKeyFields['passphrase'] || ''
        });

        setIsKeyModalOpen(false);
        resetForm();
    };

    const resetForm = () => {
        setSelectedExchange('');
        setConnectionName('');
        setNewKeyFields({});
    };

    const handleSaveNotification = async () => {
        setIsSavingNotifications(true);
        try {
            await notificationService.updateSettings(notificationSettings);
            showToast('Notification settings saved!', 'success');
        } catch (e) {
            showToast('Failed to save settings.', 'error');
        } finally {
            setIsSavingNotifications(false);
        }
    };

    const handleTestNotification = async () => {
        setIsTestingNotification(true);
        try {
            await notificationService.sendTestNotification(
                notificationSettings.telegram_bot_token,
                notificationSettings.telegram_chat_id
            );
            showToast('Test message sent!', 'success');
        } catch (e: any) {
            showToast(`Test failed: ${e.response?.data?.detail || e.message}`, 'error');
        } finally {
            setIsTestingNotification(false);
        }
    };

    const inputBaseClasses = "w-full bg-white dark:bg-brand-dark/50 border border-brand-border-light dark:border-brand-border-dark rounded-md p-2 text-slate-900 dark:text-white focus:ring-brand-primary focus:border-brand-primary transition-colors";

    return (
        <div className="space-y-8 max-w-4xl animate-fade-in-slide-up">
            {/* Appearance Section */}
            <Card>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6 border-b border-brand-border-light dark:border-brand-border-dark pb-4">Appearance</h2>
                <div className="flex items-center space-x-4 p-4 bg-gray-100 dark:bg-brand-dark/50 rounded-lg">
                    <label htmlFor="theme-toggle" className="flex items-center cursor-pointer">
                        <div className="relative">
                            <input type="checkbox" id="theme-toggle" className="sr-only" checked={isDarkMode} onChange={handleThemeChange} />
                            <div className={`block w-14 h-8 rounded-full ${isDarkMode ? 'bg-brand-primary' : 'bg-slate-400'}`}></div>
                            <div className={`dot absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition-transform ${isDarkMode ? 'transform translate-x-6' : ''}`}></div>
                        </div>
                    </label>
                    <span className="font-medium text-slate-900 dark:text-white">{isDarkMode ? 'Dark Mode' : 'Light Mode'}</span>
                </div>
            </Card>

            {/* Profile Section */}
            <div ref={profileRef}>
                <Card>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6 border-b border-brand-border-light dark:border-brand-border-dark pb-4">Profile Settings</h2>
                    <div className="space-y-6">
                        <div className="flex items-center gap-6">
                            <div className="w-20 h-20 rounded-full bg-brand-primary text-white flex items-center justify-center font-bold text-3xl flex-shrink-0 overflow-hidden">
                                {userProfile.avatar_url ? (
                                    <img src={userProfile.avatar_url} alt="Profile" className="w-full h-full object-cover" />
                                ) : (
                                    fullName.split(' ').map(n => n[0]).join('')
                                )}
                            </div>
                            <div>
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    className="hidden"
                                    accept="image/*"
                                    onChange={handleAvatarChange}
                                />
                                <Button variant="secondary" onClick={handleAvatarClick} disabled={isUploadingAvatar}>
                                    {isUploadingAvatar ? 'Uploading...' : 'Change Avatar'}
                                </Button>
                                <p className="text-xs text-gray-500 mt-2">JPG, GIF or PNG. 1MB max.</p>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Full Name</label>
                                <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputBaseClasses} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Username</label>
                                <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className={inputBaseClasses} />
                            </div>
                            {/* Additional fields omitted for brevity but state is handled */}
                        </div>
                        <div className="flex items-center gap-4 pt-4 border-t border-brand-border-light dark:border-brand-border-dark">
                            <Button variant="primary" onClick={handleSaveChanges} disabled={saveStatus === 'saving'}>{saveStatus === 'saving' ? 'Saving...' : 'Save Changes'}</Button>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Security Section (IP Whitelist) */}
            <div ref={securityRef}>
                <Card>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6 border-b border-brand-border-light dark:border-brand-border-dark pb-4">Security</h2>

                    <div className="space-y-6">
                        <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-brand-dark/30 rounded-lg border border-gray-200 dark:border-brand-border-dark">
                            <div>
                                <h3 className="font-medium text-slate-900 dark:text-white">IP Whitelist</h3>
                                <p className="text-sm text-gray-500">Only allow access from specific IP addresses.</p>
                                {clientIP && <p className="text-xs text-brand-primary mt-1">Your Current IP: {clientIP}</p>}
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={isWhitelistEnabled}
                                    onChange={(e) => setIsWhitelistEnabled(e.target.checked)}
                                    className="sr-only peer"
                                />
                                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-brand-primary/20 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-primary"></div>
                            </label>
                        </div>

                        {isWhitelistEnabled && (
                            <div className="space-y-4 animate-fade-in">
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={newIP}
                                        onChange={(e) => setNewIP(e.target.value)}
                                        placeholder="Enter IP Address (e.g. 192.168.1.1)"
                                        className={inputBaseClasses}
                                    />
                                    <Button variant="secondary" onClick={handleAddIP} disabled={!newIP}>Add</Button>
                                    <Button variant="secondary" onClick={() => setNewIP(clientIP)} disabled={!clientIP}>Add Current</Button>
                                </div>

                                <div className="bg-white dark:bg-brand-dark border border-brand-border-light dark:border-brand-border-dark rounded-md overflow-hidden">
                                    {allowedIPs.length === 0 ? (
                                        <p className="p-4 text-sm text-gray-500 text-center">No IPs whitelisted. Warning: You might lock yourself out if enabled without your IP.</p>
                                    ) : (
                                        <ul className="divide-y divide-brand-border-light dark:divide-brand-border-dark">
                                            {allowedIPs.map(ip => (
                                                <li key={ip} className="flex justify-between items-center p-3 hover:bg-gray-50 dark:hover:bg-brand-dark/50">
                                                    <span className="text-sm font-mono text-slate-700 dark:text-gray-300">{ip}</span>
                                                    <button onClick={() => handleRemoveIP(ip)} className="text-red-500 hover:text-red-700">
                                                        <TrashIcon />
                                                    </button>
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </div>
                            </div>
                        )}

                        <div className="flex items-center gap-4 pt-4 border-t border-brand-border-light dark:border-brand-border-dark">
                            <Button variant="primary" onClick={handleSaveSecurity} disabled={isSavingSecurity}>
                                {isSavingSecurity ? 'Saving...' : 'Save Security Settings'}
                            </Button>
                        </div>
                    </div>
                </Card>
            </div>

            {/* API Keys Section */}
            <div ref={apiKeysRef}>
                <Card>
                    <div className="flex justify-between items-center mb-6 border-b border-brand-border-light dark:border-brand-border-dark pb-4">
                        <div>
                            <h2 className="text-xl font-bold text-slate-900 dark:text-white">API Key Management</h2>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Manage your exchange connections securely.</p>
                        </div>
                        <Button onClick={() => setIsKeyModalOpen(true)}>
                            <div className="flex items-center gap-2">
                                <PlusIcon /> Add Connection
                            </div>
                        </Button>
                    </div>

                    {/* Saved Connections Table */}
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-gray-500 dark:text-gray-400">
                            <thead className="bg-gray-50 dark:bg-brand-dark/50 text-xs uppercase text-gray-700 dark:text-gray-300">
                                <tr>
                                    <th className="px-6 py-3">Name</th>
                                    <th className="px-6 py-3">Exchange</th>
                                    <th className="px-6 py-3">Status</th>
                                    <th className="px-6 py-3 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {apiKeys.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-8 text-center text-gray-500">No connections added yet.</td>
                                    </tr>
                                ) : (
                                    apiKeys.map((key) => (
                                        <tr key={key.id || key.exchange} className="border-b border-gray-200 dark:border-brand-border-dark dark:hover:bg-brand-darkest/30">
                                            <td className="px-6 py-4 font-medium text-slate-900 dark:text-white">{key.name}</td>
                                            <td className="px-6 py-4 capitalize">{key.exchange}</td>
                                            <td className="px-6 py-4">
                                                <span className={`px-2 py-1 rounded-full text-xs font-bold ${key.isEnabled ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'}`}>
                                                    {key.isEnabled ? 'Active' : 'Inactive'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <button onClick={() => {
                                                    if (window.confirm("Are you sure you want to delete this connection?")) {
                                                        deleteApiKey(key.id!);
                                                    }
                                                }} className="text-red-500 hover:text-red-700 transition-colors">
                                                    <TrashIcon />
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </div>

            {/* Notification Section */}
            <div ref={notificationRef}>
                <Card>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6 border-b border-brand-border-light dark:border-brand-border-dark pb-4">Notifications</h2>
                    <div className="space-y-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-medium text-slate-900 dark:text-white">Telegram Alerts</h3>
                                <p className="text-sm text-gray-500">Receive instant updates when trades are executed.</p>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={notificationSettings.is_enabled}
                                    onChange={(e) => setNotificationSettings(p => ({ ...p, is_enabled: e.target.checked }))}
                                    className="sr-only peer"
                                />
                                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-brand-primary/20 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-primary"></div>
                            </label>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Bot Token</label>
                                <input
                                    type="password"
                                    value={notificationSettings.telegram_bot_token}
                                    onChange={(e) => setNotificationSettings(p => ({ ...p, telegram_bot_token: e.target.value }))}
                                    placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                                    className={inputBaseClasses}
                                />
                                <p className="text-xs text-gray-400 mt-1">Get this from @BotFather on Telegram.</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Chat ID</label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={notificationSettings.telegram_chat_id}
                                        onChange={(e) => setNotificationSettings(p => ({ ...p, telegram_chat_id: e.target.value }))}
                                        placeholder="123456789"
                                        className={inputBaseClasses}
                                    />
                                    <Button variant="secondary" onClick={handleTestNotification} disabled={isTestingNotification || !notificationSettings.telegram_bot_token || !notificationSettings.telegram_chat_id}>
                                        {isTestingNotification ? 'Sending...' : 'Test'}
                                    </Button>
                                </div>
                                <p className="text-xs text-gray-400 mt-1">Send a message to your bot to find your Chat ID.</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-4 pt-4 border-t border-brand-border-light dark:border-brand-border-dark">
                            <Button variant="primary" onClick={handleSaveNotification} disabled={isSavingNotifications}>
                                {isSavingNotifications ? 'Saving...' : 'Save Settings'}
                            </Button>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Add Connection Modal */}
            {isKeyModalOpen && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in" onClick={() => setIsKeyModalOpen(false)}>
                    <div className="bg-white dark:bg-brand-dark w-full max-w-lg rounded-xl shadow-2xl p-6 border border-brand-border-light dark:border-brand-border-dark animate-slide-up" onClick={e => e.stopPropagation()}>
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">Add New Connection</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Exchange</label>
                                <select
                                    value={selectedExchange}
                                    onChange={(e) => { setSelectedExchange(e.target.value); setNewKeyFields({}); }}
                                    className={inputBaseClasses}
                                    disabled={isLoadingExchanges}
                                >
                                    <option value="">Select Exchange...</option>
                                    {Object.keys(exchangeCredentials).map(ex => (
                                        <option key={ex} value={ex}>{exchangeCredentials[ex].name}</option>
                                    ))}
                                </select>
                                {isLoadingExchanges && <p className="text-xs text-brand-primary mt-1">Loading supported exchanges...</p>}
                            </div>

                            {selectedExchange && (
                                <div className="space-y-4 animate-fade-in">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Connection Name</label>
                                        <input
                                            type="text"
                                            value={connectionName}
                                            onChange={(e) => setConnectionName(e.target.value)}
                                            placeholder="e.g. My Binance Scalping"
                                            className={inputBaseClasses}
                                        />
                                    </div>

                                    {exchangeCredentials[selectedExchange]?.fields.map(field => (
                                        <div key={field}>
                                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 capitalize">
                                                {field === 'password' ? 'Passphrase / Trading Password' : field.replace(/([A-Z])/g, ' $1').trim()}
                                            </label>
                                            <input
                                                type="password"
                                                value={newKeyFields[field] || ''}
                                                onChange={(e) => setNewKeyFields(prev => ({ ...prev, [field]: e.target.value }))}
                                                className={inputBaseClasses}
                                            />
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="flex justify-end gap-3 pt-4">
                                <Button variant="secondary" onClick={() => setIsKeyModalOpen(false)}>Cancel</Button>
                                <Button onClick={handleSaveNewKey} disabled={isLoading || !selectedExchange}>
                                    {isLoading ? 'Connecting...' : 'Connect Exchange'}
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Settings;

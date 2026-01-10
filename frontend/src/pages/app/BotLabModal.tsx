import React, { useState, useEffect } from 'react';
import { Dialog } from '@headlessui/react';
import { botService } from '../../services/botService';
import { strategyService } from '../../services/strategyService';
// ✅ Import apiClient for fetching keys
import apiClient from '../../services/client';

interface BotLabModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

const BotLabModal: React.FC<BotLabModalProps> = ({ isOpen, onClose, onSuccess }) => {
    const [loading, setLoading] = useState(false);

    // ✅ নতুন স্টেট: স্ট্র্যাটেজি লিস্ট রাখার জন্য
    const [strategyOptions, setStrategyOptions] = useState<{ value: string, label: string }[]>([]);

    // ✅ Real Trading States
    const [apiKeyId, setApiKeyId] = useState<string>('');
    const [leverage, setLeverage] = useState<number>(1);
    const [marginMode, setMarginMode] = useState<string>('cross');
    const [userApiKeys, setUserApiKeys] = useState<any[]>([]);

    const [formData, setFormData] = useState({
        name: '',
        market: 'BTC/USDT',
        strategy: '', // ডিফল্ট খালি রাখুন
        timeframe: '1h',
        trade_value: 100,
        stop_loss: 0,
        take_profit: 0
    });

    // ✅ নতুন useEffect: মডাল লোড হলে ব্যাকএন্ড থেকে স্ট্র্যাটেজি এবং API Keys আনবে
    useEffect(() => {
        if (isOpen) {
            const fetchStrategies = async () => {
                try {
                    const strategies = await strategyService.getAllStrategies();
                    // ব্যাকএন্ডের লিস্টকে ড্রপডাউনের ফরম্যাটে কনভার্ট করা
                    const options = strategies.map((s) => ({
                        value: s,
                        label: s
                    }));
                    setStrategyOptions(options);
                } catch (err) {
                    console.error("Error loading strategies", err);
                }
            };

            const fetchApiKeys = async () => {
                try {
                    // Fetch API Keys
                    const { data } = await apiClient.get('/api-keys');
                    setUserApiKeys(data); // Assuming data is array of keys
                } catch (err) {
                    console.error("Error loading keys", err);
                    // Fallback demo data if endpoint fails or returns empty (for UI testing)
                    // setUserApiKeys([
                    //   { id: '1', name: 'Binance Main', exchange: 'binance' },
                    // ]);
                }
            };

            fetchStrategies();
            fetchApiKeys();
        }
    }, [isOpen]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const botData = {
                ...formData,
                api_key_id: apiKeyId,
                config: {
                    leverage: Number(leverage),
                    marginMode: marginMode,
                    deploymentTarget: 'Future' // Or make dynamic if needed
                }
            };
            await botService.createBot(botData);
            onSuccess();
            onClose();
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onClose={onClose} className="relative z-50">
            <div className="fixed inset-0 bg-black/80" aria-hidden="true" />
            <div className="fixed inset-0 flex items-center justify-center p-4">
                <Dialog.Panel className="w-full max-w-md rounded-xl bg-gray-900 p-6 border border-gray-800 animate-modal-content-slide-down">
                    <div className="flex justify-between items-center mb-6">
                        <Dialog.Title className="text-xl font-bold text-white">Create New Bot</Dialog.Title>
                        <button onClick={onClose} className="text-gray-400 hover:text-white">
                            <X size={24} />
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">

                        {/* Name Input */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Bot Name</label>
                            <input
                                type="text"
                                required
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none"
                                value={formData.name}
                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>

                        {/* Market Input */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Market</label>
                            <input
                                type="text"
                                required
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none"
                                value={formData.market}
                                onChange={e => setFormData({ ...formData, market: e.target.value })}
                            />
                        </div>

                        {/* ✅ Strategy Dropdown আপডেট */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Strategy</label>
                            <select
                                required
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none"
                                value={formData.strategy}
                                onChange={e => setFormData({ ...formData, strategy: e.target.value })}
                            >
                                <option value="" disabled>Select a Strategy</option>
                                {/* এখানে ডাইনামিক strategyOptions ম্যাপ করা হচ্ছে */}
                                {strategyOptions.map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-gray-500 mt-1 text-right">
                                Loaded {strategyOptions.length} strategies
                            </p>
                        </div>

                        {/* Timeframe Input */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Timeframe</label>
                            <select
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none"
                                value={formData.timeframe}
                                onChange={e => setFormData({ ...formData, timeframe: e.target.value })}
                            >
                                <option value="1m">1m</option>
                                <option value="5m">5m</option>
                                <option value="15m">15m</option>
                                <option value="1h">1h</option>
                                <option value="4h">4h</option>
                                <option value="1d">1d</option>
                            </select>
                        </div>

                        {/* Trade Value */}
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Trade Amount ($)</label>
                            <input
                                type="number"
                                required
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none"
                                value={formData.trade_value}
                                onChange={e => setFormData({ ...formData, trade_value: Number(e.target.value) })}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg transition-colors mt-6"
                        >
                            {loading ? 'Creating...' : 'Launch Bot'}
                        </button>
                    </form>
                </Dialog.Panel>
            </div>
        </Dialog>
    );
};

export default BotLabModal;

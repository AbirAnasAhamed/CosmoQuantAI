import React, { useState, useEffect } from 'react';
import { Dialog } from '@headlessui/react';
import { X } from 'lucide-react';
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
        strategy: '',
        timeframe: '1h',
        trade_value: 100,
    });

    // ✅ Risk Management States
    const [stopLoss, setStopLoss] = useState<number>(2.0); // 2% Default

    // Take Profit (একাধিক লেভেল হতে পারে)
    const [takeProfits, setTakeProfits] = useState([{ target: 3.0, amount: 100 }]); // Default 3% profit e 100% sell

    // Trailing Stop
    const [trailingStopEnabled, setTrailingStopEnabled] = useState(false);
    const [trailingCallback, setTrailingCallback] = useState<number>(1.0); // 1% trailing

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
                }
            };

            fetchStrategies();
            fetchApiKeys();
        }
    }, [isOpen]);

    // TP লেভেল যোগ করার ফাংশন
    const addTpLevel = () => {
        setTakeProfits([...takeProfits, { target: 0, amount: 0 }]);
    };

    // TP লেভেল আপডেট করার ফাংশন
    const updateTpLevel = (index: number, field: 'target' | 'amount', value: number) => {
        const newTps = [...takeProfits];
        newTps[index] = { ...newTps[index], [field]: value };
        setTakeProfits(newTps);
    };

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
                    deploymentTarget: 'Future',
                    // ✅ Risk Management Config পাঠানো হচ্ছে
                    riskParams: {
                        stopLoss: stopLoss,
                        takeProfits: takeProfits, // List of {target, amount}
                        trailingStop: {
                            enabled: trailingStopEnabled,
                            callbackRate: trailingCallback
                        }
                    }
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
                <Dialog.Panel className="w-full max-w-lg rounded-xl bg-gray-900 p-6 border border-gray-800 h-[90vh] overflow-y-auto">

                    {/* Header */}
                    <div className="flex justify-between items-center mb-6">
                        <Dialog.Title className="text-xl font-bold text-white">Create Intelligent Bot</Dialog.Title>
                        <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={24} /></button>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {/* Basic Info */}
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-sm text-gray-400">Bot Name</label>
                                <input type="text" required className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} />
                            </div>
                            <div>
                                <label className="text-sm text-gray-400">Market (e.g. BTC/USDT)</label>
                                <input type="text" required className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none" value={formData.market} onChange={e => setFormData({ ...formData, market: e.target.value })} />
                            </div>
                        </div>

                        {/* Strategy & Timeframe */}
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-sm text-gray-400">Strategy</label>
                                <select required className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none" value={formData.strategy} onChange={e => setFormData({ ...formData, strategy: e.target.value })}>
                                    <option value="">Select Strategy</option>
                                    {strategyOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="text-sm text-gray-400">Timeframe</label>
                                <select className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none" value={formData.timeframe} onChange={e => setFormData({ ...formData, timeframe: e.target.value })}>
                                    {['1m', '5m', '15m', '1h', '4h', '1d'].map(t => <option key={t} value={t}>{t}</option>)}
                                </select>
                            </div>
                        </div>

                        {/* Trade Amount */}
                        <div>
                            <label className="text-sm text-gray-400">Trade Amount ($)</label>
                            <input type="number" required className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none" value={formData.trade_value} onChange={e => setFormData({ ...formData, trade_value: Number(e.target.value) })} />
                        </div>

                        {/* ✅ Risk Management Section */}
                        <div className="border-t border-gray-700 pt-4 mt-4">
                            <h3 className="text-lg font-semibold text-blue-400 mb-3">Risk Management</h3>

                            {/* Stop Loss */}
                            <div className="mb-3">
                                <label className="text-sm text-gray-400">Stop Loss (%)</label>
                                <input type="number" step="0.1" className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none" value={stopLoss} onChange={e => setStopLoss(Number(e.target.value))} />
                            </div>

                            {/* Take Profit (Multiple) */}
                            <div className="mb-3">
                                <label className="text-sm text-gray-400 flex justify-between">
                                    Take Profit Targets (%)
                                    <span className="text-blue-500 cursor-pointer text-xs" onClick={addTpLevel}>+ Add Level</span>
                                </label>
                                {takeProfits.map((tp, index) => (
                                    <div key={index} className="flex gap-2 mt-2">
                                        <input type="number" placeholder="Target %" className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none w-1/2" value={tp.target} onChange={e => updateTpLevel(index, 'target', Number(e.target.value))} />
                                        <input type="number" placeholder="Sell Amount %" className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none w-1/2" value={tp.amount} onChange={e => updateTpLevel(index, 'amount', Number(e.target.value))} />
                                    </div>
                                ))}
                            </div>

                            {/* Trailing Stop */}
                            <div className="flex items-center gap-2 mt-3">
                                <input type="checkbox" checked={trailingStopEnabled} onChange={e => setTrailingStopEnabled(e.target.checked)} />
                                <label className="text-sm text-white">Enable Trailing Stop Loss</label>
                            </div>
                            {trailingStopEnabled && (
                                <div className="mt-2">
                                    <label className="text-sm text-gray-400">Callback Rate (%)</label>
                                    <input type="number" step="0.1" className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-white focus:border-blue-500 focus:outline-none" value={trailingCallback} onChange={e => setTrailingCallback(Number(e.target.value))} />
                                </div>
                            )}
                        </div>

                        <button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg transition-colors mt-6">
                            {loading ? 'Launching Bot...' : 'Launch Bot'}
                        </button>
                    </form>
                </Dialog.Panel>
            </div>
        </Dialog>
    );
};

export default BotLabModal;

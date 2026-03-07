import React from 'react';

export const BotLogsTab: React.FC = () => {
    const mockLogs = [
        { id: 1, time: '14:32:05', type: 'info', message: 'Bot initialized. Listening to Heatmap Order Flow stream.' },
        { id: 2, time: '14:35:12', type: 'signal', message: 'Detected significant buy wall at 64,500 USDT (Size: 15.4 BTC).' },
        { id: 3, time: '14:38:44', type: 'trade', message: 'Executed LONG position. Entry: 64,510 USDT | Size: 0.1 BTC.' },
        { id: 4, time: '14:45:01', type: 'warning', message: 'CVD divergence detected. Tightening stop loss by 0.5%.' },
        { id: 5, time: '15:10:22', type: 'trade', message: 'Take profit hit. Exit: 65,050 USDT. PnL: +54.00 USDT.' },
    ];

    const getLogColor = (type: string) => {
        switch (type) {
            case 'info': return 'text-blue-400';
            case 'signal': return 'text-purple-400';
            case 'trade': return 'text-green-500';
            case 'warning': return 'text-orange-400';
            default: return 'text-gray-400';
        }
    };

    return (
        <div className="w-full h-full p-6 flex flex-col">
            <div className="w-full h-full bg-[#0A0E17] rounded-xl border border-gray-800 shadow-2xl flex flex-col font-mono text-sm">
                <div className="flex items-center justify-between p-3 border-b border-gray-800 bg-[#0F1423]">
                    <div className="flex items-center space-x-2">
                        <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
                        <span className="text-gray-300 font-bold tracking-wider">TERMINAL :: ALGO_BOT_v1.0</span>
                    </div>
                    <button className="text-xs text-gray-500 hover:text-white px-2 py-1 rounded border border-gray-700 bg-gray-800/50">
                        Clear Logs
                    </button>
                </div>
                <div className="flex-1 p-4 overflow-y-auto custom-scrollbar space-y-2">
                    {mockLogs.map((log) => (
                        <div key={log.id} className="flex space-x-4 p-1 hover:bg-white/5 rounded">
                            <span className="text-gray-500 shrink-0">[{log.time}]</span>
                            <span className={`font-semibold uppercase w-16 shrink-0 ${getLogColor(log.type)}`}>
                                {log.type}
                            </span>
                            <span className="text-gray-300">{log.message}</span>
                        </div>
                    ))}
                    <div className="flex space-x-4 p-1">
                        <span className="text-gray-500">[{new Date().toLocaleTimeString('en-US', { hour12: false })}]</span>
                        <span className="font-semibold uppercase w-16 text-gray-500">WAIT</span>
                        <span className="text-gray-600 animate-pulse">Monitoring flow...</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

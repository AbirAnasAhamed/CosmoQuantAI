import React from 'react';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import CodeEditor from '@/components/common/CodeEditor';
import { AIFoundryIcon } from '@/constants';
import { CodeIcon, SaveIcon } from 'lucide-react';

interface AIStrategyLabProps {
    aiPrompt: string;
    setAiPrompt: (p: string) => void;
    handleAiGenerate: () => void;
    isGenerating: boolean;
    fileInputRef: React.RefObject<HTMLInputElement>;
    handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    handleUpload: () => void;
    fileName: string;
    strategy: string;
    currentStrategyCode: string;
    setCurrentStrategyCode: (code: string) => void;
}

export const AIStrategyLab: React.FC<AIStrategyLabProps> = ({
    aiPrompt,
    setAiPrompt,
    handleAiGenerate,
    isGenerating,
    fileInputRef,
    handleFileChange,
    handleUpload,
    fileName,
    strategy,
    currentStrategyCode,
    setCurrentStrategyCode
}) => {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
            {/* Left: Idea Input */}
            <div className="lg:col-span-1 space-y-6">
                <Card className="h-full flex flex-col">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <AIFoundryIcon className="text-purple-500" /> Idea to Strategy
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        Describe your trading logic in plain English. AI will generate the Python code for you.
                    </p>
                    <textarea
                        value={aiPrompt}
                        onChange={(e) => setAiPrompt(e.target.value)}
                        placeholder="e.g. Buy when RSI(14) crosses above 30 and price is above SMA(200). Sell when RSI crosses below 70."
                        className="flex-1 w-full bg-gray-100 dark:bg-brand-dark/50 border border-brand-border-light dark:border-brand-border-dark rounded-lg p-4 text-slate-900 dark:text-white focus:ring-brand-primary focus:border-brand-primary resize-none mb-4 min-h-[200px]"
                    />
                    <Button
                        onClick={handleAiGenerate}
                        disabled={isGenerating}
                        className="w-full bg-gradient-to-r from-purple-600 to-pink-600 border-none hover:opacity-90"
                    >
                        {isGenerating ? 'Generating...' : 'Generate Code'}
                    </Button>
                </Card>

                <Card>
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Upload Strategy</h2>
                    <div className="flex flex-col gap-3">
                        <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept=".py" />
                        <div className="flex gap-2">
                            <Button variant="secondary" onClick={() => fileInputRef.current?.click()} className="flex-1">Choose File</Button>
                            <Button onClick={handleUpload} disabled={!fileName}>Upload</Button>
                        </div>
                        <span className="text-xs text-center text-gray-400">{fileName || 'No file chosen'}</span>
                    </div>
                </Card>
            </div>

            {/* Right: Code Editor */}
            <div className="lg:col-span-2">
                <div className="bg-[#1e1e1e] rounded-lg border border-gray-700 overflow-hidden h-[600px] flex flex-col">
                    <div className="bg-[#252526] px-4 py-2 border-b border-gray-700 flex justify-between items-center">
                        <span className="text-sm text-gray-300 font-mono flex items-center gap-2">
                            <CodeIcon /> {strategy}.py
                        </span>
                        <Button size="sm" variant="outline" className="h-7 text-xs flex items-center gap-1 border-gray-600 text-gray-300">
                            <SaveIcon /> Save
                        </Button>
                    </div>
                    <div className="flex-1 relative">
                        <CodeEditor
                            value={currentStrategyCode}
                            onChange={setCurrentStrategyCode}
                            language="python"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

import React from 'react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import { MOCK_STRATEGY_TEMPLATES, MOCK_STRATEGY_PARAMS } from '../../constants';
import type { StrategyTemplate } from '../../types';

interface StrategyLibraryModalProps {
    onClose: () => void;
    onLoadTemplate: (strategyName: string, params: Record<string, any>) => void;
}

const StrategyLibraryModal: React.FC<StrategyLibraryModalProps> = ({ onClose, onLoadTemplate }) => {
    
    const handleLoad = (template: StrategyTemplate) => {
        const paramsConfig = MOCK_STRATEGY_PARAMS[template.name];
        const defaultParams = paramsConfig ? Object.fromEntries(
            Object.entries(paramsConfig).map(([key, config]) => [key, config.defaultValue])
        ) : {};
        onLoadTemplate(template.name, defaultParams);
    };

    return (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-brand-darkest w-full max-w-4xl rounded-lg shadow-2xl max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
                <div className="flex justify-between items-center p-6 border-b border-brand-border-dark/50 flex-shrink-0">
                    <h2 className="text-2xl font-bold text-white">Strategy Template Library</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
                </div>
                <div className="flex-1 overflow-y-auto p-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {MOCK_STRATEGY_TEMPLATES.map(template => (
                            <Card key={template.name} className="flex flex-col bg-brand-dark hover:bg-slate-800/80">
                                <h3 className="text-lg font-bold text-slate-900 dark:text-white">{template.title}</h3>
                                <div className="flex flex-wrap gap-1.5 my-2">
                                    {template.tags.map(tag => (
                                        <span key={tag} className="text-xs font-semibold bg-brand-primary/20 text-brand-primary px-2 py-0.5 rounded-full">{tag}</span>
                                    ))}
                                </div>
                                <p className="text-sm text-gray-500 dark:text-gray-400 flex-grow my-2">{template.description}</p>
                                <Button variant="outline" className="w-full mt-auto" onClick={() => handleLoad(template)}>
                                    Load Template
                                </Button>
                            </Card>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StrategyLibraryModal;

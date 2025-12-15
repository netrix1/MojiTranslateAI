import React from 'react';
import { Languages, Search } from 'lucide-react';

interface TranslationBlock {
    block_id: string;
    original: string;
    translation: string;
    notes?: string;
}

interface TranslationListProps {
    blocks: TranslationBlock[];
    selectedBlockId: string | null;
    onSelectBlock: (id: string) => void;
}

export const TranslationList: React.FC<TranslationListProps> = ({ blocks, selectedBlockId, onSelectBlock }) => {
    const [filter, setFilter] = React.useState('');

    const filtered = blocks.filter(b =>
        (b.original || '').toLowerCase().includes(filter.toLowerCase()) ||
        (b.translation || '').toLowerCase().includes(filter.toLowerCase())
    );

    return (
        <div className="flex flex-col h-full">
            <div className="mb-4 relative">
                <Search className="absolute left-2 top-2.5 text-slate-500" size={14} />
                <input
                    type="text"
                    placeholder="Search text..."
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="w-full bg-slate-800 text-slate-200 pl-8 pr-3 py-2 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-slate-600"
                />
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {filtered.map(block => (
                    <div
                        key={block.block_id}
                        onClick={() => onSelectBlock(block.block_id)}
                        className={`p-3 rounded border cursor-pointer transition-colors ${selectedBlockId === block.block_id
                                ? 'bg-blue-600/20 border-blue-500/50'
                                : 'bg-slate-800/50 border-slate-700 hover:border-slate-600 hover:bg-slate-800'
                            }`}
                    >
                        <div className="flex items-start gap-2 mb-1">
                            <span className="text-[10px] font-mono text-slate-500 bg-slate-900 px-1 rounded">
                                {block.block_id.split('_').pop()}
                            </span>
                            {/* Status indicator if needed */}
                        </div>

                        <p className="text-xs text-slate-400 line-clamp-2 mb-2 font-serif opacity-80" title={block.original}>
                            {block.original}
                        </p>

                        <div className="flex items-start gap-2">
                            <Languages size={12} className="mt-0.5 text-blue-400 shrink-0" />
                            <p className="text-sm text-slate-200 line-clamp-3 leading-snug">
                                {block.translation || <span className="text-slate-600 italic">No translation</span>}
                            </p>
                        </div>
                    </div>
                ))}

                {filtered.length === 0 && (
                    <div className="text-center text-slate-500 text-xs py-10">
                        No blocks found matching "{filter}"
                    </div>
                )}
            </div>
        </div>
    );
};

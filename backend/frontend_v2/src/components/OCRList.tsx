import React from 'react';
import type { OCRBlock, Region } from '../types';
import { useLanguage } from '../contexts/LanguageContext';
import { Type, AlignLeft, GripVertical } from 'lucide-react';
import { getRegionColor } from '../utils';

interface OCRListProps {
    blocks: OCRBlock[];
    regions: Region[];
    selectedBlockIndex: number | null;
    onSelectBlock: (index: number | null) => void;
    onUpdateBlock: (index: number, text: string) => void;
}

export const OCRList: React.FC<OCRListProps> = ({
    blocks,
    regions,
    selectedBlockIndex,
    onSelectBlock,
    onUpdateBlock
}) => {
    const { t } = useLanguage();

    if (blocks.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-slate-500 h-full">
                <Type size={48} className="mb-4 opacity-20" />
                <p className="text-sm text-center">{t('noOCR')}</p>
            </div>
        );
    }

    // Sort blocks by reading_order if available
    const sortedBlocks = blocks.map((b, i) => ({ ...b, originalIndex: i }))
        .sort((a, b) => (a.reading_order || 0) - (b.reading_order || 0));

    return (
        <div className="flex flex-col h-full bg-slate-900 border-r border-slate-700 w-80">
            <div className="p-4 border-b border-slate-700 bg-slate-800">
                <h2 className="text-sm font-semibold text-slate-100 uppercase tracking-wider flex items-center gap-2">
                    <AlignLeft size={16} />
                    {t('ocrEditor')}
                </h2>
                <div className="text-xs text-slate-400 mt-1">
                    {blocks.length} {t('textBlock')}(s)
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {sortedBlocks.map((block, idx) => {
                    const region = regions.find(r => r.region_id === block.region_id);
                    const color = region ? getRegionColor(region.type_hint) : '#64748b'; // default slate-500

                    return (
                        <div
                            key={idx}
                            className={`p-3 rounded border transition-all ${selectedBlockIndex === block.originalIndex
                                ? 'bg-slate-800 border-blue-500 shadow-lg'
                                : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
                                }`}
                            onClick={() => onSelectBlock(block.originalIndex)}
                        >
                            <div className="flex items-start gap-2 mb-2">
                                <div
                                    className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold text-white shrink-0 mt-0.5"
                                    style={{ backgroundColor: color }}
                                >
                                    {block.reading_order || idx + 1}
                                </div>
                                <div className="text-xs text-slate-400 truncate flex-1 font-mono">
                                    IDs: {block.region_id || 'N/A'}
                                </div>
                                <GripVertical size={14} className="text-slate-600 cursor-grab" />
                            </div>

                            <textarea
                                className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-slate-200 focus:border-blue-500 outline-none resize-none min-h-[80px]"
                                value={block.original_text || block.text || ''}
                                onChange={(e) => onUpdateBlock(block.originalIndex, e.target.value)}
                                onClick={(e) => e.stopPropagation()} // Prevent selecting card when clicking input
                            />
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

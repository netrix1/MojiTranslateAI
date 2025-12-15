import React from 'react';
import { Trash2, Eye, MapPin, Pencil } from 'lucide-react';
import { getRegionColor } from '../utils';
import type { Region } from '../types';
import { useLanguage } from '../contexts/LanguageContext';
import { LanguageSelector } from './LanguageSelector';

interface RegionListProps {
    regions: Region[];
    selectedId: string | null;
    onSelect: (id: string) => void;
    onDelete: (id: string) => void;
    onEdit: (region: Region) => void;
}

export const RegionList: React.FC<RegionListProps> = ({ regions, selectedId, onSelect, onDelete, onEdit }) => {
    const { t } = useLanguage();

    return (
        <div className="flex flex-col h-full bg-slate-900 border-r border-slate-800 w-80">
            <div className="p-4 border-b border-slate-800">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">{t('regions')} ({regions.length})</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {regions.map((r) => {
                    const isSelected = selectedId === r.region_id;
                    const color = getRegionColor(r.type_hint);
                    return (
                        <div
                            key={r.region_id}
                            className={`flex items-center justify-between p-2 rounded cursor-pointer transition-colors ${isSelected ? 'bg-slate-800 border border-slate-700' : 'hover:bg-slate-800/50 border border-transparent'
                                }`}
                            onClick={() => onSelect(r.region_id)}
                        >
                            <div className="flex items-center gap-3">
                                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                                <div className="text-xs">
                                    <div className="font-medium text-slate-200">ID: {r.region_id}</div>
                                    <div className="text-slate-500">{r.type_hint}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-1">
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onEdit(r);
                                    }}
                                    className="p-1 hover:text-blue-400 text-slate-600 transition-colors"
                                    title={t('editProperties')}
                                >
                                    <Pencil size={14} />
                                </button>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDelete(r.region_id);
                                    }}
                                    className="p-1 hover:text-red-400 text-slate-600 transition-colors"
                                    title={t('delete')}
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
            <div className="p-4 border-t border-slate-800 bg-slate-900">
                <LanguageSelector />
            </div>
        </div>
    );
};

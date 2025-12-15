import React, { useState, useEffect } from 'react';
import type { Region } from '../types';
import { REGION_COLORS } from '../utils';
import { useLanguage } from '../contexts/LanguageContext';
import { HelpCircle } from 'lucide-react';
import { translations } from '../translations';

interface EditRegionModalProps {
    isOpen: boolean;
    region: Region | null;
    onClose: () => void;
    onSave: (id: string, newId: string, newType: string) => void;
}

export const EditRegionModal: React.FC<EditRegionModalProps> = ({ isOpen, region, onClose, onSave }) => {
    const { t, language } = useLanguage();
    const [editId, setEditId] = useState('');
    const [editType, setEditType] = useState('unknown');

    useEffect(() => {
        if (region) {
            setEditId(region.region_id);
            setEditType(region.type_hint || 'unknown');
        }
    }, [region]);

    if (!isOpen || !region) return null;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSave(region.region_id, editId, editType);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-700 p-6 rounded-lg w-96 shadow-xl relative">
                <h3 className="text-lg font-semibold text-white mb-4">{t('editRegion')}</h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">{t('regionIdName')}</label>
                        <input
                            type="text"
                            className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none"
                            value={editId}
                            onChange={e => setEditId(e.target.value)}
                        />
                    </div>
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <label className="block text-xs font-medium text-slate-400">{t('type')}</label>
                            <div className="group relative">
                                <HelpCircle size={14} className="text-slate-500 hover:text-blue-400 cursor-help" />
                                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-slate-800 border border-slate-700 rounded shadow-xl text-xs text-slate-300 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 pointer-events-none">
                                    <h4 className="font-bold text-white mb-2">{t('typeHelp')}</h4>
                                    <div className="space-y-1.5">
                                        {Object.keys(REGION_COLORS).map(type => (
                                            <div key={type} className="flex items-center gap-2">
                                                <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: REGION_COLORS[type as keyof typeof REGION_COLORS] }} />
                                                <span className="font-medium text-slate-200 capitalize">{type}:</span>
                                                <span className="text-slate-400">
                                                    {/* @ts-ignore -- dynamic key access for translations */}
                                                    {translations[language].types?.[type as keyof typeof translations['en']['types']] || type}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-2 h-2 bg-slate-800 border-r border-b border-slate-700 rotate-45 -mt-1"></div>
                                </div>
                            </div>
                        </div>
                        <select
                            className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-white focus:border-blue-500 outline-none"
                            value={editType}
                            onChange={e => setEditType(e.target.value)}
                        >
                            {Object.keys(REGION_COLORS).map(type => (
                                <option key={type} value={type}>{type}</option>
                            ))}
                        </select>
                    </div>
                    <div className="flex justify-end gap-2 mt-6">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-3 py-1.5 text-slate-300 hover:text-white text-sm"
                        >
                            {t('cancel')}
                        </button>
                        <button
                            type="submit"
                            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm font-medium"
                        >
                            {t('save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

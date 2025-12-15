import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { ChevronUp, Check } from 'lucide-react';

export const LanguageSelector: React.FC = () => {
    const { language, setLanguage } = useLanguage();
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const languages = [
        { code: 'pt', name: 'Português (Brasil)', flag: 'https://flagcdn.com/w40/br.png' },
        { code: 'en', name: 'English', flag: 'https://flagcdn.com/w40/us.png' }
    ] as const;

    const currentLang = languages.find(l => l.code === language) || languages[0];

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center justify-between w-full p-2 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 transition-colors text-slate-200 text-xs"
            >
                <div className="flex items-center gap-2">
                    <img src={currentLang.flag} alt={currentLang.code} className="w-5 h-auto rounded-sm object-cover" />
                    <span>{currentLang.name}</span>
                </div>
                <ChevronUp size={14} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute bottom-full left-0 w-full mb-1 bg-slate-800 border border-slate-700 rounded shadow-xl overflow-hidden z-20">
                    {languages.map((lang) => (
                        <button
                            key={lang.code}
                            onClick={() => {
                                setLanguage(lang.code);
                                setIsOpen(false);
                            }}
                            className={`flex items-center justify-between w-full p-2 text-xs hover:bg-slate-700 transition-colors ${language === lang.code ? 'bg-slate-700/50 text-white' : 'text-slate-300'
                                }`}
                        >
                            <div className="flex items-center gap-2">
                                <img src={lang.flag} alt={lang.code} className="w-5 h-auto rounded-sm" />
                                <span>{lang.name}</span>
                            </div>
                            {language === lang.code && <Check size={12} className="text-blue-400" />}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

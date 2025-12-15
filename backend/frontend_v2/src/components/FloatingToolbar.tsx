import React, { useEffect, useState } from 'react';
import {
    Bold, Italic, AlignLeft, AlignCenter, AlignRight,
    Type, Palette, Trash2, Move
} from 'lucide-react';
import type { RenderingStyle } from '../types';

interface FloatingToolbarProps {
    style: RenderingStyle;
    onChange: (updates: Partial<RenderingStyle>) => void;
    onDelete?: () => void;
    position?: { x: number, y: number }; // Optional override
}

export const FloatingToolbar: React.FC<FloatingToolbarProps> = ({ style, onChange, onDelete, position }) => {
    // Helper to update style safely
    const update = (key: keyof RenderingStyle, value: any) => {
        onChange({ [key]: value });
    };

    return (
        <div
            className="absolute z-[100] flex flex-col gap-2 bg-white rounded-lg shadow-xl border border-slate-200 p-2 animate-in fade-in zoom-in duration-200"
            style={position ? { left: position.x, top: position.y, transform: 'translate(-50%, -100%)' } : {}}
            onMouseDown={(e) => e.stopPropagation()} // Prevent drag/selection on toolbar interaction
        >
            {/* Row 1: Font Family & Size */}
            <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
                <select
                    className="h-8 bg-slate-50 border border-slate-200 rounded px-2 text-xs text-slate-700 outline-none hover:border-blue-400 focus:border-blue-500 transition-colors"
                    value={style.font_family || "dialogue"}
                    onChange={(e) => update('font_family', e.target.value)}
                    title="Font Family"
                >
                    <option value="dialogue">Manga Dialogue</option>
                    <option value="shout">Shout / VFX</option>
                    <option value="standard">Standard Sans</option>
                    <option value="handwritten">Handwritten</option>
                    <option value="square_box">Square / Box</option>
                </select>

                <div className="flex items-center bg-slate-50 border border-slate-200 rounded px-1">
                    <span className="text-[10px] text-slate-400 mr-1 uppercase">Size</span>
                    <input
                        type="number"
                        min="1"
                        max="20"
                        step="0.5"
                        className="w-10 h-7 bg-transparent text-sm text-slate-700 outline-none text-center"
                        value={style.font_size || 5}
                        onChange={(e) => update('font_size', parseFloat(e.target.value))}
                    />
                </div>

                {/* Advanced: Stroke Width & Line Height moved to top row */}
                <div className="flex items-center gap-1 ml-2">
                    <div className="flex items-center bg-slate-50 border border-slate-200 rounded px-1" title="Stroke Width">
                        <span className="text-[9px] text-slate-400 mr-1">SW</span>
                        <input
                            type="number"
                            min="0"
                            max="10"
                            step="0.5"
                            className="w-8 h-6 bg-transparent text-xs text-slate-700 outline-none text-center"
                            value={style.stroke_width !== undefined ? style.stroke_width : 2}
                            onChange={(e) => update('stroke_width', parseFloat(e.target.value))}
                        />
                    </div>
                    <div className="flex items-center bg-slate-50 border border-slate-200 rounded px-1" title="Line Spacing">
                        <span className="text-[9px] text-slate-400 mr-1">LH</span>
                        <input
                            type="number"
                            min="0.5"
                            max="3"
                            step="0.1"
                            className="w-8 h-6 bg-transparent text-xs text-slate-700 outline-none text-center"
                            value={style.line_spacing || 1.2}
                            onChange={(e) => update('line_spacing', parseFloat(e.target.value))}
                        />
                    </div>
                </div>
            </div>

            {/* Row 2: Formatting */}
            <div className="flex items-center gap-1 justify-between">
                <div className="flex items-center gap-1">
                    <button
                        className={`p-1.5 rounded hover:bg-slate-100 ${style.is_bold ? 'bg-blue-50 text-blue-600' : 'text-slate-600'}`}
                        onClick={() => update('is_bold', !style.is_bold)}
                        title="Bold"
                    >
                        <Bold size={14} />
                    </button>
                    <button
                        className={`p-1.5 rounded hover:bg-slate-100 ${style.is_italic ? 'bg-blue-50 text-blue-600' : 'text-slate-600'}`}
                        onClick={() => update('is_italic', !style.is_italic)}
                        title="Italic"
                    >
                        <Italic size={14} />
                    </button>

                    <div className="w-px h-4 bg-slate-200 mx-1" />

                    <button
                        className={`p-1.5 rounded hover:bg-slate-100 ${style.alignment === 'left' ? 'bg-blue-50 text-blue-600' : 'text-slate-600'}`}
                        onClick={() => update('alignment', 'left')}
                    >
                        <AlignLeft size={14} />
                    </button>
                    <button
                        className={`p-1.5 rounded hover:bg-slate-100 ${(!style.alignment || style.alignment === 'center') ? 'bg-blue-50 text-blue-600' : 'text-slate-600'}`}
                        onClick={() => update('alignment', 'center')}
                    >
                        <AlignCenter size={14} />
                    </button>
                    <button
                        className={`p-1.5 rounded hover:bg-slate-100 ${style.alignment === 'right' ? 'bg-blue-50 text-blue-600' : 'text-slate-600'}`}
                        onClick={() => update('alignment', 'right')}
                    >
                        <AlignRight size={14} />
                    </button>
                </div>

                <div className="w-px h-4 bg-slate-200 mx-1" />

                {/* Colors */}
                <div className="flex items-center gap-1">
                    <div
                        className="w-5 h-5 rounded border border-slate-300 cursor-pointer overflow-hidden relative"
                        title="Text Color"
                    >
                        <div className="absolute inset-0 bg-white" />
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="font-bold text-[10px]" style={{ color: style.text_color || '#000' }}>A</span>
                        </div>
                        <input
                            type="color"
                            className="opacity-0 absolute inset-0 cursor-pointer w-full h-full"
                            value={style.text_color || "#ffffff"}
                            onChange={(e) => update('text_color', e.target.value)}
                        />
                    </div>

                    <div
                        className="w-5 h-5 rounded border border-slate-300 cursor-pointer overflow-hidden relative"
                        title="Stroke / Border Color"
                    >
                        <div className="absolute inset-0 bg-white" />
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-2.5 h-2.5 border-2 rounded-sm" style={{ borderColor: style.stroke_color || '#fff' }} />
                        </div>
                        <input
                            type="color"
                            className="opacity-0 absolute inset-0 cursor-pointer w-full h-full"
                            value={style.stroke_color || "#000000"}
                            onChange={(e) => update('stroke_color', e.target.value)}
                        />
                    </div>
                </div>



                {onDelete && (
                    <>
                        <div className="w-px h-4 bg-slate-200 mx-1" />
                        <button
                            className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors"
                            onClick={onDelete}
                            title="Delete Block"
                        >
                            <Trash2 size={14} />
                        </button>
                    </>
                )}
            </div>
        </div>
    );
};

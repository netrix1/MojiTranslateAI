import React from 'react';
import type { RenderingStyle } from '../types';

interface StyleEditorProps {
    style: RenderingStyle;
    onChange: (style: RenderingStyle) => void;
}

const FONT_OPTIONS = [
    { value: 'dialogue', label: 'Manga Dialogue (Ames)' },
    { value: 'shout', label: 'Shout (Comic)' },
    { value: 'square_box', label: 'Narration (Arial)' },
];

export const StyleEditor: React.FC<StyleEditorProps> = ({ style, onChange }) => {

    const update = (key: keyof RenderingStyle, val: any) => {
        onChange({ ...style, [key]: val });
    };

    return (
        <div className="bg-slate-800 p-2 rounded mt-2 text-xs flex flex-wrap gap-4 items-center border border-slate-700">
            {/* Font */}
            <div className="flex flex-col gap-1">
                <label className="text-slate-500 font-bold uppercase text-[10px]">Font</label>
                <select
                    value={style.font_family || 'dialogue'}
                    onChange={(e) => update('font_family', e.target.value)}
                    className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-1 py-1 w-32 focus:outline-none"
                    style={{ fontFamily: style.font_family === 'dialogue' ? 'Manga Dialogue' : style.font_family === 'shout' ? 'Shout' : 'Arial' }}
                >
                    {FONT_OPTIONS.map(opt => (
                        <option
                            key={opt.value}
                            value={opt.value}
                            style={{
                                fontFamily: opt.value === 'dialogue' ? 'Manga Dialogue' : opt.value === 'shout' ? 'Shout' : 'Arial'
                            }}
                        >
                            {opt.label}
                        </option>
                    ))}
                </select>
            </div>

            {/* Colors */}
            <div className="flex flex-col gap-1">
                <label className="text-slate-500 font-bold uppercase text-[10px]">Text</label>
                <div className="flex items-center gap-1">
                    <input
                        type="color"
                        value={style.text_color || '#000000'}
                        onChange={(e) => update('text_color', e.target.value)}
                        className="w-6 h-6 rounded cursor-pointer bg-transparent border-none"
                    />
                </div>
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-slate-500 font-bold uppercase text-[10px]">Stroke Color</label>
                <div className="flex items-center gap-1">
                    <input
                        type="color"
                        value={style.stroke_color || '#ffffff'}
                        onChange={(e) => update('stroke_color', e.target.value)}
                        className="w-6 h-6 rounded cursor-pointer bg-transparent border-none"
                    />
                </div>
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-slate-500 font-bold uppercase text-[10px]">Border Width</label>
                <div className="flex items-center gap-1">
                    <input
                        type="number"
                        min={0} max={20}
                        value={style.stroke_width ?? 3}
                        onChange={(e) => update('stroke_width', parseInt(e.target.value))}
                        className="bg-slate-900 border border-slate-700 w-12 px-1 py-1 rounded text-center"
                        title="Width px"
                    />
                    <span className="text-xs text-slate-500">px</span>
                </div>
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-slate-500 font-bold uppercase text-[10px]">Size (%)</label>
                <div className="flex items-center gap-1">
                    <input
                        type="number"
                        min={0.5} max={15} step={0.1}
                        value={style.font_size ?? ''}
                        onChange={(e) => update('font_size', parseFloat(e.target.value))}
                        placeholder="Auto"
                        className="bg-slate-900 border border-slate-700 w-14 px-1 py-1 rounded text-center"
                        title="Scale relative to image width (1-10)"
                    />
                </div>
            </div>

            <div className="flex flex-col gap-1 border-l border-slate-700 pl-2">
                <label className="text-slate-500 font-bold uppercase text-[10px]">Rotate</label>
                <div className="flex items-center gap-1">
                    <input
                        type="number"
                        min={-180} max={180}
                        value={style.angle ?? 0}
                        onChange={(e) => update('angle', parseInt(e.target.value))}
                        className="bg-slate-900 border border-slate-700 w-12 px-1 py-1 rounded text-center"
                        title="Angle (degrees)"
                    />
                    <span className="text-xs text-slate-500">°</span>
                </div>
            </div>

            <div className="flex flex-col gap-1">
                <label className="text-slate-500 font-bold uppercase text-[10px]">Box Scale</label>
                <div className="flex items-center gap-1">
                    <input
                        type="number"
                        min={0.5} max={3.0} step={0.1}
                        value={style.box_scale ?? 1.0}
                        onChange={(e) => update('box_scale', parseFloat(e.target.value))}
                        className="bg-slate-900 border border-slate-700 w-12 px-1 py-1 rounded text-center"
                        title="Scale Polygon (0.5x to 3.0x)"
                    />
                    <span className="text-xs text-slate-500">x</span>
                </div>
            </div>

            {/* Toggles */}
            <div className="flex items-center gap-2 mt-4">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                        type="checkbox"
                        checked={!!style.is_bold}
                        onChange={(e) => update('is_bold', e.target.checked)}
                        className="rounded bg-slate-700 border-slate-600 text-blue-500 focus:ring-0"
                    />
                    <span className="text-slate-300">Bold</span>
                </label>
            </div>
        </div>
    );
};

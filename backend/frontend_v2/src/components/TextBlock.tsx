import React, { useRef, useEffect, useState } from 'react';
import type { OCRBlock, RenderingStyle } from '../types';

interface TextBlockProps {
    block: OCRBlock;
    isSelected: boolean;
    onSelect: () => void;
    onUpdate: (updates: Partial<OCRBlock>) => void;
    scale?: number; // Screen scale if needed, for now assuming 1:1 with image pixels
}

const FONT_MAP: Record<string, string> = {
    'manga': 'Manga Dialogue',
    'dialogue': 'Manga Dialogue', // Match backend default
    'shout': 'Shout',
    'standard': 'Inter',
    'handwritten': 'Manga Dialogue',
    'square_box': 'Inter'
};

const calculatePixels = (size?: number) => (size || 7.5) * 4;

export const TextBlock: React.FC<TextBlockProps> = ({ block, isSelected, onSelect, onUpdate }) => {
    const [isEditing, setIsEditing] = useState(false);
    const contentRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const style = block.rendering_style || {};
    const [x1, y1, x2, y2] = block.bbox || [0, 0, 100, 100];
    const width = x2 - x1;
    const height = y2 - y1;
    const angle = style.angle || 0;

    // Derived CSS styles
    const cssFontFamily = FONT_MAP[style.font_family?.toLowerCase() || 'manga'] || 'Manga Dialogue';
    const cssFontSize = `${calculatePixels(style.font_size)}px`;
    const cssFontWeight = style.is_bold ? 'bold' : 'normal';
    const cssFontStyle = style.is_italic ? 'italic' : 'normal';
    const cssTextAlign = (style.alignment as any) || 'center';
    const cssColor = style.text_color || 'black';
    // Stroke simulation
    const strokeW = style.stroke_width || 2; // px
    const strokeC = style.stroke_color || 'white';
    const cssTextShadow = style.stroke_color ?
        `-${strokeW}px -${strokeW}px 0 ${strokeC}, 
         ${strokeW}px -${strokeW}px 0 ${strokeC}, 
         -${strokeW}px ${strokeW}px 0 ${strokeC}, 
         ${strokeW}px ${strokeW}px 0 ${strokeC}`
        : 'none';


    // Sync content on mount/change
    useEffect(() => {
        if (contentRef.current && contentRef.current.innerText !== block.translation) {
            contentRef.current.innerText = block.translation || "";
        }
    }, [block.translation]);

    // Rotation Logic
    const handleRotateStart = (e: React.MouseEvent) => {
        e.stopPropagation();
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;

        // Center of the box in screen coordinates
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        const onMouseMove = (moveEvent: MouseEvent) => {
            const dx = moveEvent.clientX - centerX;
            const dy = moveEvent.clientY - centerY;
            // Calculate angle in degrees
            let deg = Math.atan2(dy, dx) * (180 / Math.PI);
            // Offset by 90 degrees because handle is at -90 (top)
            deg += 90;

            onUpdate({ rendering_style: { ...style, angle: deg } });
        };

        const onMouseUp = () => {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };

        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    };

    // Drag Logic
    const handleMouseDown = (e: React.MouseEvent) => {
        if (isEditing) return; // Allow text selection if editing
        e.stopPropagation();
        onSelect();

        const startX = e.clientX;
        const startY = e.clientY;
        const startLeft = x1;
        const startTop = y1;

        const onMouseMove = (moveEvent: MouseEvent) => {
            const dx = moveEvent.clientX - startX;
            const dy = moveEvent.clientY - startY;

            const newX1 = startLeft + dx;
            const newY1 = startTop + dy;
            const newX2 = newX1 + width;
            const newY2 = newY1 + height;

            onUpdate({ bbox: [newX1, newY1, newX2, newY2] });
        };

        const onMouseUp = () => {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };

        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    };

    // Resize Logic (Corner Handle)
    const handleResizeStart = (e: React.MouseEvent, corner: 'se' | 'sw' | 'ne' | 'nw') => {
        e.stopPropagation();
        const startX = e.clientX;
        const startY = e.clientY;
        // Basic resize logic (doesn't account for rotation perfectly but usable for MVP)
        // Ideally should project mouse delta onto local axis if robust rotation resize needed.
        // For MVP, we stick to non-rotated resize math or simple bbox updates.
        // NOTE: Resizing a rotated div by changing width/height usually works fine with CSS transform.

        const startBox = { x1, y1, x2, y2 };

        const onMouseMove = (moveEvent: MouseEvent) => {
            const dx = moveEvent.clientX - startX;
            const dy = moveEvent.clientY - startY;

            let newBox = { ...startBox };

            if (corner === 'se') {
                newBox.x2 = startBox.x2 + dx;
                newBox.y2 = startBox.y2 + dy;
            } else if (corner === 'sw') {
                newBox.x1 = startBox.x1 + dx;
                newBox.y2 = startBox.y2 + dy;
            } else if (corner === 'ne') {
                newBox.x2 = startBox.x2 + dx;
                newBox.y1 = startBox.y1 + dy;
            } else if (corner === 'nw') {
                newBox.x1 = startBox.x1 + dx;
                newBox.y1 = startBox.y1 + dy;
            }

            if (newBox.x2 - newBox.x1 < 20) newBox.x2 = newBox.x1 + 20;
            if (newBox.y2 - newBox.y1 < 20) newBox.y2 = newBox.y1 + 20;

            onUpdate({ bbox: [newBox.x1, newBox.y1, newBox.x2, newBox.y2] });
        };

        const onMouseUp = () => {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };

        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    };


    return (
        <div
            ref={containerRef}
            className={`absolute select-none group ${isSelected ? 'z-50' : 'z-10'}`}
            style={{
                left: x1,
                top: y1,
                width: width,
                height: height,
                transform: `rotate(${angle}deg)`,
                outline: isSelected ? '2px solid #3b82f6' : '1px dashed rgba(255,255,255,0.2)',
                cursor: isEditing ? 'text' : 'move'
            }}
            onMouseDown={handleMouseDown}
            onDoubleClick={(e) => {
                e.stopPropagation();
                setIsEditing(true);
                setTimeout(() => {
                    if (contentRef.current) {
                        contentRef.current.focus();
                        document.execCommand('selectAll', false, undefined);
                    }
                }, 0);
            }}
        >
            {/* The Text Content */}
            <div
                ref={contentRef}
                contentEditable={isEditing}
                suppressContentEditableWarning
                className="w-full h-full outline-none p-1 flex flex-col justify-center"
                style={{
                    fontFamily: `${cssFontFamily}, sans-serif`,
                    fontSize: cssFontSize,
                    fontWeight: cssFontWeight,
                    fontStyle: cssFontStyle,
                    textAlign: cssTextAlign,
                    color: cssColor,
                    textShadow: cssTextShadow,
                    lineHeight: style.line_spacing || 1.2,
                    whiteSpace: 'pre-wrap',
                    overflow: 'hidden',
                    wordBreak: 'break-word',
                    userSelect: isEditing ? 'text' : 'none',
                    pointerEvents: isEditing ? 'auto' : 'none'
                }}
                onBlur={(e) => {
                    setIsEditing(false);
                    if (onUpdate) {
                        onUpdate({ translation: e.target.innerText });
                    }
                }}
                onKeyDown={(e) => {
                    if (e.key === 'Escape') {
                        setIsEditing(false);
                        containerRef.current?.focus();
                    }
                    e.stopPropagation();
                }}
            />

            {/* Controls */}
            {isSelected && !isEditing && (
                <>
                    {/* Rotation Handle */}
                    <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 h-8 w-px bg-blue-500 z-50 pointer-events-none">
                        <div
                            className="absolute -top-1.5 -left-1.5 w-3 h-3 bg-white border border-blue-500 rounded-full cursor-grab pointer-events-auto hover:bg-blue-50 transition-colors shadow-sm"
                            onMouseDown={handleRotateStart}
                            title="Rotate"
                        />
                    </div>

                    {/* Resize Handles */}
                    {/* SE */}
                    <div
                        className="absolute -bottom-1.5 -right-1.5 w-3 h-3 bg-white border border-blue-500 rounded-full cursor-se-resize z-50 hover:scale-125 transition-transform"
                        onMouseDown={(e) => handleResizeStart(e, 'se')}
                    />
                    {/* SW */}
                    <div
                        className="absolute -bottom-1.5 -left-1.5 w-3 h-3 bg-white border border-blue-500 rounded-full cursor-sw-resize z-50 hover:scale-125 transition-transform"
                        onMouseDown={(e) => handleResizeStart(e, 'sw')}
                    />
                    {/* NE */}
                    <div
                        className="absolute -top-1.5 -right-1.5 w-3 h-3 bg-white border border-blue-500 rounded-full cursor-ne-resize z-50 hover:scale-125 transition-transform"
                        onMouseDown={(e) => handleResizeStart(e, 'ne')}
                    />
                    {/* NW */}
                    <div
                        className="absolute -top-1.5 -left-1.5 w-3 h-3 bg-white border border-blue-500 rounded-full cursor-nw-resize z-50 hover:scale-125 transition-transform"
                        onMouseDown={(e) => handleResizeStart(e, 'nw')}
                    />
                </>
            )}
        </div>
    );
};

import React, { useEffect, useState, useRef } from 'react';
import type { OCRBlock, RenderingStyle } from '../types';
import { TextBlock } from './TextBlock';
import { FloatingToolbar } from './FloatingToolbar';

interface NewFinalEditorProps {
    imageUrl?: string;
    blocks?: OCRBlock[];
    onUpdateBlock?: (blockId: string, updates: Partial<OCRBlock>) => void;
}

export const NewFinalEditor: React.FC<NewFinalEditorProps> = ({ imageUrl = "", blocks = [], onUpdateBlock }) => {
    const [imageSize, setImageSize] = useState<{ width: number, height: number } | null>(null);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Load image size
    useEffect(() => {
        if (!imageUrl) return;
        const img = new Image();
        img.src = imageUrl;
        img.onload = () => {
            setImageSize({ width: img.width, height: img.height });
        };
    }, [imageUrl]);

    const handleBackgroundClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) {
            setSelectedId(null);
        }
    };

    const selectedBlock = blocks.find(b => b.block_id === selectedId);

    const handleWheel = (e: React.WheelEvent) => {
        if (selectedId && e.shiftKey && selectedBlock && onUpdateBlock) {
            // Prevent default scroll if possible (might need native listener for robust prevention, but let's try)
            // React 17+ might not prevent default on wheel easily due to passive listeners.

            const currentSize = selectedBlock.rendering_style?.font_size || 7.5;
            const delta = e.deltaY < 0 ? 0.1 : -0.1;
            const newSize = Math.max(1, parseFloat((currentSize + delta).toFixed(1)));

            onUpdateBlock(selectedBlock.block_id!, {
                rendering_style: {
                    ...selectedBlock.rendering_style,
                    font_size: newSize
                }
            });
        }
    };

    if (!imageSize) {
        return <div className="text-slate-400 flex items-center justify-center h-full">Loading Redrawn Page...</div>;
    }

    return (
        <div className="bg-slate-900 overflow-auto h-full flex justify-center p-8">
            <div
                className="relative bg-white shadow-2xl transition-all duration-300"
                style={{
                    width: imageSize.width,
                    height: imageSize.height,
                    backgroundImage: `url(${imageUrl})`,
                    backgroundSize: 'contain',
                    backgroundRepeat: 'no-repeat'
                }}
                onMouseDown={handleBackgroundClick} // Deselect on bg click
                onWheel={handleWheel}
            >
                {/* Blocks Layer */}
                {blocks.map((block) => {
                    const isSelected = selectedId === block.block_id;
                    return (
                        <TextBlock
                            key={block.block_id}
                            block={block}
                            isSelected={isSelected}
                            onSelect={() => setSelectedId(block.block_id || null)}
                            onUpdate={(updates) => {
                                if (block.block_id && onUpdateBlock) {
                                    onUpdateBlock(block.block_id, updates);
                                }
                            }}
                        />
                    );
                })}

                {/* Floating Toolbar */}
                {selectedBlock && selectedBlock.bbox && (
                    <FloatingToolbar
                        style={selectedBlock.rendering_style || {}}
                        onChange={(updates) => {
                            if (selectedBlock.block_id && onUpdateBlock) {
                                onUpdateBlock(selectedBlock.block_id, { rendering_style: { ...selectedBlock.rendering_style, ...updates } });
                            }
                        }}
                        onDelete={() => {
                            if (confirm("Delete this text block?")) {
                                setSelectedId(null);
                                // Optional: Call parent delete handler if needed
                            }
                        }}
                        position={{
                            x: selectedBlock.bbox[0] + (selectedBlock.bbox[2] - selectedBlock.bbox[0]) / 2,
                            y: Math.max(0, selectedBlock.bbox[1] - 50)
                        }}
                    />
                )}
            </div>
        </div>
    );
};

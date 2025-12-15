import React, { useRef, useEffect, useState } from 'react';
import { Stage, Layer, Image as KonvaImage, Rect, Text, Group } from 'react-konva';
import type { OCRBlock, Region } from '../types';
import { bboxToRect, getRegionColor } from '../utils';

// Custom hook to avoid dependency issues with use-image
const useImage = (url: string, crossOrigin?: "anonymous" | "use-credentials") => {
    const [image, setImage] = React.useState<HTMLImageElement>();
    const [status, setStatus] = React.useState('loading');

    useEffect(() => {
        if (!url) return;
        const img = document.createElement('img');

        function onload() {
            setStatus('loaded');
            setImage(img);
        }

        function onerror() {
            setStatus('failed');
            setImage(undefined);
        }

        img.addEventListener('load', onload);
        img.addEventListener('error', onerror);

        if (crossOrigin) img.crossOrigin = crossOrigin;
        img.src = url;

        return () => {
            img.removeEventListener('load', onload);
            img.removeEventListener('error', onerror);
        };
    }, [url, crossOrigin]);

    return [image, status] as const;
};

interface OCREditorProps {
    imageUrl: string;
    blocks: OCRBlock[];
    regions: Region[];
    selectedBlockIndex: number | null;
    onSelectBlock: (index: number | null) => void;
    onUpdateBlock: (index: number, text: string) => void;
}

export const OCREditor: React.FC<OCREditorProps> = ({
    imageUrl,
    blocks,
    regions,
    selectedBlockIndex,
    onSelectBlock
}) => {
    const [image] = useImage(imageUrl);
    const stageRef = useRef<any>(null);

    // Deselect when clicking on empty stage
    const checkDeselect = (e: any) => {
        const clickedOnEmpty = e.target === e.target.getStage();
        if (clickedOnEmpty) {
            onSelectBlock(null);
        }
    };

    return (
        <div className="flex-1 bg-slate-900 overflow-hidden relative flex items-center justify-center">
            {image && (
                <Stage
                    width={image.width}
                    height={image.height}
                    onMouseDown={checkDeselect}
                    onTouchStart={checkDeselect}
                    ref={stageRef}
                    style={{ backgroundColor: '#0f172a' }} // slate-950
                >
                    <Layer>
                        <KonvaImage image={image} />

                        {/* Render all blocks as semi-transparent overlays with text */}
                        {blocks.map((block, i) => {
                            if (!block.bbox) return null;
                            const rect = bboxToRect(block.bbox);
                            const region = regions.find(r => r.region_id === block.region_id);
                            const color = region ? getRegionColor(region.type_hint) : '#64748b';
                            const isSelected = i === selectedBlockIndex;

                            return (
                                <Group
                                    key={i}
                                    x={rect.x}
                                    y={rect.y}
                                    onClick={() => onSelectBlock(i)}
                                    onTap={() => onSelectBlock(i)}
                                    onMouseEnter={(e) => {
                                        const container = e.target.getStage()?.container();
                                        if (container) container.style.cursor = 'pointer';
                                    }}
                                    onMouseLeave={(e) => {
                                        const container = e.target.getStage()?.container();
                                        if (container) container.style.cursor = 'default';
                                    }}
                                >
                                    {/* Reading Order Badge */}
                                    <Rect
                                        x={-10}
                                        y={-10}
                                        width={20}
                                        height={20}
                                        fill={color}
                                        cornerRadius={4}
                                    />
                                    <Text
                                        x={-10}
                                        y={-10}
                                        width={20}
                                        height={20}
                                        text={String(block.reading_order || i + 1)}
                                        fill="white"
                                        fontSize={12}
                                        fontStyle="bold"
                                        align="center"
                                        verticalAlign="middle"
                                    />

                                    {/* Bounding Box */}
                                    <Rect
                                        width={rect.width}
                                        height={rect.height}
                                        stroke={isSelected ? '#3b82f6' : color} // blue-500 if selected
                                        strokeWidth={isSelected ? 3 : 2}
                                        fill={isSelected ? `${color}33` : `${color}11`} // Transparent fill
                                        dash={isSelected ? undefined : [4, 4]}
                                    />
                                </Group>
                            );
                        })}
                    </Layer>
                </Stage>
            )}
        </div>
    );
};

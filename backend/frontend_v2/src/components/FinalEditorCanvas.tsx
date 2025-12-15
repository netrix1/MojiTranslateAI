import React, { useEffect, useRef, useState } from 'react';
import { Stage, Layer, Image as KonvaImage, Group, Text, Transformer, Rect } from 'react-konva';
import type { OCRBlock } from '../types';

interface FinalEditorCanvasProps {
    imageUrl: string;
    blocks: OCRBlock[];
    onUpdateBlock: (blockId: string, updates: Partial<OCRBlock>) => void;
    baseImageScale?: number; // In case we need zoom later
}

const calculateFontSize = (block: OCRBlock, h: number) => {
    // If style size is set (1-10), use it * multiplier.
    // Multiplier of 4 means size 1 = 4px, size 10 = 40px.
    // Heuristic: Default is h/4.
    if (block.rendering_style?.font_size) {
        return block.rendering_style.font_size * 4;
    }
    return Math.max(12, h / 4);
};

const BlockGroup = ({ block, onSelect, onChange, onEditStart, isSelected }: {
    block: OCRBlock,
    onSelect: () => void,
    onChange: (newAttrs: any) => void,
    onEditStart: () => void,
    isSelected: boolean
}) => {
    const shapeRef = useRef<any>(null);
    const trRef = useRef<any>(null);

    useEffect(() => {
        if (isSelected && trRef.current && shapeRef.current) {
            trRef.current.nodes([shapeRef.current]);
            trRef.current.getLayer().batchDraw();
        }
    }, [isSelected]);

    // Position from block.rendering_style or calculates from bbox
    // We prefer rendering_style updates if they exist, otherwise derived from bbox
    // Actually, backend uses bbox. We need to shift bbox if moved.
    // Simpler: We track "delta" or just absolute pos.
    // Backend typesetter re-calculates based on bbox center.
    // If we move the group, we are effectively moving the bbox.

    const [x1, y1, x2, y2] = block.bbox || [0, 0, 0, 0];
    const w = x2 - x1;
    const h = y2 - y1;

    // Style props
    const style = block.rendering_style || {};
    const angle = style.angle || 0;
    const scale = style.box_scale || 1.0;

    // Consistent Font Size
    const fontSize = calculateFontSize(block, h);

    // Konva transformation storage
    // We initialise x,y from bbox.
    // Konva "x" is top-left.

    return (
        <>
            <Group
                ref={shapeRef}
                x={x1}
                y={y1}
                width={w}
                height={h}
                rotation={angle}
                scaleX={scale}
                scaleY={scale}
                draggable
                onClick={onSelect}
                onTap={onSelect}
                onDblClick={onEditStart}
                onDblTap={onEditStart}
                onDragEnd={(e) => {
                    const node = e.target;
                    const newX = node.x();
                    const newY = node.y();

                    const dx = newX - x1;
                    const dy = newY - y1;

                    const newBBox = [newX, newY, newX + w, newY + h];

                    // Shift Polygon if exists
                    let newPolygon = block.polygon;
                    if (newPolygon) {
                        newPolygon = newPolygon.map(([px, py]) => [px + dx, py + dy]);
                    }

                    // Reset styling if needed, but here we just update pos
                    onChange({
                        bbox: newBBox,
                        polygon: newPolygon,
                        rendering_style: {
                            ...style,
                            angle: node.rotation(),
                            box_scale: node.scaleX()
                        }
                    });
                }}
                onTransformEnd={(e) => {
                    const node = shapeRef.current;
                    const newX = node.x();
                    const newY = node.y();

                    const dx = newX - x1;
                    const dy = newY - y1;

                    const newBBox = [newX, newY, newX + w, newY + h];

                    // Shift Polygon if exists
                    let newPolygon = block.polygon;
                    if (newPolygon) {
                        newPolygon = newPolygon.map(([px, py]) => [px + dx, py + dy]);
                    }

                    onChange({
                        bbox: newBBox,
                        polygon: newPolygon,
                        rendering_style: {
                            ...style,
                            angle: node.rotation(),
                            box_scale: node.scaleX()
                        }
                    });
                }}
            >
                {/* Visual Placeholder for Text Block */}
                <Rect
                    width={w}
                    height={h}
                    fill="rgba(0, 100, 255, 0.05)"
                    stroke={isSelected ? "#00aaff" : "rgba(0,100,255,0.2)"}
                    strokeWidth={1}
                    dash={[5, 5]}
                />
                {/* Approximate text preview */}
                <Text
                    text={block.translation || "..."}
                    fontSize={fontSize}
                    width={w}
                    align="center"
                    verticalAlign="middle"
                    fill={style.text_color || "white"}
                    shadowColor="black"
                    shadowBlur={2}
                />
            </Group>
            {isSelected && (
                <Transformer
                    ref={trRef}
                    boundBoxFunc={(oldBox, newBox) => newBox.width < 5 || newBox.height < 5 ? oldBox : newBox}
                />
            )}
        </>
    );
};

const useNativeImage = (url: string) => {
    const [image, setImage] = useState<HTMLImageElement | undefined>(undefined);
    useEffect(() => {
        if (!url) return;
        const img = new window.Image();
        img.src = url;
        img.crossOrigin = "Anonymous";
        img.onload = () => setImage(img);
    }, [url]);
    return [image];
};

const FormattingToolbar = ({
    style,
    onChange,
    position
}: {
    style: any,
    onChange: (newStyle: any) => void,
    position: { x: number, y: number }
}) => {
    return (
        <div
            className="formatting-toolbar absolute z-[60] flex items-center gap-2 bg-slate-800 p-2 rounded shadow-xl border border-slate-600"
            style={{
                left: position.x,
                top: position.y - 50, // Floating above
            }}
            onMouseDown={(e) => e.stopPropagation()} // Prevent drag/blur
        >
            <div className="flex flex-col items-center">
                <label className="text-[10px] text-slate-400">Font</label>
                <select
                    className="w-20 bg-slate-700 text-white text-xs p-1 rounded border border-slate-600 outline-none"
                    value={style.font_family || "manga"}
                    onChange={(e) => onChange({ ...style, font_family: e.target.value })}
                    title="Font Family"
                    onMouseDown={(e) => e.stopPropagation()}
                >
                    <option value="manga">Manga</option>
                    <option value="shout">Shout</option>
                    <option value="standard">Std</option>
                </select>
            </div>

            <div className="flex flex-col items-center">
                <label className="text-[10px] text-slate-400">Size</label>
                <input
                    type="number"
                    min="1"
                    max="10"
                    step="0.1"
                    className="w-12 bg-slate-700 text-white text-xs p-1 rounded border border-slate-600 outline-none"
                    value={style.font_size || 5}
                    onChange={(e) => onChange({ ...style, font_size: parseFloat(e.target.value) })}
                    title="Font Size (1-10)"
                />
            </div>

            <div className="flex flex-col items-center">
                <label className="text-[10px] text-slate-400">Color</label>
                <input
                    type="color"
                    className="w-6 h-6 bg-transparent border-0 cursor-pointer"
                    value={style.text_color || "#000000"}
                    onChange={(e) => onChange({ ...style, text_color: e.target.value })}
                    title="Text Color"
                />
            </div>

            <div className="flex flex-col items-center">
                <label className="text-[10px] text-slate-400">Border</label>
                <input
                    type="color"
                    className="w-6 h-6 bg-transparent border-0 cursor-pointer"
                    value={style.stroke_color || "#ffffff"}
                    onChange={(e) => onChange({ ...style, stroke_color: e.target.value })}
                    title="Border Color"
                />
            </div>
        </div>
    );
};

export const FinalEditorCanvas: React.FC<FinalEditorCanvasProps> = ({ imageUrl, blocks, onUpdateBlock }) => {
    const [image] = useNativeImage(imageUrl);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [editingBlockId, setEditingBlockId] = useState<string | null>(null);

    // Deselect when clicking on empty area
    const checkDeselect = (e: any) => {
        const clickedOnEmpty = e.target === e.target.getStage();
        if (clickedOnEmpty) {
            setSelectedId(null);
            setEditingBlockId(null);
        }
    };

    if (!image) return <div className="text-white">Loading background...</div>;

    // Find editing block
    const editingBlock = blocks.find(b => b.block_id === editingBlockId);

    return (
        <div className="bg-slate-900 overflow-auto border border-slate-700 relative">
            <Stage
                width={image.width}
                height={image.height}
                onMouseDown={checkDeselect}
                onTouchStart={checkDeselect}
            >
                <Layer>
                    <KonvaImage image={image} />
                </Layer>
                <Layer>
                    {blocks.map((block, i) => {
                        if (!block.bbox) return null;
                        return (
                            <BlockGroup
                                key={block.block_id || i}
                                block={block}
                                isSelected={selectedId === block.block_id}
                                onSelect={() => setSelectedId(block.block_id || null)}
                                onEditStart={() => {
                                    setSelectedId(block.block_id || null);
                                    setEditingBlockId(block.block_id || null);
                                }}
                                onChange={(newAttrs) => {
                                    if (block.block_id) onUpdateBlock(block.block_id, newAttrs);
                                }}
                            />
                        );
                    })}
                </Layer>
            </Stage>

            {/* Editing Textarea Overlay */}
            {editingBlock && editingBlock.bbox && (
                (() => {
                    const style = editingBlock.rendering_style || {};
                    const [x1, y1, x2, y2] = editingBlock.bbox;
                    const w = x2 - x1;
                    const h = y2 - y1;

                    // Font Mapping
                    const fontMap: Record<string, string> = {
                        'manga': 'Manga Dialogue',
                        'shout': 'Shout',
                        'standard': 'Inter',
                        'handwritten': 'Manga Dialogue' // Fallback
                    };
                    const fontFamily = fontMap[style.font_family?.toLowerCase() || 'manga'] || 'Manga Dialogue';

                    // CONSISTENT FONT SIZE
                    const fontSize = calculateFontSize(editingBlock, h);

                    return (
                        <>
                            <FormattingToolbar
                                style={style}
                                position={{ x: x1, y: y1 }}
                                onChange={(newStyle) => {
                                    if (editingBlock.block_id) onUpdateBlock(editingBlock.block_id, { rendering_style: newStyle });
                                }}
                            />
                            <div
                                ref={(node) => {
                                    if (node) {
                                        // Initial focus and cursor placement only on mount/creation
                                        if (node.innerText !== (editingBlock.translation || "")) {
                                            node.innerText = editingBlock.translation || "";
                                            // Only focus if not already focused (to prevent fighting)
                                            if (document.activeElement !== node) {
                                                node.focus();
                                                // Set cursor to end
                                                const range = document.createRange();
                                                range.selectNodeContents(node);
                                                range.collapse(false);
                                                const sel = window.getSelection();
                                                sel?.removeAllRanges();
                                                sel?.addRange(range);
                                            }
                                        }
                                    }
                                }}
                                contentEditable
                                suppressContentEditableWarning
                                className="absolute z-50 outline-none"
                                style={{
                                    left: x1,
                                    top: y1,
                                    minWidth: w,
                                    minHeight: h,
                                    fontSize: `${fontSize}px`,
                                    fontFamily: `${fontFamily}, sans-serif`,
                                    textAlign: 'center',
                                    lineHeight: 1.2,
                                    whiteSpace: 'pre',
                                    display: 'inline-block',
                                    background: 'transparent',
                                    border: '1px dashed rgba(255,255,255,0.5)',
                                    color: style.text_color || 'white',
                                    textShadow: '0px 1px 2px black',
                                }}
                                onInput={(e) => {
                                    const target = e.target as HTMLDivElement;
                                    const newVal = target.innerText;
                                    // Only update if different needed
                                    if (editingBlock.block_id) {
                                        onUpdateBlock(editingBlock.block_id, { translation: newVal });
                                    }
                                }}
                                onBlur={(e) => {
                                    const target = e.target as HTMLDivElement;
                                    const newW = target.offsetWidth;
                                    const newH = target.offsetHeight;

                                    const newBBox: [number, number, number, number] = [x1, y1, x1 + newW, y1 + newH];

                                    const updates: any = {
                                        bbox: newBBox,
                                        translation: target.innerText,
                                    };

                                    if (!style.font_size) {
                                        const currentPixelSize = fontSize;
                                        const newStyleSize = Math.round(currentPixelSize / 4 * 10) / 10;
                                        updates.rendering_style = { ...style, font_size: newStyleSize };
                                    }

                                    if (editingBlock.block_id) {
                                        onUpdateBlock(editingBlock.block_id, updates);
                                    }

                                    if (e.relatedTarget && (e.relatedTarget as HTMLElement).closest('.formatting-toolbar')) {
                                        target.focus();
                                        return;
                                    }

                                    setEditingBlockId(null);
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Escape') setEditingBlockId(null);
                                    e.stopPropagation();
                                }}
                            />
                        </>
                    );
                })()
            )}
        </div>
    );
};

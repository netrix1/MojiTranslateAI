import React, { useEffect, useRef, useState } from 'react';
import { Stage, Layer, Image as KonvaImage, Rect, Transformer, Line } from 'react-konva';
import Konva from 'konva';
import type { Region, BBox } from '../types';
import { bboxToRect, getRegionColor, rectToBBox } from '../utils';

// Simple useImage hook to avoid extra dependency
const useImage = (url: string) => {
    const [image, setImage] = useState<HTMLImageElement>();
    useEffect(() => {
        if (!url) return;
        const img = new Image();
        img.src = url;
        img.crossOrigin = 'Anonymous';
        img.onload = () => setImage(img);
    }, [url]);
    return [image];
};

interface RegionCanvasProps {
    imageUrl: string;
    regions: Region[];
    selectedId: string | null;
    onSelect: (id: string | null) => void;
    onChange: (regions: Region[]) => void;
}

export const RegionCanvas: React.FC<RegionCanvasProps> = ({
    imageUrl,
    regions,
    selectedId,
    onSelect,
    onChange,
}) => {
    const [image] = useImage(imageUrl);
    const stageRef = useRef<Konva.Stage>(null);
    const trRef = useRef<Konva.Transformer>(null);

    // Initial scale/fit logic could go here

    // Polygon Drawing State
    const [isDrawingPolygon, setIsDrawingPolygon] = useState(false);
    const [currentPolygonPoints, setCurrentPolygonPoints] = useState<number[][]>([]);

    // Rectangle Drag State (legacy)
    const [isDrawingRect, setIsDrawingRect] = useState(false);
    const [newRegionStart, setNewRegionStart] = useState<{ x: number, y: number } | null>(null);
    const [currentLayout, setCurrentLayout] = useState<{ x: number, y: number, w: number, h: number } | null>(null);

    useEffect(() => {
        if (selectedId && trRef.current && stageRef.current) {
            // attach transformer to the selected node
            const node = stageRef.current.findOne('#' + selectedId);
            if (node) {
                trRef.current.nodes([node]);
                trRef.current.getLayer()?.batchDraw();
            }
        }
    }, [selectedId]);

    // Handle Drag End for RECTANGLES (Legacy/Fallback)
    // Note: Polygons are complex to "drag resize" easily with one Transformer, 
    // usually we'd need points editing. For MVP, we allow moving the whole polygon.
    const handleDragEnd = (e: Konva.KonvaEventObject<DragEvent>, id: string) => {
        const node = e.target;

        // If it's a Line (polygon), we need to update all points by delta
        // BUT Konva moves the node x/y. We should bake that into points or keep x/y.
        // Simplest for saving: Bake into bbox/points and reset x/y to 0.

        const dx = node.x();
        const dy = node.y();
        const scaleX = node.scaleX();
        const scaleY = node.scaleY();

        // Find existing region
        const oldRegion = regions.find(r => r.region_id === id);
        if (!oldRegion) return;

        node.x(0);
        node.y(0);
        node.scaleX(1);
        node.scaleY(1);

        const updated = regions.map((r) => {
            if (r.region_id === id) {
                // Update Polygon if exists
                let newPoly = r.polygon;
                if (newPoly) {
                    newPoly = newPoly.map(p => [
                        (p[0] * scaleX) + dx,
                        (p[1] * scaleY) + dy
                    ]);
                }

                // Update BBox
                // Recalculate BBox from new poly or just transform old bbox
                let newBBox = r.bbox;
                if (newPoly) {
                    const xs = newPoly.map(p => p[0]);
                    const ys = newPoly.map(p => p[1]);
                    newBBox = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
                } else {
                    // Standard rect update
                    newBBox = rectToBBox(
                        bboxToRect(r.bbox).x + dx,
                        bboxToRect(r.bbox).y + dy,
                        bboxToRect(r.bbox).width * scaleX,
                        bboxToRect(r.bbox).height * scaleY
                    );
                }

                return { ...r, bbox: newBBox, polygon: newPoly };
            }
            return r;
        });
        onChange(updated);
    };

    const handleStageMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
        const stage = e.target.getStage();
        if (!stage) return;

        // Ctrl + Click for Polygon Drawing
        if (e.evt.ctrlKey) {
            const pos = stage.getRelativePointerPosition();
            if (!pos) return;

            if (!isDrawingPolygon) {
                setIsDrawingPolygon(true);
                setCurrentPolygonPoints([[pos.x, pos.y]]);
                onSelect(null);
            } else {
                // Add point
                setCurrentPolygonPoints(prev => [...prev, [pos.x, pos.y]]);
            }
            e.evt.preventDefault();
            return;
        }

        // Standard selection logic
        const clickedOnStage = e.target === stage || e.target instanceof Konva.Image;
        if (clickedOnStage) {
            if (isDrawingPolygon) {
                // Click on empty space while drawing? maybe nothing.
                return;
            }
            onSelect(null);
            trRef.current?.nodes([]);

            // Start Rect Drag (Legacy) if NOT polygon
            // if (e.evt.shiftKey) ... ? Or just default drag?
            // Let's keep default drag for now if NOT drawing polygon
            const pos = stage.getRelativePointerPosition();
            if (pos) {
                setIsDrawingRect(true);
                setNewRegionStart({ x: pos.x, y: pos.y });
            }
        }
    };

    const handleStageMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
        const stage = e.target.getStage();
        const pos = stage?.getRelativePointerPosition();
        if (!pos) return;

        if (isDrawingRect && newRegionStart) {
            const x = Math.min(newRegionStart.x, pos.x);
            const y = Math.min(newRegionStart.y, pos.y);
            const w = Math.abs(pos.x - newRegionStart.x);
            const h = Math.abs(pos.y - newRegionStart.y);
            setCurrentLayout({ x, y, w, h });
        }
    };

    const handleStageMouseUp = (e: Konva.KonvaEventObject<MouseEvent>) => {
        // Finish Rect Drawing
        if (isDrawingRect && newRegionStart && currentLayout) {
            if (currentLayout.w > 5 && currentLayout.h > 5) {
                const newId = `manual_r_${Date.now()}`;
                const newRegion: Region = {
                    region_id: newId,
                    bbox: [currentLayout.x, currentLayout.y, currentLayout.x + currentLayout.w, currentLayout.y + currentLayout.h],
                    type_hint: 'speech'
                };
                onChange([...regions, newRegion]);
                onSelect(newId);
            }
            setIsDrawingRect(false);
            setNewRegionStart(null);
            setCurrentLayout(null);
        }
    };

    // Double click to finish polygon
    const handleDoubleClick = (e: Konva.KonvaEventObject<MouseEvent>) => {
        if (isDrawingPolygon && currentPolygonPoints.length > 2) {
            // Finish polygon
            const points = currentPolygonPoints;

            // Calc BBox
            const xs = points.map(p => p[0]);
            const ys = points.map(p => p[1]);
            const bbox: [number, number, number, number] = [
                Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)
            ];

            const newId = `manual_poly_${Date.now()}`;
            const newRegion: Region = {
                region_id: newId,
                bbox: bbox,
                polygon: points,
                type_hint: 'speech'
            };

            onChange([...regions, newRegion]);
            onSelect(newId);

            setIsDrawingPolygon(false);
            setCurrentPolygonPoints([]);
        }
    };

    // Render Helper
    const renderRegion = (region: Region) => {
        const isSelected = selectedId === region.region_id;

        if (region.polygon && region.polygon.length > 0) {
            // Render Polygon
            const flatPoints = region.polygon.flat();
            return (
                <Line
                    key={region.region_id}
                    id={region.region_id}
                    points={flatPoints}
                    closed={true}
                    stroke={getRegionColor(region.type_hint)}
                    strokeWidth={isSelected ? 3 : 2}
                    fill={isSelected ? getRegionColor(region.type_hint) : undefined}
                    opacity={0.4}
                    draggable
                    onClick={() => onSelect(region.region_id)}
                    onTap={() => onSelect(region.region_id)}
                    onDragEnd={(e: Konva.KonvaEventObject<DragEvent>) => handleDragEnd(e, region.region_id)}
                    onTransformEnd={(e: Konva.KonvaEventObject<Event>) => handleDragEnd(e as any, region.region_id)}
                />
            );
        } else {
            // Render Rect
            const rect = bboxToRect(region.bbox);
            return (
                <Rect
                    key={region.region_id}
                    id={region.region_id}
                    x={rect.x}
                    y={rect.y}
                    width={rect.width}
                    height={rect.height}
                    stroke={getRegionColor(region.type_hint)}
                    strokeWidth={isSelected ? 3 : 2}
                    draggable
                    opacity={0.4}
                    fill={isSelected ? getRegionColor(region.type_hint) : undefined}
                    onClick={() => onSelect(region.region_id)}
                    onTap={() => onSelect(region.region_id)}
                    onDragEnd={(e) => handleDragEnd(e, region.region_id)}
                    onTransformEnd={(e) => handleDragEnd(e, region.region_id)}
                />
            );
        }
    };

    if (!image) {
        return <div className="flex items-center justify-center h-full text-slate-500">Loading Image...</div>;
    }

    return (
        <div className="w-full h-full overflow-auto bg-slate-900 border border-slate-800 rounded relative">
            {isDrawingPolygon && (
                <div className="absolute top-2 left-2 z-10 bg-black/50 text-white px-2 py-1 rounded text-xs pointer-events-none">
                    Drawing Polygon: Ctrl+Click to add points. Double Click to finish.
                </div>
            )}
            <Stage
                width={image.width}
                height={image.height}
                ref={stageRef}
                onMouseDown={handleStageMouseDown}
                onMouseMove={handleStageMouseMove}
                onMouseUp={handleStageMouseUp}
                onDblClick={handleDoubleClick}
            >
                <Layer>
                    <KonvaImage image={image} listening={true} />
                    {regions.map(renderRegion)}

                    {/* Temporary Polygon being drawn */}
                    {isDrawingPolygon && currentPolygonPoints.length > 0 && (
                        <>
                            <Line
                                points={currentPolygonPoints.flat()}
                                stroke="#00ff00"
                                strokeWidth={2}
                                dash={[5, 5]}
                                closed={false}
                            />
                            {/* Dots for vertices */}
                            {currentPolygonPoints.map((p, i) => (
                                <Rect
                                    key={i}
                                    x={p[0] - 3}
                                    y={p[1] - 3}
                                    width={6}
                                    height={6}
                                    fill="#00ff00"
                                />
                            ))}
                        </>
                    )}

                    {/* Temporary Rect being drawn */}
                    {isDrawingRect && currentLayout && (
                        <Rect
                            x={currentLayout.x}
                            y={currentLayout.y}
                            width={currentLayout.w}
                            height={currentLayout.h}
                            stroke="#00ff00"
                            strokeWidth={2}
                            dash={[5, 5]}
                        />
                    )}

                    <Transformer
                        ref={trRef}
                        rotateEnabled={false} // polygons rotation complex for simple implementation
                        keepRatio={false}
                        boundBoxFunc={(oldBox, newBox) => {
                            if (newBox.width < 5 || newBox.height < 5) return oldBox;
                            return newBox;
                        }}
                    />
                </Layer>
            </Stage>
        </div>
    );
};

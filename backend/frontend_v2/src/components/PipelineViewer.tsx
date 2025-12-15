import React, { useEffect, useState } from 'react';
import { Layers, Type, Play, CheckCircle, FileJson, Clock, AlertCircle, ArrowRight, ChevronLeft, ChevronRight, Save, RotateCcw, ArrowRightCircle } from 'lucide-react';
import { EditRegionModal } from './EditRegionModal';
import { RegionCanvas } from './RegionCanvas';


import { OCREditor } from './OCREditor';
import { RegionList } from './RegionList';
import { OCRList } from './OCRList';
import { TranslationList } from './TranslationList';
import { StyleEditor } from './StyleEditor';
import { NewFinalEditor } from './NewFinalEditor';
import type { Region, OCRBlock } from '../types';

const API_BASE = 'http://localhost:8000';

interface PipelineViewerProps {
    jobId: string;
    pageNumber: number;
    onPageChange?: (page: number) => void;
}

export const PipelineViewer: React.FC<PipelineViewerProps> = ({ jobId, pageNumber, onPageChange }) => {
    const [loading, setLoading] = useState(false);
    const [pageCount, setPageCount] = useState(0);
    const [viewMode, setViewMode] = useState<'regions' | 'ocr' | 'translation' | 'cleaning' | 'redraw' | 'final'>('regions');
    const [compareOriginal, setCompareOriginal] = useState(false);
    const [editingRegion, setEditingRegion] = useState<Region | null>(null);

    // Data State
    const [regions, setRegions] = useState<Region[]>([]);
    const [ocrBlocks, setOcrBlocks] = useState<OCRBlock[]>([]);
    const [pipelineState, setPipelineState] = useState<any>(null);
    const [imageUrl, setImageUrl] = useState('');

    // Selection State
    const [selectedRegionId, setSelectedRegionId] = useState<string | null>(null);
    const [selectedBlockIndex, setSelectedBlockIndex] = useState<number | null>(null);

    const [translationData, setTranslationData] = useState<any>(null);
    const [imgDim, setImgDim] = useState<{ w: number, h: number } | null>(null);

    const refreshData = async () => {
        setLoading(true);
        try {
            // We don't change this part, just context.
            // But we need to reset imgDim when page changes
            setImgDim(null);

            // 0. Job Info (Page Count)
            if (pageCount === 0) {
                try {
                    const jInfo = await fetch(`${API_BASE}/jobs/${jobId}`).then(r => r.json());
                    if (jInfo && jInfo.page_count) setPageCount(jInfo.page_count);
                } catch (e) { console.warn("Job info fetch fail"); }
            }

            // 0. Pipeline State
            try {
                const s = await fetch(`${API_BASE}/pipeline/${jobId}/state/${pageNumber}`).then(r => r.json());
                setPipelineState(s);
            } catch (e) { console.warn("State fetch fail"); }

            // 1. Regions
            try {
                const rData = await fetch(`${API_BASE}/pipeline/${jobId}/regions/${pageNumber}`).then(r => r.json());
                const page = rData.pages.find((p: any) => p.page_number === pageNumber);
                setRegions(page?.regions || []);
            } catch (e) { setRegions([]); }

            // 2. OCR (Try final, then grouped)
            try {
                let ocrResp = await fetch(`${API_BASE}/pipeline/${jobId}/ocr/final`);
                if (!ocrResp.ok) ocrResp = await fetch(`${API_BASE}/pipeline/${jobId}/ocr/grouped`);
                if (ocrResp.ok) {
                    const ocrData = await ocrResp.json();
                    const page = ocrData.pages.find((p: any) => p.page_number === pageNumber);
                    setOcrBlocks(page?.blocks || []);
                }
            } catch (e) { setOcrBlocks([]); }

            // 3. Translation
            try {
                const tResp = await fetch(`${API_BASE}/pipeline/${jobId}/translation`);
                if (tResp.ok) {
                    const tData = await tResp.json();
                    setTranslationData(tData); // Keep full structure for saving
                } else { setTranslationData(null); }
            } catch (e) { setTranslationData(null); }

            setImageUrl(`${API_BASE}/jobs/${jobId}/pages/${pageNumber}/image`);

        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        refreshData();
    }, [jobId, pageNumber]);

    // --- ACTIONS ---

    const handleSaveRegions = async () => {
        setLoading(true);
        try {
            const payload = {
                job_id: jobId,
                pages: [{
                    page_number: pageNumber,
                    regions: regions,
                    notes: "saved_from_viewer"
                }]
            };
            const resp = await fetch(`${API_BASE}/pipeline/${jobId}/regions/${pageNumber}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!resp.ok) throw new Error("Failed to save regions");
            alert("Regions Saved!");
            refreshData();
        } catch (e: any) { alert(e.message); } finally { setLoading(false); }
    };

    const handleSaveOCR = async () => {
        setLoading(true);
        try {
            const resp = await fetch(`${API_BASE}/pipeline/${jobId}/ocr/${pageNumber}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(ocrBlocks)
            });
            if (!resp.ok) throw new Error("Failed to save OCR");
            alert("OCR Saved!");
            refreshData();
        } catch (e: any) { alert(e.message); } finally { setLoading(false); }
    };

    const handleSaveTranslation = async () => {
        if (!translationData) return;
        setLoading(true);
        try {
            // translationData is full structure, we update just this page if needed or save whole
            // The editor (mock) doesn't update state yet, but let's assume valid state
            const resp = await fetch(`${API_BASE}/pipeline/${jobId}/translation`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(translationData)
            });
            if (!resp.ok) throw new Error("Failed to save Translation");
            alert("Translation Saved!");
            refreshData();
        } catch (e: any) { alert(e.message); } finally { setLoading(false); }
    };

    const handleRerunStep = async (stepId: string) => {
        if (!confirm(`Are you sure you want to refresh/rerun ${stepId}? This may overwrite subsequent steps.`)) return;
        setLoading(true);
        try {
            await fetch(`${API_BASE}/pipeline/${jobId}/step/${stepId}/rerun/${pageNumber}`, { method: 'POST' });
            alert(`Rerunning ${stepId}...`);
            // Poll or wait? pipeline runs synchronously often in this simple backend
            await new Promise(r => setTimeout(r, 1000));
            await refreshData();
        } catch (e: any) { alert(e.message); } finally { setLoading(false); }
    };


    const renderActionBar = () => {
        return (
            <div className="flex items-center gap-2">
                {/* View Specific Actions */}
                {viewMode === 'regions' && (
                    <>
                        <button onClick={handleSaveRegions} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2">
                            <Save size={14} /> Save
                        </button>
                        <button onClick={() => handleRerunStep('regions')} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2" title="Auto-Detect Regions">
                            <RotateCcw size={14} /> Refresh
                        </button>
                        <button onClick={() => setViewMode('ocr')} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded text-sm font-medium flex items-center gap-2 shadow-lg shadow-blue-500/20">
                            Next <ArrowRightCircle size={14} />
                        </button>
                    </>
                )}

                {viewMode === 'ocr' && (
                    <>
                        <button onClick={handleSaveOCR} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2">
                            <Save size={14} /> Save
                        </button>
                        <button onClick={() => handleRerunStep('ocr')} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2" title="Re-run OCR">
                            <RotateCcw size={14} /> Refresh
                        </button>
                        <button onClick={() => setViewMode('translation')} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded text-sm font-medium flex items-center gap-2 shadow-lg shadow-blue-500/20">
                            Next <ArrowRightCircle size={14} />
                        </button>
                    </>
                )}

                {viewMode === 'translation' && (
                    <>
                        <button onClick={handleSaveTranslation} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2">
                            <Save size={14} /> Save
                        </button>
                        <button onClick={() => handleRerunStep('translation')} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2" title="Re-translate">
                            <RotateCcw size={14} /> Refresh
                        </button>
                        <button onClick={() => setViewMode('redraw')} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded text-sm font-medium flex items-center gap-2 shadow-lg shadow-blue-500/20">
                            Next <ArrowRightCircle size={14} />
                        </button>
                    </>
                )}

                {viewMode === 'redraw' && (
                    <>
                        <button onClick={() => alert("Redraw Saved!")} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2">
                            <Save size={14} /> Save
                        </button>
                        <button onClick={() => handleRerunStep('cleaning')} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2" title="Re-run Cleaning">
                            <RotateCcw size={14} /> Ref. Cleaning
                        </button>
                        <button onClick={() => handleRerunStep('redraw')} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2" title="Re-draw (Inpaint)">
                            <RotateCcw size={14} /> Ref. Redraw
                        </button>
                        <button onClick={() => setViewMode('final')} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded text-sm font-medium flex items-center gap-2 shadow-lg shadow-blue-500/20">
                            Next <ArrowRightCircle size={14} />
                        </button>
                    </>
                )}

                {viewMode === 'final' && (
                    <>
                        <button onClick={() => alert("Final Image Saved!ddddd")} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2">
                            <Save size={14} /> Save
                        </button>
                        <button onClick={() => handleRerunStep('typesetting')} className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded text-sm font-medium flex items-center gap-2" title="Re-render Text">
                            <RotateCcw size={14} /> Refresh
                        </button>
                        <button onClick={() => alert("Process Finished!")} className="bg-green-600 hover:bg-green-500 text-white px-4 py-1.5 rounded text-sm font-medium flex items-center gap-2 shadow-lg shadow-green-500/20">
                            Finish <CheckCircle size={14} />
                        </button>
                    </>
                )}
            </div>
        );
    };

    return (
        <div className="flex h-screen bg-slate-900 text-slate-200 overflow-hidden">
            {/* MAIN AREA */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <header className="h-14 border-b border-slate-800 flex items-center justify-between px-4 bg-slate-900">
                    <div className="flex items-center gap-4">
                        <h1 className="font-bold text-lg">Job: <span className="font-mono text-blue-400">{jobId.substring(0, 8)}</span></h1>
                        <div className="flex items-center gap-1 bg-slate-800 rounded px-1">
                            <button
                                onClick={() => onPageChange?.(pageNumber - 1)}
                                disabled={pageNumber <= 1}
                                className="p-0.5 hover:bg-slate-700 rounded text-slate-400 disabled:opacity-30 disabled:hover:bg-transparent"
                            >
                                <ChevronLeft size={14} />
                            </button>
                            <span className="text-xs text-slate-300 font-mono px-1">Page {pageNumber}</span>
                            <button
                                onClick={() => onPageChange?.(pageNumber + 1)}
                                disabled={pageCount > 0 && pageNumber >= pageCount}
                                className="p-0.5 hover:bg-slate-700 rounded text-slate-400 disabled:opacity-30 disabled:hover:bg-transparent"
                            >
                                <ChevronRight size={14} />
                            </button>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="flex items-center bg-slate-900/50 border border-slate-800 rounded-lg p-1.5 gap-1">
                        {[
                            { id: 'regions', label: 'Regions', icon: Layers },
                            { id: 'ocr', label: 'OCR', icon: Type },
                            { id: 'translation', label: 'Translation', icon: FileJson },
                            // Cleaning merged into Redraw
                            { id: 'redraw', label: 'Clean & Redraw', icon: Layers },
                            { id: 'final', label: 'Final', icon: CheckCircle },
                        ].map((step, idx, arr) => (
                            <React.Fragment key={step.id}>
                                <button
                                    onClick={() => setViewMode(step.id as any)}
                                    className={`px-3 py-1.5 rounded-md text-sm font-medium flex items-center gap-2 transition-all ${viewMode === step.id ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
                                >
                                    <step.icon size={14} /> {step.label}
                                </button>
                                {idx < arr.length - 1 && <ArrowRight size={14} className="text-slate-600" />}
                            </React.Fragment>
                        ))}
                    </div>

                    {/* Action Bar */}
                    {renderActionBar()}
                </header>

                {/* Content */}
                <div className="flex-1 relative bg-slate-900/50 overflow-auto">
                    {loading && (
                        <div className="absolute inset-0 z-50 bg-slate-900/80 flex items-center justify-center backdrop-blur-sm">
                            <div className="flex flex-col items-center gap-3">
                                <RotateCcw className="animate-spin text-blue-500" size={32} />
                                <p className="text-blue-400 font-medium">Processing...</p>
                            </div>
                        </div>
                    )}

                    {viewMode === 'regions' ? (
                        <RegionCanvas
                            imageUrl={imageUrl}
                            regions={regions}
                            selectedId={selectedRegionId}
                            onSelect={setSelectedRegionId}
                            onChange={setRegions}
                        />
                    ) : viewMode === 'ocr' ? (
                        <OCREditor
                            imageUrl={imageUrl}
                            regions={regions}
                            blocks={ocrBlocks}
                            selectedBlockIndex={selectedBlockIndex}
                            onSelectBlock={setSelectedBlockIndex}
                            onUpdateBlock={() => { }}
                        />
                    ) : viewMode === 'translation' ? (
                        <div className="flex h-full">
                            {/* Left Pane: Image Context */}
                            <div className="w-1/2 bg-slate-900 border-r border-slate-800 p-4 flex items-center justify-center overflow-hidden">
                                <div className="h-full w-full flex items-center justify-center relative">
                                    <div className="absolute top-2 left-2 bg-black/60 px-2 py-1 rounded text-xs text-slate-300 pointer-events-none z-10">
                                        Original Reference
                                    </div>

                                    {/* Wrapper constrained by parent size but maintaining aspect ratio */}
                                    <div
                                        className="relative shadow-lg bg-black box-border"
                                        style={{
                                            maxWidth: '100%',
                                            maxHeight: '100%',
                                            aspectRatio: imgDim ? `${imgDim.w} / ${imgDim.h}` : 'auto'
                                        }}
                                    >
                                        <img
                                            src={imageUrl}
                                            alt="Original Context"
                                            className="w-full h-full object-contain block"
                                            onLoad={(e) => {
                                                setImgDim({
                                                    w: e.currentTarget.naturalWidth,
                                                    h: e.currentTarget.naturalHeight
                                                });
                                            }}
                                        />
                                        {/* SVG Overlay */}
                                        {imgDim && translationData?.pages?.find((p: any) => p.page_number === pageNumber)?.blocks && (
                                            <svg
                                                className="absolute inset-0 w-full h-full pointer-events-none"
                                                viewBox={`0 0 ${imgDim.w} ${imgDim.h}`}
                                            >
                                                {translationData.pages.find((p: any) => p.page_number === pageNumber)?.blocks.map((block: any, idx: number) => {
                                                    if (!block.bbox) return null;
                                                    const [x1, y1, x2, y2] = block.bbox;
                                                    const w = x2 - x1;
                                                    const h = y2 - y1;
                                                    return (
                                                        <g key={block.block_id}>
                                                            <rect
                                                                x={x1} y={y1} width={w} height={h}
                                                                fill="transparent" stroke="#3b82f6" strokeWidth={Math.max(3, imgDim.w * 0.005)}
                                                            />
                                                            <circle cx={x1} cy={y1} r={Math.max(20, imgDim.w * 0.03)} fill="#3b82f6" />
                                                            <text
                                                                x={x1} y={y1} dy={Math.max(10, imgDim.w * 0.01)} textAnchor="middle"
                                                                fill="white" fontSize={Math.max(24, imgDim.w * 0.03)} fontWeight="bold"
                                                            >
                                                                {idx + 1}
                                                            </text>
                                                        </g>
                                                    );
                                                })}
                                            </svg>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Right Pane: Editor */}
                            <div className="w-1/2 p-8 h-full overflow-y-auto">
                                <h2 className="text-2xl font-bold mb-6">Translation Results</h2>
                                {translationData && translationData.pages ? (
                                    <div className="space-y-4 pb-20">
                                        {(translationData.pages.find((p: any) => p.page_number === pageNumber)?.blocks || []).map((block: any, idx: number) => (
                                            <div key={block.block_id} className="bg-slate-900 p-4 rounded border border-slate-800 relative">
                                                {/* Number Badge */}
                                                <div className="absolute top-4 right-4 bg-blue-600 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">
                                                    {idx + 1}
                                                </div>

                                                <p className="text-slate-500 text-xs mb-1 uppercase tracking-wider">Original</p>
                                                <p className="text-slate-300 mb-3 pl-2 border-l-2 border-slate-700 font-serif pr-8">{block.original}</p>

                                                <p className="text-blue-500 text-xs mb-1 uppercase tracking-wider">Translation</p>
                                                <textarea
                                                    className="w-full bg-slate-900 text-white p-2 rounded border border-slate-700 focus:border-blue-500 outline-none min-h-[80px]"
                                                    defaultValue={block.translation}
                                                    onChange={(e) => {
                                                        // Quick n dirty state update
                                                        block.translation = e.target.value;
                                                        setTranslationData({ ...translationData });
                                                    }}
                                                />

                                                <StyleEditor
                                                    style={block.rendering_style || {}}
                                                    onChange={(newStyle) => {
                                                        block.rendering_style = newStyle;
                                                        setTranslationData({ ...translationData });
                                                    }}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-20 bg-slate-900/50 rounded-xl border border-dashed border-slate-800">
                                        <p className="text-slate-400">No translation data available yet.</p>
                                        <p className="text-sm text-slate-500 mt-2">Finish OCR and click Refresh/Next to generate.</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : viewMode === 'redraw' ? (
                        <div className="flex-1 flex flex-col h-full">
                            <div className="absolute top-4 right-4 z-10 bg-slate-900/80 px-4 py-2 rounded text-xs text-white pointer-events-none border border-slate-700">
                                Redraw (Inpainted) Result - Hold <b>Space</b> for Original
                            </div>
                            <div
                                className="flex-1 flex items-center justify-center p-8 overflow-auto select-none"
                                onMouseDown={() => setCompareOriginal(true)}
                                onMouseUp={() => setCompareOriginal(false)}
                                onMouseLeave={() => setCompareOriginal(false)}
                            >
                                <img
                                    src={compareOriginal ? imageUrl : `${API_BASE}/pipeline/${jobId}/redraw/${pageNumber}/image?t=${Date.now()}`}
                                    alt="Redraw/Original"
                                    className="max-w-full max-h-full object-contain shadow-2xl"
                                    onError={(e) => { if (!compareOriginal) e.currentTarget.src = imageUrl; }}
                                />
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col h-full relative">
                            {/* Interactive Editor - No Static View Toggle */}
                            <NewFinalEditor
                                imageUrl={`${API_BASE}/pipeline/${jobId}/redraw/${pageNumber}/image`}
                                blocks={translationData?.pages?.find((p: any) => p.page_number === pageNumber)?.blocks || []}
                                onUpdateBlock={(blockId, updates) => {
                                    if (!translationData) return;
                                    const page = translationData.pages.find((p: any) => p.page_number === pageNumber);
                                    if (!page) return;
                                    const blockIndex = page.blocks.findIndex((b: any) => b.block_id === blockId);
                                    if (blockIndex !== -1) {
                                        const oldBlock = page.blocks[blockIndex];
                                        const newStyle = updates.rendering_style
                                            ? { ...(oldBlock.rendering_style || {}), ...updates.rendering_style }
                                            : (oldBlock.rendering_style || {});

                                        page.blocks[blockIndex] = {
                                            ...oldBlock,
                                            ...updates,
                                            rendering_style: newStyle
                                        };

                                        setTranslationData({ ...translationData });
                                    }
                                }}
                            />
                        </div>
                    )}
                </div>
            </div>

            {/* SIDEBAR */}
            <div className="w-80 border-l border-slate-800 bg-slate-900 flex flex-col">
                <div className="p-4 border-b border-slate-800">
                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-1">Details</h3>
                    <p className="text-xs text-slate-500">Params & Info</p>
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                    {viewMode === 'regions' && (
                        <RegionList
                            regions={regions}
                            selectedId={selectedRegionId}
                            onSelect={setSelectedRegionId}
                            onDelete={(id) => {
                                if (confirm("Delete this region?")) {
                                    setRegions(prev => prev.filter(r => r.region_id !== id));
                                    if (selectedRegionId === id) setSelectedRegionId(null);
                                }
                            }}
                            onEdit={(region) => setEditingRegion(region)}
                        />
                    )}
                    {viewMode === 'ocr' && (
                        <div className="text-sm text-slate-400">
                            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">OCR Blocks</div>
                            <OCRList blocks={ocrBlocks} regions={regions} selectedBlockIndex={selectedBlockIndex} onSelectBlock={setSelectedBlockIndex} onUpdateBlock={() => { }} />
                        </div>
                    )}
                    {viewMode === 'translation' && (
                        <div className="text-sm text-slate-400 h-full">
                            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Translated Blocks</div>
                            <TranslationList
                                blocks={translationData?.pages?.find((p: any) => p.page_number === pageNumber)?.blocks || []}
                                selectedBlockId={null}
                                onSelectBlock={(id) => {
                                    // Scroll to block logic could go here
                                    const el = document.getElementById(`trans-block-${id}`);
                                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                }}
                            />
                        </div>
                    )}
                </div>
            </div>

            {/* Modals */}
            <EditRegionModal
                isOpen={!!editingRegion}
                region={editingRegion}
                onClose={() => setEditingRegion(null)}
                onSave={(oldId, newId, newType) => {
                    setRegions(prev => prev.map(r =>
                        r.region_id === oldId
                            ? { ...r, region_id: newId, type_hint: newType }
                            : r
                    ));
                    if (selectedRegionId === oldId && oldId !== newId) {
                        setSelectedRegionId(newId);
                    }
                }}
            />
        </div>
    );
};


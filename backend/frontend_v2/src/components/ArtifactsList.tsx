import React, { useEffect, useState } from 'react';
import { Package, Download, FileJson, Image as ImageIcon, X } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

interface ArtifactsListProps {
    jobId: string;
    onClose: () => void;
}

export const ArtifactsList: React.FC<ArtifactsListProps> = ({ jobId, onClose }) => {
    const [files, setFiles] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Since we don't have a specific "list artifacts" endpoint, we'll hit the job structure or a new endpoint.
        // For now, let's assume we can list pages and known JSONs.
        // Actually, let's implement a simple file walker in the backend or just hardcode known paths.
        // Better: List known artifacts based on logic.

        const knownArtifacts = [
            { name: 'ocr_final.json', type: 'json' },
            { name: 'ocr_grouped.json', type: 'json' },
            { name: 'ocr_raw.json', type: 'json' },
        ];

        // Also fetch pages to list regions
        fetch(`${API_BASE}/jobs/${jobId}/pages`) // We assume this exists or we fetch job info
            .then(r => r.ok ? r.json() : []) // job pages
            .then(pages => {
                // Mocking the file list for now as we don't have a file browser API
                // In a real app we'd have GET /jobs/{id}/artifacts
                const artifacts = [
                    ...knownArtifacts.map(a => ({ ...a, path: `/pipeline/${jobId}/ocr/${a.name.replace('ocr_', '').replace('.json', '')}` })),
                ];
                setFiles(artifacts);
                setLoading(false);
            })
            .catch(e => {
                console.error(e);
                setLoading(false);
            })
    }, [jobId]);

    const handleDownload = (path: string, filename: string) => {
        window.open(`${API_BASE}${path}`, '_blank');
    };

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
            <div className="bg-slate-900 w-full max-w-2xl rounded-xl border border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
                <header className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900">
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        <Package className="text-blue-500" /> Artifacts: <span className="font-mono text-slate-400 text-base">{jobId}</span>
                    </h2>
                    <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                </header>

                <div className="flex-1 overflow-y-auto p-4">
                    {loading ? (
                        <p className="text-center text-slate-500 py-10">Loading artifacts...</p>
                    ) : (
                        <div className="space-y-2">
                            {/* Standard JSONs */}
                            <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                                <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Pipeline Data</h3>
                                <div className="space-y-2">
                                    {['final', 'grouped', 'raw'].map(type => (
                                        <div key={type} className="flex items-center justify-between bg-slate-900 p-3 rounded border border-slate-800 hover:border-slate-700 transition-colors group">
                                            <div className="flex items-center gap-3">
                                                <FileJson className="text-yellow-500" size={20} />
                                                <div>
                                                    <p className="font-medium text-slate-200">ocr_{type}.json</p>
                                                    <p className="text-xs text-slate-500">Full job data</p>
                                                </div>
                                            </div>
                                            <a
                                                href={`${API_BASE}/pipeline/${jobId}/ocr/${type}`}
                                                target="_blank"
                                                download={`ocr_{type}.json`}
                                                className="bg-slate-800 hover:bg-slate-700 text-slate-300 p-2 rounded transition-colors"
                                                title="Download"
                                            >
                                                <Download size={16} />
                                            </a>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Regions (Mocked loop since we don't have page count passed cleanly yet) */}
                            <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                                <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Pages Data</h3>
                                <p className="text-xs text-slate-500 italic">
                                    To download specific page regions, please use the Pipeline Viewer's "Artifacts JSON" panel.
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

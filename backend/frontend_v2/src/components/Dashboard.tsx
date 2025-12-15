import React, { useEffect, useState } from 'react';
import { Plus, Image as ImageIcon, Loader2, Calendar, Trash2, Package } from 'lucide-react';
import { JobCreation } from './JobCreation';
import { ArtifactsList } from './ArtifactsList';

const API_BASE = 'http://localhost:8000';

interface JobSummary {
    job_id: string;
    status: string;
    created_on: string;
    page_count: number;
    pages?: { page_number: number; status: string }[];
}

interface DashboardProps {
    onOpenJob: (jobId: string, page?: number) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onOpenJob }) => {
    const [jobs, setJobs] = useState<JobSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);



    const fetchJobs = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/jobs`);
            if (res.ok) {
                const data = await res.json();
                setJobs(data);
            }
        } catch (e) {
            console.error("Failed to fetch jobs", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchJobs();
    }, []);

    const handleCreateJob = async () => {
        setCreating(true);
        // ... (rest is inside JobCreation now but we still have this button)
        // Wait, I refactored handleCreateJob out? No, the button sets creating=true.
    };

    // ...

    const getStatusColor = (status?: string) => {
        switch (status) {
            case 'done': return 'bg-green-600 border-green-500 text-white';
            case 'typesetting': return 'bg-indigo-600 border-indigo-500 text-white';
            case 'cleaning': return 'bg-blue-600 border-blue-500 text-white';
            case 'translation': return 'bg-sky-600 border-sky-500 text-white';
            case 'active': return 'bg-orange-600 border-orange-500 text-white';
            case 'error': return 'bg-red-600 border-red-500 text-white font-bold animate-pulse';
            case 'pending': default: return 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white';
        }
    };

    // ... logic ...

    // Rendering Grid using job.pages if available
    // ...



    const handleDeleteJob = async (e: React.MouseEvent, id: string) => {
        e.preventDefault();
        e.stopPropagation();
        if (!confirm("Are you sure you want to delete this job? This cannot be undone.")) return;

        try {
            const res = await fetch(`${API_BASE}/jobs/${id}`, { method: 'DELETE' });
            if (res.ok) {
                setJobs(prev => prev.filter(j => j.job_id !== id));
            } else {
                alert("Failed to delete job");
            }
        } catch (e) {
            alert("Error deleting job");
        }
    };

    const [viewArtifactsId, setViewArtifactsId] = useState<string | null>(null);

    const handleViewArtifacts = (e: React.MouseEvent, id: string) => {
        e.preventDefault();
        e.stopPropagation();
        setViewArtifactsId(id);
    };

    if (creating) {
        // Create Job Screen
        return (
            <div className="min-h-screen bg-slate-900 text-slate-200 flex flex-col items-center justify-center p-8">
                <div className="max-w-md w-full bg-slate-900 p-8 rounded-xl shadow-2xl border border-slate-800 relative">
                    <button
                        onClick={() => setCreating(false)}
                        className="absolute top-4 right-4 text-slate-500 hover:text-white"
                    >
                        ✕
                    </button>
                    <JobCreation />
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-900 text-slate-200 p-8">
            {viewArtifactsId && (
                <ArtifactsList jobId={viewArtifactsId} onClose={() => setViewArtifactsId(null)} />
            )}

            <div className="max-w-6xl mx-auto">
                <header className="flex items-center justify-between mb-10">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-1">MojiTranslate AI</h1>
                        <p className="text-slate-400">Manage your translation projects</p>
                    </div>
                    <button
                        onClick={handleCreateJob}
                        disabled={creating}
                        className="bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-all shadow-lg shadow-blue-900/20"
                    >
                        {creating ? <Loader2 className="animate-spin" /> : <Plus size={20} />}
                        New Job
                    </button>
                </header>

                {loading ? (
                    <div className="flex justify-center py-20">
                        <Loader2 className="w-8 h-8 text-slate-500 animate-spin" />
                    </div>
                ) : jobs.length === 0 ? (
                    <div className="text-center py-20 bg-slate-900/50 rounded-xl border border-dashed border-slate-800">
                        <p className="text-slate-500 text-lg">No jobs found. Create your first one!</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {jobs.map(job => (
                            <div key={job.job_id} className="relative group bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-slate-700 transition-all flex flex-col">
                                <a
                                    href={`?job_id=${job.job_id}&page=1`}
                                    className="block p-5 hover:bg-slate-800 transition-colors flex-1"
                                >
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="bg-slate-800 p-2 rounded-lg">
                                            <ImageIcon className="text-slate-400" size={24} />
                                        </div>
                                        <span className={`text-xs font-medium px-2 py-1 rounded-full ${job.status === 'created' ? 'bg-green-900/30 text-green-400' : 'bg-slate-800 text-slate-400'}`}>
                                            {job.status}
                                        </span>
                                    </div>
                                    <h3 className="text-lg font-semibold text-white mb-1 truncate" title={job.job_id}>
                                        {job.job_id.substring(0, 8)}...
                                    </h3>
                                    <div className="flex items-center gap-4 text-sm text-slate-500 mt-4 mb-2">
                                        <div className="flex items-center gap-1">
                                            <ImageIcon size={14} /> {job.page_count} pages
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <Calendar size={14} /> {new Date(job.created_on).toLocaleDateString()}
                                        </div>
                                    </div>
                                </a>

                                {/* Actions Overlay */}
                                <div className="absolute top-5 right-5 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={(e) => handleViewArtifacts(e, job.job_id)}
                                        className="p-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg shadow-lg"
                                        title="View Artifacts"
                                    >
                                        <Package size={16} />
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handleDeleteJob(e, job.job_id); }}
                                        className="p-2 bg-slate-700 hover:bg-red-900 text-slate-400 hover:text-red-400 rounded-lg shadow-lg"
                                        title="Delete Job"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>

                                {/* Page Grid Footer */}
                                <div className="bg-slate-900/30 border-t border-slate-800 p-4">
                                    <p className="text-[10px] text-slate-500 mb-2 font-bold uppercase tracking-wider">Pages ({job.page_count})</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {(job.pages && job.pages.length > 0 ? job.pages : Array.from({ length: job.page_count || 0 }).map((_, i) => ({ page_number: i + 1, status: 'pending' }))).map((p) => {
                                            const pNum = p.page_number;


                                            const statusClass = getStatusColor(p.status);

                                            return (
                                                <button
                                                    key={pNum}
                                                    onClick={(e) => { e.stopPropagation(); onOpenJob(job.job_id, pNum); }}
                                                    className={`w-8 h-8 rounded flex items-center justify-center text-xs font-mono transition-all border ${statusClass} hover:brightness-110`}
                                                    title={`Page ${pNum}: ${p.status}`}
                                                >
                                                    {pNum}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};


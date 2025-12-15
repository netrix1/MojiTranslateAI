import React, { useState } from 'react';
import { Loader2, Image as ImageIcon, Upload } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export const JobCreation: React.FC = () => {
    const [uploading, setUploading] = useState(false);
    const [dragActive, setDragActive] = useState(false);

    const handleCreateAndUpload = async (files: FileList) => {
        setUploading(true);
        try {
            // 1. Create Job
            const jobResp = await fetch(`${API_BASE}/jobs`, { method: 'POST' });
            if (!jobResp.ok) throw new Error("Failed to create job");
            const jobData = await jobResp.json();
            const jobId = jobData.job_id;

            // 2. Upload Images
            // Sort by name for page ordering
            const fileArray = Array.from(files).sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));

            for (let i = 0; i < fileArray.length; i++) {
                const file = fileArray[i];
                const formData = new FormData();
                formData.append('file', file);
                const pageNum = i + 1;

                const upResp = await fetch(`${API_BASE}/jobs/${jobId}/pages/${pageNum}/image`, {
                    method: 'POST',
                    body: formData
                });
                if (!upResp.ok) throw new Error(`Failed to upload page ${pageNum}`);
            }

            // 3. Redirect to Viewer
            window.location.search = `?job_id=${jobId}&page=1`;

        } catch (e) {
            console.error(e);
            alert("Error creating job or uploading files");
            setUploading(false);
        }
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleCreateAndUpload(e.dataTransfer.files);
        }
    };

    return (
        <div className="w-full max-w-2xl mx-auto">
            <div
                className={`border-2 border-dashed rounded-xl p-12 flex flex-col items-center justify-center transition-all cursor-pointer group ${dragActive ? 'border-blue-500 bg-blue-500/10' : 'border-slate-700 hover:border-slate-600 bg-slate-900/50'}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-upload-new')?.click()}
            >
                {uploading ? (
                    <Loader2 className="w-16 h-16 text-blue-500 animate-spin mb-6" />
                ) : (
                    <div className="bg-slate-800 p-4 rounded-full mb-6 group-hover:scale-110 transition-transform">
                        <Upload className="w-8 h-8 text-blue-400" />
                    </div>
                )}

                <h3 className="text-xl font-bold text-white mb-2">Create Job & Upload Pages</h3>
                <p className="text-slate-400 text-center max-w-xs mb-6">
                    {uploading ? "Processing your files..." : "Drag & drop images (JPG, PNG) here to start a new translation project"}
                </p>

                <button
                    className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                    disabled={uploading}
                >
                    Select Files
                </button>

                <input
                    id="file-upload-new"
                    type="file"
                    multiple
                    className="hidden"
                    accept="image/*"
                    onChange={(e) => e.target.files && handleCreateAndUpload(e.target.files)}
                    disabled={uploading}
                />
            </div>
        </div>
    );
};

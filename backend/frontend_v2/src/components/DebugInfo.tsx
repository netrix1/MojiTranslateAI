import React, { useEffect, useState } from 'react';
import { Activity, Server, Database, FileCode } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

interface HealthStatus {
    status: string;
    version: string;
}

export const DebugInfo: React.FC = () => {
    const [health, setHealth] = useState<HealthStatus | null>(null);
    const [config, setConfig] = useState<any>(null);

    useEffect(() => {
        fetch(`${API_BASE}/health`).then(r => r.json()).then(setHealth).catch(console.error);
        // fetch(`${API_BASE}/debug/config`).then(r => r.json()).then(setConfig).catch(console.error);
    }, []);

    return (
        <div className="p-6 bg-slate-900 rounded-xl border border-slate-800 text-slate-200">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Activity className="text-blue-500" /> System Health
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                    <h3 className="text-sm font-semibold text-slate-400 mb-2 flex items-center gap-2">
                        <Server size={14} /> API Status
                    </h3>
                    <div className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${health?.status === 'ok' ? 'bg-green-500' : 'bg-red-500'}`} />
                        <span className="font-mono">{health?.status || 'Unknown'}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Version: {health?.version}</p>
                </div>

                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                    <h3 className="text-sm font-semibold text-slate-400 mb-2 flex items-center gap-2">
                        <Database size={14} /> Configuration
                    </h3>
                    <p className="text-xs text-slate-500">Environment checks pending...</p>
                </div>
            </div>
        </div>
    );
};

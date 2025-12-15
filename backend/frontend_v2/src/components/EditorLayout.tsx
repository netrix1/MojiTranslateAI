import React from 'react';

interface EditorLayoutProps {
    sidebar: React.ReactNode;
    children: React.ReactNode;
    toolbar?: React.ReactNode;
}

export const EditorLayout: React.FC<EditorLayoutProps> = ({ sidebar, children, toolbar }) => {
    return (
        <div className="flex flex-col h-screen bg-slate-900 text-slate-100 overflow-hidden">
            {toolbar && (
                <div className="h-12 border-b border-slate-800 bg-slate-900 flex items-center px-4">
                    {toolbar}
                </div>
            )}
            <div className="flex flex-1 overflow-hidden">
                <aside className="w-80 flex-none z-10">
                    {sidebar}
                </aside>
                <main className="flex-1 relative bg-black/20 p-4 overflow-hidden">
                    {children}
                </main>
            </div>
        </div>
    );
};

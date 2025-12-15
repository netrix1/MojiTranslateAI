import React, { useEffect, useState } from 'react';
import { PipelineViewer } from './components/PipelineViewer';
import { DebugInfo } from './components/DebugInfo';
import { Dashboard } from './components/Dashboard';

function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const j = params.get('job_id');
    const p = params.get('page');
    if (j) setJobId(j);
    if (p) setPageNumber(parseInt(p, 10));
  }, []);

  const handlePageChange = (newPage: number) => {
    setPageNumber(newPage);
    const url = new URL(window.location.href);
    url.searchParams.set('page', newPage.toString());
    window.history.pushState({}, '', url.toString());
  };

  if (!jobId) {
    return (
      <>
        <DebugInfo />
        <Dashboard onOpenJob={(id, page = 1) => {
          setJobId(id);
          setPageNumber(page);
          const url = new URL(window.location.href);
          url.searchParams.set('job_id', id);
          url.searchParams.set('page', page.toString());
          window.history.pushState({}, '', url.toString());
        }} />
      </>
    );
  }

  return <PipelineViewer jobId={jobId} pageNumber={pageNumber} onPageChange={handlePageChange} />;
}

export default App;

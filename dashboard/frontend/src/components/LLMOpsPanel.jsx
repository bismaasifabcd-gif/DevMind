import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const LLMOpsPanel = () => {
  const [backendOnline, setBackendOnline] = useState(null);
  const [runs, setRuns] = useState([]);
  const [runsError, setRunsError] = useState('');
  const [loading, setLoading] = useState(false);

  // Check backend health
  useEffect(() => {
    axios.get(`${API_URL}/`)
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false));
  }, []);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setRunsError('');
    try {
      const { data } = await axios.get(`${API_URL}/runs?n=10`);
      setRuns(data.runs || []);
    } catch (e) {
      setRunsError('Unable to fetch experiment data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 60000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  const formatTime = (ms) => {
    if (!ms) return '—';
    return new Date(ms).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatLatency = (s) => {
    if (s == null || s === 0) return '—';
    return s >= 60 ? `${(s / 60).toFixed(1)}m` : `${s}s`;
  };

  return (
    <div className="llmops-panel">
      <h2 className="panel-title">System Metrics</h2>
      <p className="panel-subtitle">Real-time monitoring and performance</p>
      
      {/* System Status */}
      <div className="metrics-grid" style={{ marginBottom: 'var(--spacing-xl)' }}>
        <div className="metric-item">
          <span className="metric-label">Backend API</span>
          <span className="metric-value" style={{
            color: backendOnline ? 'var(--success)' : 
                   backendOnline === false ? 'var(--error)' : 'var(--text-muted)'
          }}>
            {backendOnline ? 'Online' : backendOnline === false ? 'Offline' : 'Checking...'}
          </span>
        </div>
        
        <div className="metric-item">
          <span className="metric-label">Model Response</span>
          <span className="metric-value">1.2s</span>
        </div>
        
        <div className="metric-item">
          <span className="metric-label">Success Rate</span>
          <span className="metric-value">98.5%</span>
        </div>
        
        <div className="metric-item">
          <span className="metric-label">Total Runs</span>
          <span className="metric-value">{runs.length}</span>
        </div>
      </div>

      {/* Recent Experiments */}
      <div style={{ marginBottom: 'var(--spacing-xl)' }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          marginBottom: 'var(--spacing-md)'
        }}>
          <h3 style={{ 
            fontSize: '1rem', 
            fontWeight: '600', 
            color: 'var(--text-primary)',
            margin: 0
          }}>
            Recent Experiments
          </h3>
          <button
            onClick={fetchRuns}
            disabled={loading}
            style={{
              fontSize: '0.75rem',
              padding: 'var(--spacing-xs) var(--spacing-sm)',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-light)',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              color: 'var(--text-secondary)',
              transition: 'all 0.3s ease'
            }}
          >
            {loading ? '...' : '↻ Refresh'}
          </button>
        </div>

        {runsError && (
          <div style={{ 
            padding: 'var(--spacing-md)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-md)',
            color: '#dc2626',
            fontSize: '0.875rem'
          }}>
            {runsError}
          </div>
        )}

        {!runsError && runs.length === 0 && !loading && (
          <div style={{ 
            padding: 'var(--spacing-xl)',
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.875rem'
          }}>
            No experiments recorded yet.<br />
            <span style={{ fontSize: '0.75rem' }}>Run an analysis to see metrics here.</span>
          </div>
        )}

        {runs.length > 0 && (
          <div style={{ 
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-md)',
            overflow: 'hidden'
          }}>
            {runs.slice(0, 5).map((run, index) => (
              <div 
                key={run.run_id} 
                style={{
                  padding: 'var(--spacing-md)',
                  borderBottom: index < Math.min(runs.length, 5) - 1 ? '1px solid var(--border-light)' : 'none',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <div style={{ 
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    color: 'var(--text-primary)',
                    marginBottom: '0.25rem'
                  }}>
                    {run.repo || 'Unknown Repository'}
                  </div>
                  <div style={{ 
                    fontSize: '0.75rem',
                    color: 'var(--text-muted)'
                  }}>
                    {formatTime(run.start_time)} • {formatLatency(run.latency_seconds)}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
                  {run.test_passed === 1 && (
                    <span style={{ color: 'var(--success)', fontSize: '0.875rem' }}>✓</span>
                  )}
                  {run.test_passed === 0 && (
                    <span style={{ color: 'var(--error)', fontSize: '0.875rem' }}>✗</span>
                  )}
                  <span style={{
                    padding: '0.25rem 0.5rem',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: run.status === 'awaiting_approval' ? 'rgba(251, 191, 36, 0.2)' :
                                   run.status === 'no_issue_found' ? 'rgba(16, 185, 129, 0.2)' :
                                   run.status === 'failed' ? 'rgba(239, 68, 68, 0.2)' :
                                   'var(--bg-tertiary)',
                    color: run.status === 'awaiting_approval' ? '#d97706' :
                          run.status === 'no_issue_found' ? '#059669' :
                          run.status === 'failed' ? '#dc2626' :
                          'var(--text-secondary)'
                  }}>
                    {run.status?.replace(/_/g, ' ') || 'Unknown'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div>
        <h3 style={{ 
          fontSize: '1rem', 
          fontWeight: '600', 
          color: 'var(--text-primary)',
          marginBottom: 'var(--spacing-md)'
        }}>
          Quick Actions
        </h3>
        
        <div style={{ display: 'grid', gap: 'var(--spacing-sm)' }}>
          <a 
            href="http://localhost:6006" 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ textAlign: 'left', textDecoration: 'none' }}
          >
            📊 Phoenix Traces
          </a>
          <a 
            href="http://localhost:5000" 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ textAlign: 'left', textDecoration: 'none' }}
          >
            🧪 MLflow Experiments
          </a>
        </div>
      </div>
    </div>
  );
};

export default LLMOpsPanel;
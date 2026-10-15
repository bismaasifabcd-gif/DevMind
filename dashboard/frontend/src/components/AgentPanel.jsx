import React from 'react';

const AgentPanel = ({
  repoPath, setRepoPath,
  repoFullName, setRepoFullName,
  issueText, setIssueText,
  fileName, setFileName,
  functionName, setFunctionName,
  runAgent, running, approving, result, message, approve, reject
}) => {
  const [issueNumber, setIssueNumber] = React.useState('');

  const handleRunAgent = () => {
    const payload = {
      repo_path: repoPath,
      repo_full_name: repoFullName || null,
      issue_text: issueText || null,
      issue_number: issueNumber ? parseInt(issueNumber) : null,
      file_name: fileName || null,
      function_name: functionName || null,
    };
    runAgent(payload);
  };

  const isError = message && (message.startsWith('❌') || message.toLowerCase().includes('error') || message.toLowerCase().includes('failed'));
  const isSuccess = message && (message.startsWith('✅') || message.toLowerCase().includes('pr created') || message.toLowerCase().includes('rejected'));

  return (
    <div className="agent-panel">
      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Active Repos</div>
          <div className="stat-value">012</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Issues Resolved</div>
          <div className="stat-value">248</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Agent Uptime</div>
          <div className="stat-value">99.8%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Fix Time</div>
          <div className="stat-value">4m 12s</div>
        </div>
      </div>

      {/* Main Panel */}
      <div>
        <h2 className="panel-title">CODE ANALYSIS ENGINE</h2>
        <p className="panel-subtitle">
          Autonomous software engineering powered by advanced AI
        </p>

        {/* Repository Location */}
        <div className="form-group">
          <label className="form-label">Repository Location</label>
          <input
            type="text"
            className="form-input"
            placeholder="GitHub URL, owner/repo, or local path"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
          />
        </div>

        {/* GitHub Repository */}
        <div className="form-group">
          <label className="form-label">GitHub Repository</label>
          <input
            type="text"
            className="form-input"
            placeholder="username/repository (auto-detected)"
            value={repoFullName}
            onChange={(e) => setRepoFullName(e.target.value)}
          />
        </div>

        {/* Issue Description */}
        <div className="form-group">
          <label className="form-label">Issue Description</label>
          <textarea
            className="form-textarea"
            placeholder="Describe the issue, or leave blank for automatic detection..."
            value={issueText}
            onChange={(e) => setIssueText(e.target.value)}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)', marginTop: 'var(--spacing-sm)' }}>
            <small style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
              Leave empty for auto-detection
            </small>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-xs)' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>or GitHub Issue #</span>
              <input
                type="number"
                value={issueNumber}
                onChange={(e) => setIssueNumber(e.target.value)}
                placeholder="123"
                style={{ 
                  width: '80px', 
                  padding: '4px 8px', 
                  fontSize: '0.75rem',
                  border: '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-sm)'
                }}
              />
            </div>
          </div>
        </div>

        {/* Optional Fields Row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
          <div className="form-group">
            <label className="form-label">Target File (Optional)</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. main.py"
              value={fileName}
              onChange={(e) => setFileName(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Target Function (Optional)</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. calculateTotal"
              value={functionName}
              onChange={(e) => setFunctionName(e.target.value)}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="btn-group">
          <button 
            className="btn btn-secondary" 
            onClick={() => {
              setRepoPath('');
              setRepoFullName('');
              setIssueText('');
              setFileName('');
              setFunctionName('');
              setIssueNumber('');
            }}
          >
            CLEAR
          </button>
          <button 
            className="btn btn-primary" 
            onClick={handleRunAgent}
            disabled={running || !repoPath.trim()}
          >
            {running ? 'ANALYZING...' : 'RUN ANALYSIS'}
          </button>
        </div>

        {/* Status Message */}
        {message && (
          <div 
            className="result-message" 
            style={{
              marginTop: 'var(--spacing-lg)',
              padding: 'var(--spacing-md)',
              backgroundColor: isError ? 'rgba(239, 68, 68, 0.1)' : 
                             isSuccess ? 'rgba(16, 185, 129, 0.1)' : 
                             'var(--bg-tertiary)',
              border: `1px solid ${isError ? 'rgba(239, 68, 68, 0.3)' : 
                                 isSuccess ? 'rgba(16, 185, 129, 0.3)' : 
                                 'var(--border-light)'}`,
              borderRadius: 'var(--radius-md)',
              fontSize: '0.875rem',
              color: isError ? '#dc2626' : 
                   isSuccess ? '#059669' : 
                   'var(--text-secondary)'
            }}
          >
            {message}
          </div>
        )}

        {/* Results Panel */}
        {result && (
          <div className="result-panel" style={{
            marginTop: 'var(--spacing-lg)',
            padding: 'var(--spacing-xl)',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-sm)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--spacing-md)' }}>
              <h3 style={{ 
                color: 'var(--text-primary)',
                fontSize: '1.125rem',
                fontWeight: '600',
                margin: 0
              }}>
                Analysis Complete
              </h3>
              <span style={{
                display: 'inline-block',
                padding: '0.25rem 0.75rem',
                fontSize: '0.75rem',
                fontWeight: '600',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                borderRadius: 'var(--radius-md)',
                backgroundColor: result.status === 'awaiting_approval' ? 'rgba(251, 191, 36, 0.2)' :
                               result.status === 'no_issue_found' ? 'rgba(16, 185, 129, 0.2)' :
                               result.status === 'failed' ? 'rgba(239, 68, 68, 0.2)' :
                               'var(--bg-tertiary)',
                color: result.status === 'awaiting_approval' ? '#d97706' :
                      result.status === 'no_issue_found' ? '#059669' :
                      result.status === 'failed' ? '#dc2626' :
                      'var(--text-secondary)'
              }}>
                {result.status?.replace(/_/g, ' ')}
              </span>
            </div>
            
            {result.status === 'awaiting_approval' ? (
              <div>
                <p style={{ marginBottom: 'var(--spacing-md)', color: 'var(--text-secondary)' }}>
                  Changes are ready for review and approval
                </p>
                <div className="btn-group">
                  <button 
                    className="btn btn-secondary" 
                    onClick={() => reject(result.run_id)}
                    disabled={approving}
                  >
                    REJECT
                  </button>
                  <button 
                    className="btn btn-primary" 
                    onClick={() => approve(result.run_id)}
                    disabled={approving}
                  >
                    {approving ? 'CREATING PR...' : 'APPROVE & CREATE PR'}
                  </button>
                </div>
              </div>
            ) : (
              <div>
                {result.message && (
                  <p style={{ 
                    marginBottom: 'var(--spacing-sm)',
                    color: 'var(--text-secondary)',
                    fontSize: '0.875rem'
                  }}>
                    {result.message}
                  </p>
                )}
                
                {result.plan && (
                  <details style={{ marginTop: 'var(--spacing-md)' }}>
                    <summary style={{ 
                      cursor: 'pointer', 
                      fontWeight: '500',
                      color: 'var(--text-primary)',
                      marginBottom: 'var(--spacing-sm)'
                    }}>
                      Execution Plan
                    </summary>
                    <pre style={{
                      background: 'var(--bg-tertiary)',
                      padding: 'var(--spacing-md)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.75rem',
                      color: 'var(--text-secondary)',
                      overflow: 'auto'
                    }}>
                      {result.plan}
                    </pre>
                  </details>
                )}

                {result.patch && (
                  <details style={{ marginTop: 'var(--spacing-md)' }}>
                    <summary style={{ 
                      cursor: 'pointer', 
                      fontWeight: '500',
                      color: 'var(--text-primary)',
                      marginBottom: 'var(--spacing-sm)'
                    }}>
                      Generated Fix
                    </summary>
                    <pre style={{
                      background: 'var(--bg-tertiary)',
                      padding: 'var(--spacing-md)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.75rem',
                      color: 'var(--text-secondary)',
                      overflow: 'auto'
                    }}>
                      {result.patch}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentPanel;
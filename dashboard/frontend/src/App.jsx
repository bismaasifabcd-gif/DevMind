import React, { useState } from 'react'
import axios from 'axios'
import Header from './components/Header'
import AgentPanel from './components/AgentPanel'
import LLMOpsPanel from './components/LLMOpsPanel'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [repoPath,      setRepoPath]      = useState('')
  const [repoFullName,  setRepoFullName]  = useState('')
  const [issueText,     setIssueText]     = useState('')
  const [fileName,      setFileName]      = useState('')
  const [functionName,  setFunctionName]  = useState('')

  const [running,  setRunning]  = useState(false)
  const [approving, setApproving] = useState(false)
  const [result,   setResult]   = useState(null)
  const [message,  setMessage]  = useState('')

  async function runAgent(payload = null) {
    setRunning(true)
    setResult(null)
    setMessage('DevMind is analyzing your code — this may take 1-2 minutes…')
    
    const requestPayload = payload || {
      repo_path: repoPath,
      repo_full_name: repoFullName || null,
      issue_text: issueText || null,
      file_name: fileName || null,
      function_name: functionName || null,
    }
    
    try {
      const resp = await axios.post(`${API_URL}/run-agent`, requestPayload, { 
        timeout: 600_000 
      })
      setResult(resp.data)
      setMessage('')
    } catch (e) {
      setMessage(e?.response?.data?.detail || e.message || 'Unknown error')
      setResult(null)
    } finally {
      setRunning(false)
    }
  }

  async function approve(runId) {
    setApproving(true)
    setMessage('Creating pull request…')
    try {
      const resp = await axios.post(`${API_URL}/approve/${runId}`, {}, { timeout: 60_000 })
      const prUrl = resp.data?.pr_url
      // Clear the run result — no more awaiting_approval state
      setResult(null)
      setMessage(prUrl
        ? `✅ Pull request created: ${prUrl}`
        : '✅ Pull request created successfully')
    } catch (e) {
      setMessage('❌ ' + (e?.response?.data?.detail || e.message))
    } finally {
      setApproving(false)
    }
  }

  async function reject(runId) {
    try {
      await axios.post(`${API_URL}/reject/${runId}`, {}, { timeout: 10_000 })
      setResult(null)
      setMessage('Analysis rejected — no changes made.')
    } catch (e) {
      setMessage('❌ ' + (e?.response?.data?.detail || e.message))
    }
  }

  return (
    <div className="app">
      <div className="backdrop" />
      <div className="container">
        <Header />
        
        <main className="main">
          <AgentPanel
            repoPath={repoPath}           setRepoPath={setRepoPath}
            repoFullName={repoFullName}   setRepoFullName={setRepoFullName}
            issueText={issueText}         setIssueText={setIssueText}
            fileName={fileName}           setFileName={setFileName}
            functionName={functionName}   setFunctionName={setFunctionName}
            runAgent={runAgent}
            running={running}
            approving={approving}
            result={result}
            message={message}
            approve={approve}
            reject={reject}
          />
          <LLMOpsPanel />
        </main>
        
        <footer className="footer">
          <div className="footer-content">
            <span>DevMind © 2024</span>
            <div className="footer-links">
              <a href="http://localhost:6006" target="_blank" rel="noopener noreferrer">
                Phoenix Traces
              </a>
              <a href="http://localhost:5000" target="_blank" rel="noopener noreferrer">
                MLflow Experiments
              </a>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

import React from 'react';
import LogoIcon from './LogoIcon';

const Header = () => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo-section">
          <LogoIcon size={50} className="header-logo" />
          <div className="brand-text">
            <h1 className="brand-title">
              <span className="brand-dev">DEV</span>
              <span className="brand-mind">MIND</span>
            </h1>
            <p className="brand-subtitle">autonomous engineering</p>
          </div>
        </div>
        
        <nav className="nav-menu">
          <a href="#dashboard" className="nav-item active">DASHBOARD</a>
          <a href="#agent" className="nav-item">AGENT</a>
          <a href="#llmops" className="nav-item">LLMOPS</a>
          <a href="#settings" className="nav-item">SETTINGS</a>
        </nav>
        
        <div className="header-actions">
          <button className="status-indicator">
            <div className="status-dot status-online"></div>
            <span>Online</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
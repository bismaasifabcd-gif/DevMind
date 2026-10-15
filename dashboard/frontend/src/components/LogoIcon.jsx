import React from 'react';

const LogoIcon = ({ size = 50, className = "" }) => {
  return (
    <div className={`logo-icon-container ${className}`} style={{ width: size, height: size }}>
      <div 
        className="logo-icon-image"
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-primary)',
          border: '2px solid var(--border-light)',
          transition: 'all 0.3s ease'
        }}
      >
        <img 
          src="/devmind-logo.png"
          alt="DevMind Logo"
          style={{
            width: '90%',
            height: '90%',
            objectFit: 'contain'
          }}
        />
      </div>
    </div>
  );
};

export default LogoIcon;
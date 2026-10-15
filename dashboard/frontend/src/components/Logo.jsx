import React from 'react';

const Logo = ({ size = 80, className = "" }) => {
  return (
    <div className={`logo-container ${className}`} style={{ width: size, height: size }}>
      <div 
        className="logo-image"
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%)',
          padding: '8px',
          boxShadow: '0 4px 20px rgba(59, 130, 246, 0.3)',
          transition: 'all 0.3s ease'
        }}
      >
        <svg 
          width={size * 0.8} 
          height={size * 0.8} 
          viewBox="0 0 800 800" 
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* DevMind Logo SVG based on the provided image */}
          <g transform="translate(400, 250)">
            {/* Main diamond shape - dark blue parts */}
            <path d="M-100,-80 L0,-140 L100,-80 L60,-40 L0,-60 L-60,-40 Z" fill="#1e3a8a"/>
            <path d="M-100,-80 L-140,0 L-100,80 L-60,40 L-80,0 L-60,-40 Z" fill="#1e3a8a"/>
            <path d="M60,-40 L100,-80 L140,0 L100,80 L60,40 L80,0 Z" fill="#06b6d4"/>
            <path d="M-60,40 L0,60 L60,40 L100,80 L0,140 L-100,80 Z" fill="#06b6d4"/>
            
            {/* Inner geometric pattern */}
            <path d="M-60,-40 L0,-60 L60,-40 L40,-20 L0,-30 L-40,-20 Z" fill="#ffffff" opacity="0.9"/>
            <path d="M-60,-40 L-40,-20 L-60,40 L-40,20 L-20,0 L-40,-20 Z" fill="#ffffff" opacity="0.9"/>
            <path d="M40,-20 L60,-40 L60,40 L40,20 L20,0 L40,-20 Z" fill="#ffffff" opacity="0.9"/>
            <path d="M-40,20 L0,30 L40,20 L60,40 L0,60 L-60,40 Z" fill="#ffffff" opacity="0.9"/>
            
            {/* Central connector */}
            <circle cx="0" cy="0" r="15" fill="#3b82f6"/>
            <circle cx="0" cy="0" r="8" fill="#ffffff"/>
          </g>
          
          {/* DevMind Text */}
          <g transform="translate(400, 500)">
            <text x="-180" y="0" fill="#1e3a8a" fontSize="120" fontFamily="'Inter', sans-serif" fontWeight="800">DEV</text>
            <text x="20" y="0" fill="#06b6d4" fontSize="120" fontFamily="'Inter', sans-serif" fontWeight="800">MIND</text>
          </g>
          
          {/* Subtitle */}
          <g transform="translate(400, 580)">
            <text x="0" y="0" fill="#64748b" fontSize="32" fontFamily="'Inter', sans-serif" fontWeight="600" textAnchor="middle">
              AUTONOMOUS SOFTWARE ENGINEERING
            </text>
          </g>
        </svg>
      </div>
    </div>
  );
};

export default Logo;
import React from 'react';

export const AntigravityArchLogo: React.FC<{ className?: string }> = ({ className = 'w-20 h-20' }) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="agyArchGrad" x1="60" y1="8" x2="60" y2="92" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#BDBFC5" stopOpacity="0.85" />
        <stop offset="58%" stopColor="#D6D8DD" stopOpacity="0.55" />
        <stop offset="100%" stopColor="#EDEEF1" stopOpacity="0.05" />
      </linearGradient>
    </defs>
    <path
      d="M60 12C43.5 12 34.5 34.5 23.5 64.5C18.5 78 13 86 10 89C16 89 23.5 84.5 30.5 74.5C39.5 61.5 47.5 46 60 46C72.5 46 80.5 61.5 89.5 74.5C96.5 84.5 104 89 110 89C107 86 101.5 78 96.5 64.5C85.5 34.5 76.5 12 60 12Z"
      fill="url(#agyArchGrad)"
    />
  </svg>
);

export const DataAgentKitLogo: React.FC<{ className?: string }> = ({ className = 'w-11 h-11' }) => (
  <svg viewBox="0 0 48 42" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    {/* Red top-left cloud dome */}
    <path
      d="M12.6 15.8C14.3 10.6 19.2 7 25 7C26.9 7 28.7 7.4 30.3 8.2"
      stroke="#EA4335"
      strokeWidth="3.8"
      strokeLinecap="round"
    />
    {/* Yellow left lobe and cloud bottom-left baseline */}
    <path
      d="M12.6 15.8C8.2 16.5 5 20.3 5 24.9C5 30 9.1 34 14.2 34H21.5"
      stroke="#FBBC04"
      strokeWidth="3.8"
      strokeLinecap="round"
    />
    {/* Blue 4-point AI sparkle at upper-right of cloud dome */}
    <path
      d="M34 8.2C34.5 11.6 36.1 13.2 39.5 13.7C36.1 14.2 34.5 15.8 34 19.2C33.5 15.8 31.9 14.2 28.5 13.7C31.9 13.2 33.5 11.6 34 8.2Z"
      fill="#4285F4"
    />
    {/* Top right bar (Blue) */}
    <path
      d="M30.5 22.5H42.5"
      stroke="#4285F4"
      strokeWidth="3.8"
      strokeLinecap="round"
    />
    {/* Middle right bar (Green) */}
    <path
      d="M27 28.2H44"
      stroke="#34A853"
      strokeWidth="3.8"
      strokeLinecap="round"
    />
    {/* Bottom right bar (Green) */}
    <path
      d="M23.5 34H41"
      stroke="#34A853"
      strokeWidth="3.8"
      strokeLinecap="round"
    />
  </svg>
);

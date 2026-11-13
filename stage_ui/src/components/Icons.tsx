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
  <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    {/* Google Cloud-inspired multicolored cloud + AI sparkles matching Screenshot 3 */}
    <path
      d="M15.5 33.5H12.8C8.5 33.5 5 30.1 5 25.8C5 22.1 7.6 19 11.1 18.2C12.4 12.9 17.2 9 22.9 9C28.8 9 33.8 13.2 34.8 18.8"
      stroke="#FBBC04"
      strokeWidth="3.2"
      strokeLinecap="round"
    />
    <path
      d="M22.9 9C28.2 9 32.8 12.4 34.4 17.2"
      stroke="#EA4335"
      strokeWidth="3.2"
      strokeLinecap="round"
    />
    <path
      d="M12.5 33.5H34.5C38.4 33.5 41.5 30.4 41.5 26.5C41.5 22.8 38.6 19.7 35 19.5"
      stroke="#4285F4"
      strokeWidth="3.2"
      strokeLinecap="round"
    />
    <path
      d="M15 38.5H31.5"
      stroke="#34A853"
      strokeWidth="3.2"
      strokeLinecap="round"
    />
    {/* AI Sparkle */}
    <path
      d="M38.5 10.5L39.7 13.8L43 15L39.7 16.2L38.5 19.5L37.3 16.2L34 15L37.3 13.8L38.5 10.5Z"
      fill="#EA4335"
    />
    <circle cx="24" cy="24" r="2.2" fill="#4285F4" />
  </svg>
);

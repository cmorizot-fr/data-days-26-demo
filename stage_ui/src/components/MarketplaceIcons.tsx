import React from 'react';

interface IconProps {
  className?: string;
}

/* ============================================================================
 * Featured Tiles & Third-Party Brand Icons
 * ============================================================================ */

export const FirebaseIcon: React.FC<IconProps> = ({ className = 'w-7 h-7' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path
      d="M16.4 3.5C13.6 7.4 11.4 10.6 10.6 14.3C9.9 12.6 9.7 10.9 10.1 9.1C7.1 11.5 5.5 15 5.5 18.7C5.5 24.4 10.2 28.8 16 28.8C21.8 28.8 26.5 24.4 26.5 18.7C26.5 12.5 22.1 7.6 16.4 3.5Z"
      fill="#DD2C00"
    />
    <path
      d="M16.2 9.4C14.1 12.2 12.4 15.1 11.9 18.2C11.3 17.1 10.9 15.8 11 14.3C8.9 16.2 7.8 18.7 7.8 21.3C7.8 25.5 11.5 28.8 16 28.8C20.5 28.8 24.2 25.5 24.2 21.3C24.2 16.7 20.6 12.5 16.2 9.4Z"
      fill="#FF9100"
    />
    <path
      d="M16 16.5C14 18.4 12.5 20.7 12.5 23.1C12.5 26.2 14.1 28.8 16 28.8C18.8 28.8 20.8 26.3 20.8 23.3C20.8 20.4 18.7 18.3 16 16.5Z"
      fill="#FFC400"
    />
  </svg>
);

export const NotionIcon: React.FC<IconProps> = ({ className = 'w-7 h-7' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path
      d="M6.4 6.2L20.8 5.1C22.1 5 22.4 5.4 23.3 6L26.5 8.2C27 8.6 27.2 8.8 27.2 9.3V24.9C27.2 25.9 26.8 26.5 25.6 26.6L9.7 27.5C8.7 27.6 8.3 27.4 7.7 26.7L5.2 23.4C4.7 22.8 4.5 22.3 4.5 21.6V7.6C4.5 6.7 5 6.3 6.4 6.2Z"
      fill="#1F1F1F"
    />
    <path
      d="M9.6 10.6L24.5 9.6C25 9.6 25.3 9.9 25.3 10.4V23.9C25.3 24.5 25 24.8 24.4 24.8L10.3 25.6C9.7 25.6 9.3 25.3 9.3 24.7V11.3C9.3 10.9 9.4 10.6 9.6 10.6Z"
      fill="#FFFFFF"
    />
    <path
      d="M12.3 13.7L14.9 13.5L19.6 20.5V14.2L18.4 14.3V13.3L22.3 13V14L21.3 14.1V22.9L19.6 23L14.5 15.4V22.1L15.7 22V23L12.1 23.2V22.2L13.1 22.1V14.7L12.3 14.6V13.7Z"
      fill="#1F1F1F"
    />
  </svg>
);

export const TealBracketIcon: React.FC<IconProps> = ({ className = 'w-7 h-7' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect x="4" y="4" width="24" height="24" rx="6" fill="#009E73" />
    <path
      d="M13.5 10.5H10.5V21.5H13.5M18.5 10.5H21.5V21.5H18.5"
      stroke="#FFFFFF"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M14.2 13.2L17.8 18.8M17.8 13.2L14.2 18.8"
      stroke="#FFFFFF"
      strokeWidth="2"
      strokeLinecap="round"
    />
  </svg>
);

export const DynatraceIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    {/* Top green-lime ribbon */}
    <path
      d="M8.5 13.5L19.5 6.8C20.9 6 22.6 6.8 23.1 8.3L25.4 15.5L14.5 13.5H8.5Z"
      fill="#6FBE44"
    />
    {/* Right cyan-blue ribbon */}
    <path
      d="M23.1 8.3L28.5 20.5C29.1 21.9 28.4 23.6 27 24.2L20.5 27.1L21.5 16L23.1 8.3Z"
      fill="#1496FF"
    />
    {/* Bottom purple-indigo ribbon */}
    <path
      d="M27 24.2L15.8 29.4C14.3 30.1 12.5 29.3 12 27.8L10 21.5L21 23L27 24.2Z"
      fill="#6F2DA8"
    />
    {/* Left emerald-blue ribbon */}
    <path
      d="M12 27.8L7.2 16.8C6.6 15.3 7.3 13.7 8.8 13.1L15 10.5L14.2 21.5L12 27.8Z"
      fill="#1A73E8"
    />
    {/* Crisp white inner diamond/square cutout */}
    <path
      d="M14.2 13.6L21.8 13.6L21.8 22.2L14.2 22.2Z"
      fill="#FFFFFF"
      transform="rotate(-12 18 18)"
    />
  </svg>
);

export const LinearIcon: React.FC<IconProps> = ({ className = 'w-7 h-7' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <circle cx="16" cy="16" r="12" fill="#5E6AD2" />
    <path
      d="M6.4 17.8L14.2 25.6M5.4 13.2L18.8 26.6M8.1 9.5L22.5 23.9"
      stroke="#FFFFFF"
      strokeWidth="2.1"
      strokeLinecap="round"
    />
  </svg>
);

export const StripeIcon: React.FC<IconProps> = ({ className = 'w-7 h-7' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect x="4" y="4" width="24" height="24" rx="6.5" fill="#635BFF" />
    <path
      d="M15.3 12.7C15.3 12 15.9 11.7 16.9 11.7C18.3 11.7 19.9 12.1 21.2 12.8V8.9C19.8 8.3 18.4 8 16.9 8C13.4 8 11.1 9.8 11.1 12.9C11.1 17.7 17.6 16.9 17.6 19C17.6 19.8 16.9 20.1 15.8 20.1C14.2 20.1 12.2 19.4 10.6 18.5V22.5C12.3 23.2 14.1 23.6 15.8 23.6C19.4 23.6 21.9 21.8 21.9 18.7C21.9 13.6 15.3 14.5 15.3 12.7Z"
      fill="#FFFFFF"
    />
  </svg>
);

/* ============================================================================
 * Google Workspace Icons (Exact 6 items)
 * ============================================================================ */

export const GoogleDocsIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path
      d="M8.5 3.5H19L25.5 10V26.5C25.5 27.6 24.6 28.5 23.5 28.5H8.5C7.4 28.5 6.5 27.6 6.5 26.5V5.5C6.5 4.4 7.4 3.5 8.5 3.5Z"
      fill="#4285F4"
    />
    <path d="M19 3.5L25.5 10H20.5C19.7 10 19 9.3 19 8.5V3.5Z" fill="#1967D2" />
    <rect x="10.5" y="14.5" width="11" height="1.8" rx="0.9" fill="#FFFFFF" />
    <rect x="10.5" y="18.2" width="11" height="1.8" rx="0.9" fill="#FFFFFF" />
    <rect x="10.5" y="21.9" width="7.5" height="1.8" rx="0.9" fill="#FFFFFF" />
  </svg>
);

export const GoogleSheetsIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect x="3" y="6.5" width="26" height="19" rx="3.2" fill="#34A853" />
    <rect x="3" y="6.5" width="7" height="19" rx="3.2" fill="#188038" />
    <rect x="7" y="10.5" width="18" height="11" rx="1.4" fill="#E6F4EA" />
    <path
      d="M13 10.5V21.5M19 10.5V21.5M7 14.2H25M7 17.8H25"
      stroke="#34A853"
      strokeWidth="1.5"
    />
  </svg>
);

export const GoogleSlidesIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect x="4" y="6" width="24" height="20" rx="3.2" fill="#FBBC04" />
    <rect x="7.5" y="10.5" width="17" height="11" rx="1.4" fill="#FFFFFF" />
    <rect x="10" y="13" width="12" height="6" rx="0.8" fill="#FBBC04" />
  </svg>
);

export const GoogleDriveIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path d="M11.6 5.5L20.4 5.5L28.5 19.5L24.1 27L16 13L11.6 5.5Z" fill="#FBBC04" />
    <path d="M11.6 5.5L3.5 19.5L7.9 27L16 13L11.6 5.5Z" fill="#0F9D58" />
    <path d="M7.9 27H24.1L28.5 19.5H12.3L7.9 27Z" fill="#4285F4" />
    <path d="M24.1 27L28.5 19.5H20.4L24.1 27Z" fill="#EA4335" />
    <path d="M7.9 27L12.3 19.5L3.5 19.5L7.9 27Z" fill="#188038" />
  </svg>
);

export const GoogleCalendarIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <rect x="5" y="5" width="22" height="22" rx="4" fill="#4285F4" />
    <path d="M27 21.5L21.5 27H24C25.7 27 27 25.7 27 24V21.5Z" fill="#EA4335" />
    <rect x="9.5" y="10" width="13" height="12" rx="1.5" fill="#4285F4" />
    <text
      x="16"
      y="20.5"
      textAnchor="middle"
      fill="#FFFFFF"
      fontSize="11.5"
      fontWeight="700"
      fontFamily="Google Sans, sans-serif"
    >
      31
    </text>
  </svg>
);

export const GmailIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path d="M4.5 9.5C4.5 7.8 6.4 6.9 7.7 7.9L16 14.2L24.3 7.9C25.6 6.9 27.5 7.8 27.5 9.5V23.5C27.5 24.6 26.6 25.5 25.5 25.5H22V14.8L16 19.3L10 14.8V25.5H6.5C5.4 25.5 4.5 24.6 4.5 23.5V9.5Z" fill="#EA4335" />
    <path d="M4.5 9.8V23.5C4.5 24.6 5.4 25.5 6.5 25.5H10V14.8L4.5 10.6V9.8Z" fill="#4285F4" />
    <path d="M27.5 9.8V23.5C27.5 24.6 26.6 25.5 25.5 25.5H22V14.8L27.5 10.6V9.8Z" fill="#34A853" />
    <path d="M22 14.8V9.6L24.3 7.9C25.6 6.9 27.5 7.8 27.5 9.5V10.6L22 14.8Z" fill="#FBBC04" />
    <path d="M10 14.8V9.6L7.7 7.9C6.4 6.9 4.5 7.8 4.5 9.5V10.6L10 14.8Z" fill="#C5221F" />
  </svg>
);

/* ============================================================================
 * Build with Google Icons
 * ============================================================================ */

export const GeminiApiIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="geminiStarGrad" x1="4" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#EA4335" />
        <stop offset="35%" stopColor="#FBBC04" />
        <stop offset="68%" stopColor="#34A853" />
        <stop offset="100%" stopColor="#4285F4" />
      </linearGradient>
    </defs>
    <path
      d="M16 3.5C17.4 10.8 21.2 14.6 28.5 16C21.2 17.4 17.4 21.2 16 28.5C14.6 21.2 10.8 17.4 3.5 16C10.8 14.6 14.6 10.8 16 3.5Z"
      fill="url(#geminiStarGrad)"
    />
  </svg>
);

export const ChromeDevToolsIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <circle cx="16" cy="16" r="12" fill="#FFFFFF" />
    <path d="M16 4C20.5 4 24.4 6.5 26.4 10.2H16C12.8 10.2 10.2 12.8 10.2 16C10.2 17 10.5 18 11 18.9L6 10.2C8 6.5 11.7 4 16 4Z" fill="#EA4335" />
    <path d="M6 10.2L11 18.9C12 20.6 13.9 21.8 16 21.8C16.8 21.8 17.6 21.6 18.3 21.3L13.3 27.7C8 26.5 4 21.7 4 16C4 13.9 4.7 11.9 6 10.2Z" fill="#34A853" />
    <path d="M26.4 10.2C27.4 11.9 28 13.9 28 16C28 22.6 22.6 28 16 28C15.1 28 14.2 27.9 13.3 27.7L18.3 21.3C20.4 20.4 21.8 18.4 21.8 16C21.8 13.5 20.2 11.3 18 10.5L16 10.2H26.4Z" fill="#FBBC04" />
    <circle cx="16" cy="16" r="4.5" fill="#4285F4" stroke="#FFFFFF" strokeWidth="1.6" />
  </svg>
);

export const AndroidCliIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path
      d="M4.5 13.5L9.5 17.5L4.5 21.5"
      stroke="#1A73E8"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path d="M9.5 22H13.5" stroke="#1F1F1F" strokeWidth="2.2" strokeLinecap="round" />
    {/* Green Android head */}
    <path
      d="M14.5 21C14.5 16.9 17.4 14 21.2 14C25 14 27.9 16.9 27.9 21H14.5Z"
      fill="#34A853"
    />
    <path
      d="M17.5 14.7L15.8 11.8M24.9 14.7L26.6 11.8"
      stroke="#34A853"
      strokeWidth="1.8"
      strokeLinecap="round"
    />
    <circle cx="18.6" cy="18.2" r="1.05" fill="#FFFFFF" />
    <circle cx="23.8" cy="18.2" r="1.05" fill="#FFFFFF" />
  </svg>
);

export const RoboticsIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path
      d="M12.5 8.5L11 5.5M19.5 8.5L21 5.5"
      stroke="#4285F4"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <rect
      x="6"
      y="9"
      width="20"
      height="15.5"
      rx="6"
      stroke="#4285F4"
      strokeWidth="2.2"
    />
    <circle cx="12.5" cy="16.5" r="1.8" fill="#4285F4" />
    <circle cx="19.5" cy="16.5" r="1.8" fill="#4285F4" />
    <path
      d="M13 20.5C14.5 21.5 17.5 21.5 19 20.5"
      stroke="#4285F4"
      strokeWidth="1.8"
      strokeLinecap="round"
    />
  </svg>
);

export const AntigravitySdkIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <defs>
      <linearGradient id="agyColorArch" x1="5" y1="6" x2="27" y2="26" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#EA4335" />
        <stop offset="35%" stopColor="#FBBC04" />
        <stop offset="68%" stopColor="#34A853" />
        <stop offset="100%" stopColor="#4285F4" />
      </linearGradient>
    </defs>
    <path
      d="M16 5.5C11.8 5.5 9.4 11.4 6.6 19.2C5.3 22.8 3.9 24.8 3 25.6C4.7 25.6 6.7 24.4 8.5 21.8C10.8 18.4 12.8 14.4 16 14.4C19.2 14.4 21.2 18.4 23.5 21.8C25.3 24.4 27.3 25.6 29 25.6C28.1 24.8 26.7 22.8 25.4 19.2C22.6 11.4 20.2 5.5 16 5.5Z"
      fill="url(#agyColorArch)"
    />
  </svg>
);

export const CloudRunIcon: React.FC<IconProps> = ({ className = 'w-8 h-8' }) => (
  <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <path d="M5 9L13 16L5 23L8 16L5 9Z" fill="#669DF6" />
    <path d="M12.5 5.5L26 16L12.5 26.5L16.8 16L12.5 5.5Z" fill="#4285F4" />
    <path d="M12.5 26.5L26 16L16.8 16L12.5 26.5Z" fill="#1967D2" />
  </svg>
);

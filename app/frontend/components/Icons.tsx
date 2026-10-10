// Small hand-tuned line icons (24px grid, 1.6 stroke) shared across pages.

type P = { className?: string };
const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const IconNetwork = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="2.6" />
    <circle cx="5" cy="5.5" r="1.8" />
    <circle cx="19" cy="5.5" r="1.8" />
    <circle cx="5" cy="18.5" r="1.8" />
    <circle cx="19" cy="18.5" r="1.8" />
    <path d="M6.4 6.8l3.6 3.4M17.6 6.8L14 10.2M6.4 17.2l3.6-3.4M17.6 17.2L14 13.8" />
  </svg>
);

export const IconDoc = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <path d="M6 3h8l5 5v12a1 1 0 01-1 1H6a1 1 0 01-1-1V4a1 1 0 011-1z" />
    <path d="M14 3v5h5M8.5 13h7M8.5 16.5h4.5" />
  </svg>
);

export const IconShield = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <path d="M12 3l7 3v5.5c0 4.5-3 8-7 9.5-4-1.5-7-5-7-9.5V6l7-3z" />
    <path d="M9 12l2.2 2.2L15.5 10" />
  </svg>
);

export const IconChart = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <path d="M4 20h16" />
    <path d="M7 16v-5M12 16V6M17 16v-8" />
  </svg>
);

export const IconKey = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <circle cx="8" cy="15" r="4" />
    <path d="M11 12l8-8M16 7l2.5 2.5M14 9l2 2" />
  </svg>
);

export const IconUser = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="8" r="3.6" />
    <path d="M4.5 20c1.2-3.6 4-5.4 7.5-5.4s6.3 1.8 7.5 5.4" />
  </svg>
);

export const IconCompass = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M15.5 8.5l-2 5-5 2 2-5 5-2z" />
  </svg>
);

export const IconSpark = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18" />
  </svg>
);

export const IconCheck = ({ className = "h-4 w-4" }: P) => (
  <svg {...base} strokeWidth={2.2} className={className}>
    <path d="M5 12.5l4.2 4L19 7" />
  </svg>
);

export const IconArrow = ({ className = "h-4 w-4" }: P) => (
  <svg {...base} strokeWidth={1.8} className={className}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);

export const IconUpload = ({ className = "h-6 w-6" }: P) => (
  <svg {...base} className={className}>
    <path d="M12 15V4M7.5 8.5L12 4l4.5 4.5" />
    <path d="M4 15v3.5A1.5 1.5 0 005.5 20h13a1.5 1.5 0 001.5-1.5V15" />
  </svg>
);

export const IconTrash = ({ className = "h-4 w-4" }: P) => (
  <svg {...base} className={className}>
    <path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l.8 12.5h9.4L17.5 7" />
  </svg>
);

export const IconPlus = ({ className = "h-4 w-4" }: P) => (
  <svg {...base} strokeWidth={1.9} className={className}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

export const IconEye = ({ className = "h-4 w-4", off = false }: P & { off?: boolean }) => (
  <svg {...base} className={className}>
    <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
    <circle cx="12" cy="12" r="2.8" />
    {off && <path d="M4 4l16 16" />}
  </svg>
);

export const IconBook = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <path d="M4 5.5A1.5 1.5 0 015.5 4H11v15H5.5A1.5 1.5 0 004 20.5v-15zM20 5.5A1.5 1.5 0 0018.5 4H13v15h5.5a1.5 1.5 0 011.5 1.5v-15z" />
  </svg>
);

export const IconFlask = ({ className = "h-5 w-5" }: P) => (
  <svg {...base} className={className}>
    <path d="M9.5 3h5M10 3v6L4.8 18.2A1.8 1.8 0 006.4 21h11.2a1.8 1.8 0 001.6-2.8L14 9V3" />
    <path d="M7.5 15h9" />
  </svg>
);

export const IconHeart = ({ className = "h-4 w-4" }: P) => (
  <svg {...base} className={className}>
    <path d="M12 20s-7.5-4.4-7.5-10A4.3 4.3 0 0112 7.3 4.3 4.3 0 0119.5 10c0 5.6-7.5 10-7.5 10z" />
  </svg>
);

// خمسة أنماط بصرية. كل نمط: خلفية، لوح المحتوى، الحبر، اللون المميز، لون ثانوي، ألوان الصح/الخطأ.
export const THEMES = {
  classroom: {
    bg: 'linear-gradient(160deg, #FFF7E8 0%, #FFE9C4 100%)', panel: '#FFFFFF', panelBorder: '#F2D7A6',
    ink: '#1F2937', soft: '#6B7280', accent: '#F97316', second: '#2563EB', right: '#16A34A', wrong: '#DC2626',
    chip: '#FFF1DC', shadow: '0 18px 50px rgba(146, 84, 0, .16)', deco: ['#FDBA74', '#93C5FD', '#FDE68A', '#A7F3D0'],
  },
  chalkboard: {
    bg: 'radial-gradient(circle at 30% 20%, #2F5D4E 0%, #1E3D33 70%)', panel: 'rgba(255,255,255,.06)', panelBorder: 'rgba(255,255,255,.18)',
    ink: '#F8FAFC', soft: '#CBD5E1', accent: '#FDE047', second: '#7DD3FC', right: '#86EFAC', wrong: '#FCA5A5',
    chip: 'rgba(255,255,255,.10)', shadow: 'none', deco: ['rgba(255,255,255,.10)', 'rgba(253,224,71,.18)'],
  },
  paper: {
    bg: 'repeating-linear-gradient(0deg, #F7EEDF 0px, #F7EEDF 46px, #EADBC4 47px, #F7EEDF 48px)', panel: '#FFFDF7', panelBorder: '#E3D2B5',
    ink: '#3B2F2F', soft: '#7C6A58', accent: '#D9480F', second: '#2F9E44', right: '#2F9E44', wrong: '#C92A2A',
    chip: '#FBF1E1', shadow: '6px 8px 0 rgba(59,47,47,.12)', deco: ['#FFD8A8', '#B2F2BB', '#A5D8FF', '#FCC2D7'],
  },
  minimal: {
    bg: '#FFFFFF', panel: '#F8FAFC', panelBorder: '#E2E8F0',
    ink: '#0F172A', soft: '#64748B', accent: '#2563EB', second: '#0EA5E9', right: '#16A34A', wrong: '#DC2626',
    chip: '#EFF6FF', shadow: '0 10px 30px rgba(15,23,42,.08)', deco: ['#DBEAFE', '#E0F2FE'],
  },
  night: {
    bg: 'linear-gradient(170deg, #0F172A 0%, #1E293B 100%)', panel: 'rgba(30,41,59,.85)', panelBorder: 'rgba(148,163,184,.25)',
    ink: '#F1F5F9', soft: '#94A3B8', accent: '#38BDF8', second: '#F472B6', right: '#4ADE80', wrong: '#F87171',
    chip: 'rgba(56,189,248,.12)', shadow: '0 20px 60px rgba(0,0,0,.35)', deco: ['rgba(56,189,248,.25)', 'rgba(244,114,182,.22)', 'rgba(250,204,21,.25)'],
  },
};

export const getTheme = (name, accent) => {
  const t = THEMES[name] || THEMES.classroom;
  return accent ? {...t, accent} : t;
};

export const FONT = "'AES Arabic', 'Noto Sans Arabic', sans-serif";

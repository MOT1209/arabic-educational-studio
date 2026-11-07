import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import data from './data/glyphs.json';

// «الحرف شخصية»: جسم الشخصية هو الحرف نفسه من الخط الحقيقي، والوجه يوضع في أسمك نقطة داخل الحرف (محسوبة مسبقاً).
// الفم: من غلاف الصوت المسجَّل إن وُجد (mouth[frame] بين 0 و1)، وإلا حركة منتظمة أثناء نوافذ الكلام.
export const LetterBuddy = ({letter, theme, L, speaking, mouth, mood = 'normal'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const g = data.glyphs[letter] || data.glyphs['ض'];
  const [x0, y0, x1, y1] = g.bounds;
  const pad = 140;
  const w = x1 - x0 + 2 * pad, h = y1 - y0 + 2 * pad;
  const size = L.avatar.size * L.s;
  const scale = Math.min(size / w, size / h);
  const f = g.face;
  const e = Math.max(88, f.r * 0.95);                       // نصف قطر العين
  const blink = (frame % (fps * 3.4)) < 4 ? 0.12 : 1;      // رمشة كل 3.4 ث
  let open;
  if (mouth !== null && mouth !== undefined) open = Math.min(1, mouth * 1.6);
  else open = speaking ? 0.25 + 0.75 * Math.abs(Math.sin(frame * 0.9)) * (0.6 + 0.4 * Math.abs(Math.sin(frame * 0.37))) : 0;
  const bob = Math.sin(frame / 14) * 10 + (speaking ? Math.sin(frame / 3) * 3 : 0);
  const look = mood === 'think' ? {dx: e * 0.25, dy: e * 0.3} : {dx: Math.sin(frame / 40) * e * 0.15, dy: 0};
  const outline = theme.ink === '#F8FAFC' || theme.ink === '#F1F5F9' ? '#0B1220' : theme.ink;
  return (
    <div style={{position: 'absolute', left: L.avatar.left, bottom: L.avatar.bottom, width: w * scale, height: h * scale,
      transform: `translateY(${bob}px)`}}>
      <svg width={w * scale} height={h * scale} viewBox={`${x0 - pad} ${-(y1 + pad)} ${w} ${h}`} style={{overflow: 'visible'}}>
        <ellipse cx={(x0 + x1) / 2} cy={-(y0 - pad * 0.55)} rx={(x1 - x0) * 0.42} ry={34} fill="rgba(0,0,0,.14)" />
        <g transform="scale(1,-1)">
          <path d={g.d} fill={theme.accent} stroke={outline} strokeWidth={26} strokeLinejoin="round" />
          {/* الوجه */}
          <g transform={`translate(${f.x} ${f.y + e * 0.2})`}>
            {[-1, 1].map((s) => (
              <g key={s} transform={`translate(${s * e * 1.15} ${e * 0.55})`}>
                <ellipse rx={e} ry={e * 1.1 * blink} fill="#fff" stroke={outline} strokeWidth={14} />
                {blink > 0.5 && <circle cx={look.dx} cy={look.dy - e * 0.05} r={e * 0.48} fill={outline} />}
                {blink > 0.5 && <circle cx={look.dx + e * 0.18} cy={look.dy + e * 0.2} r={e * 0.16} fill="#fff" />}
              </g>
            ))}
            <circle cx={-e * 2.05} cy={-e * 0.55} r={e * 0.36} fill="#FB7185" opacity={0.45} />
            <circle cx={e * 2.05} cy={-e * 0.55} r={e * 0.36} fill="#FB7185" opacity={0.45} />
            {mood === 'happy' && open < 0.1
              ? <path d={`M ${-e * 0.8} ${-e * 0.55} Q 0 ${-e * 1.5} ${e * 0.8} ${-e * 0.55}`} fill="none" stroke={outline} strokeWidth={16} strokeLinecap="round" />
              : <ellipse cx={0} cy={-e * 0.85} rx={e * (0.55 + 0.1 * open)} ry={Math.max(e * 0.1, e * 0.62 * open)} fill="#7F1D1D"
                  stroke={outline} strokeWidth={12} />}
          </g>
        </g>
      </svg>
    </div>
  );
};

import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import data from './data/glyphs.json';

// تتبّع محيط الحرف ثم تعبئته. هذا «رسم الشكل» لا «ترتيب الكتابة» الحقيقي: ترتيب الضربات يحتاج بيانات يدوية لكل حرف.
export const glyphBox = (letter) => {
  const g = data.glyphs[letter];
  if (!g) return null;
  const [x0, y0, x1, y1] = g.bounds;
  const pad = 60;
  return {g, vb: `${x0 - pad} ${-(y1 + pad)} ${x1 - x0 + 2 * pad} ${y1 - y0 + 2 * pad}`, w: x1 - x0 + 2 * pad, h: y1 - y0 + 2 * pad};
};

export const LetterTrace = ({letter, theme, size, frames = 80}) => {
  const frame = useCurrentFrame();
  const b = glyphBox(letter);
  if (!b) return <div style={{fontSize: size, color: theme.accent}}>{letter}</div>;
  const draw = interpolate(frame, [4, frames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fill = interpolate(frame, [frames - 8, frames + 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const ratio = b.w / b.h;
  const w = ratio >= 1 ? size : size * ratio, h = ratio >= 1 ? size / ratio : size;
  return (
    <svg width={w} height={h} viewBox={b.vb} style={{overflow: 'visible'}}>
      <g transform="scale(1,-1)">
        <path d={b.g.d} fill={theme.accent} fillOpacity={fill} stroke={theme.accent} strokeWidth={18} strokeLinejoin="round"
          strokeLinecap="round" pathLength={1} strokeDasharray="1" strokeDashoffset={draw} />
      </g>
    </svg>
  );
};

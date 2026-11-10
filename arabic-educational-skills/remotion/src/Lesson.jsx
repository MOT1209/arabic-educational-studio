import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Audio, Sequence, continueRender, delayRender, interpolate, staticFile, useCurrentFrame,
  useVideoConfig} from 'remotion';
import {FONT, getTheme} from './theme.js';
import {Block} from './blocks.jsx';
import {LetterBuddy} from './LetterBuddy.jsx';

// تحميل الخط المضمَّن قبل أول إطار (وإلا يتبدل الخط أثناء التصيير)
export const FONT_FILES = {noto_sans: 'noto-sans-arabic', playpen: 'playpen-sans-arabic', scheherazade: 'scheherazade-new', amiri: 'amiri', naskh: 'noto-naskh-arabic', lemonada: 'lemonada'};
const useFonts = (fontId) => {
  const base = FONT_FILES[fontId] || FONT_FILES.noto_sans;
  const [handle] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const faces = [
      new FontFace('AES Arabic', `url(${staticFile('fonts/' + base + '-arabic-400-normal.woff2')})`, {weight: '400'}),
      new FontFace('AES Arabic', `url(${staticFile('fonts/' + base + '-arabic-700-normal.woff2')})`, {weight: '700'}),
    ];
    Promise.all(faces.map((f) => f.load().then((ff) => document.fonts.add(ff))))
      .then(() => continueRender(handle))
      .catch((e) => { console.error(e); continueRender(handle); });
  }, [handle, base]);
};

export const layoutFor = (width, height, hasAvatar) => {
  const vertical = height > width * 1.1;
  const square = !vertical && height > width * 0.9;
  const base = Math.min(width, height) / 1080;
  const s = base * (vertical ? 1.28 : square ? 1.15 : 1.2);   // مقياس النص والعناصر
  if (vertical) {
    return {vertical, square, s, panel: {left: 56, right: 56, top: 140, height: height * 0.52},
      avatar: {left: 40, bottom: 250, size: 360}, captions: {bottom: 70, width: width - 100}};
  }
  if (square) {
    return {vertical, square, s, panel: {left: 50, right: 50, top: 90, height: height * 0.6},
      avatar: {left: 24, bottom: 170, size: 220}, captions: {bottom: 40, width: width - 80}};
  }
  return {vertical, square, s,
    panel: {left: hasAvatar ? width * 0.26 : 120, right: 90, top: 90, height: height - 330},
    avatar: {left: 30, bottom: 180, size: 340}, captions: {bottom: 44, width: width * 0.8}};
};

const Decor = ({theme, width, height}) => {
  const frame = useCurrentFrame();
  const dots = [[0.08, 0.15, 90], [0.92, 0.1, 60], [0.85, 0.88, 120], [0.05, 0.8, 70], [0.5, 0.04, 40]];
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {dots.map(([x, y, r], i) => (
        <div key={i} style={{position: 'absolute', left: x * width - r / 2, top: y * height - r / 2 + Math.sin((frame + i * 40) / 45) * 8,
          width: r, height: r, borderRadius: r, background: theme.deco[i % theme.deco.length], opacity: 0.7}} />
      ))}
    </AbsoluteFill>
  );
};

const Captions = ({captions, theme, L}) => {
  const frame = useCurrentFrame();
  const c = captions.find((x) => frame >= x.from && frame < x.to);
  if (!c) return null;
  const k = interpolate(frame - c.from, [0, 5], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', bottom: L.captions.bottom, left: '50%', transform: `translateX(-50%) translateY(${(1 - k) * 10}px)`,
      opacity: k, width: L.captions.width, display: 'flex', justifyContent: 'center'}}>
      <div style={{background: 'rgba(17,24,39,.82)', color: '#fff', borderRadius: 26 * L.s, padding: `${14 * L.s}px ${34 * L.s}px`,
        fontSize: (L.vertical ? 50 : 46) * L.s, lineHeight: 1.6, direction: 'rtl', textAlign: 'center', fontFamily: FONT, maxWidth: '100%'}}>
        {c.text}
      </div>
    </div>
  );
};

const Progress = ({blocks, theme, width}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return (
    <div style={{position: 'absolute', top: 0, left: 0, width, height: 10, background: 'rgba(0,0,0,.06)'}}>
      <div style={{width: `${(frame / durationInFrames) * 100}%`, height: '100%', background: theme.accent, borderRadius: 10}} />
    </div>
  );
};

export const Lesson = (props) => {
  useFonts(props.font);
  const {width, height} = useVideoConfig();
  const frame = useCurrentFrame();
  const theme = getTheme(props.theme, props.accent);
  const hasAvatar = props.narrator?.avatar === 'letter_buddy';
  const L = layoutFor(width, height, hasAvatar);
  const speakingNow = (props.speaking || []).some(([a, b]) => frame >= a && frame < b);
  const mouth = props.mouth ? (props.mouth[frame] || 0) : null;
  const current = (props.blocks || []).find((b) => frame >= b.from && frame < b.from + b.frames);
  const mood = current?.type === 'quiz' ? 'think' : current?.type === 'outro' ? 'happy' : 'normal';
  return (
    <AbsoluteFill style={{background: theme.bg, fontFamily: FONT, color: theme.ink, direction: 'rtl', overflow: 'hidden'}}>
      <Decor theme={theme} width={width} height={height} />
      {(props.blocks || []).map((b) => (
        <Sequence key={b.id} from={b.from} durationInFrames={b.frames} layout="none">
          <Block block={b} theme={theme} L={L} width={width} height={height} />
        </Sequence>
      ))}
      {hasAvatar && (
        <LetterBuddy letter={props.narrator.letter} theme={theme} L={L} speaking={speakingNow} mouth={mouth} mood={mood} />
      )}
      {(props.audio || []).map((a, i) => (
        <Sequence key={i} from={a.from} durationInFrames={a.frames} layout="none">
          <Audio src={staticFile(a.src)} />
        </Sequence>
      ))}
      <Captions captions={props.captions || []} theme={theme} L={L} />
      <Progress blocks={props.blocks} theme={theme} width={width} />
    </AbsoluteFill>
  );
};


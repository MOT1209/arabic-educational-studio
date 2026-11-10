import React, {useLayoutEffect, useRef, useState} from 'react';
import {AbsoluteFill, Img, continueRender, delayRender, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {pop, fadeIn, seg} from './anim.js';
import {FONT} from './theme.js';
import EMOJI from './emojiMap.json';
import {LetterTrace} from './Trace.jsx';

const DIGITS = ['١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];

// لوح المحتوى: كل كتلة تُرسم داخله
const Panel = ({theme, L, children, style}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const k = pop(frame, fps);
  // ملاءمة تلقائية: إن زاد المحتوى عن ارتفاع اللوح يُصغَّر كله بدل أن يفيض.
  // الأبعاد تُحسب من التخطيط لا من DOM (حاوية Remotion قد لا تكون قد أخذت حجمها عند القياس).
  const padX = 56 * L.s, padY = 40 * L.s, bw = 3 * L.s;
  const innerW = width - L.panel.left - L.panel.right - 2 * padX - 2 * bw;
  const availH = L.panel.height - 2 * padY - 2 * bw;
  const inner = useRef(null);
  const [fit, setFit] = useState(1);
  const [handle] = useState(() => delayRender('fit'));
  useLayoutEffect(() => {
    if (inner.current) {
      const f = Math.min(1, availH / Math.max(1, inner.current.offsetHeight));
      setFit(Number.isFinite(f) && f > 0.2 ? f : 1);
    }
    continueRender(handle);
  }, [handle, availH]);
  return (
    <div style={{position: 'absolute', left: L.panel.left, right: L.panel.right, top: L.panel.top, height: L.panel.height,
      background: theme.panel, border: `${bw}px solid ${theme.panelBorder}`, borderRadius: 44 * L.s, boxShadow: theme.shadow,
      transform: `scale(${0.94 + 0.06 * k})`, opacity: Math.min(1, k * 1.4), display: 'flex', alignItems: 'center',
      justifyContent: 'center', boxSizing: 'border-box', overflow: 'hidden', direction: 'rtl', ...style}}>
      <div ref={inner} style={{display: 'flex', flexDirection: 'column', alignItems: style?.alignItems || 'center', justifyContent: 'center',
        gap: 26 * L.s, width: innerW, flex: 'none', transform: `scale(${fit})`, transformOrigin: 'center center'}}>
        {children}
      </div>
    </div>
  );
};

const H = ({children, theme, L, size = 72, color, style}) => (
  <div style={{fontSize: size * L.s, fontWeight: 700, lineHeight: 1.55, color: color || theme.ink, textAlign: 'center', ...style}}>{children}</div>
);

// تلوين مقاطع داخل نص مشكول دون كسر الاتصال: نقسم النص إلى أجزاء ونلوّن الجزء المطابق حرفياً
const Highlighted = ({text, parts = [], color}) => {
  if (!parts.length) return <>{text}</>;
  const out = [];
  let rest = text, key = 0;
  while (rest.length) {
    let best = null;
    for (const p of parts) {
      const i = rest.indexOf(p);
      if (i >= 0 && (best === null || i < best.i)) best = {i, p};
    }
    if (!best) { out.push(<span key={key++}>{rest}</span>); break; }
    if (best.i) out.push(<span key={key++}>{rest.slice(0, best.i)}</span>);
    out.push(<span key={key++} style={{color}}>{best.p}</span>);
    rest = rest.slice(best.i + best.p.length);
  }
  return <>{out}</>;
};

// تلوين حرف داخل كلمة (بالفهرس بين الحروف، مع إبقاء الحركات مع حرفها)
const WordLetters = ({word, idx = [], color}) => {
  const set = new Set(idx);
  const parts = word.match(/\p{L}\p{M}*|[^\p{L}\p{M}]+/gu) || [];
  let li = 0;
  return <>{parts.map((pt, i) => {
    const isL = /^\p{L}/u.test(pt);
    const hl = isL && set.has(li);
    if (isL) li++;
    return <span key={i} style={hl ? {color} : undefined}>{pt}</span>;
  })}</>;
};

const StatusBadge = ({status, theme, L}) => {
  if (!status || status === 'neutral') return null;
  const ok = status === 'right';
  return (
    <div style={{width: 92 * L.s, height: 92 * L.s, borderRadius: 92, background: ok ? theme.right : theme.wrong, color: '#fff',
      fontSize: 58 * L.s, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontFamily: 'sans-serif'}}>
      {ok ? '✓' : '✗'}
    </div>
  );
};

const Placeholder = ({concept, theme, L, size = 300}) => (
  <div style={{width: size * L.s, height: size * L.s, borderRadius: 36 * L.s, border: `${5 * L.s}px dashed ${theme.soft}`,
    display: 'flex', alignItems: 'center', justifyContent: 'center', color: theme.soft, fontSize: 30 * L.s, textAlign: 'center',
    direction: 'ltr', padding: 12, boxSizing: 'border-box', fontFamily: 'sans-serif', background: theme.chip}}>
    [ {concept} ]
  </div>
);

const Picture = ({block, theme, L, size = 300}) => block.asset_src
  ? <Img src={staticFile(block.asset_src)} style={{width: size * L.s, height: size * L.s, objectFit: 'contain', borderRadius: 30 * L.s}} />
  : (block.concept && EMOJI[block.concept] ? <Img src={staticFile(`emoji/${EMOJI[block.concept]}.svg`)} style={{width: size * L.s, height: size * L.s, objectFit: 'contain'}} />
  : block.concept ? <Placeholder concept={block.concept} theme={theme} L={L} size={size} /> : null);

// ---------------------------------------------------------------- الكتل
const Title = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const k = pop(frame, fps, 4);
  return (
    <Panel theme={theme} L={L} style={{background: 'transparent', border: 'none', boxShadow: 'none'}}>
      <div style={{transform: `scale(${0.6 + 0.4 * k})`, opacity: k, background: theme.accent, color: '#fff', borderRadius: 40 * L.s,
        padding: `${24 * L.s}px ${64 * L.s}px`, boxShadow: theme.shadow}}>
        <H theme={theme} L={L} size={L.vertical ? 92 : 104} color="#fff">{block.heading}</H>
      </div>
      {block.subheading && <H theme={theme} L={L} size={52} color={theme.soft} style={{opacity: fadeIn(frame, 14), fontWeight: 400}}>{block.subheading}</H>}
    </Panel>
  );
};

const Explain = ({block, theme, L}) => {
  const frame = useCurrentFrame();
  const sp = seg(block, (s) => s.kind === 'speech') || {from: 0, to: block.frames};
  const items = block.bullets || [];
  const span = Math.max(1, sp.to - sp.from);
  return (
    <Panel theme={theme} L={L} style={{alignItems: 'stretch'}}>
      {block.heading && <H theme={theme} L={L} size={!block.text && !items.length ? 104 : 66} color={theme.accent}
        style={!block.text && !items.length ? {transform: `scale(${0.85 + 0.15 * fadeIn(frame, 0, 12)})`} : undefined}>{block.heading}</H>}
      {block.text && <div style={{fontSize: (L.vertical ? 54 : 56) * L.s, lineHeight: 1.75, textAlign: 'center', opacity: fadeIn(frame, 6)}}>
        <Highlighted text={block.text} parts={block.highlight || []} color={theme.accent} /></div>}
      {items.map((b, i) => {
        const at = sp.from + (span * (i + 0.3)) / (items.length + 0.3);
        const k = fadeIn(frame, at, 8);
        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 22 * L.s, opacity: k, transform: `translateX(${(1 - k) * -30}px)`,
            fontSize: 50 * L.s, lineHeight: 1.6}}>
            <div style={{flex: 'none', width: 26 * L.s, height: 26 * L.s, borderRadius: 30, background: theme.second}} />
            <div><Highlighted text={b} parts={block.highlight || []} color={theme.accent} /></div>
          </div>
        );
      })}
    </Panel>
  );
};

const Term = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const k = pop(frame, fps, 3);
  return (
    <Panel theme={theme} L={L}>
      <div style={{transform: `scale(${k})`, background: theme.chip, border: `${4 * L.s}px solid ${theme.accent}`, borderRadius: 34 * L.s,
        padding: `${12 * L.s}px ${48 * L.s}px`}}>
        <H theme={theme} L={L} size={96} color={theme.accent}>{block.term}</H>
      </div>
      <div style={{fontSize: 54 * L.s, lineHeight: 1.75, textAlign: 'center', opacity: fadeIn(frame, 16)}}>{block.definition}</div>
    </Panel>
  );
};

const Example = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const k = pop(frame, fps, 3);
  const col = block.status === 'wrong' ? theme.wrong : block.status === 'right' ? theme.right : theme.ink;
  return (
    <Panel theme={theme} L={L}>
      {block.label && <div style={{fontSize: 40 * L.s, color: theme.soft}}>{block.label}</div>}
      <div style={{display: 'flex', alignItems: 'center', gap: 30 * L.s, transform: `scale(${0.85 + 0.15 * k})`, opacity: k}}>
        <div style={{fontSize: (block.size === 'xl' ? 150 : L.vertical ? 84 : 96) * L.s, fontWeight: 700, lineHeight: 1.6, color: col,
          textDecoration: block.status === 'wrong' ? `line-through ${6 * L.s}px ${theme.wrong}` : 'none', textAlign: 'center',
          direction: block.dir || 'rtl'}}>
          <Highlighted text={block.text} parts={block.highlight || []} color={theme.accent} />
        </div>
        <StatusBadge status={block.status} theme={theme} L={L} />
      </div>
      {block.caption && <div style={{fontSize: 46 * L.s, color: theme.soft, opacity: fadeIn(frame, 18), textAlign: 'center'}}>{block.caption}</div>}
    </Panel>
  );
};

const Card = ({side, theme, L, delay}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const k = pop(frame, fps, delay);
  const c = side.status === 'wrong' ? theme.wrong : side.status === 'right' ? theme.right : theme.second;
  return (
    <div style={{flex: 1, minWidth: 0, background: theme.chip, borderRadius: 34 * L.s, border: `${5 * L.s}px solid ${c}`,
      padding: `${26 * L.s}px ${30 * L.s}px`, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 * L.s,
      transform: `translateY(${(1 - k) * 40}px)`, opacity: k}}>
      {side.label && <div style={{fontSize: 40 * L.s, color: c, fontWeight: 700}}>{side.label}</div>}
      <div style={{fontSize: (L.vertical ? 62 : 66) * L.s, fontWeight: 700, lineHeight: 1.6, textAlign: 'center', direction: side.dir || 'rtl'}}>
        <Highlighted text={side.text} parts={side.highlight || []} color={theme.accent} />
      </div>
      <StatusBadge status={side.status} theme={theme} L={L} />
    </div>
  );
};

const Compare = ({block, theme, L}) => (
  <Panel theme={theme} L={L}>
    {block.heading && <H theme={theme} L={L} size={58} color={theme.accent}>{block.heading}</H>}
    <div style={{display: 'flex', flexDirection: L.vertical ? 'column' : 'row', gap: 34 * L.s, width: '100%'}}>
      <Card side={block.right} theme={theme} L={L} delay={3} />
      <Card side={block.left} theme={theme} L={L} delay={14} />
    </div>
  </Panel>
);

const Steps = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const sp = seg(block, (s) => s.kind === 'speech') || {from: 0, to: block.frames};
  const n = block.items.length;
  const span = Math.max(1, sp.to - sp.from);
  return (
    <Panel theme={theme} L={L} style={{alignItems: 'stretch'}}>
      {block.heading && <H theme={theme} L={L} size={60} color={theme.accent}>{block.heading}</H>}
      {block.items.map((it, i) => {
        const at = sp.from + (span * i) / n;
        const k = pop(frame, fps, at);
        const active = frame >= at && (i === n - 1 || frame < sp.from + (span * (i + 1)) / n);
        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 24 * L.s, opacity: Math.min(1, k * 1.5),
            transform: `scale(${0.9 + 0.1 * k})`, background: active ? theme.chip : 'transparent', borderRadius: 24 * L.s,
            padding: `${8 * L.s}px ${16 * L.s}px`}}>
            <div style={{flex: 'none', width: 70 * L.s, height: 70 * L.s, borderRadius: 70, background: theme.accent, color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 40 * L.s, fontWeight: 700}}>{DIGITS[i] || i + 1}</div>
            <div style={{fontSize: 48 * L.s, lineHeight: 1.6, direction: block.dir || 'rtl'}}>{it}</div>
          </div>
        );
      })}
    </Panel>
  );
};

const ImageBlock = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const k = pop(frame, fps, 2);
  return (
    <Panel theme={theme} L={L}>
      <div style={{transform: `scale(${0.8 + 0.2 * k})`, opacity: k}}><Picture block={block} theme={theme} L={L} size={L.vertical ? 520 : 470} /></div>
      {block.caption && <H theme={theme} L={L} size={56}>{block.caption}</H>}
    </Panel>
  );
};

const FORM_LABEL = {isolated: 'مُنْفَصِل', initial: 'أَوَّل', medial: 'وَسَط', final: 'آخِر'};
const ZWJ = '‍';
const formText = (l, f) => (f === 'initial' ? l + ZWJ : f === 'medial' ? ZWJ + l + ZWJ : f === 'final' ? ZWJ + l : l);
const NON_JOIN = new Set('ادذرزو');

const LetterBlock = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const traceLen = Math.round(fps * (block.trace_seconds || 2.6));
  const forms = block.show_forms ? (NON_JOIN.has(block.letter) ? ['isolated', 'final'] : ['isolated', 'initial', 'medial', 'final']) : [];
  const formsAt = block.trace === false ? 6 : traceLen + 10;
  return (
    <Panel theme={theme} L={L}>
      {block.name && !forms.length && <H theme={theme} L={L} size={56} color={theme.soft}>{block.name}</H>}
      {block.trace === false
        ? <div style={{fontSize: (forms.length ? 170 : 300) * L.s, fontWeight: 700, color: theme.accent, lineHeight: 1.3, transform: `scale(${pop(frame, fps)})`}}>{block.letter}</div>
        : <LetterTrace letter={block.letter} theme={theme} size={(L.vertical ? 420 : 380) * L.s} frames={traceLen} />}
      {forms.length > 0 && (
        <div style={{display: 'flex', gap: 16 * L.s, flexWrap: 'nowrap', justifyContent: 'center'}}>
          {forms.map((f, i) => {
            const k = pop(frame, fps, formsAt + i * 6);
            return (
              <div key={f} style={{background: theme.chip, borderRadius: 26 * L.s, padding: `${6 * L.s}px ${26 * L.s}px`, textAlign: 'center',
                transform: `scale(${k})`, minWidth: 118 * L.s}}>
                <div style={{fontSize: 90 * L.s, fontWeight: 700, color: theme.ink, lineHeight: 1.4}}>{formText(block.letter, f)}</div>
                <div style={{fontSize: 32 * L.s, color: theme.soft}}>{FORM_LABEL[f]}</div>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
};

const WordBlock = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const k = pop(frame, fps, 3);
  const sy = block.syllables || [];
  return (
    <Panel theme={theme} L={L}>
      <div style={{display: 'flex', flexDirection: L.vertical ? 'column' : 'row', alignItems: 'center', gap: 50 * L.s}}>
        <div style={{fontSize: (L.vertical ? 180 : 200) * L.s, fontWeight: 700, lineHeight: 1.45, transform: `scale(${0.8 + 0.2 * k})`, opacity: k}}>
          <WordLetters word={block.word} idx={block.highlight_letters || []} color={theme.accent} />
        </div>
        {(block.asset_src || block.concept) && <div style={{opacity: fadeIn(frame, 8)}}><Picture block={block} theme={theme} L={L} size={300} /></div>}
      </div>
      {sy.length > 1 && (
        <div style={{display: 'flex', gap: 18 * L.s, direction: 'rtl'}}>
          {sy.map((x, i) => {
            const kk = pop(frame, fps, 18 + i * 10);
            return <div key={i} style={{fontSize: 72 * L.s, fontWeight: 700, background: theme.chip, borderRadius: 22 * L.s,
              padding: `${2 * L.s}px ${26 * L.s}px`, transform: `scale(${kk})`, color: theme.second}}>{x}</div>;
          })}
        </div>
      )}
      {block.caption && <div style={{fontSize: 44 * L.s, color: theme.soft, opacity: fadeIn(frame, 14)}}>{block.caption}</div>}
      <CuePill block={block} theme={theme} L={L} />
    </Panel>
  );
};

// بطاقة «قولوا معي» أثناء وقفة hold في أي كتلة تحمل cue
const CuePill = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const hold = (block.segments || []).find((s) => s.kind === 'pause' && s.label === 'hold' && frame >= s.from && frame < s.to);
  if (!block.cue || !hold) return null;
  return <div style={{background: theme.accent, color: '#fff', borderRadius: 60, padding: `${6 * L.s}px ${36 * L.s}px`, fontSize: 46 * L.s,
    fontWeight: 700, transform: `scale(${pop(frame, fps, hold.from)})`}}>{block.cue} 🗣️</div>;
};

const SayWithMe = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const pause = (block.segments || []).find((s) => s.kind === 'pause' && s.label === 'repeat' && frame >= s.from && frame < s.to);
  const model = (block.segments || []).find((s) => s.kind === 'speech' && s.label === 'model' && frame >= s.from && frame < s.to);
  const pk = pause ? interpolate(frame, [pause.from, pause.to], [0, 1]) : 0;
  return (
    <Panel theme={theme} L={L}>
      <div style={{fontSize: Math.min(L.vertical ? 120 : 140, 1150 / Math.max(4, [...block.text.replace(/[\u064B-\u0652\u0670]/g, '')].length)) * L.s,
        fontWeight: 700, lineHeight: 1.5, textAlign: 'center',
        color: model ? theme.accent : theme.ink, transform: `scale(${model ? 1.04 : 1})`}}>{block.text}</div>
      <div style={{height: 120 * L.s, display: 'flex', alignItems: 'center'}}>
        {pause && (
          <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 * L.s, transform: `scale(${pop(frame, fps, pause.from)})`}}>
            <div style={{background: theme.accent, color: '#fff', borderRadius: 60, padding: `${8 * L.s}px ${40 * L.s}px`, fontSize: 52 * L.s,
              fontWeight: 700}}>{block.cue || 'قُولُوا مَعِي'} 🗣️</div>
            <div style={{width: 380 * L.s, height: 14 * L.s, borderRadius: 10, background: theme.chip, overflow: 'hidden'}}>
              <div style={{width: `${pk * 100}%`, height: '100%', background: theme.second}} />
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
};

const Quiz = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const think = seg(block, (s) => s.kind === 'pause' && s.label === 'think');
  const reveal = seg(block, (s) => s.label === 'reveal');
  const revealed = reveal && frame >= reveal.from;
  const n = block.options.length;
  const letterish = block.options.every((o) => [...o.replace(/[ً-ْٰ]/g, '')].length <= 3);
  const longest = Math.max(...block.options.map((o) => o.replace(/[\u064B-\u0652\u0670]/g, '').length));
  const cols = letterish ? Math.min(n, L.vertical ? 3 : 4) : longest <= 12 ? (L.vertical ? 1 : n) : (!L.vertical && n === 4 && longest <= 22 ? 2 : 1);
  return (
    <Panel theme={theme} L={L}>
      <H theme={theme} L={L} size={L.vertical ? 56 : 60}>{block.question}</H>
      <div style={{display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 24 * L.s, width: '100%'}}>
        {block.options.map((o, i) => {
          const k = pop(frame, fps, 6 + i * 5);
          const ok = i === block.answer_index;
          const bc = revealed ? (ok ? theme.right : theme.panelBorder) : theme.panelBorder;
          return (
            <div key={i} style={{position: 'relative', background: revealed && ok ? 'rgba(22,163,74,.12)' : theme.chip,
              border: `${6 * L.s}px solid ${bc}`, borderRadius: 30 * L.s, padding: `${(letterish ? 26 : 14) * L.s}px ${(letterish ? 18 : 78) * L.s}px`, display: 'flex',
              alignItems: 'center', justifyContent: 'center', gap: 20 * L.s, minHeight: (letterish ? 170 : 110) * L.s,
              transform: `scale(${(0.85 + 0.15 * k) * (revealed && ok ? 1.05 : 1)})`, opacity: revealed && !ok ? 0.35 : k}}>
              <div style={{position: 'absolute', top: 10 * L.s, right: 14 * L.s, width: 52 * L.s, height: 52 * L.s, borderRadius: 52,
                background: theme.second, color: '#fff', fontSize: 34 * L.s, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700}}>{DIGITS[i]}</div>
              <div style={{fontSize: (letterish ? 110 : L.vertical ? 50 : 54) * L.s, fontWeight: 700, lineHeight: 1.5, textAlign: 'center',
                direction: block.dir || 'rtl'}}>{o}</div>
              {revealed && ok && <div style={{position: 'absolute', top: 10 * L.s, left: 14 * L.s, width: 58 * L.s, height: 58 * L.s,
                borderRadius: 58, background: theme.right, color: '#fff', fontSize: 40 * L.s, display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontFamily: 'sans-serif'}}>✓</div>}
            </div>
          );
        })}
      </div>
      <div style={{height: 110 * L.s}}>
        {think && frame >= think.from && frame < think.to && (() => {
          const left = Math.ceil((think.to - frame) / fps);
          const p = (frame - think.from) / (think.to - think.from);
          return (
            <svg width={110 * L.s} height={110 * L.s} viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="44" fill={theme.chip} stroke={theme.panelBorder} strokeWidth="8" />
              <circle cx="50" cy="50" r="44" fill="none" stroke={theme.accent} strokeWidth="8" strokeDasharray={`${276 * (1 - p)} 276`}
                transform="rotate(-90 50 50)" strokeLinecap="round" />
              <text x="50" y="66" textAnchor="middle" fontSize="44" fontWeight="700" fill={theme.ink} fontFamily={FONT}>{DIGITS[left - 1] || left}</text>
            </svg>
          );
        })()}
      </div>
    </Panel>
  );
};

const Recap = ({block, theme, L}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const sp = seg(block, (s) => s.kind === 'speech') || {from: 0, to: block.frames};
  const n = block.points.length, span = Math.max(1, sp.to - sp.from);
  return (
    <Panel theme={theme} L={L} style={{alignItems: 'stretch'}}>
      <H theme={theme} L={L} size={64} color={theme.accent}>{block.heading || 'تَعَلَّمْنَا الْيَوْمَ'}</H>
      {block.points.map((p, i) => {
        const at = sp.from + (span * i) / n;
        const k = pop(frame, fps, at);
        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 22 * L.s, opacity: Math.min(1, k * 1.5), fontSize: 50 * L.s, lineHeight: 1.6}}>
            <div style={{flex: 'none', width: 60 * L.s, height: 60 * L.s, borderRadius: 60, background: theme.right, color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 38 * L.s, transform: `scale(${k})`, fontFamily: 'sans-serif'}}>✓</div>
            <div>{p}</div>
          </div>
        );
      })}
    </Panel>
  );
};

const Outro = ({block, theme, L, width, height}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const k = pop(frame, fps, 3);
  const bits = Array.from({length: 26}, (_, i) => i);
  return (
    <>
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        {bits.map((i) => {
          const x = ((i * 73) % 100) / 100 * width;
          const y = ((frame * (2 + (i % 4)) + i * 97) % (height + 100)) - 50;
          return <div key={i} style={{position: 'absolute', left: x, top: y, width: 22, height: 22, borderRadius: i % 2 ? 22 : 4,
            background: theme.deco[i % theme.deco.length] || theme.accent, transform: `rotate(${frame * 3 + i * 20}deg)`, opacity: 0.9}} />;
        })}
      </AbsoluteFill>
      <Panel theme={theme} L={L} style={{background: 'transparent', border: 'none', boxShadow: 'none'}}>
        <div style={{transform: `scale(${k})`}}><H theme={theme} L={L} size={L.vertical ? 84 : 96} color={theme.accent}>{block.text || 'أَحْسَنْتُمْ!'}</H></div>
        {block.subtext && <H theme={theme} L={L} size={50} color={theme.soft} style={{fontWeight: 400, opacity: fadeIn(frame, 15)}}>{block.subtext}</H>}
      </Panel>
    </>
  );
};

const MAP = {title: Title, explain: Explain, term: Term, example: Example, compare: Compare, steps: Steps, image: ImageBlock,
  letter: LetterBlock, word: WordBlock, say_with_me: SayWithMe, quiz: Quiz, recap: Recap, outro: Outro};

export const Block = (props) => {
  const C = MAP[props.block.type];
  return C ? <C {...props} /> : null;
};

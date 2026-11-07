import {spring, interpolate} from 'remotion';
export const pop = (frame, fps, delay = 0) => spring({frame: frame - delay, fps, config: {damping: 14, stiffness: 140, mass: 0.7}});
export const fadeIn = (frame, start = 0, len = 10) => interpolate(frame, [start, start + len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
// أول مقطع من نوع/وسم معيّن في الكتلة
export const seg = (block, pred) => (block.segments || []).find(pred);

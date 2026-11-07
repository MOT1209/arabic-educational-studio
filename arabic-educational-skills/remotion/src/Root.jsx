import React from 'react';
import {Composition} from 'remotion';
import {Lesson} from './Lesson.jsx';

// Aspect ratio presets for multi-platform rendering
export const PRESETS = {
  youtube: {width: 1920, height: 1080, fps: 30, label: 'YouTube (16:9)'},
  shorts: {width: 1080, height: 1920, fps: 30, label: 'Shorts/Reels/TikTok (9:16)'},
  square: {width: 1080, height: 1080, fps: 30, label: 'Square (1:1)'},
};

const fallback = {fps: 30, width: 1920, height: 1080, durationInFrames: 60, blocks: [], captions: [], audio: [],
  speaking: [], theme: 'classroom', narrator: {avatar: 'none'}, title: ''};

export const Root = () => (
  <>
    {/* YouTube 16:9 */}
    <Composition
      id="Lesson-16x9"
      component={Lesson}
      defaultProps={{...fallback, width: 1920, height: 1080}}
      fps={30}
      width={1920}
      height={1080}
      durationInFrames={60}
      calculateMetadata={({props}) => ({
        durationInFrames: Math.max(1, props.durationInFrames || 60),
        width: 1920,
        height: 1080,
        fps: props.fps || 30,
      })}
    />
    {/* Shorts/Reels/TikTok 9:16 */}
    <Composition
      id="Lesson-9x16"
      component={Lesson}
      defaultProps={{...fallback, width: 1080, height: 1920}}
      fps={30}
      width={1080}
      height={1920}
      durationInFrames={60}
      calculateMetadata={({props}) => ({
        durationInFrames: Math.max(1, props.durationInFrames || 60),
        width: 1080,
        height: 1920,
        fps: props.fps || 30,
      })}
    />
    {/* Square 1:1 */}
    <Composition
      id="Lesson-1x1"
      component={Lesson}
      defaultProps={{...fallback, width: 1080, height: 1080}}
      fps={30}
      width={1080}
      height={1080}
      durationInFrames={60}
      calculateMetadata={({props}) => ({
        durationInFrames: Math.max(1, props.durationInFrames || 60),
        width: 1080,
        height: 1080,
        fps: props.fps || 30,
      })}
    />
  </>
);
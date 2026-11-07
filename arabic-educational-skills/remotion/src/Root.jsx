import React from 'react';
import {Composition} from 'remotion';
import {Lesson} from './Lesson.jsx';

const fallback = {fps: 30, width: 1920, height: 1080, durationInFrames: 60, blocks: [], captions: [], audio: [],
  speaking: [], theme: 'classroom', narrator: {avatar: 'none'}, title: ''};

export const Root = () => (
  <Composition
    id="Lesson"
    component={Lesson}
    defaultProps={fallback}
    fps={30}
    width={1920}
    height={1080}
    durationInFrames={60}
    calculateMetadata={({props}) => ({
      durationInFrames: Math.max(1, props.durationInFrames || 60),
      width: props.width || 1920,
      height: props.height || 1080,
      fps: props.fps || 30,
    })}
  />
);

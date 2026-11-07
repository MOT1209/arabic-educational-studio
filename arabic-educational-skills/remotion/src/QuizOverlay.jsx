import React, {useState, useEffect} from 'react';
import {useCurrentFrame, useVideoConfig, interpolate, spring} from 'remotion';

// Interactive Quiz Overlay for educational video scenes
// Props:
//   question: string (Arabic text)
//   options: array of {text, correct: boolean}
//   duration: number (seconds for countdown)
//   startFrame: number (when quiz appears)
//   showSummary: boolean (end-of-video summary)
export const QuizOverlay = ({
  question,
  options = [],
  duration = 5,
  startFrame = 0,
  correctSound = true,
  theme = {},
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const elapsed = (frame - startFrame) / fps;
  const countdown = Math.max(0, duration - elapsed);
  const isExpired = countdown <= 0;

  // Determine which option was "selected" (for visual feedback)
  // In render mode, we show the correct answer after countdown
  const showAnswer = isExpired;

  const containerStyle = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: '80%',
    maxWidth: 800,
    background: theme.cardBg || 'rgba(255,255,255,0.95)',
    borderRadius: 16,
    padding: 24,
    boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
    direction: 'rtl',
    textAlign: 'right',
    fontFamily: 'Noto Sans Arabic, sans-serif',
  };

  const questionStyle = {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 20,
    color: theme.text || '#1a1a1a',
  };

  const optionStyle = (opt, idx) => ({
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    margin: '8px 0',
    borderRadius: 8,
    border: '2px solid',
    borderColor: showAnswer
      ? (opt.correct ? '#22c55e' : '#ef4444')
      : (theme.border || '#e5e7eb'),
    background: showAnswer
      ? (opt.correct ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.1)')
      : 'transparent',
    cursor: 'pointer',
    fontSize: 20,
    transition: 'all 0.3s ease',
  });

  const timerStyle = {
    width: '100%',
    height: 8,
    background: '#e5e7eb',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 16,
  };

  const timerFillStyle = {
    width: `${(countdown / duration) * 100}%`,
    height: '100%',
    background: countdown > duration * 0.3 ? '#3b82f6' : '#ef4444',
    transition: 'width 0.1s linear',
  };

  if (frame < startFrame) return null;

  return (
    <div style={containerStyle}>
      {/* Timer bar */}
      <div style={timerStyle}>
        <div style={timerFillStyle} />
      </div>

      {/* Countdown number */}
      <div style={{textAlign: 'center', fontSize: 24, fontWeight: 'bold', marginBottom: 12, color: countdown > 1 ? '#3b82f6' : '#ef4444'}}>
        {Math.ceil(countdown)}
      </div>

      {/* Question */}
      <div style={questionStyle}>{question}</div>

      {/* Options */}
      {options.map((opt, idx) => (
        <div key={idx} style={optionStyle(opt, idx)}>
          <span>{opt.text}</span>
          {showAnswer && (
            <span style={{fontSize: 20}}>
              {opt.correct ? '✅' : '❌'}
            </span>
          )}
        </div>
      ))}

      {/* Feedback */}
      {showAnswer && (
        <div style={{textAlign: 'center', marginTop: 16, fontSize: 22, fontWeight: 'bold', color: '#22c55e'}}>
          إجابة صحيحة! 🎉
        </div>
      )}
    </div>
  );
};

// Summary slide component
export const QuizSummary = ({totalPoints, maxPoints, theme = {}}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const scale = spring({frame, fps, config: {damping: 12, stiffness: 100}});

  return (
    <div style={{
      position: 'absolute',
      top: 0, left: 0, right: 0, bottom: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: theme.bg || '#f8fafc',
      direction: 'rtl',
    }}>
      <h2 style={{fontSize: 48, fontWeight: 'bold', color: theme.text || '#1a1a1a', transform: `scale(${scale})`}}>
        ملخص النتائج
      </h2>
      <div style={{fontSize: 64, fontWeight: 'bold', color: '#3b82f6', marginTop: 24}}>
        {totalPoints} / {maxPoints}
      </div>
      <div style={{fontSize: 24, color: theme.text || '#1a1a1a', marginTop: 16}}>
        {totalPoints === maxPoints ? 'أحسنت! 🌟' : 'أحسنت! واصل التعلم 📚'}
      </div>
    </div>
  );
};
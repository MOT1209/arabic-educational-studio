import React, {useState, useRef} from 'react';

// Web Studio UI for Arabic Educational Video Editor
// Features: RTL sidebar, live preview, script editor, tashkeel toggle, voice gen, dark/light theme

const WebStudio = () => {
  const [theme, setTheme] = useState('dark');
  const [script, setScript] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(60);
  const [tashkeelApplied, setTashkeelApplied] = useState(false);
  const [voiceGenerated, setVoiceGenerated] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const videoRef = useRef(null);

  const isDark = theme === 'dark';
  const bg = isDark ? 'bg-gray-900' : 'bg-gray-100';
  const cardBg = isDark ? 'bg-gray-800' : 'bg-white';
  const text = isDark ? 'text-gray-100' : 'text-gray-900';
  const border = isDark ? 'border-gray-700' : 'border-gray-300';

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
    if (videoRef.current) {
      if (isPlaying) videoRef.current.pause();
      else videoRef.current.play();
    }
  };

  const handleTashkeel = () => {
    // Call auto_tashkeel API
    setTashkeelApplied(!tashkeelApplied);
  };

  const handleGenerateVoice = () => {
    // Call TTS API
    setVoiceGenerated(!voiceGenerated);
  };

  return (
    <div className={`min-h-screen ${bg} ${text} flex`} dir="rtl">
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <header className={`h-14 ${cardBg} border-b ${border} flex items-center justify-between px-4`}>
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold">استوديو الفيديو التعليمي</h1>
            <span className="text-sm text-gray-400">v5.0</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTheme(isDark ? 'light' : 'dark')}
              className={`px-3 py-1.5 rounded-md text-sm ${isDark ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'}`}
            >
              {isDark ? '☀️ فاتح' : '🌙 داكن'}
            </button>
            <button className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium">
              تصدير
            </button>
          </div>
        </header>

        {/* Preview + Timeline */}
        <div className="flex-1 flex flex-col p-4 gap-4">
          {/* Preview Window */}
          <div className={`${cardBg} rounded-lg border ${border} flex-1 flex items-center justify-center min-h-[300px]`}>
            <div className="text-center text-gray-400">
              <div className="text-6xl mb-2">🎬</div>
              <p>معاينة الفيديو</p>
              <p className="text-sm">1920 × 1080 (16:9)</p>
            </div>
          </div>

          {/* Playback Controls */}
          <div className={`${cardBg} rounded-lg border ${border} p-3 flex items-center gap-4`}>
            <button
              onClick={handlePlayPause}
              className="w-10 h-10 flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white rounded-full"
            >
              {isPlaying ? '⏸' : '▶'}
            </button>
            <div className="flex-1">
              <input
                type="range"
                min={0}
                max={duration}
                value={currentTime}
                onChange={(e) => setCurrentTime(Number(e.target.value))}
                className="w-full h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            <span className="text-sm text-gray-400 min-w-[80px] text-center">
              {Math.floor(currentTime)}s / {duration}s
            </span>
          </div>
        </div>
      </div>

      {/* Right Sidebar (RTL) */}
      <aside className={`${sidebarOpen ? 'w-80' : 'w-12'} ${cardBg} border-l ${border} transition-all duration-300 flex flex-col`}>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className={`h-10 flex items-center justify-center border-b ${border} hover:bg-gray-700`}
        >
          {sidebarOpen ? '◀' : '▶'}
        </button>

        {sidebarOpen && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Script Editor */}
            <div>
              <h3 className="font-bold mb-2">محرر السيناريو</h3>
              <textarea
                value={script}
                onChange={(e) => setScript(e.target.value)}
                className={`w-full h-40 p-3 rounded-md border ${border} ${isDark ? 'bg-gray-700' : 'bg-gray-50'} text-sm resize-none`}
                placeholder="أدخل النص العربي هنا..."
                dir="rtl"
              />
            </div>

            {/* Tashkeel Toggle */}
            <button
              onClick={handleTashkeel}
              className={`w-full py-2 rounded-md text-sm font-medium transition-colors ${
                tashkeelApplied
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-gray-600 hover:bg-gray-500 text-white'
              }`}
            >
              {tashkeelApplied ? '✓ تم التشكيل' : 'تطبيق التشكيل'}
            </button>

            {/* Generate Voice */}
            <button
              onClick={handleGenerateVoice}
              className={`w-full py-2 rounded-md text-sm font-medium transition-colors ${
                voiceGenerated
                  ? 'bg-purple-600 hover:bg-purple-700 text-white'
                  : 'bg-gray-600 hover:bg-gray-500 text-white'
              }`}
            >
              {voiceGenerated ? '✓ تم توليد الصوت' : 'توليد الصوت'}
            </button>

            {/* Layers Panel */}
            <div>
              <h3 className="font-bold mb-2">الطبقات</h3>
              <div className={`border ${border} rounded-md p-2 space-y-1`}>
                {['Background', 'Character', 'Text', 'Quiz'].map((layer, i) => (
                  <div key={i} className={`flex items-center justify-between p-2 rounded ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
                    <span className="text-sm">{layer}</span>
                    <button className="text-xs text-gray-400 hover:text-white">👁</button>
                  </div>
                ))}
              </div>
            </div>

            {/* Tools */}
            <div>
              <h3 className="font-bold mb-2">الأدوات</h3>
              <div className="grid grid-cols-2 gap-2">
                {['نص', 'صورة', 'صوت', 'تأثير'].map((tool, i) => (
                  <button
                    key={i}
                    className={`p-2 rounded-md text-sm ${isDark ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'}`}
                  >
                    {tool}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
};

export default WebStudio;
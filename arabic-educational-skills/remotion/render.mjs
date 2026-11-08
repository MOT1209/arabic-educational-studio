// يصيّر خصائص درس (JSON من studio plan render) إلى MP4.
// الاستعمال: node render.mjs <props.json> <out.mp4> <publicDir> [--still FRAME --png out.png] [--concurrency N]
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const args = process.argv.slice(2);
const [propsPath, out, publicDir] = args;
if (!propsPath || !out || !publicDir) {
  console.error('usage: node render.mjs props.json out.mp4 publicDir [--still FRAME] [--concurrency N]');
  process.exit(2);
}
const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const PROPS_MAJOR = '1';
const inputProps = JSON.parse(fs.readFileSync(propsPath, 'utf8'));
if (inputProps.props_version && String(inputProps.props_version).split('.')[0] !== PROPS_MAJOR) {
  console.error(`unsupported props_version ${inputProps.props_version}; this renderer implements ${PROPS_MAJOR}.x`);
  process.exit(2);
}
const here = path.dirname(fileURLToPath(import.meta.url));
const browserExecutable = process.env.AES_CHROME || undefined;
// src/Root.jsx registers one composition per aspect ratio (Lesson-16x9 and
// friends), so the id has to come from the props the plan produced.
const FORMAT_COMPOSITIONS = {'16:9': 'Lesson-16x9', '9:16': 'Lesson-9x16', '1:1': 'Lesson-1x1'};
const compositionId = opt('--composition')
  || FORMAT_COMPOSITIONS[inputProps.format]
  || (inputProps.width === 1080 && inputProps.height === 1920 ? 'Lesson-9x16'
    : inputProps.width === 1080 && inputProps.height === 1080 ? 'Lesson-1x1'
    : 'Lesson-16x9');
const serveUrl = await bundle({entryPoint: path.join(here, 'src', 'index.jsx'), publicDir: path.resolve(publicDir)});
const composition = await selectComposition({serveUrl, id: compositionId, inputProps, browserExecutable});
const chromiumOptions = {gl: 'swangle'};
const still = opt('--still');
if (still !== undefined) {
  const frames = String(still).split(',').map(Number);
  for (const f of frames) {
    const o = frames.length > 1 ? out.replace(/(\.png)?$/, `_${String(f).padStart(5, '0')}.png`) : out;
    await renderStill({composition, serveUrl, output: o, frame: Math.min(f, composition.durationInFrames - 1), inputProps,
      onBrowserLog: process.env.AES_DEBUG ? (l) => console.log('[browser]', l.text) : undefined,
      browserExecutable, chromiumOptions});
    console.log('still', o);
  }
} else {
  let last = -1;
  await renderMedia({composition, serveUrl, codec: 'h264', outputLocation: out, inputProps, browserExecutable, chromiumOptions,
    concurrency: Number(opt('--concurrency') || 0) || null, crf: 20, audioCodec: 'aac', enforceAudioTrack: true,
    onProgress: ({progress}) => { const p = Math.floor(progress * 10); if (p !== last) { last = p; console.log(`progress ${p * 10}%`); } }});
  console.log('done', out);
}

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
const inputProps = JSON.parse(fs.readFileSync(propsPath, 'utf8'));
const here = path.dirname(fileURLToPath(import.meta.url));
const browserExecutable = process.env.AES_CHROME || undefined;
const serveUrl = await bundle({entryPoint: path.join(here, 'src', 'index.jsx'), publicDir: path.resolve(publicDir)});
const composition = await selectComposition({serveUrl, id: 'Lesson', inputProps, browserExecutable});
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

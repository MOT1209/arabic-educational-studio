# AI Lesson Scriptwriter — Prompt Template

## System Prompt

You are an expert Arabic educational content creator specializing in creating engaging, pedagogically sound video scripts for children aged 6-10. You create scripts for Arabic language lessons (Nahw, Sarf, Imla, Balagha, Reading, Writing, Phonetics, Vocabulary).

## Input Format

```json
{
  "subject_title": "إنَّ وأخواتها",
  "target_age_group": "kids_6_10",
  "video_duration_seconds": 60,
  "lesson_type": "nahw",
  "key_concepts": ["إنَّ تنصب الاسم وتُرفع الخبر", "اسم إنَّ منصوب", "خبر إنَّ مرفوع"],
  "examples": ["إنَّ الطالبَ مجتهدٌ", "إنَّ الشمسَ مشرقةٌ"]
}
```

## Output Format

```json
{
  "scenes": [
    {
      "scene_id": 1,
      "duration_sec": 5,
      "narration_text": "مَرْحَبًا! الْيَوْمَ نَتَعَلَّمُ إنَّ وأخواتها.",
      "visual_elements": ["CharacterBuddy", "TitleText"],
      "on_screen_text": "إنَّ وأخواتها",
      "background_color": "#4F46E5",
      "character_mood": "happy",
      "speech_bubble": "مرحباً!"
    }
  ]
}
```

## Prompt Template (TypeScript/Node.js)

```typescript
const SCRIPTWRITER_PROMPT = `
You are an expert Arabic educational content creator. Create a {duration}-second educational video script about "{subject}" for children aged {ageGroup}.

Requirements:
1. Output ONLY valid JSON matching the schema below.
2. Each scene must have: scene_id, duration_sec, narration_text (fully diacritized Arabic), visual_elements, on_screen_text, background_color, character_mood, speech_bubble.
3. Total duration must equal {duration} seconds.
4. Use simple, clear Arabic (Fusha Mubassata).
5. Include a hook in the first 3 seconds.
6. Include at least one example, one common mistake, and one exercise.
7. End with a summary and CTA (subscribe/next lesson).
8. character_mood: "happy" | "explaining" | "thinking" | "asking"
9. visual_elements: choose from ["CharacterBuddy", "TitleText", "ArabicText", "Highlight", "Quiz", "Callout", "Badge"]
10. background_color: hex color

Schema:
{
  "scenes": [
    {
      "scene_id": number,
      "duration_sec": number,
      "narration_text": string (fully diacritized),
      "visual_elements": string[],
      "on_screen_text": string,
      "background_color": string,
      "character_mood": string,
      "speech_bubble": string | null
    }
  ]
}

Topic: {subject}
Key concepts: {concepts}
Examples: {examples}
`;

interface ScriptInput {
  subject_title: string;
  target_age_group: string;
  video_duration_seconds: number;
  lesson_type: string;
  key_concepts: string[];
  examples: string[];
}

interface Scene {
  scene_id: number;
  duration_sec: number;
  narration_text: string;
  visual_elements: string[];
  on_screen_text: string;
  background_color: string;
  character_mood: 'happy' | 'explaining' | 'thinking' | 'asking';
  speech_bubble: string | null;
}

interface ScriptOutput {
  scenes: Scene[];
}

async function generateScript(input: ScriptInput): Promise<ScriptOutput> {
  const prompt = SCRIPTWRITER_PROMPT
    .replace('{duration}', String(input.video_duration_seconds))
    .replace('{subject}', input.subject_title)
    .replace('{ageGroup}', input.target_age_group)
    .replace('{concepts}', input.key_concepts.join(', '))
    .replace('{examples}', input.examples.join(', '));

  // Call your LLM API here (OpenAI, Anthropic, etc.)
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: 'gpt-4',
      messages: [{role: 'user', content: prompt}],
      temperature: 0.7,
    }),
  });

  const data = await response.json();
  const content = data.choices[0].message.content;
  return JSON.parse(content) as ScriptOutput;
}

// Feed output into Remotion
function scriptToRemotionProps(script: ScriptOutput) {
  const totalFrames = script.scenes.reduce((sum, s) => sum + s.duration_sec * 30, 0);
  return {
    fps: 30,
    width: 1920,
    height: 1080,
    durationInFrames: totalFrames,
    blocks: script.scenes.map((s, i) => ({
      id: `scene_${String(i + 1).padStart(2, '0')}`,
      duration_seconds: s.duration_sec,
      learning_goal: s.on_screen_text,
      dialogue: [{
        character: 'teacher',
        text_diacritized: s.narration_text,
        text_plain: s.narration_text.replace(/[ًٌٍَُِّْٰٕٓٔ]/g, ''),
        start: 0,
        end: s.duration_sec,
      }],
      visuals: s.visual_elements.map(v => ({type: v.toLowerCase(), start: 0, end: s.duration_sec})),
    })),
    captions: [],
    audio: [],
    speaking: [],
    theme: 'classroom',
    narrator: {avatar: 'none'},
    title: script.scenes[0]?.on_screen_text || '',
  };
}

export {generateScript, scriptToRemotionProps};
```

## Integration with Remotion

```typescript
// In your Remotion project:
import {generateScript, scriptToRemotionProps} from './scriptwriter';

const script = await generateScript({
  subject_title: 'إنَّ وأخواتها',
  target_age_group: 'kids_6_10',
  video_duration_seconds: 60,
  lesson_type: 'nahw',
  key_concepts: ['إنَّ تنصب الاسم وتُرفع الخبر'],
  examples: ['إنَّ الطالبَ مجتهدٌ'],
});

const props = scriptToRemotionProps(script);
// Pass props to <Lesson {...props} />
```
PYEOF
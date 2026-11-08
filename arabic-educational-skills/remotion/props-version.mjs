// حارس إصدار خصائص الدرس. منفصل عن render.mjs كي يُختبر دون تثبيت Remotion.
export const PROPS_MAJOR = '1';

// يُعيد رسالة خطأ عند غياب الإصدار أو عند إصدار رئيسي غير مدعوم، وإلا null.
export function propsVersionError(props) {
  const version = props && props.props_version;
  if (!version) {
    return `props_version is missing; regenerate the props with the studio (this renderer implements ${PROPS_MAJOR}.x)`;
  }
  if (String(version).split('.')[0] !== PROPS_MAJOR) {
    return `unsupported props_version ${version}; this renderer implements ${PROPS_MAJOR}.x`;
  }
  return null;
}

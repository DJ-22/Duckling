import type { StudentState } from "../../types/session";

function deriveState(comprehension: number): StudentState {
  if (comprehension >= 67) return "clicks";
  if (comprehension >= 34) return "thinking";
  return "confused";
}

const FACE: Record<StudentState, { body: string; mouth: string; thought: string; label: string }> = {
  confused: { body: "#fde68a", mouth: "M 38 64 Q 50 58 62 64", thought: "?", label: "confused" },
  thinking: { body: "#fcd34d", mouth: "M 40 63 L 60 63", thought: "…", label: "thinking" },
  clicks: { body: "#fbbf24", mouth: "M 38 60 Q 50 72 62 60", thought: "!", label: "it clicks!" },
};

export function Student({
  comprehension,
  state,
}: {
  comprehension: number;
  state?: StudentState;
}) {
  const current = state ?? deriveState(comprehension);
  const face = FACE[current];
  const wideEyes = current === "clicks";

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <span
          key={face.thought}
          className="absolute -right-2 -top-2 flex h-7 w-7 items-center justify-center rounded-full bg-white text-lg font-bold text-amber-600 shadow transition-all duration-500"
        >
          {face.thought}
        </span>
        <svg width="120" height="120" viewBox="0 0 100 100" role="img" aria-label={`Student: ${face.label}`}>
          <circle cx="50" cy="52" r="36" fill={face.body} className="transition-[fill] duration-700" />
          <circle cx="40" cy={wideEyes ? 44 : 46} r={wideEyes ? 5 : 3.5} fill="#1f2937" className="transition-all duration-500" />
          <circle cx="60" cy={wideEyes ? 44 : 46} r={wideEyes ? 5 : 3.5} fill="#1f2937" className="transition-all duration-500" />
          <polygon points="46,54 54,54 50,61" fill="#f97316" />
          <path d={face.mouth} stroke="#1f2937" strokeWidth="2.5" fill="none" strokeLinecap="round" className="transition-all duration-500" />
        </svg>
      </div>

      <div className="w-40">
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
          <div
            className="h-full rounded-full bg-amber-400 transition-[width] duration-700 ease-out"
            style={{ width: `${Math.min(100, Math.max(0, comprehension))}%` }}
          />
        </div>
        <p className="mt-1 text-center text-xs capitalize text-gray-500">{face.label}</p>
      </div>
    </div>
  );
}

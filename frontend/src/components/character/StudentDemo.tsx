import { useState } from "react";
import { Student } from "./Student";
import { UnderstandingMap } from "../UnderstandingMap";
import type { UnderstandingMapEntry } from "../../types/session";

const SAMPLE_MAP: UnderstandingMapEntry[] = [
  { concept_id: "1", concept_name: "Server Virtualization", felt: 80, shown: 92 },
  { concept_id: "2", concept_name: "Para Virtualization", felt: 75, shown: 30 },
  { concept_id: "3", concept_name: "Memory Virtualization", felt: 50, shown: 55 },
];

export function StudentDemo() {
  const [comprehension, setComprehension] = useState(10);

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-8 p-8">
      <div className="flex flex-col items-center gap-4">
        <Student comprehension={comprehension} />
        <input
          type="range"
          min={0}
          max={100}
          value={comprehension}
          onChange={(e) => setComprehension(Number(e.target.value))}
          className="w-64"
        />
        <span className="text-sm text-gray-500">comprehension: {comprehension}</span>
      </div>
      <UnderstandingMap entries={SAMPLE_MAP} />
    </div>
  );
}

export type StudentState = "confused" | "thinking" | "clicks";

export interface SessionView {
  id: string;
  concept_id: string;
  concept_name: string;
  status: "in_progress" | "completed";
  comprehension: number;
  student_state: StudentState;
  felt: number | null;
  transcript: Array<Record<string, unknown>>;
}

export interface TurnResponse {
  turn_index: number;
  question: string;
  overall: number;
  delta: number;
  comprehension: number;
  student_state: StudentState;
  weakest_gap: string;
}

export interface UnderstandingMapEntry {
  concept_id: string;
  concept_name: string;
  felt: number | null;
  shown: number;
}

export interface CompletionResult {
  comprehension: number;
  final_overall: number;
  felt: number | null;
  understanding_map: UnderstandingMapEntry[];
}

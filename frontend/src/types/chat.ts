export type Language = "en" | "es" | "ar";
export type Citation = {
  id: string;
  title: string;
  url: string;
  excerpt: string;
};
export type ChatResponse = {
  status:
    | "answered"
    | "unknown"
    | "out_of_scope"
    | "medical_safety"
    | "unavailable"
    | "privacy";
  answer: string;
  sources: Citation[];
  conversation_id: string;
  needs_quote: boolean;
  disclaimer: string | null;
  language: Language;
  quote_url: string | null;
  suggested_questions: string[];
};
export type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
  error?: boolean;
};
export type KnowledgeSource = {
  id: string;
  title: string;
  category: string;
  url: string;
  status?: string;
};
export type KnowledgeStatus = {
  ready: boolean;
  source_count: number;
  chunk_count: number;
  last_updated: string | null;
  sources: KnowledgeSource[];
};
export type Health = {
  status: string;
  knowledge_ready: boolean;
  generation_available: boolean;
  answer_mode: "gemini" | "extractive";
  gemini_configured: boolean;
};

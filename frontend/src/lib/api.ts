import type {
  ChatResponse,
  Health,
  KnowledgeStatus,
  Language,
} from "@/types/chat";

const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

export async function getStatus(): Promise<{
  health: Health;
  knowledge: KnowledgeStatus;
}> {
  const [health, knowledge] = await Promise.all([
    fetch(`${BASE}/api/health`, {
      signal: AbortSignal.timeout(15000),
      cache: "no-store",
    }),
    fetch(`${BASE}/api/knowledge/status`, {
      signal: AbortSignal.timeout(15000),
      cache: "no-store",
    }),
  ]);
  if (!health.ok || !knowledge.ok) throw new Error("Connection unavailable");
  return { health: await health.json(), knowledge: await knowledge.json() };
}

export async function sendMessage(
  message: string,
  conversation_id: string | null,
  language: Language,
  signal: AbortSignal,
): Promise<ChatResponse> {
  const response = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id, language }),
    signal: AbortSignal.any([signal, AbortSignal.timeout(45000)]),
  });
  if (response.status === 429)
    throw new Error(
      "You’ve reached the request limit. Please wait a minute and try again.",
    );
  if (!response.ok)
    throw new Error(
      "The assistant couldn’t complete this request. Please try again shortly.",
    );
  return response.json();
}

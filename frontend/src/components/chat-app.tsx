"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  ArrowRight,
  ArrowUp,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Copy,
  ExternalLink,
  FileText,
  Globe2,
  Layers3,
  Menu,
  MessageSquare,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Trash2,
  Wallet,
  X,
  AlertCircle,
  Video,
  MapPin,
} from "lucide-react";
import { getStatus, sendMessage } from "@/lib/api";
import type { Health, KnowledgeStatus, Language, Message } from "@/types/chat";

const suggestions = [
  {
    icon: Stethoscope,
    label: "Explore treatments",
    detail: "What treatments does ITC offer?",
    question: "What treatments does ITC offer?",
    color: "blue",
  },
  {
    icon: Layers3,
    label: "Understand a package",
    detail: "What’s included in the care?",
    question: "What is included in the adenocarcinoma package?",
    color: "teal",
  },
  {
    icon: Wallet,
    label: "Find treatment costs",
    detail: "See prices with their sources",
    question: "What is the price of the adenocarcinoma package in Mexico?",
    color: "violet",
  },
  {
    icon: MessageSquare,
    label: "Take the next step",
    detail: "How do I request a quote?",
    question: "How do I request a quote?",
    color: "amber",
  },
];
const labels = {
  en: {
    placeholder: "Ask about a treatment, package, or price…",
    send: "Send message",
    language: "English",
    suggestions: "You could ask",
  },
  es: {
    placeholder: "Pregunta sobre un tratamiento, paquete o precio…",
    send: "Enviar mensaje",
    language: "Español",
    suggestions: "Puedes preguntar",
  },
  ar: {
    placeholder: "اسأل عن علاج أو باقة أو سعر…",
    send: "إرسال الرسالة",
    language: "العربية",
    suggestions: "يمكنك أن تسأل",
  },
};

type SavedChat = {
  id: string;
  title: string;
  messages: Message[];
  conversationId: string | null;
  updatedAt: number;
};
const CHAT_STORAGE_KEY = "placidway-chat-history-v1";
const MAX_SAVED_CHATS = 20;
const MAX_MESSAGES_PER_CHAT = 60;

function readSavedChats(): SavedChat[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY) || "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((chat): chat is SavedChat =>
      typeof chat?.id === "string" &&
      typeof chat?.title === "string" &&
      Array.isArray(chat?.messages) &&
      chat.messages.every((message: Message) =>
        typeof message?.id === "string" &&
        (message?.role === "user" || message?.role === "assistant") &&
        typeof message?.text === "string",
      ) &&
      (chat?.conversationId === null || typeof chat?.conversationId === "string") &&
      typeof chat?.updatedAt === "number",
    ).slice(0, MAX_SAVED_CHATS);
  } catch {
    return [];
  }
}

function Mark({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand-mark ${small ? "small" : ""}`} aria-hidden="true">
      <Sparkles size={small ? 18 : 23} strokeWidth={1.8} />
    </span>
  );
}

function AssistantMessage({
  message,
  onSuggestion,
  busy,
}: {
  message: Message;
  onSuggestion: (question: string) => void;
  busy: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const response = message.response;
  return (
    <article
      className={`message assistant ${message.error ? "error-message" : ""}`}
    >
      <Mark small />
      <div
        className="message-body"
        dir={response?.language === "ar" ? "rtl" : "auto"}
      >
        <div className="message-name">
          PlacidWay assistant{" "}
          <span>
            {response?.sources.length
              ? "Based on listed sources"
              : "Here to help"}
          </span>
        </div>
        <div className="answer-copy">
          <ReactMarkdown
            skipHtml
            components={{
              a: ({ children }) => <span>{children}</span>,
              img: () => null,
            }}
          >
            {message.text}
          </ReactMarkdown>
        </div>
        {response?.disclaimer && (
          <div className="medical-note">
            <CircleHelp size={15} />
            <span>{response.disclaimer}</span>
          </div>
        )}
        {!!response?.sources.length && (
          <div className="citations">
            <div className="citation-label">
              <BookOpen size={16} /> Sources for this answer
            </div>
            {response.sources.map((source, index) => (
              <details key={source.id} className="citation">
                <summary>
                  <span className="source-number">{index + 1}</span>
                  <span>{source.title}</span>
                  <ChevronDown size={15} />
                </summary>
                <div className="citation-evidence">
                  <blockquote>{source.excerpt}</blockquote>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Read original page <ExternalLink size={13} />
                  </a>
                </div>
              </details>
            ))}
          </div>
        )}
        {response?.needs_quote && response.quote_url && (
          <a
            className="quote-link"
            href={response.quote_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Request a quote from PlacidWay <ArrowRight size={15} />
          </a>
        )}
        {!!response?.suggested_questions?.length && (
          <div className="followup-suggestions">
            <span>{labels[response.language].suggestions}</span>
            <div>
              {response.suggested_questions.map((question) => (
                <button
                  type="button"
                  key={question}
                  onClick={() => onSuggestion(question)}
                  disabled={busy}
                >
                  {question} <ArrowUp size={13} />
                </button>
              ))}
            </div>
          </div>
        )}
        {!message.error && (
          <div className="message-actions">
            <button
              aria-label="Copy answer"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(message.text);
                  setCopied(true);
                  setCopyError(false);
                  setTimeout(() => setCopied(false), 2000);
                } catch {
                  setCopyError(true);
                }
              }}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? "Copied" : "Copy"}
            </button>
            {copyError && <span>Copy unavailable in this browser.</span>}
          </div>
        )}
      </div>
    </article>
  );
}

export function ChatApp() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [language, setLanguage] = useState<Language>("en");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [savedChats, setSavedChats] = useState<SavedChat[]>([]);
  const [activeChatId, setActiveChatId] = useState("");
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeStatus | null>(null);
  const [connection, setConnection] = useState<
    "loading" | "connected" | "failed"
  >("loading");
  const [view, setView] = useState<"chat" | "sources">("chat");
  const [menuOpen, setMenuOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [largeText, setLargeText] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const modalRef = useRef<HTMLElement>(null);

  async function refreshStatus() {
    setConnection("loading");
    try {
      const data = await getStatus();
      setHealth(data.health);
      setKnowledge(data.knowledge);
      setConnection("connected");
    } catch {
      setConnection("failed");
    }
  }
  useEffect(() => {
    void refreshStatus();
    return () => abortRef.current?.abort();
  }, []);
  useEffect(() => {
    try {
      setLargeText(localStorage.getItem("placidway-large-text") === "true");
    } catch {
      // The default reading size still works when browser storage is unavailable.
    }
  }, []);
  useEffect(() => {
    const chats = readSavedChats();
    setSavedChats(chats);
    setActiveChatId(chats[0]?.id ?? crypto.randomUUID());
    setMessages(chats[0]?.messages ?? []);
    setConversationId(chats[0]?.conversationId ?? null);
    setHistoryLoaded(true);
  }, []);
  useEffect(() => {
    if (!historyLoaded || !activeChatId || !messages.length) return;
    const firstQuestion = messages.find((message) => message.role === "user")?.text;
    if (!firstQuestion) return;
    const title = firstQuestion.length > 44
      ? `${firstQuestion.slice(0, 44).trimEnd()}…`
      : firstQuestion;
    setSavedChats((previous) => {
      const current = previous.find((chat) => chat.id === activeChatId);
      const updated: SavedChat = {
        id: activeChatId,
        title,
        messages: messages.slice(-MAX_MESSAGES_PER_CHAT),
        conversationId,
        updatedAt: current?.updatedAt ?? Date.now(),
      };
      return [updated, ...previous.filter((chat) => chat.id !== activeChatId)].slice(0, MAX_SAVED_CHATS);
    });
  }, [messages, conversationId, activeChatId, historyLoaded]);
  useEffect(() => {
    if (!historyLoaded) return;
    try {
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(savedChats));
    } catch {
      // Conversation remains usable when storage is disabled or full.
    }
  }, [savedChats, historyLoaded]);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        setAboutOpen(false);
      }
    };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, []);
  useEffect(() => {
    if (!aboutOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    const trap = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const controls = modalRef.current?.querySelectorAll<HTMLElement>(
        'button, a[href], select, [tabindex="0"]',
      );
      if (!controls?.length) return;
      const first = controls[0],
        last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trap);
    return () => {
      document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [aboutOpen]);

  function clearChat() {
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
    setMessages([]);
    setInput("");
    setConversationId(null);
    setActiveChatId(crypto.randomUUID());
    setView("chat");
    setMenuOpen(false);
    inputRef.current?.focus();
  }
  function openChat(chat: SavedChat) {
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
    setActiveChatId(chat.id);
    setMessages(chat.messages);
    setConversationId(chat.conversationId);
    setInput("");
    setView("chat");
    setMenuOpen(false);
  }
  function deleteChat(chatId: string) {
    const remaining = savedChats.filter((chat) => chat.id !== chatId);
    setSavedChats(remaining);
    if (activeChatId === chatId) {
      abortRef.current?.abort();
      abortRef.current = null;
      setBusy(false);
      const next = remaining[0];
      setActiveChatId(next?.id ?? crypto.randomUUID());
      setMessages(next?.messages ?? []);
      setConversationId(next?.conversationId ?? null);
      setInput("");
      setView("chat");
    }
  }
  async function submit(text = input) {
    const message = text.trim();
    if (!message || busy || message.length > 1500) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setView("chat");
    setInput("");
    setBusy(true);
    setMessages((previous) => [
      ...previous,
      { id: crypto.randomUUID(), role: "user", text: message },
    ]);
    try {
      const response = await sendMessage(
        message,
        conversationId,
        language,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setConversationId(response.conversation_id);
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: response.answer,
          response,
        },
      ]);
    } catch (error) {
      if (controller.signal.aborted) return;
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text:
            error instanceof Error
              ? error.message
              : "Connection unavailable. Please try again.",
          error: true,
        },
      ]);
    } finally {
      if (abortRef.current === controller) {
        setBusy(false);
        abortRef.current = null;
        inputRef.current?.focus();
      }
    }
  }
  const ready = health?.knowledge_ready && health?.generation_available;
  const statusLabel =
    connection === "loading"
      ? "Connecting"
      : connection === "failed"
        ? "Connection unavailable"
        : ready
          ? health?.answer_mode === "extractive"
            ? "Source reading mode"
            : "Ready to help"
          : health?.knowledge_ready
            ? "Sources ready · AI offline"
            : "Knowledge unavailable";

  return (
    <div className={`app-shell ${largeText ? "large-text" : ""}`}>
      <a className="skip-link" href="#main-content">
        Skip to conversation
      </a>
      {menuOpen && (
        <button
          className="sidebar-backdrop"
          onClick={() => setMenuOpen(false)}
          aria-label="Close navigation"
        />
      )}
      <aside
        className={`sidebar ${menuOpen ? "open" : ""}`}
        aria-label="Main navigation"
      >
        <a href="/" className="brand">
          <img
            className="brand-logo"
            src="/brand/placidway-logo.png"
            alt="PlacidWay"
            width="170"
            height="86"
          />
          <span className="brand-sub">AI KNOWLEDGE ASSISTANT</span>
        </a>
        <div className="workspace-label">YOUR HEALTHCARE GUIDE</div>
        <button className="new-chat" onClick={clearChat}>
          <Plus size={17} /> New conversation
        </button>
        <nav className="nav-items">
          <button
            className={view === "chat" ? "active" : ""}
            onClick={() => {
              setView("chat");
              setMenuOpen(false);
            }}
          >
            <MessageSquare size={18} /> Ask the assistant{" "}
            <ChevronRight size={15} />
          </button>
          <button
            className={view === "sources" ? "active" : ""}
            onClick={() => {
              setView("sources");
              setMenuOpen(false);
            }}
          >
            <BookOpen size={18} /> Knowledge sources{" "}
            <span className="nav-count">7</span>
          </button>
        </nav>
        <div className="sidebar-topics">
          <div className="workspace-label">EXPLORE A TOPIC</div>
          {[
            "ITC clinic overview",
            "Adenocarcinoma package",
            "Adrenal cancer package",
            "Anal cancer package",
          ].map((topic, index) => (
            <button
              key={topic}
              onClick={() => {
                setMenuOpen(false);
                void submit(
                  index
                    ? `What is included in the ${topic.toLowerCase()}?`
                    : "Tell me about ITC Immunity Therapy Center.",
                );
              }}
              disabled={busy}
            >
              <span className="topic-dot" />
              {topic}
            </button>
          ))}
        </div>
        <div className="sidebar-history" aria-label="Chat history">
          <div className="workspace-label">RECENT CHATS</div>
          {savedChats.length ? (
            <div className="history-list">
              {savedChats.map((chat) => (
                <div className={`history-item ${activeChatId === chat.id ? "active" : ""}`} key={chat.id}>
                  <button
                    className="history-select"
                    onClick={() => openChat(chat)}
                    aria-current={activeChatId === chat.id ? "page" : undefined}
                    title={chat.title}
                  >
                    <MessageSquare size={16} aria-hidden="true" />
                    <span>{chat.title}</span>
                  </button>
                  <button
                    className="history-delete"
                    onClick={() => deleteChat(chat.id)}
                    aria-label={`Delete conversation: ${chat.title}`}
                    title="Delete conversation"
                  >
                    <Trash2 size={16} aria-hidden="true" />
                  </button>
                </div>
              ))}
            </div>
          ) : <p className="history-empty">Your chats will appear here.</p>}
          <p className="history-privacy">Saved only in this browser.</p>
        </div>
        <div className="sidebar-bottom">
          <div className="trust-card">
            <ShieldCheck size={20} />
            <strong>Clarity starts with a source.</strong>
            <p>
              Every factual answer points back to the approved website content.
            </p>
            <button onClick={() => setAboutOpen(true)}>
              How this assistant works <ArrowRight size={13} />
            </button>
          </div>
          <div className="sidebar-footer">
            <span className="demo-dot" /> Assessment project <span>v1.0</span>
          </div>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div className="topbar-title">
            <button
              className="mobile-menu icon-button"
              onClick={() => setMenuOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={21} />
            </button>
            <img
              className="topbar-logo"
              src="/brand/placidway-logo.png"
              alt="PlacidWay"
              width="94"
              height="47"
            />
            <span>AI Knowledge Assistant</span>
            <span className="beta-tag">BETA</span>
          </div>
          <div className="topbar-right">
            <button
              type="button"
              className="text-size-toggle"
              aria-label={largeText ? "Use standard text size" : "Use larger text"}
              aria-pressed={largeText}
              onClick={() => {
                const next = !largeText;
                setLargeText(next);
                try {
                  localStorage.setItem("placidway-large-text", String(next));
                } catch {
                  // The choice remains active for this tab.
                }
              }}
            >
              <span aria-hidden="true">Aa</span>
              <span>Text size</span>
            </button>
            <span
              className={`connection ${ready && connection === "connected" ? "ready" : "pending"}`}
            >
              <i />
              {statusLabel}
            </span>
            <button
              className="icon-button help-button"
              aria-label="About this assistant"
              onClick={() => setAboutOpen(true)}
            >
              <CircleHelp size={20} />
            </button>
          </div>
        </header>

        <main
          id="main-content"
          className={`main-content ${view === "sources" ? "sources-view" : ""}`}
        >
          {view === "sources" ? (
            <section className="sources-page">
              <span className="eyebrow">
                <BookOpen size={14} /> THE KNOWLEDGE LIBRARY
              </span>
              <h1>See where answers come from.</h1>
              <p className="page-description">
                The assistant uses only the seven PlacidWay pages approved for
                this assessment. Open a page to read the original information.
              </p>
              <div className="source-summary">
                <span>
                  <ShieldCheck size={17} />
                  {knowledge?.source_count ?? 0} sources available
                </span>
                <span>
                  {knowledge?.last_updated
                    ? `Refreshed ${new Date(knowledge.last_updated).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`
                    : "Awaiting knowledge status"}
                </span>
                <button
                  onClick={refreshStatus}
                  disabled={connection === "loading"}
                >
                  <RefreshCw
                    size={14}
                    className={connection === "loading" ? "spin" : ""}
                  />
                  Check status
                </button>
              </div>
              {knowledge?.sources.map((source, index) => (
                <a
                  key={source.id}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="library-source"
                >
                  <span className="library-icon">
                    {source.category === "clinic_videos" ? (
                      <Video size={20} />
                    ) : source.category.includes("price") ? (
                      <Wallet size={20} />
                    ) : (
                      <FileText size={20} />
                    )}
                  </span>
                  <div>
                    <span className="source-category">
                      SOURCE {String(index + 1).padStart(2, "0")} ·{" "}
                      {source.category.replaceAll("_", " ")}
                    </span>
                    <h2>{source.title}</h2>
                    <span className="source-domain">placidway.com</span>
                  </div>
                  <span
                    className={`source-state ${source.status === "indexed" ? "indexed" : ""}`}
                  >
                    {source.status === "indexed" ? "Indexed" : "Unavailable"}
                  </span>
                  <ExternalLink size={17} />
                </a>
              ))}
              {!knowledge && (
                <div className="empty-sources">
                  <AlertCircle size={25} />
                  <p>
                    The source list could not be loaded. Check the connection
                    and try again.
                  </p>
                  <button className="secondary-button" onClick={refreshStatus}>
                    Retry connection
                  </button>
                </div>
              )}
              <p className="library-note">
                The library contains website descriptions. A listing or
                testimonial does not establish a treatment’s safety or
                effectiveness.
              </p>
            </section>
          ) : (
            <>
              <div
                className="conversation-scroll"
                aria-live="polite"
                aria-relevant="additions text"
              >
                {!messages.length ? (
                  <section className="welcome">
                    <div className="welcome-emblem">
                      <Sparkles size={27} strokeWidth={1.4} />
                      <span className="emblem-orbit" />
                    </div>
                    <span className="eyebrow">INFORMATION YOU CAN TRACE</span>
                    <h1>
                      A clearer way to understand
                      <br />
                      <span>your options.</span>
                    </h1>
                    <p className="welcome-description">
                      Ask questions about treatments, clinics, and pricing
                      <br className="desktop-break" /> using verified website
                      information.
                    </p>
                    <div className="scope-pill">
                      <MapPin size={13} />
                      <span>ITC Immunity Therapy Center</span>
                      <span className="pill-divider" />
                      Tijuana, Mexico
                    </div>
                    <div className="suggestions">
                      {suggestions.map(({ icon: Icon, ...suggestion }) => (
                        <button
                          key={suggestion.label}
                          onClick={() => submit(suggestion.question)}
                          disabled={busy}
                          className="suggestion"
                        >
                          <span
                            className={`suggestion-icon ${suggestion.color}`}
                          >
                            <Icon size={20} strokeWidth={1.7} />
                          </span>
                          <strong>{suggestion.label}</strong>
                          <span>{suggestion.detail}</span>
                          <ArrowUp size={16} className="suggestion-arrow" />
                        </button>
                      ))}
                    </div>
                    <div className="welcome-trust">
                      <span>
                        <BookOpen size={14} />7 approved pages
                      </span>
                      <span>
                        <ShieldCheck size={14} />
                        Sources with every answer
                      </span>
                      <span>
                        <Globe2 size={14} />
                        English · Español · العربية
                      </span>
                    </div>
                  </section>
                ) : (
                  <section className="conversation" aria-label="Conversation">
                    {messages.map((message) =>
                      message.role === "user" ? (
                        <article className="message user" key={message.id}>
                          <div dir="auto">{message.text}</div>
                        </article>
                      ) : (
                        <AssistantMessage
                          key={message.id}
                          message={message}
                          onSuggestion={(question) => void submit(question)}
                          busy={busy}
                        />
                      ),
                    )}
                    {busy && (
                      <div className="message assistant thinking" role="status">
                        <Mark small />
                        <div>
                          <span>Looking for supporting information</span>
                          <span className="thinking-dots">
                            <i />
                            <i />
                            <i />
                          </span>
                        </div>
                      </div>
                    )}
                    <div ref={endRef} />
                  </section>
                )}
              </div>
              <div className="composer-area">
                {health?.answer_mode === "extractive" && (
                  <div className="mode-notice">
                    <BookOpen size={13} />
                    <span>
                      Showing verified source excerpts. Gemini is not connected
                      in this demo.
                    </span>
                  </div>
                )}
                {connection === "failed" && (
                  <div className="connection-notice">
                    <AlertCircle size={15} />
                    <span>The assistant is unreachable right now.</span>
                    <button onClick={refreshStatus}>Retry connection</button>
                  </div>
                )}
                {connection === "connected" && !ready && (
                  <div className="connection-notice">
                    <AlertCircle size={15} />
                    <span>
                      {health?.knowledge_ready
                        ? "AI answers are unavailable. You can still explore the source pages and listed prices."
                        : "The knowledge library is unavailable. Please try again later."}
                    </span>
                  </div>
                )}
                <form
                  className={`composer ${busy ? "working" : ""}`}
                  onSubmit={(event) => {
                    event.preventDefault();
                    void submit();
                  }}
                >
                  <label className="sr-only" htmlFor="question">
                    Your question
                  </label>
                  <textarea
                    ref={inputRef}
                    id="question"
                    placeholder={labels[language].placeholder}
                    value={input}
                    maxLength={1500}
                    rows={1}
                    dir={language === "ar" ? "rtl" : "auto"}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (
                        event.key === "Enter" &&
                        !event.shiftKey &&
                        !event.nativeEvent.isComposing
                      ) {
                        event.preventDefault();
                        void submit();
                      }
                    }}
                  />
                  <div className="composer-bottom">
                    <div className="composer-tools">
                      <Globe2 size={15} />
                      <label className="sr-only" htmlFor="language">
                        Response language
                      </label>
                      <select
                        id="language"
                        value={language}
                        onChange={(event) =>
                          setLanguage(event.target.value as Language)
                        }
                      >
                        <option value="en">English</option>
                        <option value="es">Español</option>
                        <option value="ar">العربية</option>
                      </select>
                      <span className="composer-divider" />
                      <span className="privacy-hint">
                        Please keep personal health details private
                      </span>
                    </div>
                    <div className="send-area">
                      {input.length > 1200 && (
                        <span className="character-count">
                          {input.length}/1500
                        </span>
                      )}
                      <button
                        className="send-button"
                        type="submit"
                        disabled={!input.trim() || busy}
                        aria-label={labels[language].send}
                      >
                        {busy ? (
                          <RefreshCw size={18} className="spin" />
                        ) : (
                          <ArrowUp size={20} />
                        )}
                      </button>
                    </div>
                  </div>
                </form>
                <div className="composer-footnote">
                  <ShieldCheck size={12} />
                  <span>
                    Website information, not personalized medical advice.
                  </span>
                  <button onClick={() => setAboutOpen(true)}>Learn more</button>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
      {aboutOpen && (
        <div className="modal-backdrop" onClick={() => setAboutOpen(false)}>
          <section
            ref={modalRef}
            className="about-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="about-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              autoFocus
              className="modal-close icon-button"
              onClick={() => setAboutOpen(false)}
              aria-label="Close about dialog"
            >
              <X size={20} />
            </button>
            <Mark />
            <h2 id="about-title">
              A guide to the website.
              <br />
              Evidence you can read.
            </h2>
            <p>
              This independent assessment project answers from seven specified
              PlacidWay pages. It is not an official booking service.
            </p>
            <ul>
              <li>Open each source card to see the supporting passage.</li>
              <li>When information is missing, the assistant says so.</li>
              <li>Bookings and quote requests go directly to PlacidWay.</li>
              <li>A clinician must assess individual treatment suitability.</li>
            </ul>
            <div className="about-privacy">
              <ShieldCheck size={18} />
              <p>
                Please don’t enter your name, email, or medical history. Chat
                history is saved in this browser and can be deleted one chat at
                a time. Limited topic context is retained temporarily on the
                server. AI requests contain public excerpts and a constrained
                topic description.
              </p>
            </div>
            <button
              className="primary-button"
              onClick={() => {
                setAboutOpen(false);
                setView("sources");
              }}
            >
              Explore the sources <ArrowRight size={16} />
            </button>
          </section>
        </div>
      )}
    </div>
  );
}

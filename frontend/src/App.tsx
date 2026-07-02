import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import "./App.css";
import {
  AUTH_EXPIRED_EVENT,
  ApiRequestError,
  clearStoredAccessToken,
  confirmMemoryCandidate,
  createMemory,
  deleteMemory,
  getApiErrorMessage,
  getConversation,
  getCurrentUser,
  getStoredAccessToken,
  isAiProviderUnavailableError,
  listAuditLogs,
  listConversations,
  listMemories,
  loginUser,
  registerUser,
  revokeMemory,
  sendChatMessage,
  storeAccessToken,
  updateMemory,
} from "./lib/api";
import type {
  AuditLog,
  AuthUser,
  ChatResponse,
  ConversationDetail,
  ConversationSummary,
  MemoryCandidateItem,
  MemoryItem,
} from "./types";

type AuthMode = "login" | "register";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  safetyLevel?: string | null;
  detectedEmotion?: string | null;
};

type MemoryEditState = {
  id: string;
  memoryType: string;
  content: string;
  confidence: string;
  sensitivity: string;
  consentState: string;
};

const ACTIVE_CONVERSATION_KEY = "akon_active_conversation_id";

const QUICK_START_PROMPTS = [
  "Help me think through an important decision.",
  "Teach me something step by step.",
  "Draft a professional message for me.",
  "Help me plan my next move.",
  "Analyze this idea and tell me if it is strong.",
  "Help me organize my thoughts clearly.",
];

function getStoredActiveConversationId(): string | undefined {
  return localStorage.getItem(ACTIVE_CONVERSATION_KEY) || undefined;
}

function storeActiveConversationId(conversationId: string): void {
  localStorage.setItem(ACTIVE_CONVERSATION_KEY, conversationId);
}

function clearActiveConversationId(): void {
  localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
}

function formatErrorMessage(error: unknown): string {
  const message = getApiErrorMessage(error);

  if (error instanceof ApiRequestError && error.requestId) {
    return `${message} Request ID: ${error.requestId}`;
  }

  return message;
}

function buildChatFailureMessage(error: unknown): string {
  if (isAiProviderUnavailableError(error)) {
    return (
      "I’m having trouble reaching my AI provider right now. " +
      "Your message was not saved, so you can try again shortly without losing the thread."
    );
  }

  return formatErrorMessage(error);
}

function isSameDay(firstDate: Date, secondDate: Date): boolean {
  return (
    firstDate.getFullYear() === secondDate.getFullYear() &&
    firstDate.getMonth() === secondDate.getMonth() &&
    firstDate.getDate() === secondDate.getDate()
  );
}

function formatMessageTimestamp(createdAt: string): string {
  const messageDate = new Date(createdAt);

  if (Number.isNaN(messageDate.getTime())) {
    return "Just now";
  }

  const now = new Date();

  if (isSameDay(messageDate, now)) {
    return new Intl.DateTimeFormat(undefined, {
      hour: "numeric",
      minute: "2-digit",
    }).format(messageDate);
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    year: messageDate.getFullYear() === now.getFullYear() ? undefined : "numeric",
  }).format(messageDate);
}

function formatConversationDate(createdAt?: string | null): string {
  if (!createdAt) {
    return "Recent";
  }

  const conversationDate = new Date(createdAt);

  if (Number.isNaN(conversationDate.getTime())) {
    return "Recent";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(conversationDate);
}

function mapConversationToMessages(
  conversation: ConversationDetail,
): ChatMessage[] {
  return conversation.messages.map((message) => ({
    role: message.role === "assistant" ? "assistant" : "user",
    content: message.content,
    createdAt: message.created_at,
    safetyLevel: message.safety_level,
    detectedEmotion: message.detected_emotion,
  }));
}

function removeCandidateAtIndex(
  candidates: MemoryCandidateItem[],
  candidateIndex: number,
): MemoryCandidateItem[] {
  return candidates.filter((_, index) => index !== candidateIndex);
}

function buildMemoryEditState(memory: MemoryItem): MemoryEditState {
  return {
    id: memory.id,
    memoryType: memory.memory_type,
    content: memory.content,
    confidence: memory.confidence,
    sensitivity: memory.sensitivity,
    consentState: memory.consent_state,
  };
}

function App() {
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const conversationOpenRequestRef = useRef(0);

  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [token, setToken] = useState<string | null>(() => getStoredAccessToken());
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

  const [email, setEmail] = useState("user@example.com");
  const [password, setPassword] = useState("strongpassword123");
  const [displayName, setDisplayName] = useState("Akon User");

  const [chatInput, setChatInput] = useState("");
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(
    () => getStoredActiveConversationId(),
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [memoryCandidates, setMemoryCandidates] = useState<MemoryCandidateItem[]>([]);

  const [memoryType, setMemoryType] = useState("preference");
  const [memoryContent, setMemoryContent] = useState("");
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [memoryEditState, setMemoryEditState] = useState<MemoryEditState | null>(null);
  const [memoryActionId, setMemoryActionId] = useState<string | null>(null);

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isMemoryLoading, setIsMemoryLoading] = useState(false);
  const [isWorkspaceLoading, setIsWorkspaceLoading] = useState(false);
  const [openingConversationId, setOpeningConversationId] = useState<string | null>(
    null,
  );
  const [candidateActionIndex, setCandidateActionIndex] = useState<number | null>(null);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isAuthenticated = Boolean(token && currentUser);
  const isBusy =
    isAuthLoading ||
    isChatLoading ||
    isMemoryLoading ||
    isWorkspaceLoading ||
    candidateActionIndex !== null ||
    memoryActionId !== null;

  const userLabel = useMemo(() => {
    if (!currentUser) {
      return "Guest";
    }

    return currentUser.display_name || currentUser.email;
  }, [currentUser]);

  const activeConversationTitle = useMemo(() => {
    if (!activeConversationId) {
      return "New chat";
    }

    return (
      conversations.find((conversation) => conversation.id === activeConversationId)
        ?.title || "Conversation"
    );
  }, [activeConversationId, conversations]);

  const activeMemoryCount = memories.filter(
    (memory) => memory.consent_state !== "revoked",
  ).length;

  function cancelPendingConversationOpen() {
    conversationOpenRequestRef.current += 1;
    setOpeningConversationId(null);
    setIsWorkspaceLoading(false);
  }

  useEffect(() => {
    function handleAuthExpired() {
      resetAuthenticatedState();
      setErrorMessage("Your session expired. Please login again.");
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);

    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    };
  }, []);

  useEffect(() => {
    const messageList = messageListRef.current;

    if (!messageList) {
      return;
    }

    const frameId = window.requestAnimationFrame(() => {
      messageList.scrollTo({
        top: messageList.scrollHeight,
        behavior: "smooth",
      });
    });

    return () => window.cancelAnimationFrame(frameId);
  }, [messages, isChatLoading]);

  useEffect(() => {
    async function restoreSession() {
      const storedToken = getStoredAccessToken();

      if (!storedToken) {
        setIsBootstrapping(false);
        return;
      }

      try {
        const user = await getCurrentUser(storedToken);
        setToken(storedToken);
        setCurrentUser(user);

        await refreshWorkspace(storedToken);

        const storedConversationId = getStoredActiveConversationId();

        if (storedConversationId) {
          await openConversation(storedToken, storedConversationId, false);
        }
      } catch {
        resetAuthenticatedState();
      } finally {
        setIsBootstrapping(false);
      }
    }

    void restoreSession();
  }, []);

  async function refreshWorkspace(authToken = token) {
    if (!authToken) {
      return;
    }

    setIsWorkspaceLoading(true);

    try {
      const [memoryList, conversationList, auditList] = await Promise.all([
        listMemories(authToken),
        listConversations(authToken),
        listAuditLogs(authToken),
      ]);

      setMemories(memoryList);
      setConversations(conversationList);
      setAuditLogs(auditList);
    } finally {
      setIsWorkspaceLoading(false);
    }
  }

  async function openConversation(
    authToken: string,
    conversationId: string,
    shouldSetStatus = true,
  ) {
    const requestId = conversationOpenRequestRef.current + 1;
    conversationOpenRequestRef.current = requestId;

    setIsWorkspaceLoading(true);
    setOpeningConversationId(conversationId);
    setActiveConversationId(conversationId);
    setMessages([]);
    setMemoryCandidates([]);
    resetFeedback();

    try {
      const conversation = await getConversation(authToken, conversationId);

      if (conversationOpenRequestRef.current !== requestId) {
        return;
      }

      setActiveConversationId(conversation.id);
      storeActiveConversationId(conversation.id);
      setMessages(mapConversationToMessages(conversation));
      setMemoryCandidates([]);

      if (shouldSetStatus) {
        setStatusMessage("Conversation reopened.");
      }
    } catch (error) {
      if (conversationOpenRequestRef.current !== requestId) {
        return;
      }

      clearActiveConversationId();
      setActiveConversationId(undefined);
      setErrorMessage(formatErrorMessage(error));
    } finally {
      if (conversationOpenRequestRef.current === requestId) {
        setOpeningConversationId(null);
        setIsWorkspaceLoading(false);
      }
    }
  }

  function resetFeedback() {
    setErrorMessage(null);
    setStatusMessage(null);
  }

  function resetAuthenticatedState() {
    cancelPendingConversationOpen();
    clearStoredAccessToken();
    clearActiveConversationId();
    setToken(null);
    setCurrentUser(null);
    setMessages([]);
    setMemoryCandidates([]);
    setMemories([]);
    setMemoryEditState(null);
    setConversations([]);
    setAuditLogs([]);
    setActiveConversationId(undefined);
    setOpeningConversationId(null);
  }

  async function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();
    setIsAuthLoading(true);

    try {
      if (authMode === "register") {
        await registerUser({
          email,
          password,
          display_name: displayName,
        });
      }

      const login = await loginUser({
        email,
        password,
      });

      clearActiveConversationId();
      storeAccessToken(login.access_token);
      setToken(login.access_token);
      setCurrentUser(login.user);
      setActiveConversationId(undefined);
      cancelPendingConversationOpen();
      setMessages([]);
      setMemoryCandidates([]);
      setMemoryEditState(null);

      await refreshWorkspace(login.access_token);

      setStatusMessage("Welcome in. Akon is ready.");
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setIsAuthLoading(false);
    }
  }

  function handleLogout() {
    resetAuthenticatedState();
    setStatusMessage("You are signed out.");
  }

  function handleNewConversation() {
    cancelPendingConversationOpen();
    clearActiveConversationId();
    setActiveConversationId(undefined);
    setMessages([]);
    setMemoryCandidates([]);
    setChatInput("");
    setStatusMessage("New chat started.");
  }

  function handleQuickPrompt(prompt: string) {
    resetFeedback();
    setChatInput(prompt);
  }

  async function handleConversationClick(conversationId: string) {
    if (!token) {
      return;
    }

    await openConversation(token, conversationId);
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();

    const trimmedMessage = chatInput.trim();

    if (!token || !trimmedMessage || isChatLoading) {
      return;
    }

    const userMessage: ChatMessage = {
      role: "user",
      content: trimmedMessage,
      createdAt: new Date().toISOString(),
    };

    setMessages((current) => [...current, userMessage]);
    setChatInput("");
    setIsChatLoading(true);

    try {
      const response: ChatResponse = await sendChatMessage(
        token,
        trimmedMessage,
        activeConversationId,
      );

      setActiveConversationId(response.conversation_id);
      storeActiveConversationId(response.conversation_id);
      setMemoryCandidates(response.memory_candidates);

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.reply,
          createdAt: new Date().toISOString(),
          safetyLevel: response.safety_level,
          detectedEmotion: response.detected_emotion,
        },
      ]);

      await refreshWorkspace(token);
    } catch (error) {
      const chatFailureMessage = buildChatFailureMessage(error);

      if (isAiProviderUnavailableError(error)) {
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: chatFailureMessage,
            createdAt: new Date().toISOString(),
          },
        ]);
        setStatusMessage("Akon could not complete that reply. Please try again shortly.");
      } else {
        setErrorMessage(chatFailureMessage);
      }
    } finally {
      setIsChatLoading(false);
    }
  }

  function handleChatInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }

    event.preventDefault();

    if (isChatLoading || !chatInput.trim()) {
      return;
    }

    event.currentTarget.form?.requestSubmit();
  }

  async function handleCreateMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();

    if (!token || !memoryContent.trim()) {
      return;
    }

    setIsMemoryLoading(true);

    try {
      await createMemory(token, {
        memory_type: memoryType,
        content: memoryContent.trim(),
        source: "frontend_manual",
        confidence: "medium",
        sensitivity: "low",
        consent_state: "explicit",
      });

      setMemoryContent("");
      setStatusMessage("Akon saved that memory.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setIsMemoryLoading(false);
    }
  }

  async function handleApproveCandidate(
    candidate: MemoryCandidateItem,
    candidateIndex: number,
  ) {
    if (!token) {
      return;
    }

    resetFeedback();
    setCandidateActionIndex(candidateIndex);

    try {
      await confirmMemoryCandidate(token, candidate);
      setMemoryCandidates((current) => removeCandidateAtIndex(current, candidateIndex));
      setStatusMessage("Memory approved and saved.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setCandidateActionIndex(null);
    }
  }

  function handleIgnoreCandidate(candidateIndex: number) {
    setMemoryCandidates((current) => removeCandidateAtIndex(current, candidateIndex));
    setStatusMessage("Suggested memory ignored.");
  }

  function handleBeginEditMemory(memory: MemoryItem) {
    resetFeedback();
    setMemoryEditState(buildMemoryEditState(memory));
  }

  function handleCancelEditMemory() {
    setMemoryEditState(null);
    setStatusMessage("Memory edit cancelled.");
  }

  async function handleSubmitMemoryEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();

    if (!token || !memoryEditState || !memoryEditState.content.trim()) {
      return;
    }

    setMemoryActionId(memoryEditState.id);

    try {
      await updateMemory(token, memoryEditState.id, {
        memory_type: memoryEditState.memoryType,
        content: memoryEditState.content.trim(),
        confidence: memoryEditState.confidence,
        sensitivity: memoryEditState.sensitivity,
        consent_state: memoryEditState.consentState,
      });

      setMemoryEditState(null);
      setStatusMessage("Memory updated.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setMemoryActionId(null);
    }
  }

  async function handleRevokeMemory(memory: MemoryItem) {
    if (!token) {
      return;
    }

    resetFeedback();
    setMemoryActionId(memory.id);

    try {
      await revokeMemory(token, memory.id);
      setMemoryEditState(null);
      setStatusMessage("Memory revoked. Akon will stop using it.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setMemoryActionId(null);
    }
  }

  async function handleDeleteMemory(memory: MemoryItem) {
    if (!token) {
      return;
    }

    const shouldDelete = window.confirm(
      "Delete this memory permanently? This cannot be undone.",
    );

    if (!shouldDelete) {
      return;
    }

    resetFeedback();
    setMemoryActionId(memory.id);

    try {
      await deleteMemory(token, memory.id);

      if (memoryEditState?.id === memory.id) {
        setMemoryEditState(null);
      }

      setStatusMessage("Memory deleted permanently.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setMemoryActionId(null);
    }
  }

  if (isBootstrapping) {
    return (
      <main className="boot-shell">
        <section className="boot-card">
          <div className="brand-mark">A</div>
          <h1>Opening Akon</h1>
          <p>Preparing your AI workspace.</p>
        </section>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="public-shell">
        <section className="public-hero">
          <nav className="public-nav" aria-label="Product navigation">
            <div className="brand-lockup">
              <div className="brand-mark">A</div>
              <div>
                <strong>Akon</strong>
                <span>AI Companion Platform</span>
              </div>
            </div>

            <button
              className="ghost-button compact-button"
              type="button"
              onClick={() => setAuthMode("login")}
            >
              Sign in
            </button>
          </nav>

          <div className="public-grid">
            <section className="public-copy">
              <p className="eyebrow">Akon AI · v0.3.9</p>
              <h1>Your intelligent companion for thought, work, learning, and life.</h1>
              <p className="hero-copy">
                Akon helps you think clearly, write better, learn faster, plan next
                steps, reflect with care, and keep useful context under your control.
              </p>

              <div className="hero-pills">
                <span>Adaptive intelligence</span>
                <span>Memory with consent</span>
                <span>Private by design</span>
                <span>Built for everyday life</span>
              </div>
            </section>

            <form className="auth-card" onSubmit={handleAuthSubmit}>
              <div className="card-header centered">
                <p className="eyebrow">Your AI workspace</p>
                <h2>
                  {authMode === "login" ? "Welcome back" : "Create your Akon account"}
                </h2>
                <p>
                  Continue your conversations, saved context, and personal AI workspace.
                </p>
              </div>

              <label>
                Email
                <input
                  value={email}
                  type="email"
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </label>

              <label>
                Password
                <input
                  value={password}
                  type="password"
                  minLength={10}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </label>

              {authMode === "register" && (
                <label>
                  Display name
                  <input
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                  />
                </label>
              )}

              <button disabled={isAuthLoading} type="submit">
                {isAuthLoading
                  ? "Preparing..."
                  : authMode === "login"
                    ? "Enter Akon"
                    : "Create account"}
              </button>

              <button
                className="ghost-button"
                type="button"
                onClick={() =>
                  setAuthMode((current) => (current === "login" ? "register" : "login"))
                }
              >
                {authMode === "login"
                  ? "Create a new account"
                  : "I already have an account"}
              </button>
            </form>
          </div>
        </section>

        {(errorMessage || statusMessage || isBusy) && (
          <section className="feedback-row public-feedback">
            {errorMessage && <div className="alert error">{errorMessage}</div>}
            {statusMessage && <div className="alert success">{statusMessage}</div>}
            {isBusy && <div className="alert loading">Akon is preparing your workspace...</div>}
          </section>
        )}
      </main>
    );
  }

  return (
    <main className="product-shell">
      <aside className="app-sidebar">
        <div className="sidebar-top">
          <div className="brand-lockup">
            <div className="brand-mark">A</div>
            <div>
              <strong>Akon</strong>
              <span>AI Workspace</span>
            </div>
          </div>

          <button className="new-chat-button" type="button" onClick={handleNewConversation}>
            + New chat
          </button>
        </div>

        <section className="sidebar-section">
          <div className="sidebar-section-header">
            <span>Recent chats</span>
            {isWorkspaceLoading && <small>Syncing...</small>}
          </div>

          <div className="conversation-list">
            {conversations.length === 0 ? (
              <p className="empty-state">No chats yet.</p>
            ) : (
              conversations.map((conversation) => (
                <button
                  className={
                    conversation.id === activeConversationId
                      ? "conversation-item active"
                      : "conversation-item"
                  }
                  key={conversation.id}
                  type="button"
                  aria-current={
                    conversation.id === activeConversationId ? "true" : undefined
                  }
                  onClick={() => void handleConversationClick(conversation.id)}
                >
                  <strong>{conversation.title || "Untitled conversation"}</strong>
                  <span>
                    {conversation.safety_level || "Normal"} ·{" "}
                    {formatConversationDate(conversation.created_at)}
                  </span>
                </button>
              ))
            )}
          </div>
        </section>

        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="user-avatar">{userLabel.slice(0, 1).toUpperCase()}</div>
            <div>
              <strong>{userLabel}</strong>
              <span>{currentUser?.email}</span>
            </div>
          </div>

          <button className="ghost-button compact-button" type="button" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </aside>

      <section className="chat-workspace">
        <header className="chat-topbar">
          <div>
            <p className="eyebrow">Akon AI</p>
            <h1>{activeConversationTitle}</h1>
          </div>

          <div className="workspace-metrics" aria-label="Workspace metrics">
            <span>{conversations.length} chats</span>
            <span>{activeMemoryCount} memories</span>
            <span>{auditLogs.length} activities</span>
          </div>
        </header>

        {(errorMessage || statusMessage || isBusy) && (
          <section className="feedback-row">
            {errorMessage && <div className="alert error">{errorMessage}</div>}
            {statusMessage && <div className="alert success">{statusMessage}</div>}
            {isBusy && <div className="alert loading">Akon is updating your workspace...</div>}
          </section>
        )}

        <section className="chat-surface">
          <div className="message-list" ref={messageListRef}>
            {openingConversationId ? (
              <div className="empty-conversation loading-conversation">
                <div className="pulse-dot" />
                <p>Opening this conversation...</p>
              </div>
            ) : messages.length === 0 ? (
              <div className="empty-conversation pro-empty-state">
                <div className="brand-mark large-brand-mark">A</div>
                <h2>How can Akon help?</h2>
                <p>
                  Ask a question, draft something, study a topic, think through a
                  decision, or organize your next move.
                </p>

                <div className="prompt-grid">
                  {QUICK_START_PROMPTS.map((prompt) => (
                    <button
                      className="prompt-card"
                      key={prompt}
                      type="button"
                      onClick={() => handleQuickPrompt(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                  <strong>{message.role === "user" ? "You" : "Akon"}</strong>
                  <p>{message.content}</p>
                  <div className="message-meta">
                    <time dateTime={message.createdAt}>
                      {formatMessageTimestamp(message.createdAt)}
                    </time>
                    {message.safetyLevel && message.safetyLevel !== "S0" && (
                      <span>Care level: {message.safetyLevel}</span>
                    )}
                  </div>
                  {message.role === "assistant" &&
                    message.detectedEmotion &&
                    message.detectedEmotion !== "neutral" && (
                      <small className="message-emotion">
                        Akon sensed: {message.detectedEmotion}
                      </small>
                    )}
                </article>
              ))
            )}

            {isChatLoading && (
              <article className="message assistant thinking">
                <strong>Akon</strong>
                <p>Thinking...</p>
              </article>
            )}
          </div>

          <form className="chat-form" onSubmit={handleSendMessage}>
            <textarea
              value={chatInput}
              placeholder="Message Akon..."
              onChange={(event) => setChatInput(event.target.value)}
              onKeyDown={handleChatInputKeyDown}
            />
            <button disabled={isChatLoading || !chatInput.trim()} type="submit">
              {isChatLoading ? "Sending..." : "Send"}
            </button>
          </form>
        </section>
      </section>

      <aside className="context-panel">
        <section className="context-card">
          <div className="card-header">
            <p className="eyebrow">Memory</p>
            <h2>Personal context</h2>
            <p>
              Add preferences, goals, constraints, or background details so Akon becomes
              more useful over time.
            </p>
          </div>

          <form className="stack-form" onSubmit={handleCreateMemory}>
            <label>
              Type
              <select
                value={memoryType}
                onChange={(event) => setMemoryType(event.target.value)}
              >
                <option value="preference">Preference</option>
                <option value="goal">Goal</option>
                <option value="constraint">Constraint</option>
                <option value="emotional_baseline">Emotional baseline</option>
                <option value="cultural_context">Cultural context</option>
              </select>
            </label>

            <label>
              What should Akon remember?
              <textarea
                value={memoryContent}
                placeholder="Example: I prefer direct, step-by-step guidance when learning something difficult."
                onChange={(event) => setMemoryContent(event.target.value)}
              />
            </label>

            <button disabled={isMemoryLoading || !memoryContent.trim()} type="submit">
              {isMemoryLoading ? "Saving..." : "Save memory"}
            </button>
          </form>
        </section>

        {memoryCandidates.length > 0 && (
          <section className="context-card">
            <div className="card-header">
              <p className="eyebrow">Suggested memory</p>
              <h2>Review before saving</h2>
              <p>Nothing is saved unless you approve it.</p>
            </div>

            <div className="scroll-list">
              {memoryCandidates.map((candidate, index) => (
                <div
                  className="mini-item warm candidate-card"
                  key={`${candidate.memory_type}-${candidate.content}-${index}`}
                >
                  <strong>{candidate.memory_type}</strong>
                  <p>{candidate.content}</p>
                  <small>{candidate.reason}</small>

                  <div className="candidate-actions">
                    <button
                      type="button"
                      disabled={candidateActionIndex !== null}
                      onClick={() => void handleApproveCandidate(candidate, index)}
                    >
                      {candidateActionIndex === index ? "Saving..." : "Approve"}
                    </button>
                    <button
                      className="ghost-button"
                      type="button"
                      disabled={candidateActionIndex !== null}
                      onClick={() => handleIgnoreCandidate(index)}
                    >
                      Ignore
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="context-card">
          <div className="card-header">
            <p className="eyebrow">Saved memory</p>
            <h2>{activeMemoryCount} active</h2>
          </div>

          <div className="scroll-list memory-scroll-list">
            {memories.length === 0 ? (
              <p className="empty-state">No saved memory yet.</p>
            ) : (
              memories.map((memory) => {
                const isEditing = memoryEditState?.id === memory.id;
                const isActing = memoryActionId === memory.id;

                if (isEditing && memoryEditState) {
                  return (
                    <form
                      className="mini-item memory-edit-card"
                      key={memory.id}
                      onSubmit={handleSubmitMemoryEdit}
                    >
                      <label>
                        Type
                        <select
                          value={memoryEditState.memoryType}
                          onChange={(event) =>
                            setMemoryEditState((current) =>
                              current
                                ? {
                                    ...current,
                                    memoryType: event.target.value,
                                  }
                                : current,
                            )
                          }
                        >
                          <option value="preference">Preference</option>
                          <option value="goal">Goal</option>
                          <option value="constraint">Constraint</option>
                          <option value="emotional_baseline">Emotional baseline</option>
                          <option value="cultural_context">Cultural context</option>
                        </select>
                      </label>

                      <label>
                        Content
                        <textarea
                          value={memoryEditState.content}
                          onChange={(event) =>
                            setMemoryEditState((current) =>
                              current
                                ? {
                                    ...current,
                                    content: event.target.value,
                                  }
                                : current,
                            )
                          }
                        />
                      </label>

                      <div className="memory-edit-grid">
                        <label>
                          Confidence
                          <select
                            value={memoryEditState.confidence}
                            onChange={(event) =>
                              setMemoryEditState((current) =>
                                current
                                  ? {
                                      ...current,
                                      confidence: event.target.value,
                                    }
                                  : current,
                              )
                            }
                          >
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                          </select>
                        </label>

                        <label>
                          Sensitivity
                          <select
                            value={memoryEditState.sensitivity}
                            onChange={(event) =>
                              setMemoryEditState((current) =>
                                current
                                  ? {
                                      ...current,
                                      sensitivity: event.target.value,
                                    }
                                  : current,
                              )
                            }
                          >
                            <option value="low">Low</option>
                            <option value="high">High</option>
                          </select>
                        </label>
                      </div>

                      <label>
                        Consent state
                        <select
                          value={memoryEditState.consentState}
                          onChange={(event) =>
                            setMemoryEditState((current) =>
                              current
                                ? {
                                    ...current,
                                    consentState: event.target.value,
                                  }
                                : current,
                            )
                          }
                        >
                          <option value="explicit">Explicit</option>
                          <option value="implicit">Implicit</option>
                          <option value="revoked">Revoked</option>
                        </select>
                      </label>

                      <div className="memory-actions">
                        <button disabled={isActing} type="submit">
                          {isActing ? "Saving..." : "Save"}
                        </button>
                        <button
                          className="ghost-button"
                          disabled={isActing}
                          type="button"
                          onClick={handleCancelEditMemory}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  );
                }

                return (
                  <div className="mini-item memory-item-card" key={memory.id}>
                    <div className="memory-item-header">
                      <strong>{memory.memory_type}</strong>
                      <span className={`memory-consent ${memory.consent_state}`}>
                        {memory.consent_state}
                      </span>
                    </div>

                    <p>{memory.content}</p>
                    <small>
                      {memory.confidence} · {memory.sensitivity} ·{" "}
                      {memory.source || "manual"}
                    </small>

                    <div className="memory-actions">
                      <button
                        className="ghost-button"
                        disabled={Boolean(memoryActionId)}
                        type="button"
                        onClick={() => handleBeginEditMemory(memory)}
                      >
                        Edit
                      </button>

                      {memory.consent_state !== "revoked" && (
                        <button
                          className="ghost-button"
                          disabled={Boolean(memoryActionId)}
                          type="button"
                          onClick={() => void handleRevokeMemory(memory)}
                        >
                          {isActing ? "Revoking..." : "Revoke"}
                        </button>
                      )}

                      <button
                        className="danger-button"
                        disabled={Boolean(memoryActionId)}
                        type="button"
                        onClick={() => void handleDeleteMemory(memory)}
                      >
                        {isActing ? "Deleting..." : "Delete"}
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

        <section className="context-card compact-context-card">
          <div className="card-header">
            <p className="eyebrow">Trust</p>
            <h2>Recent activity</h2>
          </div>

          <div className="scroll-list trust-list">
            {auditLogs.length === 0 ? (
              <p className="empty-state">No activity yet.</p>
            ) : (
              auditLogs.slice(0, 8).map((auditLog) => (
                <div className="mini-item" key={auditLog.id}>
                  <strong>{auditLog.action}</strong>
                  <p>{auditLog.entity_type}</p>
                  <small>{auditLog.risk_level}</small>
                </div>
              ))
            )}
          </div>
        </section>
      </aside>
    </main>
  );
}

export default App;
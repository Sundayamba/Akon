import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";
import {
  AUTH_EXPIRED_EVENT,
  ApiRequestError,
  clearStoredAccessToken,
  createMemory,
  getConversation,
  getCurrentUser,
  getStoredAccessToken,
  listAuditLogs,
  listConversations,
  listMemories,
  loginUser,
  registerUser,
  sendChatMessage,
  storeAccessToken,
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
  safetyLevel?: string | null;
};

const ACTIVE_CONVERSATION_KEY = "akon_active_conversation_id";

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
  if (error instanceof ApiRequestError) {
    const requestIdText = error.requestId ? ` Request ID: ${error.requestId}` : "";
    return `${error.message}${requestIdText}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong.";
}

function mapConversationToMessages(
  conversation: ConversationDetail,
): ChatMessage[] {
  return conversation.messages.map((message) => ({
    role: message.role === "assistant" ? "assistant" : "user",
    content: message.content,
    safetyLevel: message.safety_level,
  }));
}

function App() {
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [token, setToken] = useState<string | null>(() => getStoredAccessToken());
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

  const [email, setEmail] = useState("rex@example.com");
  const [password, setPassword] = useState("strongpassword123");
  const [displayName, setDisplayName] = useState("Rex");

  const [chatInput, setChatInput] = useState("");
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(
    () => getStoredActiveConversationId(),
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [memoryCandidates, setMemoryCandidates] = useState<MemoryCandidateItem[]>([]);

  const [memoryType, setMemoryType] = useState("preference");
  const [memoryContent, setMemoryContent] = useState("");
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isMemoryLoading, setIsMemoryLoading] = useState(false);
  const [isWorkspaceLoading, setIsWorkspaceLoading] = useState(false);

  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isAuthenticated = Boolean(token && currentUser);
  const isBusy =
    isAuthLoading || isChatLoading || isMemoryLoading || isWorkspaceLoading;

  const userLabel = useMemo(() => {
    if (!currentUser) {
      return "Guest";
    }

    return currentUser.display_name || currentUser.email;
  }, [currentUser]);

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
    setIsWorkspaceLoading(true);
    resetFeedback();

    try {
      const conversation = await getConversation(authToken, conversationId);

      setActiveConversationId(conversation.id);
      storeActiveConversationId(conversation.id);
      setMessages(mapConversationToMessages(conversation));
      setMemoryCandidates([]);

      if (shouldSetStatus) {
        setStatusMessage("Conversation reopened.");
      }
    } catch (error) {
      clearActiveConversationId();
      setActiveConversationId(undefined);
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setIsWorkspaceLoading(false);
    }
  }

  function resetFeedback() {
    setErrorMessage(null);
    setStatusMessage(null);
  }

  function resetAuthenticatedState() {
    clearStoredAccessToken();
    clearActiveConversationId();
    setToken(null);
    setCurrentUser(null);
    setMessages([]);
    setMemoryCandidates([]);
    setMemories([]);
    setConversations([]);
    setAuditLogs([]);
    setActiveConversationId(undefined);
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
      setMessages([]);
      setMemoryCandidates([]);

      await refreshWorkspace(login.access_token);

      setStatusMessage("Welcome in. Akon is ready to listen.");
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
    clearActiveConversationId();
    setActiveConversationId(undefined);
    setMessages([]);
    setMemoryCandidates([]);
    setChatInput("");
    setStatusMessage("New conversation started.");
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

    if (!token || !trimmedMessage) {
      return;
    }

    const userMessage: ChatMessage = {
      role: "user",
      content: trimmedMessage,
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
          safetyLevel: response.safety_level,
        },
      ]);

      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setIsChatLoading(false);
    }
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
      setStatusMessage("Akon saved that understanding.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setIsMemoryLoading(false);
    }
  }

  if (isBootstrapping) {
    return (
      <main className="app-shell boot-shell">
        <div className="ambient-orb orb-one" />
        <div className="ambient-orb orb-two" />
        <section className="card boot-card">
          <div className="pulse-dot" />
          <h1>Opening your Akon space...</h1>
          <p>Checking your session and preparing your companion workspace.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <div className="ambient-orb orb-one" />
      <div className="ambient-orb orb-two" />
      <div className="ambient-orb orb-three" />

      <section className="hero-panel">
        <div className="hero-content">
          <p className="eyebrow">Akon companion preview · v0.2.6</p>
          <h1>A calm place to think, feel, and move forward.</h1>
          <p className="hero-copy">
            Akon is being shaped as a supportive AI companion that remembers with
            permission, responds with care, and helps you turn heavy moments into
            clear next steps.
          </p>

          <div className="hero-pills">
            <span>Private by design</span>
            <span>Memory with consent</span>
            <span>Gentle guidance</span>
          </div>
        </div>

        <div className="companion-card">
          <div className="companion-avatar">
            <span>A</span>
          </div>
          <div>
            <span className="soft-label">Current space</span>
            <strong>{isAuthenticated ? "Akon is with you" : "Begin when ready"}</strong>
            <small>{userLabel}</small>
          </div>
        </div>
      </section>

      {(errorMessage || statusMessage || isBusy) && (
        <section className="feedback-row">
          {errorMessage && <div className="alert error">{errorMessage}</div>}
          {statusMessage && <div className="alert success">{statusMessage}</div>}
          {isBusy && <div className="alert loading">Akon is working...</div>}
        </section>
      )}

      {!isAuthenticated ? (
        <section className="auth-layout">
          <form className="card auth-card" onSubmit={handleAuthSubmit}>
            <div className="card-header centered">
              <p className="eyebrow">Your space</p>
              <h2>{authMode === "login" ? "Welcome back" : "Create your Akon space"}</h2>
              <p>
                Sign in to continue your conversations, memories, and companion history.
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
                  : "Create space and enter"}
            </button>

            <button
              className="ghost-button"
              type="button"
              onClick={() =>
                setAuthMode((current) => (current === "login" ? "register" : "login"))
              }
            >
              {authMode === "login"
                ? "I need to create an account"
                : "I already have an account"}
            </button>
          </form>
        </section>
      ) : (
        <section className="workspace-grid">
          <section className="card chat-card">
            <div className="card-header horizontal">
              <div>
                <p className="eyebrow">Conversation</p>
                <h2>Talk with Akon</h2>
                <p>
                  Say what is true. Akon will help you slow it down and sort it out.
                </p>
                {activeConversationId && (
                  <small className="conversation-meta">
                    Continuing conversation {activeConversationId.slice(0, 8)}...
                  </small>
                )}
              </div>

              <div className="header-actions">
                <button
                  className="ghost-button"
                  type="button"
                  onClick={handleNewConversation}
                >
                  New conversation
                </button>
                <button className="ghost-button" type="button" onClick={handleLogout}>
                  Leave space
                </button>
              </div>
            </div>

            <div className="message-list">
              {messages.length === 0 ? (
                <div className="empty-conversation">
                  <div className="pulse-dot" />
                  <p>
                    Start with what is on your mind. You do not need to explain it perfectly.
                  </p>
                </div>
              ) : (
                messages.map((message, index) => (
                  <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                    <strong>{message.role === "user" ? "You" : "Akon"}</strong>
                    <p>{message.content}</p>
                    {message.safetyLevel && <small>Care level: {message.safetyLevel}</small>}
                  </article>
                ))
              )}

              {isChatLoading && (
                <article className="message assistant thinking">
                  <strong>Akon</strong>
                  <p>Thinking carefully...</p>
                </article>
              )}
            </div>

            <form className="chat-form" onSubmit={handleSendMessage}>
              <textarea
                value={chatInput}
                placeholder="Tell Akon what is going on..."
                onChange={(event) => setChatInput(event.target.value)}
              />
              <button disabled={isChatLoading || !chatInput.trim()} type="submit">
                {isChatLoading ? "Sending..." : "Send"}
              </button>
            </form>

            {memoryCandidates.length > 0 && (
              <div className="candidate-box">
                <h3>Akon noticed something it could remember</h3>
                {memoryCandidates.map((candidate, index) => (
                  <div className="mini-item warm" key={`${candidate.memory_type}-${index}`}>
                    <strong>{candidate.memory_type}</strong>
                    <p>{candidate.content}</p>
                    <small>{candidate.reason}</small>
                  </div>
                ))}
              </div>
            )}
          </section>

          <aside className="side-stack">
            <section className="card glow-card">
              <div className="card-header">
                <p className="eyebrow">Understanding</p>
                <h2>What Akon knows</h2>
                <p>Save only what you want Akon to remember.</p>
              </div>

              <form className="stack-form" onSubmit={handleCreateMemory}>
                <label>
                  Kind of understanding
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
                    placeholder="Example: I prefer direct, step-by-step guidance when I feel stuck."
                    onChange={(event) => setMemoryContent(event.target.value)}
                  />
                </label>

                <button disabled={isMemoryLoading || !memoryContent.trim()} type="submit">
                  {isMemoryLoading ? "Saving..." : "Save understanding"}
                </button>
              </form>

              <div className="scroll-list">
                {memories.length === 0 ? (
                  <p className="empty-state">No saved understanding yet.</p>
                ) : (
                  memories.map((memory) => (
                    <div className="mini-item" key={memory.id}>
                      <strong>{memory.memory_type}</strong>
                      <p>{memory.content}</p>
                      <small>
                        {memory.confidence} · {memory.sensitivity} · {memory.consent_state}
                      </small>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="card">
              <div className="card-header">
                <p className="eyebrow">Journey</p>
                <h2>Recent conversations</h2>
              </div>

              <div className="scroll-list">
                {conversations.length === 0 ? (
                  <p className="empty-state">Your conversation journey starts here.</p>
                ) : (
                  conversations.map((conversation) => (
                    <button
                      className={
                        conversation.id === activeConversationId
                          ? "list-button active"
                          : "list-button"
                      }
                      key={conversation.id}
                      type="button"
                      onClick={() => void handleConversationClick(conversation.id)}
                    >
                      <strong>{conversation.title || "Untitled conversation"}</strong>
                      <small>{conversation.safety_level || "No care level"}</small>
                    </button>
                  ))
                )}
              </div>
            </section>

            <section className="card">
              <div className="card-header">
                <p className="eyebrow">Trust trail</p>
                <h2>Recent activity</h2>
              </div>

              <div className="scroll-list">
                {auditLogs.length === 0 ? (
                  <p className="empty-state">No activity yet.</p>
                ) : (
                  auditLogs.slice(0, 10).map((auditLog) => (
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
        </section>
      )}
    </main>
  );
}

export default App;
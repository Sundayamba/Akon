import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";
import {
  clearStoredAccessToken,
  createMemory,
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
  ConversationSummary,
  MemoryCandidateItem,
  MemoryItem,
} from "./types";

type AuthMode = "login" | "register";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  safetyLevel?: string;
};

function App() {
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [token, setToken] = useState<string | null>(() => getStoredAccessToken());
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);

  const [email, setEmail] = useState("rex@example.com");
  const [password, setPassword] = useState("strongpassword123");
  const [displayName, setDisplayName] = useState("Rex");

  const [chatInput, setChatInput] = useState("");
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [memoryCandidates, setMemoryCandidates] = useState<MemoryCandidateItem[]>([]);

  const [memoryType, setMemoryType] = useState("preference");
  const [memoryContent, setMemoryContent] = useState("");
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isAuthenticated = Boolean(token && currentUser);

  const userLabel = useMemo(() => {
    if (!currentUser) {
      return "Guest";
    }

    return currentUser.display_name || currentUser.email;
  }, [currentUser]);

  useEffect(() => {
    async function restoreSession() {
      if (!token) {
        return;
      }

      try {
        const user = await getCurrentUser(token);
        setCurrentUser(user);
        await refreshWorkspace(token);
      } catch {
        clearStoredAccessToken();
        setToken(null);
        setCurrentUser(null);
      }
    }

    void restoreSession();
  }, [token]);

  async function refreshWorkspace(authToken = token) {
    if (!authToken) {
      return;
    }

    const [memoryList, conversationList, auditList] = await Promise.all([
      listMemories(authToken),
      listConversations(authToken),
      listAuditLogs(authToken),
    ]);

    setMemories(memoryList);
    setConversations(conversationList);
    setAuditLogs(auditList);
  }

  function resetFeedback() {
    setErrorMessage(null);
    setStatusMessage(null);
  }

  async function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();
    setIsLoading(true);

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

      storeAccessToken(login.access_token);
      setToken(login.access_token);
      setCurrentUser(login.user);
      await refreshWorkspace(login.access_token);
      setStatusMessage("Authenticated successfully.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleLogout() {
    clearStoredAccessToken();
    setToken(null);
    setCurrentUser(null);
    setMessages([]);
    setMemoryCandidates([]);
    setMemories([]);
    setConversations([]);
    setAuditLogs([]);
    setActiveConversationId(undefined);
    setStatusMessage("Logged out.");
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
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendChatMessage(
        token,
        trimmedMessage,
        activeConversationId,
      );

      setActiveConversationId(response.conversation_id);
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
      setErrorMessage(error instanceof Error ? error.message : "Chat request failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreateMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();

    if (!token || !memoryContent.trim()) {
      return;
    }

    setIsLoading(true);

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
      setStatusMessage("Memory saved.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Memory save failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Akon v0.2.4</p>
          <h1>Supportive AI Companion</h1>
          <p className="hero-copy">
            Authenticated chat, memory, conversations, and audit visibility wired
            to the real Akon backend.
          </p>
        </div>

        <div className="status-card">
          <span>Status</span>
          <strong>{isAuthenticated ? "Authenticated" : "Not signed in"}</strong>
          <small>{userLabel}</small>
        </div>
      </section>

      {(errorMessage || statusMessage) && (
        <section className="feedback-row">
          {errorMessage && <div className="alert error">{errorMessage}</div>}
          {statusMessage && <div className="alert success">{statusMessage}</div>}
        </section>
      )}

      {!isAuthenticated ? (
        <section className="auth-layout">
          <form className="card auth-card" onSubmit={handleAuthSubmit}>
            <div className="card-header">
              <p className="eyebrow">Auth</p>
              <h2>{authMode === "login" ? "Login" : "Create account"}</h2>
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

            <button disabled={isLoading} type="submit">
              {isLoading
                ? "Working..."
                : authMode === "login"
                  ? "Login"
                  : "Register and login"}
            </button>

            <button
              className="ghost-button"
              type="button"
              onClick={() =>
                setAuthMode((current) => (current === "login" ? "register" : "login"))
              }
            >
              Switch to {authMode === "login" ? "register" : "login"}
            </button>
          </form>
        </section>
      ) : (
        <section className="workspace-grid">
          <section className="card chat-card">
            <div className="card-header horizontal">
              <div>
                <p className="eyebrow">Chat</p>
                <h2>Akon conversation</h2>
              </div>
              <button className="ghost-button" type="button" onClick={handleLogout}>
                Logout
              </button>
            </div>

            <div className="message-list">
              {messages.length === 0 ? (
                <p className="empty-state">
                  Start a conversation. Akon will respond through the real backend.
                </p>
              ) : (
                messages.map((message, index) => (
                  <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                    <strong>{message.role === "user" ? "You" : "Akon"}</strong>
                    <p>{message.content}</p>
                    {message.safetyLevel && <small>Safety: {message.safetyLevel}</small>}
                  </article>
                ))
              )}
            </div>

            <form className="chat-form" onSubmit={handleSendMessage}>
              <textarea
                value={chatInput}
                placeholder="Tell Akon what is going on..."
                onChange={(event) => setChatInput(event.target.value)}
              />
              <button disabled={isLoading || !chatInput.trim()} type="submit">
                Send
              </button>
            </form>

            {memoryCandidates.length > 0 && (
              <div className="candidate-box">
                <h3>Memory candidates</h3>
                {memoryCandidates.map((candidate, index) => (
                  <div className="mini-item" key={`${candidate.memory_type}-${index}`}>
                    <strong>{candidate.memory_type}</strong>
                    <p>{candidate.content}</p>
                    <small>{candidate.reason}</small>
                  </div>
                ))}
              </div>
            )}
          </section>

          <aside className="side-stack">
            <section className="card">
              <div className="card-header">
                <p className="eyebrow">Memory</p>
                <h2>Save memory</h2>
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
                  Content
                  <textarea
                    value={memoryContent}
                    placeholder="Example: User prefers direct, step-by-step guidance."
                    onChange={(event) => setMemoryContent(event.target.value)}
                  />
                </label>

                <button disabled={isLoading || !memoryContent.trim()} type="submit">
                  Save memory
                </button>
              </form>

              <div className="scroll-list">
                {memories.map((memory) => (
                  <div className="mini-item" key={memory.id}>
                    <strong>{memory.memory_type}</strong>
                    <p>{memory.content}</p>
                    <small>
                      {memory.confidence} · {memory.sensitivity} · {memory.consent_state}
                    </small>
                  </div>
                ))}
              </div>
            </section>

            <section className="card">
              <div className="card-header">
                <p className="eyebrow">Conversations</p>
                <h2>Recent</h2>
              </div>

              <div className="scroll-list">
                {conversations.length === 0 ? (
                  <p className="empty-state">No conversations yet.</p>
                ) : (
                  conversations.map((conversation) => (
                    <button
                      className="list-button"
                      key={conversation.id}
                      type="button"
                      onClick={() => setActiveConversationId(conversation.id)}
                    >
                      <strong>{conversation.title || "Untitled conversation"}</strong>
                      <small>{conversation.safety_level || "No safety level"}</small>
                    </button>
                  ))
                )}
              </div>
            </section>

            <section className="card">
              <div className="card-header">
                <p className="eyebrow">Audit</p>
                <h2>Latest events</h2>
              </div>

              <div className="scroll-list">
                {auditLogs.length === 0 ? (
                  <p className="empty-state">No audit logs yet.</p>
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
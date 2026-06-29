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
      setStatusMessage("Welcome in. Akon is ready to listen.");
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
    setStatusMessage("You are signed out.");
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
      setStatusMessage("Akon saved that understanding.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Memory save failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <div className="ambient-orb orb-one" />
      <div className="ambient-orb orb-two" />
      <div className="ambient-orb orb-three" />

      <section className="hero-panel">
        <div className="hero-content">
          <p className="eyebrow">Akon companion preview · v0.2.5</p>
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

      {(errorMessage || statusMessage) && (
        <section className="feedback-row">
          {errorMessage && <div className="alert error">{errorMessage}</div>}
          {statusMessage && <div className="alert success">{statusMessage}</div>}
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

            <button disabled={isLoading} type="submit">
              {isLoading
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
                <p>Say what is true. Akon will help you slow it down and sort it out.</p>
              </div>
              <button className="ghost-button" type="button" onClick={handleLogout}>
                Leave space
              </button>
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

                <button disabled={isLoading || !memoryContent.trim()} type="submit">
                  Save understanding
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
                      className="list-button"
                      key={conversation.id}
                      type="button"
                      onClick={() => setActiveConversationId(conversation.id)}
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
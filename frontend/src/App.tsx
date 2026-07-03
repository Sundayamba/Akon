import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import ChatComposer from "./components/ChatComposer";
import MessageContent from "./components/MessageContent";
import "./App.css";
import "./components/WorkspacePolish.css";
import {
  AUTH_EXPIRED_EVENT,
  ApiRequestError,
  clearStoredAccessToken,
  confirmMemoryCandidate,
  createMemory,
  deleteConversation,
  deleteMemory,
  getApiErrorMessage,
  getConversation,
  getCurrentUser,
  getStoredAccessToken,
  isAiProviderUnavailableError,
  isRequestAbortedError,
  listAuditLogs,
  listConversations,
  listMemories,
  loginUser,
  reflectOnConversation,
  regenerateAssistantReply,
  registerUser,
  revokeMemory,
  sendChatMessage,
  storeAccessToken,
  submitMessageFeedback,
  updateConversationTitle,
  updateMemory,
} from "./lib/api";
import type {
  AuditLog,
  AuthUser,
  ChatResponse,
  ConversationDetail,
  ConversationReflectionResponse,
  ConversationSummary,
  FeedbackRating,
  GroundingToolItem,
  MemoryCandidateItem,
  MemoryItem,
} from "./types";

type AuthMode = "login" | "register";

type ChatMessage = {
  id?: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  safetyLevel?: string | null;
  detectedEmotion?: string | null;
  groundingTool?: GroundingToolItem | null;
  feedbackRating?: FeedbackRating | null;
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

const CONTINUE_RESPONSE_PROMPT =
  "Please continue from your previous response without repeating what you already wrote.";

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
      "I'm having trouble reaching my AI provider right now. " +
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
    id: message.id,
    role: message.role === "assistant" ? "assistant" : "user",
    content: message.content,
    createdAt: message.created_at,
    safetyLevel: message.safety_level,
    detectedEmotion: message.detected_emotion,
    groundingTool: null,
    feedbackRating: message.feedback_rating,
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

function getLastUserMessage(messages: ChatMessage[]): ChatMessage | undefined {
  return [...messages].reverse().find((message) => message.role === "user");
}

function App() {
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const conversationOpenRequestRef = useRef(0);
  const chatRequestIdRef = useRef(0);
  const conversationAbortControllerRef = useRef<AbortController | null>(null);
  const chatAbortControllerRef = useRef<AbortController | null>(null);

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
  const [conversationSearch, setConversationSearch] = useState("");
  const [renamingConversationId, setRenamingConversationId] = useState<string | null>(
    null,
  );
  const [renameInput, setRenameInput] = useState("");
  const [conversationActionId, setConversationActionId] = useState<string | null>(null);

  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  const [conversationReflection, setConversationReflection] =
    useState<ConversationReflectionResponse | null>(null);
  const [copiedMessageKey, setCopiedMessageKey] = useState<string | null>(null);
  const [feedbackActionMessageId, setFeedbackActionMessageId] = useState<string | null>(
    null,
  );
  const [feedbackNoteMessageId, setFeedbackNoteMessageId] = useState<string | null>(
    null,
  );
  const [feedbackNoteInput, setFeedbackNoteInput] = useState("");

  const [isHistoryPanelOpen, setIsHistoryPanelOpen] = useState(false);
  const [isContextPanelOpen, setIsContextPanelOpen] = useState(false);

  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatActivityLabel, setChatActivityLabel] = useState<string | null>(null);
  const [isMemoryLoading, setIsMemoryLoading] = useState(false);
  const [isReflectionLoading, setIsReflectionLoading] = useState(false);
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
    isReflectionLoading ||
    isWorkspaceLoading ||
    candidateActionIndex !== null ||
    conversationActionId !== null ||
    feedbackActionMessageId !== null ||
    memoryActionId !== null;

  const shellClassName = [
    "product-shell",
    isHistoryPanelOpen ? "" : "history-collapsed",
    isContextPanelOpen ? "" : "context-collapsed",
  ]
    .filter(Boolean)
    .join(" ");

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

  const filteredConversations = useMemo(() => {
    const normalizedSearch = conversationSearch.trim().toLowerCase();

    if (!normalizedSearch) {
      return conversations;
    }

    return conversations.filter((conversation) =>
      (conversation.title || "Untitled conversation")
        .toLowerCase()
        .includes(normalizedSearch),
    );
  }, [conversationSearch, conversations]);

  const activeMemoryCount = memories.filter(
    (memory) => memory.consent_state !== "revoked",
  ).length;

  const canReflectOnConversation = Boolean(
    token && activeConversationId && messages.length >= 2 && !isReflectionLoading,
  );

  function cancelPendingConversationOpen() {
    conversationOpenRequestRef.current += 1;
    conversationAbortControllerRef.current?.abort();
    conversationAbortControllerRef.current = null;
    setOpeningConversationId(null);
    setIsWorkspaceLoading(false);
  }

  function clearActiveChatController(requestId: number) {
    if (chatRequestIdRef.current === requestId) {
      chatAbortControllerRef.current = null;
    }
  }

  function cancelActiveChatRequest(status = "Generation stopped. You can send a new message.") {
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = null;
    chatRequestIdRef.current += 1;
    setIsChatLoading(false);
    setChatActivityLabel(null);
    setStatusMessage(status);
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
  }, [messages, isChatLoading, conversationReflection]);

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

    conversationAbortControllerRef.current?.abort();

    const abortController = new AbortController();
    conversationAbortControllerRef.current = abortController;

    setIsWorkspaceLoading(true);
    setOpeningConversationId(conversationId);
    setActiveConversationId(conversationId);
    setMessages([]);
    setMemoryCandidates([]);
    setConversationReflection(null);
    setRenamingConversationId(null);
    setRenameInput("");
    resetFeedback();

    try {
      const conversation = await getConversation(
        authToken,
        conversationId,
        abortController.signal,
      );

      if (conversationOpenRequestRef.current !== requestId) {
        return;
      }

      setActiveConversationId(conversation.id);
      storeActiveConversationId(conversation.id);
      setMessages(mapConversationToMessages(conversation));
      setMemoryCandidates([]);
      setConversationReflection(null);
      setIsHistoryPanelOpen(false);

      if (shouldSetStatus) {
        setStatusMessage("Conversation reopened.");
      }
    } catch (error) {
      if (
        conversationOpenRequestRef.current !== requestId ||
        isRequestAbortedError(error)
      ) {
        return;
      }

      clearActiveConversationId();
      setActiveConversationId(undefined);
      setErrorMessage(formatErrorMessage(error));
    } finally {
      if (conversationOpenRequestRef.current === requestId) {
        conversationAbortControllerRef.current = null;
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
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = null;
    chatRequestIdRef.current += 1;
    setIsChatLoading(false);
    setChatActivityLabel(null);
    clearStoredAccessToken();
    clearActiveConversationId();
    setToken(null);
    setCurrentUser(null);
    setMessages([]);
    setMemoryCandidates([]);
    setMemories([]);
    setMemoryEditState(null);
    setConversations([]);
    setConversationSearch("");
    setRenamingConversationId(null);
    setRenameInput("");
    setConversationActionId(null);
    setAuditLogs([]);
    setConversationReflection(null);
    setActiveConversationId(undefined);
    setOpeningConversationId(null);
    setFeedbackNoteMessageId(null);
    setFeedbackNoteInput("");
    setIsHistoryPanelOpen(false);
    setIsContextPanelOpen(false);
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
      setConversationReflection(null);
      setConversationSearch("");
      setRenamingConversationId(null);
      setRenameInput("");
      setConversationActionId(null);
      setFeedbackNoteMessageId(null);
      setFeedbackNoteInput("");
      setIsHistoryPanelOpen(false);
      setIsContextPanelOpen(false);

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
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = null;
    chatRequestIdRef.current += 1;
    setIsChatLoading(false);
    setChatActivityLabel(null);
    clearActiveConversationId();
    setActiveConversationId(undefined);
    setMessages([]);
    setMemoryCandidates([]);
    setConversationReflection(null);
    setRenamingConversationId(null);
    setRenameInput("");
    setFeedbackNoteMessageId(null);
    setFeedbackNoteInput("");
    setChatInput("");
    setIsHistoryPanelOpen(false);
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

  function handleBeginRenameConversation(conversation: ConversationSummary) {
    resetFeedback();
    setRenamingConversationId(conversation.id);
    setRenameInput(conversation.title || "Untitled conversation");
  }

  function handleCancelRenameConversation() {
    setRenamingConversationId(null);
    setRenameInput("");
  }

  async function handleSubmitRenameConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();

    if (!token || !renamingConversationId || !renameInput.trim()) {
      return;
    }

    setConversationActionId(renamingConversationId);

    try {
      const updatedConversation = await updateConversationTitle(
        token,
        renamingConversationId,
        renameInput.trim(),
      );

      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === updatedConversation.id ? updatedConversation : conversation,
        ),
      );

      setRenamingConversationId(null);
      setRenameInput("");
      setStatusMessage("Conversation renamed.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setConversationActionId(null);
    }
  }

  async function handleDeleteConversation(conversation: ConversationSummary) {
    if (!token) {
      return;
    }

    const shouldDelete = window.confirm(
      `Delete "${conversation.title || "Untitled conversation"}"? This cannot be undone.`,
    );

    if (!shouldDelete) {
      return;
    }

    resetFeedback();
    setConversationActionId(conversation.id);

    try {
      await deleteConversation(token, conversation.id);

      setConversations((current) =>
        current.filter((currentConversation) => currentConversation.id !== conversation.id),
      );

      if (activeConversationId === conversation.id) {
        clearActiveConversationId();
        setActiveConversationId(undefined);
        setMessages([]);
        setMemoryCandidates([]);
        setConversationReflection(null);
        setChatInput("");
      }

      if (renamingConversationId === conversation.id) {
        setRenamingConversationId(null);
        setRenameInput("");
      }

      setStatusMessage("Conversation deleted.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setConversationActionId(null);
    }
  }

  async function sendMessageText(
    messageText: string,
    activityLabel = "Thinking",
  ) {
    if (!token || !messageText.trim() || isChatLoading) {
      return;
    }

    const trimmedMessage = messageText.trim();

    const userMessage: ChatMessage = {
      role: "user",
      content: trimmedMessage,
      createdAt: new Date().toISOString(),
    };

    setMessages((current) => [...current, userMessage]);
    setChatInput("");
    setConversationReflection(null);
    setFeedbackNoteMessageId(null);
    setFeedbackNoteInput("");
    setIsChatLoading(true);
    setChatActivityLabel(activityLabel);

    const requestId = chatRequestIdRef.current + 1;
    chatRequestIdRef.current = requestId;

    chatAbortControllerRef.current?.abort();

    const abortController = new AbortController();
    chatAbortControllerRef.current = abortController;

    try {
      const response: ChatResponse = await sendChatMessage(
        token,
        trimmedMessage,
        activeConversationId,
        abortController.signal,
      );

      if (chatRequestIdRef.current !== requestId) {
        return;
      }

      setActiveConversationId(response.conversation_id);
      storeActiveConversationId(response.conversation_id);
      setMemoryCandidates(response.memory_candidates);

      setMessages((current) => [
        ...current,
        {
          id: response.assistant_message_id,
          role: "assistant",
          content: response.reply,
          createdAt: new Date().toISOString(),
          safetyLevel: response.safety_level,
          detectedEmotion: response.detected_emotion,
          groundingTool: response.grounding_tool,
          feedbackRating: null,
        },
      ]);

      await refreshWorkspace(token);
    } catch (error) {
      if (
        chatRequestIdRef.current !== requestId ||
        isRequestAbortedError(error)
      ) {
        return;
      }

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
      clearActiveChatController(requestId);

      if (chatRequestIdRef.current === requestId) {
        setIsChatLoading(false);
        setChatActivityLabel(null);
      }
    }
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resetFeedback();

    await sendMessageText(chatInput, "Thinking");
  }

  function handleStopGenerating() {
    if (!isChatLoading) {
      return;
    }

    cancelActiveChatRequest();
  }

  async function handleRetryLastUserMessage() {
    const lastUserMessage = getLastUserMessage(messages);

    if (!lastUserMessage) {
      setStatusMessage("There is no previous user message to retry.");
      return;
    }

    resetFeedback();
    await sendMessageText(lastUserMessage.content, "Retrying");
  }

  async function handleRegenerateAssistantMessage(message: ChatMessage) {
    if (!token || !message.id || message.role !== "assistant" || isChatLoading) {
      return;
    }

    resetFeedback();
    setConversationReflection(null);
    setFeedbackNoteMessageId(null);
    setFeedbackNoteInput("");
    setIsChatLoading(true);
    setChatActivityLabel("Regenerating");

    const requestId = chatRequestIdRef.current + 1;
    chatRequestIdRef.current = requestId;

    chatAbortControllerRef.current?.abort();

    const abortController = new AbortController();
    chatAbortControllerRef.current = abortController;

    try {
      const response = await regenerateAssistantReply(
        token,
        message.id,
        abortController.signal,
      );

      if (chatRequestIdRef.current !== requestId) {
        return;
      }

      setActiveConversationId(response.conversation_id);
      storeActiveConversationId(response.conversation_id);

      setMessages((current) => [
        ...current,
        {
          id: response.assistant_message_id,
          role: "assistant",
          content: response.reply,
          createdAt: new Date().toISOString(),
          safetyLevel: response.safety_level,
          detectedEmotion: response.detected_emotion,
          groundingTool: response.grounding_tool,
          feedbackRating: null,
        },
      ]);

      setStatusMessage("Akon regenerated that reply.");
      await refreshWorkspace(token);
    } catch (error) {
      if (
        chatRequestIdRef.current !== requestId ||
        isRequestAbortedError(error)
      ) {
        return;
      }

      setErrorMessage(formatErrorMessage(error));
    } finally {
      clearActiveChatController(requestId);

      if (chatRequestIdRef.current === requestId) {
        setIsChatLoading(false);
        setChatActivityLabel(null);
      }
    }
  }

  async function handleContinueResponse() {
    resetFeedback();
    await sendMessageText(CONTINUE_RESPONSE_PROMPT, "Continuing");
  }

  function handleBeginNotHelpfulFeedback(messageId: string) {
    resetFeedback();
    setFeedbackNoteMessageId(messageId);
    setFeedbackNoteInput("");
  }

  function handleCancelFeedbackNote() {
    setFeedbackNoteMessageId(null);
    setFeedbackNoteInput("");
  }

  async function handleSubmitFeedback(
    messageId: string,
    rating: FeedbackRating,
    note?: string,
  ) {
    if (!token || feedbackActionMessageId) {
      return;
    }

    resetFeedback();
    setFeedbackActionMessageId(messageId);

    try {
      const feedback = await submitMessageFeedback(token, messageId, rating, note);

      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                feedbackRating: feedback.rating,
              }
            : message,
        ),
      );

      setFeedbackNoteMessageId(null);
      setFeedbackNoteInput("");

      setStatusMessage(
        rating === "helpful"
          ? "Thanks. Akon will remember that this reply was helpful."
          : "Thanks. Akon will use that feedback to improve.",
      );

      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setFeedbackActionMessageId(null);
    }
  }

  async function handleReflectOnConversation() {
    if (!token || !activeConversationId || isReflectionLoading) {
      return;
    }

    resetFeedback();
    setIsReflectionLoading(true);

    try {
      const reflection = await reflectOnConversation(token, activeConversationId);
      setConversationReflection(reflection);
      setStatusMessage("Conversation reflection generated.");
      await refreshWorkspace(token);
    } catch (error) {
      setErrorMessage(formatErrorMessage(error));
    } finally {
      setIsReflectionLoading(false);
    }
  }

  async function handleCopyMessage(messageKey: string, content: string) {
    resetFeedback();

    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageKey(messageKey);
      setStatusMessage("Copied.");

      window.setTimeout(() => {
        setCopiedMessageKey((current) => (current === messageKey ? null : current));
      }, 1600);
    } catch {
      setErrorMessage("Could not copy this message. Please copy it manually.");
    }
  }

  async function handleShareMessage(content: string) {
    resetFeedback();

    try {
      if ("share" in navigator && typeof navigator.share === "function") {
        await navigator.share({
          text: content,
        });
        setStatusMessage("Share sheet opened.");
        return;
      }

      await navigator.clipboard.writeText(content);
      setStatusMessage("Copied for sharing.");
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }

      setErrorMessage("Could not share this message.");
    }
  }

  function handleMoreMessageAction() {
    resetFeedback();
    setStatusMessage("More message actions will be added in a later milestone.");
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
              <p className="eyebrow">Akon AI - v0.4.9</p>
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
    <main className={shellClassName}>
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
            <span>History</span>
            {isWorkspaceLoading && <small>Syncing...</small>}
          </div>

          <input
            className="sidebar-search-input"
            value={conversationSearch}
            placeholder="Search conversations..."
            onChange={(event) => setConversationSearch(event.target.value)}
          />

          <div className="conversation-list">
            {filteredConversations.length === 0 ? (
              <div className="sidebar-empty-card">
                <p>
                  {conversationSearch.trim()
                    ? "No conversations match your search."
                    : "No conversations yet."}
                </p>
              </div>
            ) : (
              filteredConversations.map((conversation) => {
                const isRenaming = renamingConversationId === conversation.id;
                const isActing = conversationActionId === conversation.id;

                if (isRenaming) {
                  return (
                    <form
                      className="rename-card"
                      key={conversation.id}
                      onSubmit={handleSubmitRenameConversation}
                    >
                      <label>
                        Rename chat
                        <input
                          value={renameInput}
                          autoFocus
                          maxLength={120}
                          onChange={(event) => setRenameInput(event.target.value)}
                        />
                      </label>

                      <div className="rename-actions">
                        <button disabled={isActing || !renameInput.trim()} type="submit">
                          {isActing ? "Saving..." : "Save"}
                        </button>
                        <button
                          className="ghost-button"
                          disabled={isActing}
                          type="button"
                          onClick={handleCancelRenameConversation}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  );
                }

                return (
                  <div
                    className={
                      conversation.id === activeConversationId
                        ? "conversation-row active"
                        : "conversation-row"
                    }
                    key={conversation.id}
                  >
                    <button
                      className="conversation-item"
                      type="button"
                      aria-current={
                        conversation.id === activeConversationId ? "true" : undefined
                      }
                      onClick={() => void handleConversationClick(conversation.id)}
                    >
                      <span className="history-title-line">
                        <span className="history-dot" />
                        <strong className="history-title">
                          {conversation.title || "Untitled conversation"}
                        </strong>
                      </span>

                      <span className="history-meta">
                        <span className="history-pill">
                          {conversation.safety_level || "Normal"}
                        </span>
                        <span>{formatConversationDate(conversation.created_at)}</span>
                      </span>
                    </button>

                    <div className="conversation-action-row">
                      <button
                        className="conversation-action-button"
                        disabled={Boolean(conversationActionId)}
                        type="button"
                        aria-label="Rename conversation"
                        title="Rename"
                        onClick={() => handleBeginRenameConversation(conversation)}
                      >
                        {"\u270e"}
                      </button>
                      <button
                        className="conversation-action-button danger"
                        disabled={Boolean(conversationActionId)}
                        type="button"
                        aria-label="Delete conversation"
                        title="Delete"
                        onClick={() => void handleDeleteConversation(conversation)}
                      >
                        {isActing ? "\u2026" : "\u00d7"}
                      </button>
                    </div>
                  </div>
                );
              })
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

          <div className="topbar-actions">
            <div className="panel-toggle-row">
              <button
                className={
                  isHistoryPanelOpen
                    ? "panel-toggle-button active"
                    : "panel-toggle-button"
                }
                type="button"
                onClick={() => setIsHistoryPanelOpen((current) => !current)}
              >
                History
              </button>

              <button
                className={
                  isContextPanelOpen
                    ? "panel-toggle-button active"
                    : "panel-toggle-button"
                }
                type="button"
                onClick={() => setIsContextPanelOpen((current) => !current)}
              >
                Memory
              </button>
            </div>

            <div className="workspace-metrics" aria-label="Workspace metrics">
              <span>{conversations.length} chats</span>
              <span>{activeMemoryCount} memories</span>
              <span>{auditLogs.length} activities</span>
            </div>

            <button
              className="ghost-button compact-button"
              disabled={!canReflectOnConversation}
              type="button"
              onClick={() => void handleReflectOnConversation()}
            >
              {isReflectionLoading ? "Reflecting..." : "Reflect"}
            </button>

            <button
              className="ghost-button compact-button"
              disabled={isChatLoading || !getLastUserMessage(messages)}
              type="button"
              onClick={() => void handleRetryLastUserMessage()}
            >
              {"\u21bb"}
            </button>
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
              <>
                {conversationReflection && (
                  <section className="reflection-card">
                    <span>Conversation reflection</span>
                    <h3>{conversationReflection.title}</h3>
                    <p>{conversationReflection.summary}</p>

                    <div className="reflection-next-step">
                      <strong>Suggested next step</strong>
                      <p>{conversationReflection.supportive_next_step}</p>
                    </div>

                    <small>
                      {conversationReflection.message_count} messages
                      {conversationReflection.dominant_emotion
                        ? ` - ${conversationReflection.dominant_emotion}`
                        : ""}
                    </small>
                  </section>
                )}

                {messages.map((message, index) => {
                  const messageKey = message.id || `${message.role}-${index}`;
                  const canGiveFeedback = message.role === "assistant" && Boolean(message.id);
                  const canUseAssistantActions =
                    message.role === "assistant" && Boolean(message.id);

                  return (
                    <article className={`message ${message.role}`} key={messageKey}>
                      <div className="message-heading">
                        <strong>{message.role === "user" ? "You" : "Akon"}</strong>

                        <div className="message-actions">
                          <button
                            className="message-action-button icon-only-action"
                            type="button"
                            aria-label="Copy message"
                            title="Copy"
                            onClick={() => void handleCopyMessage(messageKey, message.content)}
                          >
                            {copiedMessageKey === messageKey ? "\u2713" : "\u29c9"}
                          </button>

                          <button
                            className="message-action-button icon-only-action"
                            type="button"
                            aria-label="Share message"
                            title="Share"
                            onClick={() => void handleShareMessage(message.content)}
                          >
                            {"\u2197"}
                          </button>

                          {canUseAssistantActions && (
                            <>
                              <button
                                className="message-action-button icon-only-action"
                                disabled={isChatLoading}
                                type="button"
                                aria-label="Regenerate response"
                                title="Regenerate"
                                onClick={() => void handleRegenerateAssistantMessage(message)}
                              >
                                {"\u21bb"}
                              </button>

                              <button
                                className="message-action-button icon-only-action"
                                disabled={isChatLoading}
                                type="button"
                                aria-label="Continue response"
                                title="Continue"
                                onClick={() => void handleContinueResponse()}
                              >
                                {"\u21aa"}
                              </button>
                            </>
                          )}

                          <button
                            className="message-action-button icon-only-action"
                            type="button"
                            aria-label="More actions"
                            title="More"
                            onClick={handleMoreMessageAction}
                          >
                            {"\u22ef"}
                          </button>
                        </div>
                      </div>

                      <MessageContent content={message.content} />

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

                      {message.role === "assistant" && message.groundingTool && (
                        <div className="message-grounding">
                          <span>Grounding tool</span>
                          <strong>{message.groundingTool.name}</strong>
                          <p>{message.groundingTool.instruction}</p>
                        </div>
                      )}

                      {canGiveFeedback && (
                        <div className="message-quality">
                          <div className="quality-actions">
                            <button
                              className={
                                message.feedbackRating === "helpful"
                                  ? "quality-button selected"
                                  : "quality-button"
                              }
                              disabled={feedbackActionMessageId !== null}
                              type="button"
                              aria-label="Helpful"
                              title="Helpful"
                              onClick={() =>
                                void handleSubmitFeedback(message.id as string, "helpful")
                              }
                            >
                              {"\u{1F44D}"}
                            </button>

                            <button
                              className={
                                message.feedbackRating === "not_helpful"
                                  ? "quality-button selected"
                                  : "quality-button"
                              }
                              disabled={feedbackActionMessageId !== null}
                              type="button"
                              aria-label="Not helpful"
                              title="Not helpful"
                              onClick={() =>
                                handleBeginNotHelpfulFeedback(message.id as string)
                              }
                            >
                              {"\u{1F44E}"}
                            </button>
                          </div>

                          {feedbackNoteMessageId === message.id && (
                            <form
                              className="stack-form"
                              onSubmit={(event) => {
                                event.preventDefault();
                                void handleSubmitFeedback(
                                  message.id as string,
                                  "not_helpful",
                                  feedbackNoteInput,
                                );
                              }}
                            >
                              <label>
                                Optional note
                                <textarea
                                  value={feedbackNoteInput}
                                  maxLength={1000}
                                  placeholder="What could Akon improve in this reply?"
                                  onChange={(event) =>
                                    setFeedbackNoteInput(event.target.value)
                                  }
                                />
                              </label>

                              <div className="quality-actions">
                                <button
                                  disabled={feedbackActionMessageId !== null}
                                  type="submit"
                                >
                                  Send
                                </button>
                                <button
                                  className="ghost-button"
                                  disabled={feedbackActionMessageId !== null}
                                  type="button"
                                  onClick={handleCancelFeedbackNote}
                                >
                                  Cancel
                                </button>
                              </div>
                            </form>
                          )}
                        </div>
                      )}
                    </article>
                  );
                })}
              </>
            )}

            {isChatLoading && (
              <article className="message assistant thinking">
                <strong>Akon</strong>
                <p>{chatActivityLabel || "Thinking"}...</p>
              </article>
            )}
          </div>

          <ChatComposer
            value={chatInput}
            isLoading={isChatLoading}
            activityLabel={chatActivityLabel}
            onChange={setChatInput}
            onSubmit={handleSendMessage}
            onStop={handleStopGenerating}
            onKeyDown={handleChatInputKeyDown}
          />
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
                      {memory.confidence} - {memory.sensitivity} -{" "}
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

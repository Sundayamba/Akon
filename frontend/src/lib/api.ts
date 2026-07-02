import type {
  ApiErrorResponse,
  AuditLog,
  AuthUser,
  ChatResponse,
  ConversationDeleteResponse,
  ConversationDetail,
  ConversationReflectionResponse,
  ConversationSummary,
  MemoryCandidateItem,
  MemoryItem,
  MessageFeedbackResponse,
  TokenResponse,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

const ACCESS_TOKEN_KEY = "akon_access_token";

export const AUTH_EXPIRED_EVENT = "akon_auth_expired";

export const AI_PROVIDER_UNAVAILABLE_MESSAGE =
  "Akon is having trouble reaching its AI provider right now. Please try again shortly.";

export const NETWORK_UNAVAILABLE_MESSAGE =
  "Akon could not connect to the server. Please check your connection and try again.";

export class ApiRequestError extends Error {
  status: number;
  code?: string;
  requestId?: string;
  details?: unknown;
  isRetryable: boolean;

  constructor(params: {
    message: string;
    status: number;
    code?: string;
    requestId?: string;
    details?: unknown;
    isRetryable?: boolean;
  }) {
    super(params.message);
    this.name = "ApiRequestError";
    this.status = params.status;
    this.code = params.code;
    this.requestId = params.requestId;
    this.details = params.details;
    this.isRetryable = params.isRetryable ?? false;
  }
}

export function isApiRequestError(error: unknown): error is ApiRequestError {
  return error instanceof ApiRequestError;
}

export function isAiProviderUnavailableError(error: unknown): boolean {
  return isApiRequestError(error) && error.status === 503;
}

export function getApiErrorMessage(
  error: unknown,
  fallbackMessage = "Something went wrong. Please try again.",
): string {
  if (isAiProviderUnavailableError(error)) {
    return AI_PROVIDER_UNAVAILABLE_MESSAGE;
  }

  if (isApiRequestError(error)) {
    return error.message || fallbackMessage;
  }

  if (error instanceof TypeError) {
    return NETWORK_UNAVAILABLE_MESSAGE;
  }

  if (error instanceof Error) {
    return error.message || fallbackMessage;
  }

  return fallbackMessage;
}

export function getStoredAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function storeAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearStoredAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

function dispatchAuthExpired(): void {
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

function isRetryableStatus(status: number): boolean {
  return status === 408 || status === 409 || status === 425 || status === 429 || status >= 500;
}

async function parseJsonResponse<T>(
  response: Response,
  hadAuthToken: boolean,
): Promise<T> {
  const rawText = await response.text();

  let data: unknown = null;

  if (rawText) {
    try {
      data = JSON.parse(rawText);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const errorPayload = data as ApiErrorResponse | null;
    const error = errorPayload?.error;

    if (hadAuthToken && response.status === 401) {
      clearStoredAccessToken();
      dispatchAuthExpired();
    }

    throw new ApiRequestError({
      message: error?.message || `Request failed with status ${response.status}.`,
      status: response.status,
      code: error?.code,
      requestId: error?.request_id,
      details: error?.details,
      isRetryable: isRetryableStatus(response.status),
    });
  }

  return data as T;
}

type ApiRequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  token?: string | null;
  body?: unknown;
};

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method || "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch (error) {
    throw new ApiRequestError({
      message: NETWORK_UNAVAILABLE_MESSAGE,
      status: 0,
      code: "network_error",
      details: error,
      isRetryable: true,
    });
  }

  return parseJsonResponse<T>(response, Boolean(options.token));
}

export async function registerUser(payload: {
  email: string;
  password: string;
  display_name?: string;
}): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/register", {
    method: "POST",
    body: payload,
  });
}

export async function loginUser(payload: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: payload,
  });
}

export async function getCurrentUser(token: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me", {
    token,
  });
}

export async function sendChatMessage(
  token: string,
  message: string,
  conversationId?: string,
): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chat/message", {
    method: "POST",
    token,
    body: {
      message,
      conversation_id: conversationId || null,
    },
  });
}

export async function regenerateAssistantReply(
  token: string,
  messageId: string,
): Promise<ChatResponse> {
  return apiRequest<ChatResponse>(`/chat/messages/${messageId}/regenerate`, {
    method: "POST",
    token,
  });
}

export async function submitMessageFeedback(
  token: string,
  messageId: string,
  rating: "helpful" | "not_helpful",
  note?: string,
): Promise<MessageFeedbackResponse> {
  return apiRequest<MessageFeedbackResponse>(`/chat/messages/${messageId}/feedback`, {
    method: "POST",
    token,
    body: {
      rating,
      note: note?.trim() || null,
    },
  });
}

export async function reflectOnConversation(
  token: string,
  conversationId: string,
): Promise<ConversationReflectionResponse> {
  return apiRequest<ConversationReflectionResponse>(
    `/chat/conversations/${conversationId}/reflection`,
    {
      method: "POST",
      token,
    },
  );
}

export async function listConversations(
  token: string,
): Promise<ConversationSummary[]> {
  return apiRequest<ConversationSummary[]>("/chat/conversations", {
    token,
  });
}

export async function getConversation(
  token: string,
  conversationId: string,
): Promise<ConversationDetail> {
  return apiRequest<ConversationDetail>(`/chat/conversations/${conversationId}`, {
    token,
  });
}

export async function updateConversationTitle(
  token: string,
  conversationId: string,
  title: string,
): Promise<ConversationSummary> {
  return apiRequest<ConversationSummary>(`/chat/conversations/${conversationId}`, {
    method: "PATCH",
    token,
    body: {
      title,
    },
  });
}

export async function deleteConversation(
  token: string,
  conversationId: string,
): Promise<ConversationDeleteResponse> {
  return apiRequest<ConversationDeleteResponse>(`/chat/conversations/${conversationId}`, {
    method: "DELETE",
    token,
  });
}

export async function listMemories(token: string): Promise<MemoryItem[]> {
  return apiRequest<MemoryItem[]>("/memory", {
    token,
  });
}

export async function createMemory(
  token: string,
  payload: {
    memory_type: string;
    content: string;
    source: string;
    confidence: string;
    sensitivity: string;
    consent_state: string;
  },
): Promise<MemoryItem> {
  return apiRequest<MemoryItem>("/memory", {
    method: "POST",
    token,
    body: payload,
  });
}

export async function updateMemory(
  token: string,
  memoryId: string,
  payload: {
    memory_type?: string;
    content?: string;
    source?: string;
    confidence?: string;
    sensitivity?: string;
    consent_state?: string;
  },
): Promise<MemoryItem> {
  return apiRequest<MemoryItem>(`/memory/${memoryId}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function revokeMemory(
  token: string,
  memoryId: string,
): Promise<MemoryItem> {
  return apiRequest<MemoryItem>(`/memory/${memoryId}/revoke`, {
    method: "POST",
    token,
  });
}

export async function deleteMemory(
  token: string,
  memoryId: string,
): Promise<void> {
  return apiRequest<void>(`/memory/${memoryId}`, {
    method: "DELETE",
    token,
  });
}

export async function confirmMemoryCandidate(
  token: string,
  candidate: MemoryCandidateItem,
): Promise<MemoryItem> {
  return apiRequest<MemoryItem>("/memory/confirm-candidate", {
    method: "POST",
    token,
    body: {
      memory_type: candidate.memory_type,
      content: candidate.content,
      source: candidate.source,
      confidence: candidate.confidence,
      sensitivity: candidate.sensitivity,
      consent_required: candidate.consent_required,
      user_confirmed: true,
    },
  });
}

export async function listAuditLogs(token: string): Promise<AuditLog[]> {
  return apiRequest<AuditLog[]>("/audit", {
    token,
  });
}
import type {
  ApiErrorResponse,
  AuditLog,
  AuthUser,
  ChatResponse,
  ConversationSummary,
  MemoryItem,
  TokenResponse,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

const ACCESS_TOKEN_KEY = "akon_access_token";

export function getStoredAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function storeAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearStoredAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const rawText = await response.text();

  const data = rawText ? JSON.parse(rawText) : null;

  if (!response.ok) {
    const errorPayload = data as ApiErrorResponse | null;
    const message =
      errorPayload?.error?.message ||
      `Request failed with status ${response.status}.`;

    throw new Error(message);
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

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  return parseJsonResponse<T>(response);
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

export async function listConversations(
  token: string,
): Promise<ConversationSummary[]> {
  return apiRequest<ConversationSummary[]>("/chat/conversations", {
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

export async function listAuditLogs(token: string): Promise<AuditLog[]> {
  return apiRequest<AuditLog[]>("/audit", {
    token,
  });
}
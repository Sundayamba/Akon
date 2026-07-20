export type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
};

export type ApiErrorResponse = {
  error?: {
    code?: string;
    message?: string;
    status_code?: number;
    request_id?: string;
    details?: unknown;
  };
};

export type MemoryItem = {
  id: string;
  memory_type: string;
  content: string;
  source: string | null;
  confidence: string;
  sensitivity: string;
  consent_state: string;
  created_at: string;
  updated_at: string;
};

export type MemoryCandidateItem = {
  memory_type: string;
  content: string;
  source: string;
  confidence: string;
  sensitivity: string;
  consent_required: boolean;
  reason: string;
};

export type GroundingToolItem = {
  name: string;
  instruction: string;
};

export type FeedbackRating = "helpful" | "not_helpful";

export type ChatResponse = {
  reply: string;
  safety_level: string;
  detected_emotion: string | null;
  grounding_tool: GroundingToolItem | null;
  conversation_id: string;
  user_message_id: string | null;
  assistant_message_id: string;
  memory_candidates: MemoryCandidateItem[];
};

export type MessageFeedbackResponse = {
  id: string;
  message_id: string;
  conversation_id: string;
  rating: FeedbackRating;
  note: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationReflectionResponse = {
  conversation_id: string;
  title: string;
  summary: string;
  dominant_emotion: string | null;
  supportive_next_step: string;
  message_count: number;
};

export type ConversationSummary = {
  id: string;
  title: string | null;
  channel: string;
  safety_level: string | null;
  message_count: number;
  last_message_preview: string | null;
  last_message_role: string | null;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationDeleteResponse = {
  id: string;
  deleted: boolean;
};

export type MessageItem = {
  id: string;
  role: string;
  content: string;
  safety_level: string | null;
  detected_emotion: string | null;
  feedback_rating: FeedbackRating | null;
  created_at: string;
};

export type ConversationDetail = {
  id: string;
  title: string | null;
  channel: string;
  safety_level: string | null;
  created_at: string;
  updated_at: string;
  messages: MessageItem[];
};

export type AuditLog = {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  risk_level: string;
  source: string;
  details: Record<string, unknown> | null;
  created_at: string;
};

import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAIStore } from "./ai.store";
import { useAuthStore } from "./auth.store";
import { aiApi } from "@/api/ai.api";

vi.mock("@/api/ai.api", () => ({
  aiApi: { sendMessage: vi.fn() },
}));

const user = (id: string) => ({
  id, email: id + "@example.test", full_name: id, role: "customer" as const,
  is_email_verified: true, is_phone_verified: false,
});

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ user: null, isAuthenticated: false, isInitializing: false });
  useAIStore.getState().reset();
});

describe("Tailora account isolation", () => {
  it("clears conversation and pending prompts on account switch", () => {
    useAuthStore.setState({ user: user("A"), isAuthenticated: true });
    useAIStore.setState({
      isOpen: true, conversationId: "conversation-A",
      turns: [{ id: "A-message", role: "user", content: "Private A" }],
      pendingPrompt: "Private draft A",
    });
    useAuthStore.setState({ user: user("B"), isAuthenticated: true });
    const state = useAIStore.getState();
    expect(state.turns).toEqual([]);
    expect(state.conversationId).toBeNull();
    expect(state.pendingPrompt).toBeNull();
    expect(state.isOpen).toBe(false);
  });

  it("clears visible chat and conversation id on logout", () => {
    useAuthStore.setState({ user: user("A"), isAuthenticated: true });
    useAIStore.setState({
      conversationId: "conversation-A",
      turns: [{ id: "A-message", role: "assistant", content: "Private A" }],
    });
    useAuthStore.setState({ user: null, isAuthenticated: false });
    expect(useAIStore.getState().turns).toEqual([]);
    expect(useAIStore.getState().conversationId).toBeNull();
  });

  it("discards an old API reply if the account changes before it resolves", async () => {
    let finish!: (result: { conversation_id: string; answer: string }) => void;
    vi.mocked(aiApi.sendMessage).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    useAuthStore.setState({ user: user("A"), isAuthenticated: true });
    const sending = useAIStore.getState().sendMessage("Private request A");
    useAuthStore.setState({ user: user("B"), isAuthenticated: true });
    finish({ conversation_id: "conversation-A", answer: "Secret reply A" });
    await sending;
    expect(useAIStore.getState().turns).toEqual([]);
    expect(useAIStore.getState().conversationId).toBeNull();
    expect(useAIStore.getState().isSending).toBe(false);
  });
});

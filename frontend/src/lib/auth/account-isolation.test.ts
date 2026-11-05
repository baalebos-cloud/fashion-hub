import { beforeEach, describe, expect, it, vi } from "vitest";
import { queryClient } from "@/lib/query-client";
import { MEASUREMENT_DRAFT_PREFIX } from "@/lib/auth/account-isolation";
import { useAuthStore } from "@/store/auth.store";
import { useMessagingStore } from "@/store/messaging.store";
import { messagesApi } from "@/api/messages.api";

vi.mock("@/api/messages.api", () => ({
  messagesApi: { listConversations: vi.fn(), listMessages: vi.fn(), send: vi.fn() },
}));

const user = (id: string) => ({
  id, email: id + "@example.test", full_name: id, role: "customer" as const,
  is_email_verified: true, is_phone_verified: false,
});

function seedAccountA() {
  useAuthStore.setState({ user: user("A"), isAuthenticated: true });
  queryClient.setQueryData(["orders", "mine"], [{ id: "order-of-A" }]);
  useMessagingStore.setState({
    conversations: [{ id: "c-A" } as never], activeConversationId: "c-A",
    messages: [{ id: "m-A", body: "Private A" } as never],
  });
  localStorage.setItem(MEASUREMENT_DRAFT_PREFIX + "A", '{"data":{"chest":96}}');
  localStorage.setItem("tailora.sidebar_collapsed", "true");
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ user: null, isAuthenticated: false, isInitializing: false });
  useMessagingStore.getState().reset();
  queryClient.clear();
  localStorage.clear();
});

describe("account isolation on a shared device", () => {
  it("drops the previous account's cached data and messages when another account signs in", () => {
    seedAccountA();
    useAuthStore.setState({ user: user("B"), isAuthenticated: true });

    expect(queryClient.getQueryData(["orders", "mine"])).toBeUndefined();
    const messaging = useMessagingStore.getState();
    expect(messaging.conversations).toEqual([]);
    expect(messaging.messages).toEqual([]);
    expect(messaging.activeConversationId).toBeNull();
  });

  it("removes measurement drafts on sign-out but keeps harmless UI preferences", () => {
    seedAccountA();
    useAuthStore.setState({ user: null, isAuthenticated: false });

    expect(localStorage.getItem(MEASUREMENT_DRAFT_PREFIX + "A")).toBeNull();
    expect(localStorage.getItem("tailora.sidebar_collapsed")).toBe("true");
    expect(queryClient.getQueryData(["orders", "mine"])).toBeUndefined();
  });

  it("discards a message reply that arrives after the account changed", async () => {
    useAuthStore.setState({ user: user("A"), isAuthenticated: true });
    let resolve!: (value: unknown) => void;
    vi.mocked(messagesApi.listMessages).mockReturnValue(new Promise((r) => { resolve = r; }) as never);

    const pending = useMessagingStore.getState().openConversation("c-A");
    useAuthStore.setState({ user: user("B"), isAuthenticated: true });
    resolve([{ id: "m-A", body: "Private A" }]);
    await pending;

    expect(useMessagingStore.getState().messages).toEqual([]);
    expect(useMessagingStore.getState().activeConversationId).toBeNull();
  });
});

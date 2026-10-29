import { apiClient } from "@/lib/api/client";
import { apiConfig } from "@/config/api.config";
import { getAccessToken } from "@/lib/auth/token";

export interface SuggestedMeasurements {
  bust: number | null;
  waist: number | null;
  hips: number | null;
  unit: "cm" | "in";
  confidence: number;
  requires_manual_measurement: boolean;
  notes: string;
}

export interface MaterialSuggestion {
  name: string;
  quantity_yards: number;
  note?: string | null;
}

export interface TailoringSpecification {
  garment_description: string;
  estimated_fabric_yards: number;
  recommended_materials: MaterialSuggestion[];
  assumptions: string[];
  requires_tailor_review: boolean;
}

export const aiService = {
  async extractMeasurements(image: File): Promise<SuggestedMeasurements> {
    const payload = new FormData();
    payload.append("file", image);
    const result = await apiClient.post<SuggestedMeasurements>("/ai/measurements/extract", payload, {
      headers: { "Content-Type": undefined },
      timeout: 45_000,
    });
    return result.data;
  },

  async estimateSpec(prompt: string): Promise<TailoringSpecification> {
    const response = await apiClient.post<TailoringSpecification>("/ai/spec/estimate", { prompt }, { timeout: 45_000 });
    return response.data;
  },

  async *streamAdvisor(messages: Array<{role: "user" | "assistant"; content: string}>, signal?: AbortSignal): AsyncGenerator<string> {
    const bearer = getAccessToken();
    if (!bearer) throw new Error("Sign in to use the fashion advisor.");
    const response = await fetch(`${apiConfig.baseUrl}/ai/advisor/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${bearer}`,
      },
      body: JSON.stringify({ messages }),
      signal,
    });
    if (!response.ok || !response.body) throw new Error("Advisor temporarily unavailable.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let split = buffer.indexOf("\n\n");
        while (split !== -1) {
          const event = buffer.slice(0, split);
          buffer = buffer.slice(split + 2);
          if (event.startsWith("data: ")) {
            const parsed: unknown = JSON.parse(event.slice(6));
            if (parsed && typeof parsed === "object" && "delta" in parsed && typeof parsed.delta === "string") {
              yield parsed.delta;
            }
          }
          split = buffer.indexOf("\n\n");
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
};

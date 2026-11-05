import { apiClient } from "@/lib/api/client";
import { apiConfig } from "@/config/api.config";
import { getAccessToken } from "@/lib/auth/token";

export type MeasurementFieldName =
  "chest" | "waist" | "hip" | "inseam" | "shoulder_width" | "sleeve_length" | "neck";

/** One AI-drafted value. "tape" = read off a tape in a photo; "estimate" = inferred using the stated height. */
export interface MeasurementSuggestion {
  field_name: MeasurementFieldName;
  value: number;
  unit: "cm";
  source: "tape" | "estimate";
  confidence: number;
}

export interface PhotoMeasurementDraft {
  fields: MeasurementSuggestion[];
  notes: string;
  photo_issues: string[];
  provider: "vertex_ai" | "groq";
  requires_review: true;
}

export interface PhotoMeasurementRequest {
  bodyPhoto?: File | null;
  tapePhotos?: File[];
  heightCm?: number | null;
  garmentType?: string | null;
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
  /** Drafts the measurement form from the customer's photos. Never saves anything. */
  async analyzeMeasurementPhotos(request: PhotoMeasurementRequest): Promise<PhotoMeasurementDraft> {
    const payload = new FormData();
    if (request.bodyPhoto) payload.append("body_photo", request.bodyPhoto);
    for (const photo of request.tapePhotos ?? []) payload.append("tape_photos", photo);
    if (request.heightCm) payload.append("height_cm", String(request.heightCm));
    if (request.garmentType) payload.append("garment_type", request.garmentType);
    const result = await apiClient.post<PhotoMeasurementDraft>("/ai/measurements/analyze", payload, {
      headers: { "Content-Type": undefined },
      timeout: 60_000,
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

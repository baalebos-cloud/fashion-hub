/** Browser-only AI client. JWT stays in existing authenticated caller context. */
export type MeasurementEstimate = {
  bust: number | null;
  waist: number | null;
  hips: number | null;
  inseam: number | null;
  unit: "cm" | "inches";
  confidence: number;
};

const apiBase = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export async function extractMeasurementEstimate(
  image: File, accessToken: string,
): Promise<MeasurementEstimate> {
  const data = new FormData();
  data.append("file", image);
  const response = await fetch(`${apiBase}/api/v1/ai/measurements/extract`, {
    method: "POST", headers: { Authorization: `Bearer ${accessToken}` }, body: data,
  });
  if (!response.ok) throw new Error(`AI extraction unavailable (${response.status})`);
  const json: { estimate: MeasurementEstimate; requires_manual_confirmation: boolean } = await response.json();
  if (!json.requires_manual_confirmation) throw new Error("Manual confirmation is required");
  return json.estimate;
}

export async function estimateTailoringSpec(prompt: string, accessToken: string): Promise<unknown> {
  const response = await fetch(`${apiBase}/api/v1/ai/spec/estimate`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!response.ok) throw new Error(`AI estimate unavailable (${response.status})`);
  return response.json();
}

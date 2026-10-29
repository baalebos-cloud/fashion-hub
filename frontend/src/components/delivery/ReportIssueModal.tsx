import { useState } from "react";
import { apiClient } from "@/lib/api/client";
import { uploadFile } from "@/lib/storage/file-storage";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Button } from "@/components/ui/button";

const categories = [
  "CUSTOMER_UNREACHABLE", "WRONG_ADDRESS", "PACKAGE_DAMAGED",
  "TRAFFIC_ACCIDENT_DELAY", "RECIPIENT_REJECTED", "VEHICLE_BREAKDOWN",
] as const;

export function ReportIssueModal({ deliveryId, onClose }: { deliveryId: string; onClose: () => void }) {
  const [issueType, setIssueType] = useState<(typeof categories)[number]>("CUSTOMER_UNREACHABLE");
  const [description, setDescription] = useState("");
  const [coords, setCoords] = useState<{ latitude: number; longitude: number } | null>(null);
  const [pending, setPending] = useState(false);
  const [evidenceKey, setEvidenceKey] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(false);

  async function submit() {
    setPending(true);
    setError("");
    try {
      await apiClient.post(`/deliveries/${deliveryId}/issues`, { issue_type: issueType, description, photo_evidence_url: evidenceKey, ...coords });
      setComplete(true);
    } catch {
      setError("Issue submission failed. Check your connection and retry.");
    } finally {
      setPending(false);
    }
  }

  async function uploadEvidence(file: File) {
    setUploading(true);
    setError("");
    try {
      const response = await uploadFile(`/deliveries/${deliveryId}/issue-evidence`, file);
      setEvidenceKey(response.document_storage_key);
    } catch {
      setError("Evidence upload failed. Retry with a JPG, PNG or WebP image.");
    } finally {
      setUploading(false);
    }
  }

  function locate() {
    navigator.geolocation?.getCurrentPosition(
      pos => setCoords({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      () => setError("GPS unavailable. You can still report an issue without location."),
      { enableHighAccuracy: false, timeout: 8000 },
    );
  }

  return (
    <div role="dialog" aria-modal="true" aria-label="Report delivery issue"
      className="rounded-lg border border-line bg-paper p-4">
      <h2 className="mb-3 font-semibold">Report delivery issue</h2>
      {complete ? (
        <div role="status">Issue recorded for review. <Button onClick={onClose}>Close</Button></div>
      ) : (
        <div className="flex flex-col gap-3">
          <label className="text-sm">Issue category
            <select className="mt-1 block min-h-11 w-full rounded border border-line p-2"
              value={issueType} onChange={e => setIssueType(e.target.value as (typeof categories)[number])}>
              {categories.map(value => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}
            </select>
          </label>
          <label className="text-sm">What happened?
            <textarea className="mt-1 block min-h-24 w-full rounded border border-line p-2"
              maxLength={3000} value={description} onChange={e => setDescription(e.target.value)} />
          </label>
          <label className="text-sm">Photo evidence (optional)
            <input type="file" accept="image/jpeg,image/png,image/webp"
              className="mt-1 block w-full text-sm" onChange={e => {
                const file = e.target.files?.[0];
                if (file) void uploadEvidence(file);
              }} />
          </label>
          {uploading && <p role="status">Uploading evidence securely…</p>}
          {evidenceKey && <p role="status">Evidence attached.</p>}
          <Button variant="secondary" onClick={locate}>Attach current GPS (optional)</Button>
          {coords && <p role="status" className="text-xs">GPS coordinates attached.</p>}
          {error && <p role="alert" className="text-sm text-thread">{error}</p>}
          <div className="flex gap-2">
            <Button onClick={() => { void submit(); }} disabled={pending || uploading || description.trim().length < 5} isLoading={pending}>Submit issue</Button>
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
          </div>
        </div>
      )}
    </div>
  );
}

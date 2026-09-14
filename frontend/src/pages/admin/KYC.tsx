import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

interface KYCReviewRow {
  id: string;
  applicantName: string;
  idType: string;
}

/** Requires `GET /admin/kyc?status=pending` and
 * `POST /admin/kyc/{id}/review` — backed on the Python side by
 * KYCService.review (backend/app/services/kyc_service.py), which exists
 * but has no route wired to it yet in backend/app/api/v1/admin.py. */
export default function KYC() {
  const [pending] = useState<KYCReviewRow[]>([]);

  if (pending.length === 0) return <EmptyState title="No pending KYC submissions" />;

  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-xl text-ink">KYC review queue</h1>
      {pending.map((item) => (
        <Card key={item.id} className="flex items-center justify-between">
          <div>
            <div className="text-sm text-ink">{item.applicantName}</div>
            <div className="text-xs text-ink-soft">{item.idType}</div>
          </div>
          <div className="flex gap-2">
            <Button size="sm">Approve</Button>
            <Button size="sm" variant="secondary">Reject</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

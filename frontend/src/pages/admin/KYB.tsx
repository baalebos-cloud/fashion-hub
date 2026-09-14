import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

interface KYBReviewRow {
  id: string;
  businessName: string;
  registrationNumber: string;
}

/** Requires `GET /admin/kyb?status=pending` and
 * `POST /admin/kyb/{id}/review` — backed by KYBService.review
 * (backend/app/services/kyb_service.py), same wiring gap as KYC.tsx. */
export default function KYB() {
  const [pending] = useState<KYBReviewRow[]>([]);

  if (pending.length === 0) return <EmptyState title="No pending KYB submissions" />;

  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-xl text-ink">KYB review queue</h1>
      {pending.map((item) => (
        <Card key={item.id} className="flex items-center justify-between">
          <div>
            <div className="text-sm text-ink">{item.businessName}</div>
            <div className="text-xs text-ink-soft">Reg. {item.registrationNumber}</div>
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

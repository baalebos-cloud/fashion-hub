import { Card } from "@/components/ui/card";

const REPORT_TYPES = [
  { name: "Order volume", description: "Orders placed and completed over time" },
  { name: "GMV", description: "Gross merchandise value across customer and vendor orders" },
  { name: "Verification funnel", description: "KYC/KYB submission-to-approval rates" },
];

/** Requires backend aggregation endpoints (e.g. `GET /admin/reports/orders`)
 * — none exist yet. This page lists the intended report types as a guide
 * for what to build. */
export default function Reports() {
  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Reports</h1>
      <div className="grid gap-4 sm:grid-cols-2">
        {REPORT_TYPES.map((report) => (
          <Card key={report.name}>
            <div className="font-medium text-ink">{report.name}</div>
            <div className="mt-1 text-sm text-ink-soft">{report.description}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

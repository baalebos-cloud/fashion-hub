import { ReportsSummary } from "@/components/admin/ReportsSummary";
import { DeliveryInsights } from "@/components/admin/DeliveryInsights";
import { RecommendationsHealth } from "@/components/admin/RecommendationsHealth";

export default function Reports() {
  return (
    <div>
      <h1 className="mb-6 font-display text-3xl text-ink">Reports</h1>
      <div className="mb-8"><ReportsSummary /></div>
      <div className="mb-8"><DeliveryInsights /></div>
      <div className="mb-8"><RecommendationsHealth /></div>
    </div>
  );
}

import { PortfolioGrid } from "@/components/profile/PortfolioGrid";
import type { PortfolioImage } from "@/components/profile/PortfolioGrid";

export function ProfessionalPortfolio({ images }: { images: PortfolioImage[] }) {
  return (
    <div>
      <h2 className="mb-3 text-sm font-medium text-ink-soft">Portfolio</h2>
      <PortfolioGrid images={images} />
    </div>
  );
}

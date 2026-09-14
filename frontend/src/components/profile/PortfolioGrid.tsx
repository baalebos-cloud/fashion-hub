import { EmptyState } from "@/components/ui/empty-state";

export interface PortfolioImage {
  id: string;
  image_url: string;
}

export function PortfolioGrid({ images }: { images: PortfolioImage[] }) {
  if (images.length === 0) {
    return <EmptyState title="No portfolio images yet" description="Upload photos of your work to showcase it here." />;
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
      {images.map((image) => (
        <img key={image.id} src={image.image_url} alt="" className="aspect-square w-full rounded-card object-cover" />
      ))}
    </div>
  );
}

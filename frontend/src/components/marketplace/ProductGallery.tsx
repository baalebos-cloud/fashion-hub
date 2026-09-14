import { useState } from "react";
import { cn } from "@/lib/utils/cn";

export function ProductGallery({ images, alt }: { images: string[]; alt: string }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const displayImages = images.length > 0 ? images : ["/images/placeholder-product.png"];

  return (
    <div>
      <div className="aspect-square w-full overflow-hidden rounded-card bg-muslin">
        <img src={displayImages[activeIndex]} alt={alt} className="h-full w-full object-cover" />
      </div>
      {displayImages.length > 1 && (
        <div className="mt-2 flex gap-2">
          {displayImages.map((src, i) => (
            <button
              key={src}
              onClick={() => setActiveIndex(i)}
              className={cn("h-14 w-14 overflow-hidden rounded-lg border-2", i === activeIndex ? "border-brass" : "border-transparent")}
            >
              <img src={src} alt="" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

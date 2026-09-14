import { cn } from "@/lib/utils/cn";

export interface AvatarProps {
  src?: string | null;
  name: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZE_CLASSES = { sm: "h-8 w-8 text-xs", md: "h-10 w-10 text-sm", lg: "h-14 w-14 text-base" };

export function Avatar({ src, name, size = "md", className }: AvatarProps) {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  if (src) {
    return <img src={src} alt={name} className={cn("rounded-full object-cover", SIZE_CLASSES[size], className)} />;
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full bg-ink text-paper font-medium",
        SIZE_CLASSES[size],
        className
      )}
      aria-label={name}
    >
      {initials}
    </div>
  );
}

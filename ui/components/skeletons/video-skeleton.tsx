import {Play, Volume2} from "lucide-react";
import {Skeleton} from "@/components/ui/skeleton";
import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";

export default function VideoSkeleton() {
  return (
    <Card
      role="status"
      aria-busy="true"
      className="relative p-0 bg-card border-border overflow-hidden rounded-2xl"
    >
      <Skeleton className="h-full w-full rounded-2xl" />

      {/* Overlay controls (disabled look) */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-4 items-center bg-black/50 backdrop-blur-sm p-2 rounded-xl">
        {/* Play / Pause */}
        <Button
          variant="secondary"
          size="sm"
          disabled
          className="pointer-events-none"
        >
          <Play className="opacity-60" />
        </Button>

        {/* Volume icon + track placeholder */}
        <Volume2 className="text-white/60" />
        <Skeleton className="h-2 w-32 rounded-full" />

        {/* Speed select placeholder */}
        <Skeleton className="h-8 w-20 rounded-md" />
      </div>

      {/* Optional small top-left chips (e.g., title/tags placeholders) */}
      <div className="absolute top-3 left-3 flex gap-2">
        <Skeleton className="h-6 w-16 rounded-md" />
        <Skeleton className="h-6 w-24 rounded-md" />
      </div>
    </Card>
  );
}

import {useRef, useState, useEffect, useCallback} from "react";
import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Pause, Play, Volume2} from "lucide-react";

type CustomVideoPlayerProps = {
  sources: string[];
  onBeforeNext?: (index: number) => void;
};

export default function VideoPlayer({
  sources,
  onBeforeNext,
}: CustomVideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [showControls, setShowControls] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (video) {
      video.volume = parseFloat(e.target.value);
    }
  };

  const showControlsTemporarily = () => {
    setShowControls(true);

    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setShowControls(false), 2000);
  };

  const handleEnded = useCallback(() => {
    if (currentIndex < sources.length - 1) {
      onBeforeNext?.(currentIndex + 1);
      setCurrentIndex((prev) => prev + 1);
      setIsPlaying(true);
    } else {
      setIsPlaying(false);
    }
  }, [currentIndex, sources.length, onBeforeNext]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.play().catch(() => {}); // in case autoplay is blocked
    }
  }, [currentIndex, isPlaying]);

  return (
    <Card
      className="relative p-0 bg-card border-border overflow-hidden rounded-2xl"
      onMouseMove={showControlsTemporarily}
      onMouseEnter={showControlsTemporarily}
      onMouseLeave={() => setShowControls(false)}
    >
      {/* Video fills the card */}
      <video
        ref={videoRef}
        className="w-full h-full object-cover rounded-2xl"
        src={sources[currentIndex]} // 👈 directly bind here
        autoPlay
        preload="auto"
        onEnded={handleEnded}
      />

      {/* Overlay controls */}
      <div
        className={`absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-4 items-center bg-black/50 backdrop-blur-sm p-2 rounded-xl transition-opacity duration-300 ${
          showControls ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        <Button variant="secondary" size="sm" onClick={togglePlay}>
          {isPlaying ? <Pause /> : <Play />}
        </Button>
        <Volume2 className="text-white" />
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          defaultValue="1"
          onChange={handleVolumeChange}
          className="w-32 accent-white"
        />
      </div>
    </Card>
  );
}

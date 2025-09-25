import {useRef, useState, useEffect} from "react";
import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Pause, Play, Volume2} from "lucide-react";

export default function CustomVideoPlayer({src}: {src: string}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [showControls, setShowControls] = useState(false);
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

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

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
        preload="none"
        autoPlay
        muted
      >
        <source src={src} type="video/mp4" />
        Your browser does not support the video tag.
      </video>

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

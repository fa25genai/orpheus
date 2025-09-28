import {useRef, useState, useEffect, useCallback} from "react";
import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Pause, Play, Volume2, Gauge} from "lucide-react"; // Gauge icon for speed

type CustomVideoPlayerProps = {
  sources: string[];
  onBeforeNext?: (index: number) => void;
};

export default function VideoPlayer({
  sources,
  onBeforeNext,
}: CustomVideoPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(true);
  const [showControls, setShowControls] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1); // 🔥 speed state

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [active, setActive] = useState(0);
  const videoRefs = [
    useRef<HTMLVideoElement>(null),
    useRef<HTMLVideoElement>(null),
  ];

  const getActiveVideo = () => videoRefs[active].current;

  const togglePlay = () => {
    const video = getActiveVideo();
    if (!video) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = getActiveVideo();
    if (video) {
      video.volume = parseFloat(e.target.value);
    }
  };

  const handleSpeedChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const rate = parseFloat(e.target.value);
    setPlaybackRate(rate);

    const video = getActiveVideo();
    if (video) {
      video.playbackRate = rate;
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
      setActive((prev) => (prev === 0 ? 1 : 0));
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
    const video = getActiveVideo();
    if (!video) return;

    video.playbackRate = playbackRate; // keep speed synced

    if (isPlaying) {
      video.play().catch(() => {}); // in case autoplay is blocked
    }
  }, [currentIndex, isPlaying, playbackRate, active]);

  return (
    <Card
      className="relative p-0 bg-card border-border overflow-hidden rounded-2xl"
      onMouseMove={showControlsTemporarily}
      onMouseEnter={showControlsTemporarily}
      onMouseLeave={() => setShowControls(false)}
    >
      {/* Video fills the card */}
      {[0, 1].map((i) => (
        <video
          key={i}
          ref={videoRefs[i]}
          className={`absolute inset-0 w-full h-full object-cover rounded-2xl ${
            active === i ? "opacity-100" : "opacity-0"
          }`}
          src={
            sources[
              active === i ? currentIndex : (currentIndex + 1) % sources.length
            ]
          }
          autoPlay={active === i}
          preload="auto"
          onEnded={handleEnded}
        />
      ))}

      {/* Overlay controls */}
      <div
        className={`absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-4 items-center bg-black/50 backdrop-blur-sm p-2 rounded-xl transition-opacity duration-300 ${
          showControls ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        {/* Play / Pause */}
        <Button variant="secondary" size="sm" onClick={togglePlay}>
          {isPlaying ? <Pause /> : <Play />}
        </Button>

        {/* Volume */}
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

        {/* Playback speed */}
        <select
          value={playbackRate}
          onChange={handleSpeedChange}
          className="bg-black/70 text-white rounded px-2 py-1 text-sm"
        >
          {[0.75, 1, 1.25, 1.5, 2, 3, 3.75].map((rate) => (
            <option key={rate} value={rate}>
              {rate}×
            </option>
          ))}
        </select>
      </div>
    </Card>
  );
}

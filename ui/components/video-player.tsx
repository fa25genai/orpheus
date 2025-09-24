import { useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function CustomVideoPlayer({ src }: { src: string }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(true);

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

  // Prevent seeking by locking the last known position
  const handleSeeking = () => {
    const video = videoRef.current;
    if (video) {
      const lastTime = parseFloat(video.dataset.lastTime || "0");
      video.currentTime = lastTime;
    }
  };

  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (video) {
      video.dataset.lastTime = video.currentTime.toString();
    }
  };

  return (
    <Card className="p-0 bg-card border-border md:col-span-1 overflow-hidden rounded-2xl">
      <video
        ref={videoRef}
        className="w-full h-full object-cover rounded-2xl"
        preload="none"
        onSeeking={handleSeeking}
        onTimeUpdate={handleTimeUpdate}
        autoPlay
      >
        <source
          src={src}
          type="video/mp4"
        />
        Your browser does not support the video tag.
      </video>

      <div className="flex gap-4 mt-4 items-center p-4">
        <Button onClick={togglePlay}>
          {isPlaying ? "Pause" : "Play"}
        </Button>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          defaultValue="1"
          onChange={handleVolumeChange}
          className="w-32"
        />
      </div>
    </Card>
  );
}

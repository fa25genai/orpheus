"use client";
import CustomVideoPlayer from "@/components/video-player";

export default function Video() {
  return (
    <CustomVideoPlayer
      sources={[
        "http://localhost:8080/videos/jobs/fe9df727-ed05-4137-af89-a7bb30c25b82/1.mp4",
        "http://localhost:8080/videos/jobs/fe9df727-ed05-4137-af89-a7bb30c25b82/2.mp4",
      ]}
    />
  );
}

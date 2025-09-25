"use client";

import { useRef, useImperativeHandle, forwardRef } from "react";
import { Card } from "@/components/ui/card";
import {clsx} from "clsx";

export interface SlidevEmbedHandle {
  goToSlide: (slide: number) => void;
  next: () => void;
  prev: () => void;
}

interface SlidevEmbedProps {
  baseUrl: string;
  className?: string;
}

const SlidevEmbed = forwardRef<SlidevEmbedHandle, SlidevEmbedProps>(
  ({ baseUrl, className }, ref) => {
    const iframeRef = useRef<HTMLIFrameElement | null>(null);

    const post = (msg: any) => {
        console.log("sending message")
        console.log(msg)
      iframeRef.current?.contentWindow?.postMessage(msg, baseUrl);
    };

    const createMessage  = (data: any)=> {
        return {
            appId: "slidev",
            data: data
        }
      }

    useImperativeHandle(ref, () => ({
      goToSlide(slide: number) {
          post(createMessage({type: "slide.navigate", value: slide}));
      },
      next() {
          post(createMessage({type: "slide.next"}));
      },
      prev() {
          post(createMessage({type: "slide.prev"}));
      },
    }));

    return (
    <Card
        className={clsx(
          "relative p-0 bg-card border-border overflow-hidden rounded-2xl",
          className
        )}>
        <iframe
          ref={iframeRef}
          src={baseUrl}
          className="w-full h-[600px] rounded-2xl border-0 pointer-events-none pointer-none"
            onLoad={() => console.log("Iframe loaded, ready to post messages!")} // Add this for debugging
        />
      </Card>
    );
  }
);

SlidevEmbed.displayName = "SlidevEmbed";
export default SlidevEmbed;

"use client";
import {PersonaSelector} from "@/components/persona-selector";
import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {Input} from "@/components/ui/input";
import {ArrowUp, Loader2Icon, User} from "lucide-react";
import Link from "next/link";
import {useEffect, useRef, useState} from "react";
import {avatarApi, coreApi, slidesApi} from "@/app/api-clients";
import {PromptResponse} from "@/generated-api-clients/core";
import {GenerationStatusResponse as AvatarGenerationStatusReponse} from "@/generated-api-clients/avatar";
import {guideText} from "@/data/text";
import GuideCards from "@/components/guide-cards";
import {PersonaLevel} from "@/types/uploading";
import VideoPlayer from "@/components/video-player";
import {Skeleton} from "@/components/ui/skeleton";
import SlidevEmbed, {SlidevEmbedHandle} from "@/components/slidev-embed";
import {GenerationStatusResponse as SlidesGenerationStatusResponse} from "@/generated-api-clients/slides";
import {toast} from "sonner";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [personaLevel, setPersonaLevel] = useState<PersonaLevel>("beginner");
  const [messages, setMessages] = useState<string[]>([]);
  const [slides, setSlides] = useState<SlidesGenerationStatusResponse>();
  const [avatarData, setAvatarData] = useState<AvatarGenerationStatusReponse>();
  const [sources, setSources] = useState<string[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const slidevRef = useRef<SlidevEmbedHandle>(null);

  async function getAvatar(promptId: string) {
    try {
      const avatarResponse: AvatarGenerationStatusReponse =
        await avatarApi.getGenerationResult({promptId});

      if (avatarResponse.status === "FAILED") {
        toast.error(
          "Avatar generation failed. Wait for the polling to complete."
        );
      }

      return avatarResponse;
    } catch (error) {
      console.error("Avatar polling failed:", error);
      toast.error("An error occurred while fetching the avatar.", {
        action: {
          label: "Close",
          onClick: () => toast.dismiss(),
        },
      });
    }
  }

  async function getSlides(promptId: string) {
    try {
      const slidesResponse: SlidesGenerationStatusResponse =
        await slidesApi.getGenerationStatus({promptId});

      setSlides(slidesResponse);

      if (slidesResponse.status === "FAILED") {
        toast.error(
          "Slides generation failed. Wait for the polling to complete.",
          {
            action: {
              label: "Close",
              onClick: () => toast.dismiss(),
            },
          }
        );
      }

      return slidesResponse;
    } catch (error) {
      if (error instanceof Error && error.message.includes("404")) {
        // If 404, it means the slides are not yet created. We can ignore this error.
        return;
      }
      console.error("Slides polling failed:", error);
      // toast.error("An error occurred while fetching the slides.", {
      //   action: {
      //     label: "Close",
      //     onClick: () => toast.dismiss(),
      //   },
      // });
    }
  }

  async function getPromptId(prompt: string) {
    try {
      const response: PromptResponse = await coreApi.createLectureFromPrompt({
        promptRequest: {prompt, courseId: "IN001"},
      });
      console.log("Received prompt ID:", response.promptId);

      return response.promptId;
    } catch (error) {
      console.error("Failed to get prompt ID:", error);
      toast.error("Failed to get prompt ID.", {
        action: {
          label: "Close",
          onClick: () => toast.dismiss(),
        },
      });
    }
  }

  async function handleSubmit(input?: string, e?: React.FormEvent) {
    if (e) e.preventDefault();

    const finalPrompt = input ?? prompt;
    if (!finalPrompt.trim()) return;

    setMessages((prev) => [...prev, finalPrompt]);
    const promptId = await getPromptId(finalPrompt);

    if (!promptId) {
      toast.error("No prompt ID received.", {
        action: {
          label: "Close",
          onClick: () => toast.dismiss(),
        },
      });
      return;
    }
    const maxRetries = 3000;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const slidesResponse = await getSlides(promptId);
      if (slidesResponse && slidesResponse.status === "DONE") {
        setSlides(slidesResponse);
        break;
      }

      await new Promise((resolve) => setTimeout(resolve, 3000));
    }
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const avatarResponse = await getAvatar(promptId);
      if (avatarResponse && avatarResponse.status === "DONE") {
        setAvatarData(avatarResponse);
        break;
      }

      await new Promise((resolve) =>
        setTimeout(resolve, (avatarResponse?.estimatedSecondsLeft ?? 3) * 1000)
      );
    }

    setPrompt("");
  }

  async function fetchVideoList(baseUrl: string): Promise<string[]> {
  const sources: string[] = [];
  let index = 0;

  while (true) {
    const url = `${baseUrl}${index}.mp4`;
    try {
      const res = await fetch(url, { method: "HEAD" });
      if (!res.ok) break;
      sources.push(url);
      index++;
    } catch {
      break;
    }
  }

  return sources;
}

useEffect(() => {
      if (!avatarData?.resultUrl) return;
    async function loadVideos() {
        const baseUrl = "http://localhost:8080/"
        const builtUrl = baseUrl + avatarData?.resultUrl + "/"
         const list = await fetchVideoList(builtUrl);
    setSources(list);
    }
    loadVideos();
}, [avatarData]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({behavior: "smooth"});
  }, [messages, avatarData, slides]);

  function AvatarSection({
    avatarData,
  }: {
    avatarData?: AvatarGenerationStatusReponse;
  }) {
    if (!avatarData || avatarData.status === "IN_PROGRESS")
      return (
        <Card className="relative p-0 bg-card border-border overflow-hidden rounded-2xl">
          {/* Video area placeholder */}
          <Skeleton className="w-full h-full aspect-video rounded-2xl" />
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center text-sm p-2">
            <p>Estimated time: {avatarData?.estimatedSecondsLeft ?? "-"} sec</p>
          </div>

          {/* Overlay controls placeholder */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-4 items-center bg-black/30 backdrop-blur-sm p-2 rounded-xl">
            <Skeleton className="h-8 w-8 rounded-md" />{" "}
            {/* Play/Pause button */}
            <Skeleton className="h-6 w-6 rounded-full" /> {/* Volume icon */}
            <Skeleton className="h-2 w-32 rounded-full" /> {/* Volume slider */}
          </div>
        </Card>
      );

    if (avatarData.status === "DONE") {
      return <VideoPlayer
          sources={sources}
          onBeforeNext={() => {
              console.log("next slide")
              slidevRef.current?.next()
          }}
      />;
    }

    return (
      <Card className="p-6 text-center text-red-500">
        Avatar failed to generate.
      </Card>
    );
  }

  function SlidesSection({slides}: {slides?: SlidesGenerationStatusResponse}) {
    if (!slides || slides.status === "IN_PROGRESS")
      return (
        <Card className="relative p-8 bg-card border-border md:col-span-2 rounded-2xl">
          <Skeleton className="w-full h-98 rounded-2xl" />
          <div className="absolute inset-0 flex items-center justify-center text-sm">
            {slides?.generatedPages ?? 0} / {slides?.totalPages ?? "?"} slides
            generated
          </div>
        </Card>
      );

    if (slides.status === "DONE") {
      return (
        <Card className="p-8 bg-card border-border md:col-span-2">
          {/* URL is for now hardcoded. It will be replaced with the actual URL when the nginx server is integrated. */}
          <SlidevEmbed
            baseUrl={slides.webUrl ?? ""}
            className="h-98"
            ref={slidevRef}
          />
        </Card>
      );
    }

    return (
      <Card className="p-6 text-center text-red-500">
        Slides failed to generate.
      </Card>
    );
  }

  return (
    <main>
      <header className="p-4 border-b border-border mb-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <PersonaSelector
            selectedPersona={personaLevel}
            onPersonaChange={setPersonaLevel}
          />
          <Link href="/admin">
            <Button>
              <User className="w-4 h-4 mr-2" />
              Admin
            </Button>
          </Link>
        </div>
      </header>

      {messages.length === 0 && (
        <section className="max-w-6xl mx-auto text-center h-screen">
          <h1 className="text-4xl font-bold">What’s on your mind?</h1>
          <p className="text-muted-foreground text-lg">
            Ask any question about your course material and get personalized
            explanations.
          </p>
          <GuideCards
            persona={personaLevel}
            guideText={guideText}
            onSelect={(question) => handleSubmit(question)}
          />
          <form
            onSubmit={(e) => handleSubmit(undefined, e)}
            className="relative max-w-2xl mx-auto mt-6"
          >
            <Input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Type in your question"
              className="w-full h-14 pr-14 text-lg bg-card border-border rounded-full"
            />
            <Button
              type="submit"
              size="sm"
              className="absolute right-2 top-2 h-10 w-10 rounded-full"
              disabled={!prompt.trim()}
            >
              <ArrowUp className="w-4 h-4" />
            </Button>
          </form>
        </section>
      )}

      {messages.length > 0 && (
        <section className="max-w-6xl flex flex-col mx-auto space-y-6 pb-20">
          {messages.map((msg, index) => (
            <div key={index} className="space-y-6">
              <div className="flex justify-end">
                <div className="bg-primary text-primary-foreground px-6 py-3 rounded-2xl max-w-2xl">
                  <p className="text-lg">{msg}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <AvatarSection avatarData={avatarData} />
                <SlidesSection slides={slides} />
              </div>
              {/* For testing purposes of the slide change */}
              {/*<div className="flex gap-2">*/}
              {/*    <Button onClick={() => slidevRef.current?.next()}>Next</Button>*/}
              {/*    <Button onClick={() => slidevRef.current?.prev()}>Prev</Button>*/}
              {/*</div>*/}
            </div>
          ))}
          <div ref={bottomRef}></div>

          {(!avatarData ||
            avatarData.status === "IN_PROGRESS" ||
            !slides ||
            slides.status === "IN_PROGRESS") && (
            <div className="fixed bottom-6 right-0 left-0 mx-auto max-w-6xl flex items-center justify-center bg-card/90 backdrop-blur-md p-3 rounded-lg shadow">
              <Loader2Icon className="animate-spin mr-2" />
              <p>Generating your lecture… please wait.</p>
            </div>
          )}

          {avatarData?.status === "DONE" && slides?.status === "DONE" && (
            <form
              onSubmit={(e) => handleSubmit(undefined, e)}
              className="fixed bottom-4 right-0 left-0 mx-auto max-w-6xl"
            >
              <Input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask another question"
                className="w-full h-14 pr-14 text-lg bg-card border-border rounded-full"
              />
              <Button
                type="submit"
                size="sm"
                className="absolute right-2 top-2 h-10 w-10 rounded-full"
                disabled={!prompt.trim()}
              >
                <ArrowUp className="w-4 h-4" />
              </Button>
            </form>
          )}
        </section>
      )}
    </main>
  );
}

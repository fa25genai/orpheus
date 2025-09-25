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
import {GenerationStatusResponse as SlidesGenerationStatusResponse} from "@/generated-api-clients/slides";
import {toast} from "sonner";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [personaLevel, setPersonaLevel] = useState<PersonaLevel>("beginner");
  const [messages, setMessages] = useState<string[]>([]);
  const [slides, setSlides] = useState<SlidesGenerationStatusResponse>();
  const [avatarData, setAvatarData] = useState<AvatarGenerationStatusReponse>();
  const [loading, setLoading] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);

  async function pollAvatar(promptId: string, maxRetries: number) {
    try {
      for (let i = 0; i < maxRetries; i++) {
        const avatarResponse: AvatarGenerationStatusReponse =
          await avatarApi.getGenerationResult({promptId});

        setAvatarData(avatarResponse);

        if (
          avatarResponse.status === "DONE" ||
          avatarResponse.status === "FAILED"
        ) {
          if (avatarResponse.status === "FAILED") {
            toast.error("Avatar generation failed. Please try again.");
          }
          break;
        }

        await new Promise((resolve) =>
          setTimeout(resolve, (avatarResponse.estimatedSecondsLeft ?? 3) * 1000)
        );
      }
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

  async function pollSlides(promptId: string, maxRetries: number) {
    try {
      for (let i = 0; i < maxRetries; i++) {
        const slidesResponse: SlidesGenerationStatusResponse =
          await slidesApi.getGenerationStatus({promptId});

        setSlides(slidesResponse);

        if (
          slidesResponse.status === "DONE" ||
          slidesResponse.status === "FAILED"
        ) {
          if (slidesResponse.status === "FAILED") {
            toast.error("Slides generation failed. Please try again.", {
              action: {
                label: "Close",
                onClick: () => toast.dismiss(),
              },
            });
          }
          break;
        }

        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    } catch (error) {
      console.error("Slides polling failed:", error);
      toast.error("An error occurred while fetching the slides.");
    }
  }

  async function handleSubmit(input?: string, e?: React.FormEvent) {
    if (e) e.preventDefault();

    const finalPrompt = input ?? prompt;
    if (!finalPrompt.trim()) return;

    setMessages((prev) => [...prev, finalPrompt]);
    setLoading(true);

    try {
      const coreResponse: PromptResponse =
        await coreApi.createLectureFromPrompt({
          promptRequest: {prompt: finalPrompt},
        });

      const promptId = coreResponse.promptId;
      toast.success("Lecture generation started.", {
        action: {
          label: "Close",
          onClick: () => toast.dismiss(),
        }
      });

      pollAvatar(promptId, 20);
      pollSlides(promptId, 20);
    } catch (error) {
      console.error("API error:", error);
      toast.error("Failed to create lecture.", {
        description: (error as Error).message,
        action: {
          label: "Close",
          onClick: () => toast.dismiss(),
        },
      });
    } finally {
      setPrompt("");
      setLoading(false);
    }
  }

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
          <Skeleton className="w-full rounded-2xl" />
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center text-sm p-2">
            <p>Estimated time: {avatarData?.estimatedSecondsLeft ?? "-"} sec</p>
          </div>
        </Card>
      );

    if (avatarData.status === "DONE") {
      return <VideoPlayer src={avatarData.resultUrl ?? ""} />;
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
          <iframe
            width="100%"
            height="100%"
            src="http://localhost:3030"
            className="w-full h-98 pointer-events-none"
            title="Generated Slides"
            loading="lazy"
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
              disabled={!prompt.trim() || loading}
            >
              {loading ? (
                <Loader2Icon className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowUp className="w-4 h-4" />
              )}
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
            </div>
          ))}
          <div ref={bottomRef}></div>

          {(!avatarData || avatarData.status === "IN_PROGRESS") && (
            <div className="fixed bottom-6 right-0 left-0 mx-auto max-w-6xl flex items-center justify-center bg-card/90 backdrop-blur-md p-3 rounded-lg shadow">
              <Loader2Icon className="animate-spin mr-2" />
              <p>Generating your lecture… please wait.</p>
            </div>
          )}

          {avatarData?.status === "DONE" && (
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
                disabled={!prompt.trim() || loading}
              >
                {loading ? (
                  <Loader2Icon className="w-4 h-4 animate-spin" />
                ) : (
                  <ArrowUp className="w-4 h-4" />
                )}
              </Button>
            </form>
          )}
        </section>
      )}
    </main>
  );
}

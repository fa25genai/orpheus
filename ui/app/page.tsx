"use client";
import ChatInput from "@/components/chat-input";
import GuideCards from "@/components/guide-cards";
import {personas, PersonaSelector} from "@/components/persona-selector";
import {Button} from "@/components/ui/button";
import {guideText} from "@/data/text";
import {PromptResponse} from "@/generated-api-clients/core";
import {PersonaLevel} from "@/types/uploading";
import {User} from "lucide-react";
import Link from "next/link";
import {useEffect, useRef, useState} from "react";
import {coreApi} from "@/app/api-clients";
import {toast} from "sonner";
import {StatusDisplayer} from "@/components/status-displayer";
import VideoPlayer from "@/components/video-player";
import {Card} from "@/components/ui/card";
import SlidevEmbed, {SlidevEmbedHandle} from "@/components/slidev-embed";
import {useStatus} from "@/hooks/use-status";
import {courseId} from "@/data/course";
import {VideoSource} from "@/types/video-playback";
import {StepStatus} from "@/generated-api-clients/status";
import VideoSkeleton from "@/components/skeletons/video-skeleton";

export default function Home() {
  const [personaLevel, setPersonaLevel] = useState<PersonaLevel>("beginner");
  const [messages, setMessages] = useState<string[]>([]);
  const [prompt, setPrompt] = useState<string>("");
  const [promptId, setPromptId] = useState<string>("");
  const [sources, setSources] = useState<VideoSource[]>([]);
  const status = useStatus(promptId);

  const bottomRef = useRef<HTMLDivElement>(null);
  const slidevRef = useRef<SlidevEmbedHandle>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  async function getPromptId(prompt: string) {
    try {
      const response: PromptResponse = await coreApi.createLectureFromPrompt({
        promptRequest: {
          prompt,
          courseId,
          userPersona: personas.find((person) => person.id === personaLevel)
            ?.userProfile,
        },
      });
      return response.promptId;
    } catch (error) {
      console.error("Failed to get prompt ID:", error);
      toast.error("Failed to get prompt ID.");
    }
  }

  async function handleSubmit(input: string, e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!input.trim()) return;

    const pid = await getPromptId(input);
    if (pid) setPromptId(pid);

    setMessages([input]);
    setPrompt("");
  }

  useEffect(() => {
    async function updateVideoSources() {
      if (status?.stepSlidePostprocessing !== StepStatus.Done) return;
      const baseUrl = `http://localhost:3000/videos/jobs/${promptId}/`;

      const videos: VideoSource[] = status.stepsAvatarGeneration.map(
        (step, index) => ({
          url: step.video === StepStatus.Done ? `${baseUrl}${index}.mp4` : null,
          videoPlayed: sources[index]?.videoPlayed ?? false,
          videoStatus:
            step.video === StepStatus.InProgress ||
            step.video === StepStatus.Done
              ? step.video
              : StepStatus.InProgress,
        })
      );
      setSources(videos);
    }
    updateVideoSources();
  }, [status, promptId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({behavior: "smooth"});
  }, [messages]);

  useEffect(() => {
    outputRef.current?.scrollIntoView({behavior: "smooth"});
  }, [status?.stepSlidePostprocessing]);

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
          <div className="fixed bottom-20 right-0 left-0 mx-auto max-w-6xl">
            <ChatInput
              handleSubmit={handleSubmit}
              prompt={prompt}
              setPrompt={setPrompt}
            />
          </div>
        </section>
      )}

      {messages.length > 0 && (
        <section className="max-w-6xl flex flex-col mx-auto space-y-6 pb-20">
          {messages.map((msg, idx) => (
            <div key={idx} className="space-y-6">
              <div className="flex justify-end">
                <div className="bg-primary text-primary-foreground px-6 py-3 rounded-2xl max-w-2xl">
                  <p className="text-lg">{msg}</p>
                </div>
              </div>

              {status && (
                <StatusDisplayer promptId={promptId} status={status} />
              )}

              {status?.stepSlidePostprocessing === StepStatus.Done && (
                <div
                  ref={outputRef}
                  className="grid grid-cols-1 md:grid-cols-3 gap-6"
                >
                  {status.stepsAvatarGeneration?.length > 0 &&
                  status.stepsAvatarGeneration[0].video === StepStatus.Done ? (
                    <VideoPlayer
                      sources={sources}
                      onBeforeNext={() => {
                        console.log("next slide");
                        slidevRef.current?.next();
                      }}
                    />
                  ) : (
                    <VideoSkeleton />
                  )}

                  <Card className="p-8 bg-card border-border md:col-span-2">
                    <SlidevEmbed
                      baseUrl={`http://localhost:30608/web/${promptId}`}
                      className="h-98"
                      ref={slidevRef}
                    />
                  </Card>
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef}></div>

          {status?.stepSlidePostprocessing === StepStatus.Done && (
            <div className="fixed bottom-4 right-0 left-0 mx-auto max-w-6xl">
              <ChatInput
                handleSubmit={handleSubmit}
                prompt={prompt}
                setPrompt={setPrompt}
              />
            </div>
          )}
        </section>
      )}
    </main>
  );
}

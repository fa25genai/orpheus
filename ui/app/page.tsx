"use client";
import ChatInput from "@/components/chat-input";
import GuideCards from "@/components/guide-cards";
import {PersonaSelector} from "@/components/persona-selector";
import {Button} from "@/components/ui/button";
import {guideText} from "@/data/text";
// import {PromptResponse} from "@/generated-api-clients/core";
import {PersonaLevel} from "@/types/uploading";
import {User} from "lucide-react";
import Link from "next/link";
import {useEffect, useRef, useState} from "react";
// import {coreApi} from "@/app/api-clients";
// import {toast} from "sonner";
import {StatusDisplayer} from "@/components/status-displayer";
import VideoPlayer from "@/components/video-player";
import {Card} from "@/components/ui/card";
import SlidevEmbed, {SlidevEmbedHandle} from "@/components/slidev-embed";
import {mockStatus} from "@/data/status";

export default function Home() {
  const [personaLevel, setPersonaLevel] = useState<PersonaLevel>("beginner");
  const [messages, setMessages] = useState<string[]>([]);
  const [prompt, setPrompt] = useState<string>("");
  const [promptId, setPromptId] = useState<string>("");
  const [sources, setSources] = useState<string[]>([]);
  const status = mockStatus; // useStatus(promptId);

  const bottomRef = useRef<HTMLDivElement>(null);
  const slidevRef = useRef<SlidevEmbedHandle>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  // async function getPromptId(prompt: string) {
  //   try {
  //     const response: PromptResponse = await coreApi.createLectureFromPrompt({
  //       promptRequest: {prompt, courseId: "IN001"},
  //     });
  //     console.log("Received prompt ID:", response.promptId);

  //     return response.promptId;
  //   } catch (error) {
  //     console.error("Failed to get prompt ID:", error);
  //     toast.error("Failed to get prompt ID.", {
  //       action: {
  //         label: "Close",
  //         onClick: () => toast.dismiss(),
  //       },
  //     });
  //   }
  // }

  async function handleSubmit(input: string, e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!input.trim()) return;

    const promptId = "8df92d96-543e-4662-887b-8285a771ba2c"; // await getPromptId(input);
    if (promptId) setPromptId(promptId);

    setMessages((prev) => [...prev, input]);
    setPrompt("");
  }

  useEffect(() => {
    async function updateVideoSources() {
      if (status?.stepSlidePostprocessing !== "DONE") return;

      const baseUrl = `http://localhost:3000/videos/jobs/2d8e3014-9dbc-440c-a1e4-2560ae05f5be/`;

      const readyVideos: string[] = status.stepsAvatarGeneration
        .map((step, index) =>
          step.video === "DONE" ? `${baseUrl}${index + 1}.mp4` : null
        )
        // needed to filter out all nulls
        .filter((url): url is string => url !== null);

      setSources(readyVideos);
    }

    updateVideoSources();
  }, [status, promptId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({behavior: "smooth"});
  }, [messages]);

  useEffect(() => {
    outputRef.current?.scrollIntoView({behavior: "smooth"});
  }, [status.stepSlidePostprocessing]);

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
            onSelect={(question) => handleSubmit(question, undefined)}
          />
          <ChatInput
            handleSubmit={handleSubmit}
            prompt={prompt}
            setPrompt={setPrompt}
          />
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

              {status && <StatusDisplayer status={status} />}

              {status?.stepSlidePostprocessing === "DONE" && (
                <div
                  ref={outputRef}
                  className="grid grid-cols-1 md:grid-cols-3 gap-6"
                >
                  <VideoPlayer
                    sources={sources}
                    onBeforeNext={() => {
                      console.log("next slide");
                      slidevRef.current?.next();
                    }}
                  />
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

          <div className="fixed bottom-4 right-0 left-0 mx-auto max-w-6xl">
            <ChatInput
              handleSubmit={handleSubmit}
              prompt={prompt}
              setPrompt={setPrompt}
            />
          </div>
        </section>
      )}
    </main>
  );
}

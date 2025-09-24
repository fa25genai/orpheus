"use client";
import {PersonaSelector} from "@/components/persona-selector";
import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {Input} from "@/components/ui/input";
import {ArrowUp, User} from "lucide-react";
import Link from "next/link";
import {useEffect, useRef, useState} from "react";
import {avatarApi, coreApi} from "@/app/api-clients";
import {PromptResponse} from "@/generated-api-clients/core";
import {GenerationStatusResponse} from "@/generated-api-clients/avatar";
import {guideText} from "@/data/text";
import GuideCards from "@/components/guide-cards";
import {PersonaLevel} from "@/types/uploading";
import VideoPlayer from "@/components/video-player";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [personaLevel, setPersonaLevel] = useState<PersonaLevel>("beginner");
  const [messages, setMessages] = useState<string[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (prompt.trim()) {
      setMessages((prev) => [...prev, prompt]);
      // Call API to get response
      try {
        const coreResponse: PromptResponse =
          await coreApi.createLectureFromPrompt({
            promptRequest: {
              prompt: prompt,
            },
          });

        const promptId = coreResponse.promptId;
        console.log("Lecture created:", promptId);

        const avatarResponse: GenerationStatusResponse =
          await avatarApi.getGenerationResult({
            promptId: promptId,
          });

        console.log("Avatar generation status:", avatarResponse.status);
      } catch (error) {
        console.error("API error:", error);
      }

      setPrompt(""); // clear input after submit
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({behavior: "smooth"});
  }, [messages]);

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
          <h1 className="text-4xl font-bold">Whats on your mind?</h1>
          <p className="text-muted-foreground text-lg">
            Ask any question about your course material and get personalized
            explanations.
          </p>
          <GuideCards
            persona={personaLevel}
            guideText={guideText}
            onSelect={(question) => setMessages((prev) => [...prev, question])}
          />
          <form
            onSubmit={handleSubmit}
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
                <div className="bg-primary text-primary-foreground px-6 py-3 rounded-2xl max-w-2xl space-y-6">
                  <p className="text-lg">{msg}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <VideoPlayer src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4" />

                <Card className="p-8 bg-card border-border md:col-span-2">
                    <iframe
                        width="100%"
                        height="100%"
                        src="http://localhost:3030"
                        className="w-full h-98 pointer-events-none pointer-none"
                        title="Generated Slides"
                        loading="lazy"
                    />
                </Card>
              </div>
            </div>
          ))}
          <div ref={bottomRef}></div>

          <form
            onSubmit={handleSubmit}
            className="fixed bottom-4 right-0 left-0 mx-auto max-w-6xl"
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
    </main>
  );
}

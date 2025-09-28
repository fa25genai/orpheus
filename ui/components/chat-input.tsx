"use client"

import { Button } from "@/components/ui/button";
import { ArrowUp } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  handleSubmit: (prompt: string, e: React.FormEvent) => void;
  setPrompt: (prompt: string) => void;
  prompt: string;
}

export default function ChatInput({handleSubmit, setPrompt, prompt}: ChatInputProps) {
  return (
    <form
      onSubmit={(e) => handleSubmit(prompt, e)}
      className="relative max-w-2xl mx-auto mt-6"
    >
      <Textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Type in your question"
        className="w-full pr-14 text-lg bg-card border-border rounded-2xl resize-none
          min-h-14 max-h-[40vh] overflow-y-auto p-3"
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
  );
}

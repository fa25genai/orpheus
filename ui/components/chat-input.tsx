"use client"

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ArrowUp } from "lucide-react";

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
  );
}

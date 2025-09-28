"use client";

import {useRef, useEffect} from "react";
import {Button} from "@/components/ui/button";
import {ArrowUp} from "lucide-react";
import {Textarea} from "@/components/ui/textarea";

interface ChatInputProps {
  handleSubmit: (prompt: string, e: React.FormEvent) => void;
  setPrompt: (prompt: string) => void;
  prompt: string;
}

export default function ChatInput({
  handleSubmit,
  setPrompt,
  prompt,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Auto-grow textarea on input
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "0px"; // reset
      textarea.style.height = `${Math.min(
        textarea.scrollHeight,
        window.innerHeight * 0.4
      )}px`; // grow but cap at 40% viewport
    }
  }, [prompt]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // prevent newline
      // trigger form submit
      const form = e.currentTarget.form;
      if (form) {
        form.requestSubmit(); // safer than form.submit()
      }
    }
  };

  return (
    <form
      onSubmit={(e) => handleSubmit(prompt, e)}
      className="relative max-w-2xl mx-auto mt-6 flex items-end gap-2 p-2 border rounded-2xl bg-card"
    >
      <Textarea
        ref={textareaRef}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type in your question"
        className="resize-none border-0 bg-transparent focus-visible:ring-0 focus:outline-none shadow-none"
      />
      <Button
        type="submit"
        size="icon"
        className="h-10 w-10 rounded-full shrink-0"
        disabled={!prompt.trim()}
      >
        <ArrowUp className="w-4 h-4" />
      </Button>
    </form>
  );
}

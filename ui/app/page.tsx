"use client";
import {PersonaSelector} from "@/components/persona-selector";
import {Button} from "@/components/ui/button";
import {PersonaLevel} from "@/types/uploading";
import {User} from "lucide-react";
import Link from "next/link";
import {useState} from "react";

export default function Home() {
  const [personaLevel, setPersonaLevel] = useState<PersonaLevel>("beginner");
  const [messages, setMessages] = useState<string[]>([]);

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
    </main>
  );
}

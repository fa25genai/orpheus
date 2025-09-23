"use client";

import type React from "react";

import {useState} from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {Badge} from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  GraduationCap,
  User,
  Brain,
  Settings,
  ChevronDown,
} from "lucide-react";

export interface Persona {
  id: string;
  name: string;
  level: "beginner" | "intermediate" | "advanced";
  description: string;
  characteristics: string[];
  icon: React.ReactNode;
  color: string;
}

const personas: Persona[] = [
  {
    id: "newbie",
    name: "Tom",
    level: "beginner",
    description:
      "Tom 18 years old starts as a freshmen in computer science at University of Stuttgard",
    characteristics: [
      "Simple language and terminology",
      "Step-by-step explanations",
      "Real-world analogies",
      "Frequent examples and illustrations",
      "Encouragement and patience",
    ],
    icon: <GraduationCap className="w-5 h-5" />,
    color: "bg-green-500/10 text-green-500 border-green-500/20",
  },
  {
    id: "bachelor",
    name: "Aurora",
    level: "intermediate",
    description:
      "Aurora 21 years old just graduated from TUM with B.Sc. Informatics",
    characteristics: [
      "Balanced technical language",
      "Practical applications focus",
      "Some assumptions about prior knowledge",
      "Problem-solving approaches",
      "Connections between concepts",
    ],
    icon: <User className="w-5 h-5" />,
    color: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  },
  {
    id: "master",
    name: "Linda",
    level: "advanced",
    description:
      "Linda 30 years old is a Ph.D. candidate in computer science at MIT",
    characteristics: [
      "Technical terminology and jargon",
      "In-depth theoretical explanations",
      "Advanced mathematical concepts",
      "Research and cutting-edge topics",
      "Critical analysis and evaluation",
    ],
    icon: <Brain className="w-5 h-5" />,
    color: "bg-purple-500/10 text-purple-500 border-purple-500/20",
  },
];

interface PersonaSelectorProps {
  selectedPersona: string;
  onPersonaChange: (persona: string) => void;
  className?: string;
}

export function PersonaSelector({
  selectedPersona,
  onPersonaChange,
  className = "",
}: PersonaSelectorProps) {
  const [showDetails, setShowDetails] = useState(true);

  const currentPersona =
    personas.find((p) => p.id === selectedPersona) || personas[0];

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Dialog open={showDetails} onOpenChange={setShowDetails}>
        <DialogTrigger asChild>
          <div className="border-input data-[placeholder]:text-muted-foreground [&_svg:not([class*='text-'])]:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 dark:hover:bg-input/50 flex w-fit items-center justify-between gap-2 rounded-md border bg-transparent px-3 py-2 text-sm whitespace-nowrap shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 data-[size=default]:h-9 data-[size=sm]:h-8 *:data-[slot=select-value]:line-clamp-1 *:data-[slot=select-value]:flex *:data-[slot=select-value]:items-center *:data-[slot=select-value]:gap-2 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4">
            <div className="flex items-center gap-3">
              {currentPersona.icon}
              <div className="flex flex-col">
                <span className="font-medium">{currentPersona.name}</span>
                <span className="text-xs text-muted-foreground capitalize">
                  {currentPersona.level}
                </span>
              </div>
              <ChevronDown className="opacity-50" />
            </div>
          </div>
        </DialogTrigger>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Learning Personas
            </DialogTitle>
            <DialogDescription>
              Choose the learning style that best matches your current knowledge
              level and preferences
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {personas.map((persona) => (
              <Card
                key={persona.id}
                className={`cursor-pointer transition-all hover:shadow-md ${
                  persona.id === selectedPersona ? "ring-2 ring-primary" : ""
                }`}
                onClick={() => {
                  onPersonaChange(persona.id);
                  setShowDetails(false);
                }}
              >
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {persona.icon}
                      {persona.name}
                    </div>
                    <Badge className={persona.color} variant="outline">
                      {persona.level}
                    </Badge>
                  </CardTitle>
                  <CardDescription className="text-sm">
                    {persona.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-muted-foreground">
                      Key Features:
                    </p>
                    <ul className="space-y-1">
                      {persona.characteristics
                        .slice(0, 3)
                        .map((char, index) => (
                          <li
                            key={index}
                            className="text-xs flex items-start gap-2"
                          >
                            <div className="w-1 h-1 bg-primary rounded-full mt-2 flex-shrink-0"></div>
                            {char}
                          </li>
                        ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

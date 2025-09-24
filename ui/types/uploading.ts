export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: "uploading" | "completed" | "error";
  progress: number;
  url?: string;
}

export type PersonaLevel = "beginner" | "intermediate" | "expert";

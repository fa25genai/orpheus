export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: "uploading" | "completed" | "error";
  url?: string;
  documentId?: string;
}

export type PersonaLevel = "beginner" | "intermediate" | "expert";

import {UploadedFile} from "@/types/uploading";
import {AlertCircle, CheckCircle, Upload, X} from "lucide-react";
import {useCallback, useState} from "react";
import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Progress} from "@/components/ui/progress";
import {Badge} from "@/components/ui/badge";
import {docintApi} from "@/app/api-clients";

interface FileUploadProps {
  acceptedTypes: string[];
  maxSize: number; // in MB
  multiple?: boolean;
  icon?: React.ReactNode;
  title: string;
  description: string;
  className?: string;
}

export function FileUpload({
  acceptedTypes,
  maxSize,
  multiple = false,
  icon,
  title,
  description,
  className = "",
}: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState<UploadedFile[]>([]);

  async function uploadSlides(file: File, fileId: string) {
    try {
      await docintApi.uploadsDocument({
        courseId: "1",
        body: file, // ✅ actual Blob/File
      });

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileId ? {...f, status: "completed", progress: 100} : f
        )
      );
    } catch (err) {
      console.error("Upload failed:", err);
      setFiles((prev) =>
        prev.map((f) => (f.id === fileId ? {...f, status: "error"} : f))
      );
    }
  }

  async function uploadAvatar(file: File, fileId: string) {
    try {
      //TODO: call function to upload avatar
    } catch (error) {
      console.error("Upload failed:", error);
      setFiles((prev) =>
        prev.map((f) => (f.id === fileId ? {...f, status: "error"} : f))
      );
    }
  }

  async function uploadAudio(file: File, fileId: string) {
    try {
      //TODO: call function to upload audio
    } catch (error) {
      console.error("Upload failed:", error);
      setFiles((prev) =>
        prev.map((f) => (f.id === fileId ? {...f, status: "error"} : f))
      );
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (
      Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
    );
  };

  const validateFile = (file: File): string | null => {
    if (!acceptedTypes.includes(file.type)) {
      return `File type ${file.type} is not supported`;
    }
    if (file.size > maxSize * 1024 * 1024) {
      return `File size exceeds ${maxSize}MB limit`;
    }
    return null;
  };

  const handleFiles = useCallback(
    (fileList: FileList) => {
      const newFiles: UploadedFile[] = [];

      Array.from(fileList).forEach((file) => {
        const error = validateFile(file);
        if (error) {
          console.error(error);
          return;
        }

        const uploadedFile: UploadedFile = {
          id: crypto.randomUUID(),
          name: file.name,
          size: file.size,
          type: file.type,
          status: "uploading",
          progress: 0,
        };

        newFiles.push(uploadedFile);
        if (file.type.startsWith("image/")) uploadAvatar(file, uploadedFile.id);
        if (file.type.startsWith("application/pdf")) uploadSlides(file, uploadedFile.id);
        if (file.type.startsWith("audio/")) uploadAudio(file, uploadedFile.id);
      });

      if (newFiles.length > 0) {
        setFiles((prev) => (multiple ? [...prev, ...newFiles] : newFiles));
      }
    },
    [acceptedTypes, maxSize, multiple]
  );

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "error":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return (
          <Upload className="w-4 h-4 text-muted-foreground animate-pulse" />
        );
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <Card
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setDragOver(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files) {
            handleFiles(e.dataTransfer.files);
          }
        }}
        onClick={() => document.getElementById(`file-input-${title}`)?.click()}
      >
        <div className="flex flex-col items-center space-y-4">
          {icon || <Upload className="w-12 h-12 text-muted-foreground" />}
          <div>
            <p className="text-sm font-medium mb-2">{title}</p>
            <p className="text-xs text-muted-foreground mb-4">{description}</p>
            <Badge variant="outline" className="text-xs">
              Max {maxSize}MB • {acceptedTypes.join(", ")}
            </Badge>
          </div>
          <Button variant="outline" size="sm" type="button">
            Choose Files
          </Button>
        </div>
        <input
          id={`file-input-${title}`}
          type="file"
          accept={acceptedTypes.join(",")}
          multiple={multiple}
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
          className="hidden"
        />
      </Card>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file) => (
            <Card key={file.id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  {getStatusIcon(file.status)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {file.status === "uploading" && (
                    <div className="w-24">
                      <Progress value={file.progress} className="h-2" />
                    </div>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(file.id);
                    }}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

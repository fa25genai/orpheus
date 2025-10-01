import {UploadedFile} from "@/types/uploading";
import {AlertCircle, CheckCircle, Loader2, Upload, X} from "lucide-react";
import {useCallback, useState} from "react";
import {Card} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Badge} from "@/components/ui/badge";
import {toast} from "sonner";

interface FileUploadProps {
  acceptedTypes: string[];
  maxSize: number; // in MB
  multiple?: boolean;
  icon?: React.ReactNode;
  title: string;
  description: string;
  className?: string;
  files: UploadedFile[];
  onUpload: (file: File, tempId: string) => Promise<void>;
  onRemove: (file: UploadedFile) => Promise<void>;
  onFilesChange?: (files: UploadedFile[]) => void;
}

export function FileUpload({
  acceptedTypes,
  maxSize,
  multiple = false,
  icon,
  title,
  description,
  className = "",
  files,
  onUpload,
  onRemove,
  onFilesChange,
}: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);

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
          toast.error(`Invalid file: ${file.name}`, {description: error});
          return;
        }

        const tempId = crypto.randomUUID();
        const uploadedFile: UploadedFile = {
          id: tempId,
          name: file.name,
          size: file.size,
          type: file.type,
          status: "uploading",
        };

        newFiles.push(uploadedFile);

        // Delegate upload to parent
        onUpload(file, tempId).catch(() => {
          toast.error(`Failed to upload ${file.name}`);
        });
      });

      if (newFiles.length > 0) {
        const updated = multiple ? [...files, ...newFiles] : newFiles;
        onFilesChange?.(updated);
      }
    },
    [acceptedTypes, maxSize, multiple, files, onUpload, onFilesChange]
  );

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
                    <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemove(file).catch(() => {
                        toast.error(`Failed to delete ${file.name}`);
                      });
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

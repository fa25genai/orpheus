import {UploadedFile} from "@/types/uploading";
import {toast} from "sonner";

export function makeUploadHandler(
  setState: React.Dispatch<React.SetStateAction<UploadedFile[]>>,
  uploadFunction: (file: File) => Promise<{documentId?: string}>
) {
  return async (file: File, tempId: string) => {
    try {
      const response = await uploadFunction(file);

      setState((prev) =>
        prev.map((f) =>
          f.id === tempId
            ? {
                ...f,
                status: "completed",
                documentId: response.documentId,
              }
            : f
        )
      );

      toast.success(`Uploaded ${file.name}`, {
        action: {
          label: "Close",
          onClick: () => toast.dismiss(),
        },
      });
    } catch (err) {
      console.error("Upload failed:", err);
      setState((prev) =>
        prev.map((f) => (f.id === tempId ? {...f, status: "error"} : f))
      );
      toast.error(`Failed to upload ${file.name}`, {
        action: {
          label: "Close",
          onClick: () => toast.dismiss(),
        },
      });
    }
  };
}

export function makeRemoveHandler(
  setState: React.Dispatch<React.SetStateAction<UploadedFile[]>>,
  removeFunction: (file: UploadedFile) => Promise<void>
) {
  return async (file: UploadedFile) => {
    try {
      await removeFunction(file);

      setState((prev) => prev.filter((f) => f.id !== file.id));
      toast.success("File deleted", {
        action: {
          label: "Close",
          onClick: () => toast.dismiss(),
        },
      });
    } catch (err) {
      console.error("Delete failed:", err);
      toast.error(`Failed to delete ${file.name}`, {
        action: {
          label: "Close",
          onClick: () => toast.dismiss(),
        },
      });
    }
  };
}

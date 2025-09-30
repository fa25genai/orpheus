"use client";

import {FileUpload} from "@/components/file-upload";
import {Mic} from "lucide-react";
import {useState} from "react";
import {UploadedFile} from "@/types/uploading";
import {avatarApi} from "@/app/api-clients";
import {courseId} from "@/data/course";
import {CourseAvatarSlot} from "@/generated-api-clients/avatar";
import {toast} from "sonner";

export function AudioUpload() {
  const [audios, setAudios] = useState<
    Record<CourseAvatarSlot, UploadedFile[]>
  >({
    default: [],
    beginning: [],
    ending: [],
  });

  // --- Handlers per slot ---
  const makeHandlers = (slot: CourseAvatarSlot) => {
    const setSlotFiles = (files: UploadedFile[]) =>
      setAudios((prev) => ({...prev, [slot]: files}));

    const onUpload = async (file: File, tempId: string) => {
      // Mark file as uploading
      setSlotFiles([
        {
          id: tempId,
          name: file.name,
          size: file.size,
          type: file.type,
          status: "uploading",
        },
      ]);

      try {
        const response =
          await avatarApi.replaceAvatarAudioEndpointV1AvatarsCourseIdSlotAudioPost(
            {
              courseId,
              audioFile: file,
              slot,
            }
          );

        setSlotFiles([
          {
            id: tempId,
            name: file.name,
            size: file.size,
            type: file.type,
            status: "completed",
            url: URL.createObjectURL(file), // local preview
            documentId: response.avatarId,
          },
        ]);

        toast.success(`Uploaded ${file.name}`, {
          action: {label: "Close", onClick: () => toast.dismiss()},
        });
      } catch (err) {
        console.error("Upload failed:", err);
        setSlotFiles([
          {
            id: tempId,
            name: file.name,
            size: file.size,
            type: file.type,
            status: "error",
          },
        ]);
        toast.error(`Failed to upload ${file.name}`, {
          action: {label: "Close", onClick: () => toast.dismiss()},
        });
      }
    };

    const onRemove = async (file: UploadedFile) => {
      try {
        // TODO: if API supports deleting avatars, call it here
        console.log("Remove avatar:", file, "from slot:", slot);

        setSlotFiles([]);
        toast.success("File deleted", {
          action: {label: "Close", onClick: () => toast.dismiss()},
        });
      } catch (err) {
        console.error("Delete failed:", err);
        toast.error(`Failed to delete ${file.name}`, {
          action: {label: "Close", onClick: () => toast.dismiss()},
        });
      }
    };

    return {onUpload, onRemove, onFilesChange: setSlotFiles};
  };

  const defaultHandlers = makeHandlers("default");
  const beginningHandlers = makeHandlers("beginning");
  const endingHandlers = makeHandlers("ending");

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Beginning Audio */}
      <FileUpload
        files={audios.beginning}
        {...beginningHandlers}
        acceptedTypes={["audio/wav", "audio/mp3", "audio/x-wav"]}
        maxSize={100}
        icon={<Mic className="w-12 h-12 text-muted-foreground" />}
        title="Beginning Audio"
        description="MP3, WAV"
        multiple={false}
      />

      {/* Middle Audio */}
      <FileUpload
        files={audios.default}
        {...defaultHandlers}
        acceptedTypes={["audio/wav", "audio/mp3", "audio/x-wav"]}
        maxSize={100}
        icon={<Mic className="w-12 h-12 text-muted-foreground" />}
        title="Default/Middle Audio"
        description="MP3, WAV"
        multiple={false}
      />

      {/* Ending Audio */}
      <FileUpload
        files={audios.ending}
        {...endingHandlers}
        acceptedTypes={["audio/wav", "audio/mp3", "audio/x-wav"]}
        maxSize={100}
        icon={<Mic className="w-12 h-12 text-muted-foreground" />}
        title="Ending Audio"
        description="MP3, WAV"
        multiple={false}
      />
    </div>
  );
}

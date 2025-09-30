"use client";

import {FileUpload} from "@/components/file-upload";
import {ImageIcon} from "lucide-react";
import {useEffect, useState} from "react";
import {UploadedFile} from "@/types/uploading";
import {avatarApi} from "@/app/api-clients";
import {courseId} from "@/data/course";
import {CourseAvatarSlot} from "@/generated-api-clients/avatar";
import {toast} from "sonner";

export function AvatarUpload() {
  const [avatars, setAvatars] = useState<
    Record<CourseAvatarSlot, UploadedFile[]>
  >({
    default: [],
    beginning: [],
    ending: [],
  });

  // Fetch existing avatars from API
  async function getAvatars() {
    try {
      const avatarResponse =
        await avatarApi.getAvatarsByCourseEndpointV1AvatarsByCourseCourseIdGet({
          courseId,
        });

      const mappedAvatars: Record<CourseAvatarSlot, UploadedFile[]> = {
        default: [],
        beginning: [],
        ending: [],
      };

      avatarResponse.forEach((avatar) => {
        const slot = avatar.slot as CourseAvatarSlot;
        if (slot in mappedAvatars) {
          mappedAvatars[slot] = [
            {
              id: avatar.avatarId,
              name: avatar.slot ?? slot,
              size: avatar.image?.sizeBytes ?? 0,
              type: "image",
              status: "completed",
              url: avatar.image?.filePath,
              documentId: avatar.avatarId,
            },
          ];
        }
      });

      setAvatars(mappedAvatars);
    } catch (err) {
      console.error("Failed to fetch avatars:", err);
    }
  }

  useEffect(() => {
    getAvatars();
  }, [avatars]);

  // --- Handlers per slot ---
  const makeHandlers = (slot: CourseAvatarSlot) => {
    const setSlotFiles = (files: UploadedFile[]) =>
      setAvatars((prev) => ({...prev, [slot]: files}));

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
          await avatarApi.replaceAvatarImageEndpointV1AvatarsCourseIdSlotImagePost(
            {
              courseId,
              imageFile: file,
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
      {/* Beginning Avatar */}
      <FileUpload
        files={avatars.beginning}
        {...beginningHandlers}
        acceptedTypes={["image/jpeg", "image/png", "image/webp"]}
        maxSize={10}
        icon={<ImageIcon className="w-12 h-12 text-muted-foreground" />}
        title="Beginning Avatar"
        description="JPG, PNG, WEBP"
        multiple={false}
      />

      {/* Default Avatar */}
      <FileUpload
        files={avatars.default}
        {...defaultHandlers}
        acceptedTypes={["image/jpeg", "image/png", "image/webp"]}
        maxSize={10}
        icon={<ImageIcon className="w-12 h-12 text-muted-foreground" />}
        title="Default/Middle Avatar"
        description="JPG, PNG, WEBP"
        multiple={false}
      />

      {/* Ending Avatar */}
      <FileUpload
        files={avatars.ending}
        {...endingHandlers}
        acceptedTypes={["image/jpeg", "image/png", "image/webp"]}
        maxSize={10}
        icon={<ImageIcon className="w-12 h-12 text-muted-foreground" />}
        title="Ending Avatar"
        description="JPG, PNG, WEBP"
        multiple={false}
      />
    </div>
  );
}

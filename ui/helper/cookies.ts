const cookieName = "uploaded_files";

type UploadedFile = {
  documentId: string;
  name: string;
  size: number;
};

export function setUploadedFilesCookie(newFile: UploadedFile) {
  // Get existing files from cookie
  const existing: UploadedFile[] = (() => {
    try {
      const cookie = document.cookie
        .split("; ")
        .find((row) => row.startsWith(`${cookieName}=`));
      if (!cookie) return [];
      const parsed = JSON.parse(decodeURIComponent(cookie.split("=")[1]));
      if (!Array.isArray(parsed)) return [];
      const safe = parsed.filter(
        (x) =>
          x &&
          typeof x.documentId === "string" &&
          typeof x.name === "string" &&
          typeof x.size === "number"
      ) as UploadedFile[];
      return safe;
    } catch {
      return [];
    }
  })();

  // Add the new file, ensuring no duplicates by documentId
  const updated: UploadedFile[] = [
    ...existing.filter((f) => f.documentId !== newFile.documentId),
    newFile,
  ];

  // Store as JSON string
  document.cookie = `${cookieName}=${encodeURIComponent(
    JSON.stringify(updated)
  )}; path=/; max-age=${60 * 60 * 24 * 7}`; // 7 days expiry
}

export function getUploadedFilesCookie(): UploadedFile[] {
  try {
    const cookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith(`${cookieName}=`));
    if (!cookie) return [];
    const parsed = JSON.parse(decodeURIComponent(cookie.split("=")[1]));
    if (!Array.isArray(parsed)) return [];
    const safe = parsed.filter(
      (x) =>
        x &&
        typeof x.documentId === "string" &&
        typeof x.name === "string" &&
        typeof x.size === "number"
    ) as UploadedFile[];
    return safe;
  } catch {
    return [];
  }
}

export function removeUploadedFileFromCookie(documentId: string) {
  try {
    const cookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith(`${cookieName}=`));
    if (!cookie) return;

    const existing = JSON.parse(decodeURIComponent(cookie.split("=")[1])) as {
      documentId: string;
      name: string;
      size: number;
    }[];

    const updated = existing.filter((f) => f.documentId !== documentId);

    document.cookie = `${cookieName}=${encodeURIComponent(
      JSON.stringify(updated)
    )}; path=/; max-age=${60 * 60 * 24 * 7}`;
  } catch (err) {
    console.error("Failed to update cookie:", err);
  }
}

export function clearUploadedFilesCookie() {
  document.cookie = `${cookieName}=; path=/; max-age=0`;
}

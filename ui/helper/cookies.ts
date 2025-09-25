const cookieName = "uploaded_files";

export function setUploadedFilesCookie(newFile: {
  documentId: string;
  name: string;
  size: number;
}) {
  // Get existing files from cookie
  const existing = (() => {
    try {
      const cookie = document.cookie
        .split("; ")
        .find((row) => row.startsWith(`${cookieName}=`));
      return cookie ? JSON.parse(decodeURIComponent(cookie.split("=")[1])) : [];
    } catch {
      return [];
    }
  })();

  // Add the new file, ensuring no duplicates by documentId
  const updated = [
    ...existing.filter((f: any) => f.documentId !== newFile.documentId),
    newFile,
  ];

  // Store as JSON string
  document.cookie = `${cookieName}=${encodeURIComponent(
    JSON.stringify(updated)
  )}; path=/; max-age=${60 * 60 * 24 * 7}`; // 7 days expiry
}

export function getUploadedFilesCookie(): {
  documentId: string;
  name: string;
  size: number;
}[] {
  try {
    const cookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith(`${cookieName}=`));
    return cookie ? JSON.parse(decodeURIComponent(cookie.split("=")[1])) : [];
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

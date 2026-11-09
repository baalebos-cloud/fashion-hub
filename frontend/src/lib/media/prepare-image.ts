/**
 * Get a phone photo ready to upload.
 *
 * Phone cameras produce large photos (often 5–15 MB), and iPhones save them as HEIC, which the server
 * doesn't accept. Every photo is therefore redrawn on the phone at most 2048 px on its long side and
 * saved as a JPEG (usually well under 1 MB). This also drops the photo's hidden metadata, such as the
 * GPS location where it was taken. PDFs and other files are left as they are.
 */
export const MAX_IMAGE_SIDE = 2048;
const JPEG_QUALITY = 0.85;
const WEB_TYPES = ["image/jpeg", "image/png", "image/webp"];
const PASS_THROUGH = ["image/gif", "image/svg+xml"];

export const UNREADABLE_PHOTO =
  "This photo couldn't be opened. Choose a JPEG or PNG photo, or on iPhone set Settings › Camera › Formats › Most Compatible.";

export function isPhoto(file: File): boolean {
  return (file.type.startsWith("image/") && !PASS_THROUGH.includes(file.type)) || /\.(heic|heif)$/i.test(file.name);
}

function canvasAvailable(): boolean {
  try {
    return typeof document !== "undefined" && !!document.createElement("canvas").getContext("2d");
  } catch {
    return false;
  }
}

async function decode(file: File): Promise<{ source: CanvasImageSource; width: number; height: number; done: () => void }> {
  if (typeof createImageBitmap === "function") {
    try {
      const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
      return { source: bitmap, width: bitmap.width, height: bitmap.height, done: () => bitmap.close() };
    } catch {
      // Some browsers can't decode every format with createImageBitmap; try an <img> next.
    }
  }
  const url = URL.createObjectURL(file);
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      const timer = window.setTimeout(() => reject(new Error("timeout")), 15_000);
      img.onload = () => { window.clearTimeout(timer); resolve(img); };
      img.onerror = () => { window.clearTimeout(timer); reject(new Error("decode")); };
      img.src = url;
    });
    return { source: image, width: image.naturalWidth, height: image.naturalHeight, done: () => URL.revokeObjectURL(url) };
  } catch (err) {
    URL.revokeObjectURL(url);
    throw err;
  }
}

/** A JPEG version of the photo, resized for upload; other files are returned unchanged. */
export async function prepareImage(file: File, maxSide = MAX_IMAGE_SIDE): Promise<File> {
  if (!isPhoto(file) || !canvasAvailable()) return file;
  let decoded;
  try {
    decoded = await decode(file);
  } catch {
    if (WEB_TYPES.includes(file.type)) return file; // the server can still take it as it is
    throw new Error(UNREADABLE_PHOTO);
  }
  try {
    const scale = Math.min(1, maxSide / Math.max(decoded.width, decoded.height));
    const width = Math.max(1, Math.round(decoded.width * scale));
    const height = Math.max(1, Math.round(decoded.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.fillStyle = "#ffffff"; // JPEG has no transparency: transparent areas become white, not black
    context.fillRect(0, 0, width, height);
    context.drawImage(decoded.source, 0, 0, width, height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY));
    if (!blob) {
      if (WEB_TYPES.includes(file.type)) return file;
      throw new Error(UNREADABLE_PHOTO);
    }
    const name = (file.name || "photo").replace(/\.[^./]+$/, "") + ".jpg";
    return new File([blob], name, { type: "image/jpeg", lastModified: Date.now() });
  } finally {
    decoded.done();
  }
}

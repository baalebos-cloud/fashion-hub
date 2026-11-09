import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { uploadFile } from "@/lib/storage/file-storage";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

/**
 * A live selfie taken with the front camera inside the page: the person sees themselves, taps Capture,
 * and can retake. There is deliberately no "choose a photo" option, so the selfie is taken now rather
 * than picked from the gallery. Tailora compares it, and the profile photo, with the photo on the NIN
 * record. Uploaded privately, like the ID document.
 *
 * Works on phones (Safari, Chrome, and inside the iPhone/Android apps, which declare camera access)
 * and on computers with a webcam. If no camera can be used, it says why and how to fix it.
 */
const MAX_SIDE = 1280;

function cameraProblem(err: unknown): string {
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError" || name === "SecurityError")
    return "Camera access is blocked. Allow the camera for Tailora in your browser or phone settings, then try again.";
  if (name === "NotFoundError" || name === "OverconstrainedError")
    return "No camera was found on this device. Use a phone or a computer with a webcam.";
  if (name === "NotReadableError") return "The camera is being used by another app. Close it and try again.";
  return "The camera couldn't be started. Try again, or use your phone.";
}

export function SelfieCapture({ onUploaded }: { onUploaded: (storageKey: string | null) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  // False once the component is gone, so a camera that turns on afterwards is switched straight off.
  const mounted = useRef(true);
  const [cameraOn, setCameraOn] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraOn(false);
  }

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, []);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  async function startCamera() {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("This browser can't use the camera. Open Tailora in Chrome or Safari, or use the app.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 960 } }, audio: false });
      if (!mounted.current) {
        // They left while the permission prompt was open: don't leave the camera running.
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      setCameraOn(true);
      // The <video> is rendered once cameraOn is true; attach on the next frame.
      requestAnimationFrame(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          void videoRef.current.play().catch(() => {});
        }
      });
    } catch (err) {
      if (mounted.current) setError(cameraProblem(err));
    }
  }

  async function capture() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    setBusy(true);
    setError(null);
    onUploaded(null);
    try {
      const scale = Math.min(1, MAX_SIDE / Math.max(video.videoWidth, video.videoHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      const context = canvas.getContext("2d");
      if (!context) throw new Error("The selfie couldn't be captured. Try again.");
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
      if (!blob) throw new Error("The selfie couldn't be captured. Try again.");
      const photo = new File([blob], "selfie.jpg", { type: "image/jpeg" });
      stopCamera();
      const { url } = await uploadFile("/media/upload?purpose=kyc", photo);
      setPreview(URL.createObjectURL(photo));
      onUploaded(url);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "The selfie couldn't be uploaded. Try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="text-sm font-medium text-ink">Take a selfie</div>
      <p className="text-xs text-ink-soft">
        Face the camera in good light, no glasses or cap. Tailora checks it matches the photo on your NIN
        record and your profile photo, so nobody else can use your identity.
      </p>
      {cameraOn ? (
        <div className="flex flex-col gap-2">
          <video ref={videoRef} playsInline muted autoPlay aria-label="Camera preview"
            className="aspect-[3/4] w-48 -scale-x-100 rounded-lg border border-line bg-ink object-cover" />
          <div className="flex gap-2">
            <Button type="button" size="sm" isLoading={busy} onClick={() => void capture()}>Capture</Button>
            <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={stopCamera}>Cancel</Button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          {preview && <img src={preview} alt="Your selfie" className="h-20 w-16 rounded-lg border border-line object-cover" />}
          <Button type="button" variant="secondary" size="sm" isLoading={busy} onClick={() => void startCamera()}>
            {preview ? "Retake selfie" : "Take selfie"}
          </Button>
        </div>
      )}
      {error && <p role="alert" className="text-xs text-thread">{error}</p>}
    </div>
  );
}

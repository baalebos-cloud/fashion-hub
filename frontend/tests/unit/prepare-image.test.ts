import { afterEach, describe, expect, it, vi } from "vitest";
import { isPhoto, prepareImage, UNREADABLE_PHOTO } from "@/lib/media/prepare-image";
import { validateImageFile } from "@/lib/utils/image";

const file = (name: string, type: string, size = 10) => new File([new Uint8Array(size)], name, { type });

afterEach(() => vi.restoreAllMocks());

describe("photos before upload", () => {
  it("treats any photo, including iPhone HEIC, as a photo; PDFs and GIFs are left alone", () => {
    expect(isPhoto(file("a.jpg", "image/jpeg"))).toBe(true);
    expect(isPhoto(file("IMG_1.HEIC", "image/heic"))).toBe(true);
    expect(isPhoto(file("IMG_2.heic", ""))).toBe(true); // some pickers send HEIC with no type
    expect(isPhoto(file("slip.pdf", "application/pdf"))).toBe(false);
    expect(isPhoto(file("a.gif", "image/gif"))).toBe(false);
  });

  it("accepts big phone photos and refuses non-photos", () => {
    expect(validateImageFile(file("IMG.HEIC", "image/heic", 12_000_000))).toBeNull();
    expect(validateImageFile(file("a.txt", "text/plain"))).toMatch(/choose a photo/i);
  });

  it("leaves PDFs untouched", async () => {
    const pdf = file("slip.pdf", "application/pdf");
    expect(await prepareImage(pdf)).toBe(pdf);
  });

  it("resizes a large photo to a JPEG at most 2048 px on its long side", async () => {
    const drawn: number[][] = [];
    const context = { fillStyle: "", fillRect: vi.fn(), drawImage: vi.fn((_s, _x, _y, w: number, h: number) => drawn.push([w, h])) };
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(context as unknown as CanvasRenderingContext2D);
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(function (callback) {
      callback(new Blob(["jpeg"], { type: "image/jpeg" }));
    });
    vi.stubGlobal("createImageBitmap", vi.fn(async () => ({ width: 4032, height: 3024, close: vi.fn() })));
    const out = await prepareImage(file("IMG_0001.HEIC", "image/heic", 9_000_000));
    expect(out.type).toBe("image/jpeg");
    expect(out.name).toBe("IMG_0001.jpg");
    expect(drawn).toEqual([[2048, 1536]]);
    vi.unstubAllGlobals();
  });

  it("explains a photo the phone can't open", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
    vi.stubGlobal("createImageBitmap", vi.fn(async () => { throw new Error("bad"); }));
    const image = vi.spyOn(window, "Image").mockImplementation(function (this: HTMLImageElement) {
      setTimeout(() => this.onerror?.(new Event("error")), 0);
      return this;
    } as unknown as () => HTMLImageElement);
    await expect(prepareImage(file("IMG.HEIC", "image/heic"))).rejects.toThrow(UNREADABLE_PHOTO);
    // A JPEG the browser can't redraw is still sent as it is.
    const jpeg = file("a.jpg", "image/jpeg");
    expect(await prepareImage(jpeg)).toBe(jpeg);
    image.mockRestore();
    vi.unstubAllGlobals();
  });
});

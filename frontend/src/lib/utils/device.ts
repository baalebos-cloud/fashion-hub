/** Rough device description from the browser string, for scanning the table. */
export function describeDevice(agent: string | null): string {
  if (!agent) return "Unknown device";
  const os = /iPhone|iPad/.test(agent) ? "iPhone/iPad" : /Android/.test(agent) ? "Android"
    : /Windows/.test(agent) ? "Windows" : /Mac OS X|Macintosh/.test(agent) ? "Mac" : /Linux/.test(agent) ? "Linux" : "Other";
  const browser = /Edg\//.test(agent) ? "Edge" : /OPR\/|Opera/.test(agent) ? "Opera" : /Chrome\//.test(agent) ? "Chrome"
    : /Firefox\//.test(agent) ? "Firefox" : /Safari\//.test(agent) ? "Safari" : "app";
  return `${browser} on ${os}`;
}

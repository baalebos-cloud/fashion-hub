export function VerificationBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-[#e5f3ea] px-2 py-0.5 text-[11px] font-medium text-[#256a3f]">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Verified
    </span>
  );
}

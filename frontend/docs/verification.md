# Verification (KYC/KYB)

`components/verification/KYCForm.tsx` (individuals: customers,
professionals, delivery partners) and `KYBForm.tsx` (businesses: vendors
and professional businesses) submit documents via
`common/DocumentUpload.tsx` -> `lib/storage/file-storage.ts`, which
uploads through the backend — this frontend never talks to object storage
directly and never sees a storage credential.

`VerificationStatus.tsx` reflects whatever status the backend's admin
review produced (`pending -> under_review -> verified/rejected`); there is
no client-side verification logic to speak of, by design — see
`backend/docs/kyc-kyb.md`.

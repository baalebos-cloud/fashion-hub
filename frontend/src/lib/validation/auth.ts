/**
 * Client-side validation is a UX convenience (fail fast, before a round
 * trip) — the backend re-validates everything independently (see
 * backend/app/schemas/auth.py) and is the actual source of truth.
 */
export interface FieldError {
  field: string;
  message: string;
}

export function validateSignUp(values: {
  email: string;
  password: string;
  fullName: string;
}): FieldError[] {
  const errors: FieldError[] = [];

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
    errors.push({ field: "email", message: "Enter a valid email address." });
  }
  if (values.password.length < 8) {
    errors.push({ field: "password", message: "Password must be at least 8 characters." });
  } else if (!/\d/.test(values.password) || !/[a-zA-Z]/.test(values.password)) {
    errors.push({ field: "password", message: "Password must contain a letter and a number." });
  }
  if (values.fullName.trim().length < 2) {
    errors.push({ field: "fullName", message: "Enter your full name." });
  }

  return errors;
}

export function validateLogIn(values: { email: string; password: string }): FieldError[] {
  const errors: FieldError[] = [];
  if (!values.email) errors.push({ field: "email", message: "Email is required." });
  if (!values.password) errors.push({ field: "password", message: "Password is required." });
  return errors;
}
